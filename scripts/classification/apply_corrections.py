#!/usr/bin/env python3
"""
Post-classification taxonomy corrections applied to food_classification.csv.

Re-running the LLM over all 49,688 products is impractical for bounded, well-defined
fixes, so documented rule-based corrections live here (reproducible, idempotent).

Corrections:
  1. condensed_soup split — products labelled `soup` whose name indicates a
     condensed / cream-of cooking base ("Condensed ...", "Cream of ...") are a recipe
     ingredient, not a ready-to-eat prepared dish. Relabel ingredient -> condensed_soup
     and clear is_prepared_dish. Ready-to-eat soups keep `soup`.
"""
from pathlib import Path
import polars as pl

CLF = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"


def main():
    df = pl.read_csv(CLF)
    is_cond = (pl.col("ingredient") == "soup") & pl.col("product_name").str.contains(r"(?i)condensed|cream of")
    n = df.filter(is_cond).height
    df = df.with_columns(
        pl.when(is_cond).then(pl.lit("condensed_soup")).otherwise(pl.col("ingredient")).alias("ingredient"),
        pl.when(is_cond).then(pl.lit(False)).otherwise(pl.col("is_prepared_dish")).alias("is_prepared_dish"))
    df.write_csv(CLF)
    remaining_soup = df.filter(pl.col("ingredient") == "soup").height
    print(f"condensed_soup split: reclassified {n} products soup -> condensed_soup")
    print(f"  soup (ready-to-eat) remaining: {remaining_soup}  condensed_soup: {df.filter(pl.col('ingredient')=='condensed_soup').height}")


if __name__ == "__main__":
    main()
