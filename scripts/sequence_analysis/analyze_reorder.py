#!/usr/bin/env python3
"""
Part 1.1 + 1.2 audit: correct reorder PROBABILITY (not interval fraction),
with within-order deduplication and a popularity (shuffle-order) baseline.

Definitions (per classification level L in {product_id, ingredient, category, aisle}):
  Event = one (user, order_number, level_value) after deduplicating within order.
  Observable next order exists iff order_number < user's max order (orders are 1..N consecutive).

  P_next        = P(same L appears in order n+1 | event has observable next order)
  P_within_k    = P(same L reappears within n+1..n+k | at least k observable future orders)
  P_eventual    = P(same L reappears at any later order | observable next)   [right-censored]
  old_interval  = P(gap_to_next == 1 | the item was repeated at all)  <-- reproduces buggy immediate_pct

Baseline (destroys temporal order, preserves each customer's basket set & frequencies):
  Under a uniformly random ordering of a customer's B baskets, for a value present
  in b of them, P(next basket has it | current has it) = (b-1)/(B-1).
  Aggregate expected persistence = sum b(b-1)/B  /  sum (B-1)b/B  over (user, value).
  Lift = P_next / expected.  Lift ~ 1 => "loyalty" is just popularity/aggregation.
"""

import sys
from pathlib import Path
import re
from collections import defaultdict
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequences"
SEQ.mkdir(exist_ok=True)
CLF = ROOT / "analysis" / "classification"
TAX = ROOT / "data" / "INGREDIENT_TAXONOMY.md"  # taxonomy is reference data, not analysis

LEVELS = ["product_id", "ingredient", "category", "aisle"]
K_HORIZONS = [2, 3, 5, 10]


def taxonomy_map():
    content = TAX.read_text()
    out, cur = {}, None
    for line in content.split("\n"):
        if line.startswith("### "):
            cur = line.replace("###", "").strip()
        elif line.startswith("- `") and cur:
            if m := re.match(r"^- `([a-z_]+)`: (.+)$", line):
                out[m.group(1)] = cur
    return out


def prepared_dish_ingredients():
    """Ingredient slugs under the taxonomy's 'PREPARED DISHES & MEALS' section.

    This is the authoritative definition of a prepared *dish* (a pre-made meal that
    typically needs warming/cooking) — not the noisy per-product is_prepared_dish
    flag, which also marks snacks, drinks, and condiments.
    """
    content = TAX.read_text()
    out, inside = set(), False
    for line in content.split("\n"):
        if line.startswith("### "):
            inside = "PREPARED DISHES" in line.upper()
        elif inside and (m := re.match(r"^- `([a-z_]+)`:", line)):
            out.add(m.group(1))
    return out


CHUNK_USERS = 20000


def _events_lazy(user_lo=None, user_hi=None):
    """Lazy purchase-event pipeline; food only, one row per (user, order, product).

    Optionally restricted to a user_id range so callers can process in bursts
    rather than materializing the whole ~30M-row table (which, with no swap,
    overruns the 6GB WSL budget once a downstream sort/self-join copies it).
    """
    tax = taxonomy_map()
    prepared = prepared_dish_ingredients()
    clf = (pl.scan_csv(CLF / "food_classification.csv")
           .select(["product_id", "aisle", "department", "ingredient", "is_food"])
           .with_columns(pl.col("ingredient").replace_strict(tax, default="Unknown").alias("category"),
                         pl.col("ingredient").is_in(prepared).alias("is_prepared_dish")))

    orders = (pl.scan_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"])))
    if user_lo is not None:
        orders = orders.filter((pl.col("user_id") >= user_lo) & (pl.col("user_id") <= user_hi))
    orders = orders.select(["order_id", "user_id", "order_number"])

    prior = pl.scan_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.scan_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

    # Excludes non-food products and the 2,807 unclassified food products (~5.6%
    # of the catalog, ~2% of purchase volume) where the LLM declined to assign an
    # ingredient.  All downstream analyses inherit this filter.
    return (pl.concat([prior, train])
            .join(orders, on="order_id", how="inner")
            .join(clf, on="product_id", how="left")
            .filter(pl.col("is_food") == True)
            .filter(pl.col("ingredient").is_not_null() & (pl.col("ingredient") != "unclassified"))
            .with_columns([pl.col("user_id").cast(pl.Int32),
                           pl.col("order_number").cast(pl.Int32),
                           pl.col("product_id").cast(pl.Int32)]))


def _user_bounds():
    o = (pl.scan_parquet(DATA_PROCESSED / "orders.parquet")
         .filter(pl.col("eval_set").is_in(["prior", "train"]))
         .select(pl.col("user_id").min().alias("lo"), pl.col("user_id").max().alias("hi"))
         .collect())
    return int(o["lo"][0]), int(o["hi"][0])


def load_events():
    """Full purchase-event table as one DataFrame (streaming collect, ~1.6GB).

    Safe to hold, but a downstream whole-table sort or self-join can double it and
    overrun memory — for those, iterate with iter_events() instead.
    """
    return _events_lazy().collect(engine="streaming")


def iter_events(chunk_users=CHUNK_USERS):
    """Yield the purchase-event table in user-id bursts.

    Each user's full history lands in a single chunk, so per-user operations
    (dedup, within-(user,value) windows/sorts, per-user aggregation) are exact
    within a chunk; callers accumulate across chunks. Peak memory stays ~1GB.
    """
    lo, hi = _user_bounds()
    start = lo
    while start <= hi:
        end = start + chunk_users - 1
        frame = _events_lazy(start, end).collect(engine="streaming")
        if frame.height:
            yield frame
        start = end + 1


def _user_final_order():
    """Per-customer true final order N (max order_number over ALL prior/train orders,
    not just food-containing orders). Orders are 1..N consecutive, so N is the number
    of baskets the shuffle baseline arranges a value across. Tiny (~206k rows)."""
    return (pl.scan_parquet(DATA_PROCESSED / "orders.parquet")
            .filter(pl.col("eval_set").is_in(["prior", "train"]))
            .group_by("user_id").agg(pl.col("order_number").max().alias("N"))
            .collect())


def level_partials(d, level, finals):
    """Summable component counts for one grain over a single user-id burst.

    Observed next-order reorder and its shuffle baseline are conditioned on the SAME
    event set: an occurrence of a value at order n is "observable" iff n < N (the
    customer's true final order). For each observable occurrence the baseline is the
    exact shuffle expectation (b-1)/(N-1) for a value present in b of N baskets, so
    observed and expected share one denominator (the observable-occurrence count).
    Each (user, value) is whole within a burst, so partials sum across bursts exactly.
    """
    d = (d.select(["user_id", "order_number", level])
         .filter(pl.col(level).is_not_null() & (pl.col(level).cast(pl.Utf8) != "Unknown"))
         .unique()
         .join(finals, on="user_id", how="left"))
    d = d.sort(["user_id", level, "order_number"])
    d = d.with_columns((pl.col("order_number").shift(-1).over(["user_id", level])
                        - pl.col("order_number")).alias("gap"))

    obs = pl.col("order_number") < pl.col("N")                 # has a next order (n+1 .. N)
    p = {"n_obs": d.filter(obs).height,
         "n_gap1": d.filter(obs & (pl.col("gap") == 1).fill_null(False)).height,
         "n_eventual": d.filter(obs & pl.col("gap").is_not_null()).height}
    for k in K_HORIZONS:
        obs_k = (pl.col("N") - pl.col("order_number")) >= k
        p[f"n_obs_{k}"] = d.filter(obs_k).height
        p[f"n_within_{k}"] = d.filter(obs_k & pl.col("gap").is_not_null() & (pl.col("gap") <= k)).height

    # matched baseline: sum over (user,value) of (observable occurrences)*(b-1)/(N-1)
    bc = (d.group_by(["user_id", level])
          .agg(pl.len().alias("b"), pl.col("N").first(),
               (pl.col("order_number") < pl.col("N")).sum().alias("n_obs_uv"))
          .filter(pl.col("N") > 1))
    p["exp_num"] = bc.select(
        (pl.col("n_obs_uv") * (pl.col("b") - 1) / (pl.col("N") - 1)).sum()).item() or 0.0
    return p


def finalize_level(level, p):
    n = p["n_obs"]
    p_next = p["n_gap1"] / n if n else float("nan")
    expected = p["exp_num"] / n if n else float("nan")     # same denominator as observed
    res = {"level": level, "n_events_observable_next": int(n), "p_next": p_next,
           "p_eventual_given_observable": p["n_eventual"] / n if n else float("nan"),
           "expected_p_next_shuffle": expected,
           "lift": p_next / expected if expected else float("nan")}
    for k in K_HORIZONS:
        res[f"p_within_{k}"] = p[f"n_within_{k}"] / p[f"n_obs_{k}"] if p[f"n_obs_{k}"] else float("nan")
    return res


def analyze_level(level, keep=None):
    """Whole-dataset metrics for one grain, computed in memory-safe user-id bursts.

    keep: optional callable applied to each burst frame to restrict the rows.
    """
    finals = _user_final_order()
    acc = defaultdict(float)
    for chunk in iter_events():
        d = chunk if keep is None else keep(chunk)
        for k, v in level_partials(d, level, finals).items():
            acc[k] += v
    return finalize_level(level, acc)


def _validate():
    """Brute-force check: the matched shuffle baseline (b-1)/(N-1) equals the exact
    mean next-order reorder rate over all permutations of a customer's N baskets."""
    from itertools import permutations
    for N, occ in [(4, {1, 2, 4}), (5, {1, 3}), (3, {1, 2, 3})]:
        b = len(occ)
        num = den = 0
        for perm in permutations(range(1, N + 1)):  # perm[i] = value's basket at slot i
            has = [perm[i] in occ for i in range(N)]
            for i in range(N - 1):
                if has[i]:
                    den += 1
                    num += has[i + 1]
        brute = num / den
        formula = (b - 1) / (N - 1)
        assert abs(brute - formula) < 1e-9, f"N={N} occ={occ}: brute {brute} vs formula {formula}"
    return True


def main():
    assert _validate(), "shuffle baseline failed brute-force validation"
    rows = []
    for lvl in LEVELS:
        print(f"=== {lvl} ===")
        r = analyze_level(lvl)
        rows.append(r)
        print(f"  events w/ observable next : {r['n_events_observable_next']:,}")
        print(f"  P(next order)             : {r['p_next']*100:5.1f}%")
        print(f"  P(within 2/3/5/10)        : "
              + " ".join(f"{r[f'p_within_{k}']*100:4.1f}%" for k in K_HORIZONS))
        print(f"  P(eventual|observable)    : {r['p_eventual_given_observable']*100:5.1f}%")
        print(f"  expected P(next) shuffle  : {r['expected_p_next_shuffle']*100:5.1f}%   "
              f"LIFT = {r['lift']:.2f}x")

    pl.DataFrame(rows).write_csv(SEQ / "reorder_probability_audit.csv")
    print(f"\nSaved {SEQ / 'reorder_probability_audit.csv'}")


if __name__ == "__main__":
    main()
