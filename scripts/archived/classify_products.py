#!/usr/bin/env python3
"""
Classify every product into a recipe-ingredient group — single pass, seconds.

Uses src/food_sequences/food_classifier.py: a list of common recipe-ingredient
groups applied by identify-then-group rules (name decides; aisle/department only
set food-vs-non-food scope). Writes the canonical mapping + a random review sample.
"""
import sys
from pathlib import Path
import pandas as pd, polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS
from food_sequences.food_classifier import build, CLASSIFIER_VERSION


def main():
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    departments = pd.read_parquet(DATA_PROCESSED / "departments.parquet")
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["product_id"])
    vol = pl.concat([prior, train]).group_by("product_id").len().rename({"len": "n"}).to_pandas()

    df = build(products, aisles, departments, volume=vol)
    ANALYSIS_OUTPUTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(ANALYSIS_OUTPUTS / "food_mapping.csv", index=False)

    total = df["purchase_count"].sum()
    res = df[df.status == "resolved"]; oos = df[df.status == "out_of_scope"]; un = df[df.status == "unresolved"]
    print(f"food_mapping.csv ({CLASSIFIER_VERSION}): {len(df):,} products, {res['cluster'].nunique()} groups")
    print(f"  resolved {len(res):,} ({res.purchase_count.sum()/total*100:.1f}% of volume) | "
          f"out_of_scope {len(oos):,} ({oos.purchase_count.sum()/total*100:.1f}%) | "
          f"unresolved {len(un):,} ({un.purchase_count.sum()/total*100:.1f}%)")
    print("\n  top groups by volume:")
    for (fam, cl), v in res.groupby(["role_family", "cluster"]).purchase_count.sum().sort_values(ascending=False).head(15).items():
        print(f"    {v/total*100:5.2f}%  {cl}  [{fam}]")

    df.sample(n=40, random_state=0)[["product_id", "original_name", "aisle", "cluster",
        "role_family", "status", "confidence"]].to_csv(ANALYSIS_OUTPUTS / "food_mapping_review_sample.csv", index=False)
    print("\n  wrote food_mapping.csv + food_mapping_review_sample.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
