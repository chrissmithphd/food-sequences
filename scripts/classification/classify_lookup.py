#!/usr/bin/env python3
"""
Lookup-table classifier: map products to ingredients by exact product name.

The LLM classification (classify_fabric.py) is the gold reference but costs ~8h
and requires API access. This script captures its output as a deterministic lookup
table: product_name → (ingredient, category, is_food, is_prepared_dish). No regex,
no embeddings, no LLM — just the exact mapping the LLM produced.

For a new dataset with the same or overlapping products, this table resolves every
product whose name appears in the Instacart catalog exactly. Products not in the
table are flagged "unmatched" for manual or LLM classification.

Usage:
    # Build the lookup table from current classification
    python scripts/classification/classify_lookup.py build

    # Apply it to a products table (parquet or csv)
    python scripts/classification/classify_lookup.py apply data/processed/products.parquet

    # Show match statistics without writing
    python scripts/classification/classify_lookup.py stats data/processed/products.parquet
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
CLF_PATH = DATA_DIR / "food_classification.csv"
TAXONOMY_PATH = DATA_DIR / "INGREDIENT_TAXONOMY.md"
LOOKUP_PATH = DATA_DIR / "product_ingredient_lookup.csv"

import re


def taxonomy_map():
    content = TAXONOMY_PATH.read_text()
    out, cur = {}, None
    for line in content.split("\n"):
        if line.startswith("### "):
            cur = line.replace("###", "").strip()
        elif line.startswith("- `") and cur:
            if m := re.match(r"^- `([a-z_]+)`: (.+)$", line):
                out[m.group(1)] = cur
    return out


def build():
    """Build the lookup table from the current classification."""
    clf = pl.read_csv(CLF_PATH)
    tax = taxonomy_map()

    lookup = clf.select([
        "product_id",
        pl.col("product_name").str.strip_chars().alias("product_name"),
        "aisle",
        "department",
        "ingredient",
        pl.col("ingredient").replace_strict(tax, default="Unknown").alias("category"),
        "is_food",
        "is_prepared_dish",
    ]).sort("product_name")

    lookup.write_csv(LOOKUP_PATH)
    n_food = lookup.filter(pl.col("is_food") == True).height
    n_resolved = lookup.filter(
        (pl.col("is_food") == True) & pl.col("ingredient").is_not_null()
        & (pl.col("ingredient") != "unclassified")
    ).height
    print(f"Lookup table: {lookup.height:,} products "
          f"({n_food:,} food, {n_resolved:,} with ingredients)")
    print(f"Saved to {LOOKUP_PATH}")
    return lookup


def apply(products_path: str, write: bool = True):
    """Apply the lookup table to a products file."""
    products_path = Path(products_path)
    if not LOOKUP_PATH.exists():
        print("Lookup table not found — building it first...")
        build()

    lookup = pl.read_csv(LOOKUP_PATH)
    if products_path.suffix == ".parquet":
        products = pl.read_parquet(products_path)
    else:
        products = pl.read_csv(products_path)

    # match by exact product name (case-sensitive, stripped)
    products = products.with_columns(
        pl.col("product_name").str.strip_chars().alias("_name_clean"))
    lookup_slim = lookup.select([
        pl.col("product_name").alias("_name_clean"),
        "ingredient", "category", "is_food", "is_prepared_dish",
    ])

    result = products.join(lookup_slim, on="_name_clean", how="left").drop("_name_clean")
    matched = result.filter(pl.col("ingredient").is_not_null()).height
    total = result.height

    print(f"Products: {total:,}")
    print(f"Matched by exact name: {matched:,} ({matched/total*100:.1f}%)")
    print(f"Unmatched: {total - matched:,} ({(total-matched)/total*100:.1f}%)")

    if write:
        out = products_path.parent / f"{products_path.stem}_classified{products_path.suffix}"
        if out.suffix == ".parquet":
            result.write_parquet(out)
        else:
            result.write_csv(out)
        print(f"Saved to {out}")

    return result


def stats(products_path: str):
    """Show match statistics without writing."""
    apply(products_path, write=False)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "apply":
        if len(sys.argv) < 3:
            print("Usage: classify_lookup.py apply <products_file>")
            sys.exit(1)
        apply(sys.argv[2])
    elif cmd == "stats":
        if len(sys.argv) < 3:
            print("Usage: classify_lookup.py stats <products_file>")
            sys.exit(1)
        stats(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
