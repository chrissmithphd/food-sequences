#!/usr/bin/env python3
"""
The ingredient lens: two views that product-level analysis cannot produce.

1. Top ingredients by ACTUAL PURCHASE VOLUME (not catalog product count).
   Corrects the catalog-size bias: many cracker brands vs one carrot product.

2. Distinct products vs distinct ingredients per customer. Shows how much
   apparent "variety" is really brand multiplicity on a smaller ingredient set.

Pure polars group-bys (no per-user Python loops) -> fast and memory-safe.
"""

import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

SEQ = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
SEQ.mkdir(exist_ok=True)


def main():
    clf_path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
    clf = pl.read_csv(clf_path).select(["product_id", "ingredient", "is_food"])

    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id"]))
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

    purch = (pl.concat([prior, train])
             .join(orders, on="order_id", how="inner")
             .join(clf, on="product_id", how="left")
             .filter((pl.col("is_food") == True) & pl.col("ingredient").is_not_null()
                     & (pl.col("ingredient") != "unclassified")))

    # --- View 1: top ingredients by purchase volume ---
    vol = (purch.group_by("ingredient")
           .agg(pl.len().alias("purchases"))
           .sort("purchases", descending=True)
           .head(20))
    total_purchases = purch.height
    vol = vol.with_columns((pl.col("purchases") / total_purchases * 100).alias("pct"))
    vol.write_csv(SEQ / "top_ingredients_by_volume.csv")
    print("Top 20 ingredients by ACTUAL PURCHASE VOLUME:")
    for r in vol.iter_rows(named=True):
        print(f"  {r['ingredient']:20s} {r['purchases']:>9,}  ({r['pct']:.1f}%)")

    # --- View 2: distinct products vs distinct ingredients per customer ---
    per_cust = (purch.group_by("user_id")
                .agg(pl.col("product_id").n_unique().alias("n_products"),
                     pl.col("ingredient").n_unique().alias("n_ingredients")))
    per_cust = per_cust.with_columns(
        (pl.col("n_products") / pl.col("n_ingredients")).alias("brand_multiplier"))
    per_cust.write_parquet(SEQ / "per_customer_repertoire.parquet")

    med_prod = per_cust.select(pl.col("n_products").median()).item()
    med_ing = per_cust.select(pl.col("n_ingredients").median()).item()
    med_mult = per_cust.select(pl.col("brand_multiplier").median()).item()
    print("\nPer-customer repertoire (medians):")
    print(f"  distinct products:    {med_prod:.0f}")
    print(f"  distinct ingredients: {med_ing:.0f}")
    print(f"  brand multiplier (products/ingredients): {med_mult:.2f}x")

    summary = pl.DataFrame({
        "metric": ["median_distinct_products", "median_distinct_ingredients",
                   "median_brand_multiplier", "total_food_purchases"],
        "value": [med_prod, med_ing, round(med_mult, 3), total_purchases],
    })
    summary.write_csv(SEQ / "ingredient_lens_summary.csv")
    print("\nSaved: top_ingredients_by_volume.csv, per_customer_repertoire.parquet, ingredient_lens_summary.csv")


if __name__ == "__main__":
    main()
