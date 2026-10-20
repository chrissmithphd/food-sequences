#!/usr/bin/env python3
"""
Part 10: calendar time vs order sequence.

orders.parquet has days_since_prior_order (capped at 30). Build a per-(user,order)
cumulative day index, then express ingredient repurchase gaps in DAYS as well as
orders. Does a 5-order gap mean days or months? Do customer cadences differ enough
that "staples/returns" in order-space are really about shopping frequency?

Processes purchases in user-id bursts (iter_events): each user's history is whole
within a burst, so the per-(user,ingredient) gap sort is bounded and only the small
(ogap, dgap) columns accumulate across bursts.
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from audit_reorder_probability import iter_events
from food_sequences.config import DATA_PROCESSED

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"


def main():
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["user_id", "order_number", "days_since_prior_order"])
              .sort(["user_id", "order_number"]))
    orders = orders.with_columns(pl.col("days_since_prior_order").fill_null(0).alias("d"))
    orders = orders.with_columns(pl.col("d").cum_sum().over("user_id").alias("day_idx"))

    cad = orders.group_by("user_id").agg(pl.col("days_since_prior_order").median().alias("med_cadence"))
    print("Customer shopping cadence (median days between orders):")
    for p in [0.1, 0.25, 0.5, 0.75, 0.9]:
        print(f"  p{int(p * 100)}: {cad.select(pl.col('med_cadence').quantile(p)).item():.0f} days")

    day_idx = orders.select(["user_id", "order_number", "day_idx"])

    print("\nStreaming ingredient repurchase gaps (user-id bursts)...")
    parts = []
    for chunk in iter_events():
        d = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
             .join(day_idx, on=["user_id", "order_number"], how="inner")
             .sort(["user_id", "ingredient", "order_number"]))
        d = d.with_columns(
            (pl.col("order_number") - pl.col("order_number").shift(1).over(["user_id", "ingredient"])).alias("ogap"),
            (pl.col("day_idx") - pl.col("day_idx").shift(1).over(["user_id", "ingredient"])).alias("dgap"))
        g = (d.filter(pl.col("ogap").is_not_null())
             .select(pl.col("ogap").cast(pl.Int16), pl.col("dgap").cast(pl.Int16)))
        if g.height:
            parts.append(g)

    rr = pl.concat(parts)

    # Full aggregate over every repurchase gap (no subsampling): day-gap distribution
    # for each order-gap. Computed on all rr.height gaps.
    summary = (rr.group_by("ogap").agg(
        pl.len().alias("n"),
        pl.col("dgap").quantile(0.10).alias("d_p10"),
        pl.col("dgap").quantile(0.25).alias("d_p25"),
        pl.col("dgap").median().alias("d_p50"),
        pl.col("dgap").quantile(0.75).alias("d_p75"),
        pl.col("dgap").quantile(0.90).alias("d_p90"),
    ).sort("ogap"))
    summary.write_csv(SEQ / "calendar_gap_summary.csv")

    print(f"\nIngredient repurchase gaps (n={rr.height:,}):")
    print("  order-gap -> day-gap distribution (median days, p25-p75):")
    for r in summary.filter(pl.col("ogap").is_in([1, 2, 3, 5, 10])).iter_rows(named=True):
        print(f"    {r['ogap']:2d} orders -> median {r['d_p50']:5.1f} days  "
              f"(p25-p75: {r['d_p25']:.0f}-{r['d_p75']:.0f})  [note: daily cap=30/order]")

    g5 = summary.filter(pl.col("ogap") == 5).row(0, named=True)
    print(f"\nA 5-order gap spans anywhere from {g5['d_p10']:.0f} to {g5['d_p90']:.0f} days "
          f"(p10-p90) — order-gaps are NOT a clock.")

    print("\nSaved calendar_gap_summary.csv")


if __name__ == "__main__":
    main()
