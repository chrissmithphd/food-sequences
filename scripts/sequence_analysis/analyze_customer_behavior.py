#!/usr/bin/env python3
"""
Part 9: do customers have consistent behavioral tendencies, or is it noise?

Per-customer measures (users with >=10 orders):
  product_repeat  : share of (non-first) item-events that repeat an earlier product
  ingredient_repeat: same at ingredient grain
  new_ing_rate    : share of items that are a new ingredient (exploration)
  repertoire      : distinct ingredients
  diversity       : distinct ingredients / total item-events
  switch_rate     : within-ingredient consecutive product switches
  n_orders, avg_basket

Tests:
  - split-half stability: correlate each metric between first and second half of history
  - how much is explained by n_orders / basket size (correlations)
  - distribution shape (percentiles) rather than forced clusters

Every metric is per-customer, and each customer's full history lands inside one
user-id burst, so iterating bursts and concatenating per-customer rows is exact.
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from audit_reorder_probability import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"


def per_customer(d):
    """d: (user, order_number, product_id, ingredient) unique. Returns per-user metrics."""
    fp = d.group_by(["user_id", "product_id"]).agg(pl.col("order_number").min().alias("fp"))
    fi = d.group_by(["user_id", "ingredient"]).agg(pl.col("order_number").min().alias("fi"))
    x = d.join(fp, on=["user_id", "product_id"]).join(fi, on=["user_id", "ingredient"])
    x = x.with_columns((pl.col("order_number") > pl.col("fp")).alias("prod_rep"),
                       (pl.col("order_number") > pl.col("fi")).alias("ing_rep"),
                       (pl.col("order_number") == pl.col("fi")).alias("is_new"))
    s = d.sort(["user_id", "ingredient", "order_number"])
    s = s.with_columns(pl.col("product_id").shift(1).over(["user_id", "ingredient"]).alias("prev"))
    sw = (s.filter(pl.col("prev").is_not_null())
          .group_by("user_id").agg((pl.col("product_id") != pl.col("prev")).mean().alias("switch_rate")))
    m = x.group_by("user_id").agg(
        pl.col("prod_rep").mean().alias("product_repeat"),
        pl.col("ing_rep").mean().alias("ingredient_repeat"),
        pl.col("is_new").mean().alias("new_ing_rate"),
        pl.col("ingredient").n_unique().alias("repertoire"),
        pl.len().alias("items"),
        pl.col("order_number").max().alias("n_orders"))
    m = m.with_columns((pl.col("repertoire") / pl.col("items")).alias("diversity"),
                       (pl.col("items") / pl.col("n_orders")).alias("avg_basket"))
    m = m.join(sw, on="user_id", how="left")
    return m


def main():
    m_parts, h1_parts, h2_parts = [], [], []
    for chunk in iter_events():
        d = chunk.select(["user_id", "order_number", "product_id", "ingredient"]).unique()
        B = d.group_by("user_id").agg(pl.col("order_number").max().alias("B"))

        keep10 = B.filter(pl.col("B") >= 10).select("user_id")
        m_parts.append(per_customer(d.join(keep10, on="user_id")))

        dd = d.join(B.filter(pl.col("B") >= 20), on="user_id").with_columns(
            (pl.col("order_number") > pl.col("B") / 2).alias("sh"))
        cols = ["user_id", "product_repeat", "new_ing_rate", "diversity", "switch_rate"]
        h1_parts.append(per_customer(dd.filter(~pl.col("sh")).drop("B", "sh")).select(cols))
        h2_parts.append(per_customer(dd.filter(pl.col("sh")).drop("B", "sh")).select(cols))

    m = pl.concat(m_parts)
    print(f"Per-customer metrics for {m.height:,} customers (>=10 orders).")
    print("\nDistribution (percentiles):")
    for col in ["product_repeat", "ingredient_repeat", "new_ing_rate", "repertoire", "diversity", "switch_rate", "avg_basket"]:
        q = m.select([pl.col(col).quantile(p).alias(str(p)) for p in [0.1, 0.25, 0.5, 0.75, 0.9]]).row(0)
        print(f"  {col:17s} p10={q[0]:.3f} p25={q[1]:.3f} p50={q[2]:.3f} p75={q[3]:.3f} p90={q[4]:.3f}")

    print("\nCorrelation of each metric with n_orders and avg_basket (is 'type' just volume?):")
    for col in ["product_repeat", "ingredient_repeat", "new_ing_rate", "repertoire", "diversity", "switch_rate"]:
        c_n = m.select(pl.corr("n_orders", col)).item()
        c_b = m.select(pl.corr("avg_basket", col)).item()
        print(f"  {col:17s} corr(n_orders)={c_n:+.3f}  corr(avg_basket)={c_b:+.3f}")

    j = pl.concat(h1_parts).join(pl.concat(h2_parts), on="user_id", suffix="_2").drop_nulls()
    print(f"\nSplit-half stability (users with B>=20, n={j.height:,}): corr(first,second)")
    for col in ["product_repeat", "new_ing_rate", "diversity", "switch_rate"]:
        c = j.select(pl.corr(col, f"{col}_2")).item()
        print(f"  {col:17s} r={c:+.3f}")

    m.write_parquet(SEQ / "customer_metrics.parquet")
    print("\nSaved customer_metrics.parquet")


if __name__ == "__main__":
    main()
