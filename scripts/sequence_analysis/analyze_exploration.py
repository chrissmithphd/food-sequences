#!/usr/bin/env python3
"""
Part 7: exploration over a customer's observed lifetime.

- reactivation: share of purchases that revive an ingredient dormant >=5 / >=10 orders
- within-order diversity vs order position
- per-customer first-half vs second-half new-ingredient rate (does everyone slow?)

(Repertoire growth by order position — the percentile bands — lives in
analyze_novelty_extended.py, which computes it on the reached-subset. It used to be
duplicated here with a biased per-position mean; that duplicate was removed.)

Everything is per-customer, and each customer's full history lands in one user-id
burst, so iterating bursts and accumulating per-customer / per-position rows is exact.
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "novelty"


def main():
    div_parts, rec_parts, half_parts = [], [], []

    for chunk in iter_events():
        d = chunk.select(["user_id", "order_number", "ingredient"]).unique()

        # first-seen order for each (user, ingredient), used by the second-half block
        first = d.group_by(["user_id", "ingredient"]).agg(pl.col("order_number").min().alias("fo"))

        # reactivation: gap since previous occurrence of same (user, ingredient)
        d2 = d.sort(["user_id", "ingredient", "order_number"]).with_columns(
            (pl.col("order_number") - pl.col("order_number").shift(1).over(["user_id", "ingredient"])).alias("gap"))
        rec_parts.append(d2.filter(pl.col("gap").is_not_null()).select(pl.col("gap").cast(pl.Int16)))

        # within-order ingredient diversity by position
        div_parts.append(chunk.group_by(["user_id", "order_number"])
                         .agg(pl.col("ingredient").n_unique().alias("distinct"))
                         .group_by("order_number").agg(
                             pl.col("distinct").sum().alias("sum_distinct"), pl.len().alias("n")))

        # per-customer first vs second half new-ingredient rate (B>=20)
        B = d.group_by("user_id").agg(pl.col("order_number").max().alias("B"))
        dd = (d.join(B.filter(pl.col("B") >= 20), on="user_id")
              .join(first, on=["user_id", "ingredient"])
              .with_columns((pl.col("order_number") == pl.col("fo")).alias("is_new"),
                            (pl.col("order_number") > pl.col("B") / 2).alias("second_half")))
        half_parts.append(dd.group_by(["user_id", "second_half"]).agg(
            pl.col("is_new").mean().alias("new_rate")))

    rec = pl.concat(rec_parts)
    for thr in [5, 10]:
        share = rec.select((pl.col("gap") >= thr).mean()).item()
        print(f"Reactivations: {share*100:.1f}% of ingredient-repurchases revive an item dormant >={thr} orders")

    div = (pl.concat(div_parts).group_by("order_number").agg(
        pl.col("sum_distinct").sum(), pl.col("n").sum())
        .with_columns((pl.col("sum_distinct") / pl.col("n")).alias("mean_distinct")).sort("order_number"))
    div.select(["order_number", "mean_distinct", "n"]).write_csv(SEQ / "order_diversity.csv")
    print("\nMean distinct ingredients per order, by position:")
    for r in div.filter(pl.col("order_number").is_in([1, 2, 5, 10, 20, 50])).iter_rows(named=True):
        print(f"  order {r['order_number']:>3}: {r['mean_distinct']:.1f} distinct ingredients")

    piv = (pl.concat(half_parts).pivot(values="new_rate", index="user_id", on="second_half")
           .rename({"false": "first_half", "true": "second_half"}).drop_nulls())
    corr = piv.select(pl.corr("first_half", "second_half")).item()
    mf, ms = piv["first_half"].mean(), piv["second_half"].mean()
    print(f"\nPer-customer new-ingredient rate (users with B>=20): first half {mf*100:.1f}% -> second half {ms*100:.1f}%")
    print(f"  correlation(first,second) = {corr:.3f}")
    print(f"  customers slowing down (second<first): {piv.select((pl.col('second_half')<pl.col('first_half')).mean()).item()*100:.1f}%")

    print("\nSaved order_diversity.csv")


if __name__ == "__main__":
    main()
