#!/usr/bin/env python3
"""
Part 1.3 audit of the ingredient-level pattern classification.

Reproduces analyze_patterns.py's rules vectorized in polars, then stress-tests:
  - threshold sensitivity of "return after break" (gap >= t for t in 3..10)
  - pattern prevalence stratified by customer history length
  - multi-match: how many pairs satisfy >1 rule before precedence is applied
  - once-only ingredients excluded (share) and effect on denominators
  - prevalence by (customer,ingredient) PAIR vs by CUSTOMER
  - random-placement baseline: expected prevalence if each (user,ingredient)'s
    b purchases were scattered at random over the user's B orders
Full dataset; Monte-Carlo baseline on a large sample.
"""
import sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from audit_reorder_probability import load_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"
MIN_ORDERS = 10
RETURN_T = 5


def features(purch):
    """One row per (user, ingredient) with classification features. Users w/ >=10 orders."""
    umax = purch.group_by("user_id").agg(pl.col("order_number").max().alias("B"))
    umax = umax.filter(pl.col("B") >= MIN_ORDERS)
    d = (purch.join(umax, on="user_id", how="inner")
         .select(["user_id", "ingredient", "order_number", "B"]).unique()
         .sort(["user_id", "ingredient", "order_number"]))

    # consecutive-run id within (user, ingredient)
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
    f = f.join(max_consec, on=["user_id", "ingredient"], how="left")
    return f


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
        burst.alias("m_burst"), rot.alias("m_rotation"),
    )


def prevalence(c, col="pattern"):
    return (c.group_by(col).agg(pl.len().alias("n"))
            .with_columns((pl.col("n") / c.height * 100).alias("pct")).sort("n", descending=True))


def main():
    purch = load_events()

    # once-only ingredients (excluded from the 2+ analysis)
    pairs_all = purch.group_by(["user_id", "ingredient"]).agg(pl.len().alias("n"))
    # restrict to >=10-order users to match
    umax = purch.group_by("user_id").agg(pl.col("order_number").max().alias("B")).filter(pl.col("B") >= MIN_ORDERS)
    pairs_all = pairs_all.join(umax.select("user_id"), on="user_id", how="inner")
    once = pairs_all.filter(pl.col("n") == 1).height
    multi = pairs_all.filter(pl.col("n") >= 2).height
    print(f"(>=10-order users) once-only (user,ingredient) pairs: {once:,} "
          f"({once/(once+multi)*100:.1f}%)  excluded from 2+ analysis")

    f = features(purch).filter(pl.col("n") >= 2)
    c = classify(f)
    print(f"\nPairs classified (n>=2): {c.height:,}")
    print("\nBy (customer,ingredient) PAIR:")
    for r in prevalence(c).iter_rows(named=True):
        print(f"  {r['pattern']:20s} {r['n']:>9,}  {r['pct']:5.1f}%")

    # by customer: a customer counted once per pattern they exhibit (any pair)
    bycust = c.select(["user_id", "pattern"]).unique()
    ncust = c.select("user_id").n_unique()
    print(f"\nBy CUSTOMER (share of {ncust:,} customers exhibiting >=1 pair of pattern):")
    for r in (bycust.group_by("pattern").agg(pl.len().alias("n"))
              .with_columns((pl.col("n")/ncust*100).alias("pct")).sort("n", descending=True).iter_rows(named=True)):
        print(f"  {r['pattern']:20s} {r['n']:>9,}  {r['pct']:5.1f}%")

    # threshold sensitivity for return_after_break
    print("\nReturn-after-break threshold sensitivity (share of pairs):")
    for t in [3, 4, 5, 6, 8, 10]:
        ct = classify(f, return_t=t)
        p = ct.filter(pl.col("pattern") == "return_after_break").height / ct.height * 100
        print(f"  gap>={t:2d}: {p:4.1f}%")

    # multi-match: how many match >1 rule
    mm = c.with_columns((pl.col("m_staple").cast(pl.Int8)+pl.col("m_return").cast(pl.Int8)
                        +pl.col("m_burst").cast(pl.Int8)+pl.col("m_rotation").cast(pl.Int8)).alias("nmatch"))
    dist = mm.group_by("nmatch").agg(pl.len().alias("n")).sort("nmatch")
    print("\nRules matched before precedence (0=falls to irregular):")
    for r in dist.iter_rows(named=True):
        print(f"  {r['nmatch']} rule(s): {r['n']:,} ({r['n']/mm.height*100:.1f}%)")

    # history-length stratification
    print("\nPattern prevalence by history length (B):")
    c2 = c.with_columns(pl.when(pl.col("B")<15).then(pl.lit("10-14"))
                        .when(pl.col("B")<25).then(pl.lit("15-24"))
                        .when(pl.col("B")<50).then(pl.lit("25-49"))
                        .otherwise(pl.lit("50+")).alias("hist"))
    for h in ["10-14","15-24","25-49","50+"]:
        sub = c2.filter(pl.col("hist")==h)
        if sub.height==0: continue
        ret = sub.filter(pl.col("pattern")=="return_after_break").height/sub.height*100
        irr = sub.filter(pl.col("pattern")=="irregular_mixed").height/sub.height*100
        burst = sub.filter(pl.col("pattern")=="burst_then_absence").height/sub.height*100
        stap = sub.filter(pl.col("pattern")=="persistent_staple").height/sub.height*100
        print(f"  B={h:6s} (n={sub.height:>8,}): staple {stap:4.1f}%  return {ret:4.1f}%  burst {burst:4.1f}%  irregular {irr:4.1f}%")

    # burst artifact check: do burst pairs end well before the user's last order?
    b = c.filter(pl.col("pattern")=="burst_then_absence")
    frac_window = b.select(((pl.col("B")-pl.col("last"))>=5).mean()).item()
    print(f"\nBurst pairs whose last purchase is >=5 orders before the user's final order: {frac_window*100:.1f}% "
          f"(high => genuine absence, not just window cutoff)")

    # random-placement baseline (Monte Carlo on a sample)
    print("\nRandom-placement baseline (expected prevalence if purchases scattered at random):")
    samp = f.sample(n=min(300_000, f.height), seed=7).select(["n","B"]).to_numpy().astype(int)
    rng = np.random.default_rng(7)
    cnt = {"persistent_staple":0,"return_after_break":0,"burst_then_absence":0,"regular_rotation":0,"irregular_mixed":0}
    for n, B in samp:
        orders = np.sort(rng.choice(B, size=n, replace=False)) + 1
        gaps = np.diff(orders)
        # max consecutive run
        mc = 1; cur = 1
        for g in gaps:
            if g == 1: cur += 1; mc = max(mc, cur)
            else: cur = 1
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
    for k in ["persistent_staple","regular_rotation","burst_then_absence","return_after_break","irregular_mixed"]:
        print(f"  {k:20s} observed vs random: {prevalence(c).filter(pl.col('pattern')==k)['pct'].to_list()}  "
              f"random={cnt[k]/tot*100:4.1f}%")

    c.select(["user_id","ingredient","pattern","n","B","max_gap","max_consec"]).write_parquet(SEQ/"pattern_audit.parquet")
    print(f"\nSaved {SEQ/'pattern_audit.parquet'}")


if __name__ == "__main__":
    main()
