#!/usr/bin/env python3
"""
Ingredient-level purchase pattern classification, with a frequency-preserving
random baseline.

For users with >=10 orders, each (customer, ingredient) pair with >=2 purchases is
labelled by precedence: persistent_staple (bought in >50% of orders with a run of
3+ consecutive) -> return_after_break (a gap >= RETURN_T orders) -> burst_then_absence
(>=70% of purchases in the first 30% of history) -> regular_rotation (>=3 purchases,
gap CV < 0.5, mean gap 2-5) -> irregular_mixed.

The random-placement baseline scatters each pair's b purchases at random over the
customer's B orders (preserving frequency, destroying order) and re-classifies, to
show which labels are distinctive behavior vs. consequences of frequency and
history length.

Full dataset, memory-safe: per-(customer, ingredient) features are built in user-id
bursts (each customer whole within a burst) and concatenated into one compact frame.
"""
import sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequences"
MIN_ORDERS = 10
RETURN_T = 5

PRETTY = {"persistent_staple": "Persistent Staple", "regular_rotation": "Regular Rotation",
          "burst_then_absence": "Burst then Absence", "return_after_break": "Return after Break",
          "irregular_mixed": "Irregular/Mixed"}


def burst_features(purch):
    """Per-(user, ingredient) features for one burst; users with >=10 orders."""
    umax = purch.group_by("user_id").agg(pl.col("order_number").max().alias("B")).filter(pl.col("B") >= MIN_ORDERS)
    d = (purch.join(umax, on="user_id", how="inner")
         .select(["user_id", "ingredient", "order_number", "B"]).unique()
         .sort(["user_id", "ingredient", "order_number"]))
    prev = pl.col("order_number").shift(1).over(["user_id", "ingredient"])
    d = d.with_columns((pl.col("order_number") - prev).alias("gap"))
    is_break = (pl.col("gap") != 1).fill_null(True)
    d = d.with_columns(is_break.cum_sum().over(["user_id", "ingredient"]).alias("run_id"))
    runs = d.group_by(["user_id", "ingredient", "run_id"]).agg(pl.len().alias("rl"))
    max_consec = runs.group_by(["user_id", "ingredient"]).agg(pl.col("rl").max().alias("max_consec"))
    f = d.group_by(["user_id", "ingredient"]).agg(
        pl.len().alias("n"),
        pl.col("B").first(),
        pl.col("order_number").min().alias("first"),
        pl.col("order_number").max().alias("last"),
        pl.col("gap").max().alias("max_gap"),
        pl.col("gap").mean().alias("gap_mean"),
        pl.col("gap").std().alias("gap_std"),
        (pl.col("order_number") <= pl.max_horizontal(pl.lit(3), (pl.col("B") * 0.3).floor())).sum().alias("early_n"),
    )
    return f.join(max_consec, on=["user_id", "ingredient"], how="left")


def features():
    return pl.concat([burst_features(chunk) for chunk in iter_events()])


def classify(f, return_t=RETURN_T):
    rate = pl.col("n") / pl.col("B")
    staple = (rate > 0.5) & (pl.col("max_consec") >= 3)
    ret = pl.col("max_gap") >= return_t
    burst = (pl.col("early_n") >= 0.7 * pl.col("n")) & (pl.col("n") >= 3)
    gap_cv = pl.col("gap_std") / pl.col("gap_mean")
    rot = ((pl.col("n") - 1) >= 2) & (gap_cv < 0.5) & (pl.col("gap_mean") >= 2) & (pl.col("gap_mean") <= 5)
    return f.with_columns(
        pl.when(staple).then(pl.lit("persistent_staple"))
        .when(ret).then(pl.lit("return_after_break"))
        .when(burst).then(pl.lit("burst_then_absence"))
        .when(rot).then(pl.lit("regular_rotation"))
        .otherwise(pl.lit("irregular_mixed")).alias("pattern"),
        staple.alias("m_staple"), ret.alias("m_return"),
        burst.alias("m_burst"), rot.alias("m_rotation"))


def prevalence(c, col="pattern"):
    return (c.group_by(col).agg(pl.len().alias("n"))
            .with_columns((pl.col("n") / c.height * 100).alias("pct")).sort("n", descending=True))


def main():
    f_all = features()

    once = f_all.filter(pl.col("n") == 1).height
    multi = f_all.filter(pl.col("n") >= 2).height
    print(f"(>=10-order users) once-only (user,ingredient) pairs: {once:,} "
          f"({once/(once+multi)*100:.1f}%)  excluded from 2+ analysis")

    f = f_all.filter(pl.col("n") >= 2)
    c = classify(f)
    print(f"\nPairs classified (n>=2): {c.height:,}")
    print("\nBy (customer,ingredient) PAIR:")
    for r in prevalence(c).iter_rows(named=True):
        print(f"  {r['pattern']:20s} {r['n']:>9,}  {r['pct']:5.1f}%")

    bycust = c.select(["user_id", "pattern"]).unique()
    ncust = c.select("user_id").n_unique()
    print(f"\nBy CUSTOMER (share of {ncust:,} customers exhibiting >=1 pair of pattern):")
    for r in (bycust.group_by("pattern").agg(pl.len().alias("n"))
              .with_columns((pl.col("n")/ncust*100).alias("pct")).sort("n", descending=True).iter_rows(named=True)):
        print(f"  {r['pattern']:20s} {r['n']:>9,}  {r['pct']:5.1f}%")

    print("\nReturn-after-break threshold sensitivity (share of pairs):")
    for t in [3, 4, 5, 6, 8, 10]:
        ct = classify(f, return_t=t)
        p = ct.filter(pl.col("pattern") == "return_after_break").height / ct.height * 100
        print(f"  gap>={t:2d}: {p:4.1f}%")

    mm = c.with_columns((pl.col("m_staple").cast(pl.Int8)+pl.col("m_return").cast(pl.Int8)
                        +pl.col("m_burst").cast(pl.Int8)+pl.col("m_rotation").cast(pl.Int8)).alias("nmatch"))
    print("\nRules matched before precedence (0=falls to irregular):")
    for r in mm.group_by("nmatch").agg(pl.len().alias("n")).sort("nmatch").iter_rows(named=True):
        print(f"  {r['nmatch']} rule(s): {r['n']:,} ({r['n']/mm.height*100:.1f}%)")

    print("\nPattern prevalence by history length (B):")
    c2 = c.with_columns(pl.when(pl.col("B")<15).then(pl.lit("10-14"))
                        .when(pl.col("B")<25).then(pl.lit("15-24"))
                        .when(pl.col("B")<50).then(pl.lit("25-49"))
                        .otherwise(pl.lit("50+")).alias("hist"))
    for h in ["10-14", "15-24", "25-49", "50+"]:
        sub = c2.filter(pl.col("hist") == h)
        if sub.height == 0:
            continue
        def sh(pat):
            return sub.filter(pl.col("pattern") == pat).height / sub.height * 100
        print(f"  B={h:6s} (n={sub.height:>8,}): staple {sh('persistent_staple'):4.1f}%  "
              f"return {sh('return_after_break'):4.1f}%  burst {sh('burst_then_absence'):4.1f}%  "
              f"irregular {sh('irregular_mixed'):4.1f}%")

    b = c.filter(pl.col("pattern") == "burst_then_absence")
    frac_window = b.select(((pl.col("B")-pl.col("last")) >= 5).mean()).item()
    print(f"\nBurst pairs whose last purchase is >=5 orders before the user's final order: {frac_window*100:.1f}% "
          f"(high => genuine absence, not just window cutoff)")

    print("\nRandom-placement baseline (expected prevalence if purchases scattered at random):")
    samp = f.sample(n=min(300_000, f.height), seed=7).select(["n", "B"]).to_numpy().astype(int)
    rng = np.random.default_rng(7)
    cnt = {k: 0 for k in PRETTY}
    for n, B in samp:
        orders = np.sort(rng.choice(B, size=n, replace=False)) + 1
        gaps = np.diff(orders)
        mc = cur = 1
        for g in gaps:
            if g == 1:
                cur += 1; mc = max(mc, cur)
            else:
                cur = 1
        rate = n / B
        early_cut = max(3, int(B*0.3)); early = int((orders <= early_cut).sum())
        max_gap = int(gaps.max()) if len(gaps) else 0
        gm = gaps.mean() if len(gaps) else 0; gs = gaps.std() if len(gaps) else 0
        if rate > 0.5 and mc >= 3: p = "persistent_staple"
        elif max_gap >= RETURN_T: p = "return_after_break"
        elif early >= 0.7*n and n >= 3: p = "burst_then_absence"
        elif len(gaps) >= 2 and gm and gs/gm < 0.5 and 2 <= gm <= 5: p = "regular_rotation"
        else: p = "irregular_mixed"
        cnt[p] += 1
    tot = len(samp)
    obs = {r["pattern"]: r["pct"] for r in prevalence(c).iter_rows(named=True)}
    for k in ["persistent_staple", "regular_rotation", "burst_then_absence", "return_after_break", "irregular_mixed"]:
        print(f"  {k:20s} observed {obs.get(k,0):4.1f}%  random {cnt[k]/tot*100:4.1f}%")

    # aggregate distribution (committed) + per-pair detail (user-level, gitignored)
    dist = prevalence(c)
    order = ["persistent_staple", "regular_rotation", "burst_then_absence", "return_after_break", "irregular_mixed"]
    pct = {r["pattern"]: (r["n"], r["pct"]) for r in dist.iter_rows(named=True)}
    pl.DataFrame([{"pattern": PRETTY[k], "count": pct.get(k, (0, 0))[0], "percentage": pct.get(k, (0, 0))[1]}
                 for k in order]).write_csv(SEQ / "pattern_distribution.csv")
    c.select(["user_id", "ingredient", "pattern", "n", "B", "max_gap", "max_consec"]).write_parquet(SEQ / "pattern_audit.parquet")
    print(f"\nSaved pattern_distribution.csv, pattern_audit.parquet")


if __name__ == "__main__":
    main()
