#!/usr/bin/env python3
"""
Part 8: ingredient co-occurrence within the same order (NOT the same recipe).

support(a,b) = orders containing both; expected under independence = P(a)P(b).
lift = P(a,b)/(P(a)P(b)). Popular-staple pairs have high support but lift ~1;
distinctive pairs have high lift. All observed ingredients are included; pairs are
reported down to a minimum support so rare-but-real pairings are not discarded.
"""
import sys
from pathlib import Path
from collections import Counter
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "basket"

MIN_SUPPORT = 500


def main():
    print("Pass 1/2: ingredient order-frequencies...")
    ing_orders = Counter()
    n_orders = 0
    for chunk in iter_events():
        oi = chunk.select(["user_id", "order_number", "ingredient"]).unique()
        n_orders += oi.select(["user_id", "order_number"]).unique().height
        for ing, c in oi.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            ing_orders[ing] += c
    pmap = {ing: c / n_orders for ing, c in ing_orders.items()}
    print(f"  orders={n_orders:,}  distinct ingredients={len(ing_orders):,} (all included)")

    print("Pass 2/2: within-order co-occurrence pairs (all ingredients)...")
    pair = Counter()
    for chunk in iter_events():
        oi = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
              .with_columns((pl.col("user_id").cast(pl.Int64) * 100000 + pl.col("order_number")).alias("oid"))
              .select(["oid", "ingredient"]))
        a = oi.rename({"ingredient": "a"})
        b = oi.rename({"ingredient": "b"})
        pairs = a.join(b, on="oid").filter(pl.col("a") < pl.col("b"))
        for ar, br, c in pairs.group_by(["a", "b"]).agg(pl.len().alias("c")).iter_rows():
            pair[(ar, br)] += c

    rows = [{"a": a, "b": b, "co": c} for (a, b), c in pair.items() if c >= MIN_SUPPORT]
    co = pl.DataFrame(rows, schema={"a": pl.Utf8, "b": pl.Utf8, "co": pl.Int64})
    co = co.with_columns(
        (pl.col("co") / n_orders).alias("p_ab"),
        pl.col("a").replace_strict(pmap, default=None).alias("pa"),
        pl.col("b").replace_strict(pmap, default=None).alias("pb"))
    co = co.with_columns((pl.col("p_ab") / (pl.col("pa") * pl.col("pb"))).alias("lift"))

    print(f"\nOrders: {n_orders:,}. Pairs with support>={MIN_SUPPORT}: {co.height:,}")
    print("\nTop 15 ingredient pairs by LIFT (distinctive combinations):")
    for r in co.sort("lift", descending=True).head(15).iter_rows(named=True):
        print(f"  {r['a']:16s} + {r['b']:16s} lift={r['lift']:5.1f}  support={r['co']:,}")
    print("\nTop 10 pairs by SUPPORT (popular — note low lift = just common staples):")
    for r in co.sort("co", descending=True).head(10).iter_rows(named=True):
        print(f"  {r['a']:16s} + {r['b']:16s} support={r['co']:,}  lift={r['lift']:.2f}")

    co.sort("lift", descending=True).write_csv(SEQ / "cooccurrence_pairs.csv")
    print("\nSaved cooccurrence_pairs.csv")


if __name__ == "__main__":
    main()
