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

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"
SEQ.mkdir(exist_ok=True)
CLF = ROOT / "analysis" / "classification"

LEVELS = ["product_id", "ingredient", "category", "aisle"]
K_HORIZONS = [2, 3, 5, 10]


def taxonomy_map():
    content = (CLF / "INGREDIENT_TAXONOMY.md").read_text()
    out, cur = {}, None
    for line in content.split("\n"):
        if line.startswith("### "):
            cur = line.replace("###", "").strip()
        elif line.startswith("- `") and cur:
            if m := re.match(r"^- `([a-z_]+)`: (.+)$", line):
                out[m.group(1)] = cur
    return out


CHUNK_USERS = 20000


def _events_lazy(user_lo=None, user_hi=None):
    """Lazy purchase-event pipeline; food only, one row per (user, order, product).

    Optionally restricted to a user_id range so callers can process in bursts
    rather than materializing the whole ~30M-row table (which, with no swap,
    overruns the 6GB WSL budget once a downstream sort/self-join copies it).
    """
    tax = taxonomy_map()
    clf = (pl.scan_csv(CLF / "food_classification.csv")
           .select(["product_id", "aisle", "ingredient", "is_food", "is_prepared_dish"])
           .with_columns(pl.col("ingredient").replace_strict(tax, default="Unknown").alias("category")))

    orders = (pl.scan_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"])))
    if user_lo is not None:
        orders = orders.filter((pl.col("user_id") >= user_lo) & (pl.col("user_id") <= user_hi))
    orders = orders.select(["order_id", "user_id", "order_number"])

    prior = pl.scan_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.scan_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

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


def level_partials(d, level):
    """Summable component counts for one grain over a single user-id burst.

    Each (user, value) is whole within a burst, so these partials sum across bursts
    to the exact whole-dataset metrics (next-order probability, horizons, eventual,
    old interval fraction, and the shuffle-baseline numerator/denominator).
    """
    d = (d.select(["user_id", "order_number", level])
         .filter(pl.col(level).is_not_null() & (pl.col(level).cast(pl.Utf8) != "Unknown"))
         .unique())
    umax = d.group_by("user_id").agg(pl.col("order_number").max().alias("umax"))
    d = d.join(umax, on="user_id", how="left").sort(["user_id", level, "order_number"])
    d = d.with_columns(pl.col("order_number").shift(-1).over(["user_id", level]).alias("next_occ"))
    d = d.with_columns((pl.col("next_occ") - pl.col("order_number")).alias("gap"))

    observable = pl.col("order_number") < pl.col("umax")
    p = {"n_obs": d.filter(observable).height,
         "n_gap1": d.filter(observable & (pl.col("gap") == 1).fill_null(False)).height,
         "n_eventual": d.filter(observable & pl.col("gap").is_not_null()).height,
         "n_repeated": d.filter(pl.col("gap").is_not_null()).height,
         "n_rep_gap1": d.filter(pl.col("gap").is_not_null() & (pl.col("gap") == 1)).height}
    for k in K_HORIZONS:
        obs_k = (pl.col("umax") - pl.col("order_number")) >= k
        p[f"n_obs_{k}"] = d.filter(obs_k).height
        p[f"n_within_{k}"] = d.filter(obs_k & pl.col("gap").is_not_null() & (pl.col("gap") <= k)).height

    bc = (d.group_by(["user_id", level])
          .agg(pl.len().alias("b"), pl.col("umax").first().alias("B"))
          .filter(pl.col("B") > 1))
    agg = bc.select((pl.col("b") * (pl.col("b") - 1) / pl.col("B")).sum().alias("num"),
                    ((pl.col("B") - 1) * pl.col("b") / pl.col("B")).sum().alias("den"))
    p["exp_num"] = agg["num"][0] or 0.0
    p["exp_den"] = agg["den"][0] or 0.0
    return p


def finalize_level(level, p):
    n = p["n_obs"]
    p_next = p["n_gap1"] / n if n else float("nan")
    expected = p["exp_num"] / p["exp_den"] if p["exp_den"] else float("nan")
    res = {"level": level, "n_events_observable_next": int(n), "p_next": p_next,
           "p_eventual_given_observable": p["n_eventual"] / n if n else float("nan"),
           "old_interval_immediate_frac": p["n_rep_gap1"] / p["n_repeated"] if p["n_repeated"] else float("nan"),
           "expected_p_next_shuffle": expected,
           "lift": p_next / expected if expected else float("nan")}
    for k in K_HORIZONS:
        res[f"p_within_{k}"] = p[f"n_within_{k}"] / p[f"n_obs_{k}"] if p[f"n_obs_{k}"] else float("nan")
    return res


def analyze_level(level, keep=None):
    """Whole-dataset metrics for one grain, computed in memory-safe user-id bursts.

    keep: optional callable applied to each burst frame to restrict the rows
    (e.g. a prepared-dish filter, or a per-(customer, ingredient) product-count
    filter). None processes all events.
    """
    acc = defaultdict(float)
    for chunk in iter_events():
        d = chunk if keep is None else keep(chunk)
        for k, v in level_partials(d, level).items():
            acc[k] += v
    return finalize_level(level, acc)


def main():
    rows = []
    for lvl in LEVELS:
        print(f"=== {lvl} ===")
        r = analyze_level(lvl)
        rows.append(r)
        print(f"  events w/ observable next : {r['n_events_observable_next']:,}")
        print(f"  P(next order)             : {r['p_next']*100:5.1f}%   "
              f"[old interval metric: {r['old_interval_immediate_frac']*100:5.1f}%]")
        print(f"  P(within 2/3/5/10)        : "
              + " ".join(f"{r[f'p_within_{k}']*100:4.1f}%" for k in K_HORIZONS))
        print(f"  P(eventual|observable)    : {r['p_eventual_given_observable']*100:5.1f}%")
        print(f"  expected P(next) shuffle  : {r['expected_p_next_shuffle']*100:5.1f}%   "
              f"LIFT = {r['lift']:.2f}x")

    pl.DataFrame(rows).write_csv(SEQ / "reorder_probability_audit.csv")
    print(f"\nSaved {SEQ / 'reorder_probability_audit.csv'}")


if __name__ == "__main__":
    main()
