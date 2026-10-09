#!/usr/bin/env python3
"""
Phase 1 remaining: basket overlap, category-level sequences,
and prepared-food vs broader-grocery comparison.

Batched to stay under memory limits.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS

BATCH_SIZE = 10_000


def load_metadata() -> dict:
    return {
        "products": pd.read_parquet(DATA_PROCESSED / "products.parquet"),
        "aisles": pd.read_parquet(DATA_PROCESSED / "aisles.parquet"),
        "departments": pd.read_parquet(DATA_PROCESSED / "departments.parquet"),
    }


def get_valid_user_ids(min_orders: int = 4) -> list[int]:
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")
    user_counts = (
        orders
        .filter(pl.col("eval_set").is_in(["prior", "train"]))
        .group_by("user_id")
        .agg(pl.col("order_number").max().alias("max_order"))
        .filter(pl.col("max_order") >= min_orders)
    )
    return sorted(user_counts["user_id"].to_list())


def build_basket_overlap_batch(user_ids: list[int]) -> pd.DataFrame:
    """
    For each consecutive order pair per user, compute overlap metrics:
    - shared_products: products in both orders
    - jaccard: |intersection| / |union|
    - pct_retained: fraction of previous order's items that appear again
    """
    orders = (
        pl.read_parquet(DATA_PROCESSED / "orders.parquet")
        .filter(pl.col("user_id").is_in(user_ids))
        .filter(pl.col("eval_set").is_in(["prior", "train"]))
        .select(["order_id", "user_id", "order_number"])
    )

    prior = (
        pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet")
        .select(["order_id", "product_id"])
        .join(orders, on="order_id", how="inner")
    )
    train = (
        pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet")
        .select(["order_id", "product_id"])
        .join(orders, on="order_id", how="inner")
    )
    purchases = pl.concat([prior, train]).sort(["user_id", "order_number"])

    # Group product sets per (user, order)
    baskets = (
        purchases
        .group_by(["user_id", "order_number"])
        .agg(pl.col("product_id").alias("products"))
        .sort(["user_id", "order_number"])
    ).to_pandas()

    rows = []
    for user_id, group in baskets.groupby("user_id"):
        group = group.sort_values("order_number")
        prev_set = None
        for _, row in group.iterrows():
            curr_set = set(row["products"])
            if prev_set is not None:
                shared = len(prev_set & curr_set)
                union = len(prev_set | curr_set)
                rows.append({
                    "user_id": user_id,
                    "order_number": row["order_number"],
                    "prev_basket_size": len(prev_set),
                    "curr_basket_size": len(curr_set),
                    "shared_products": shared,
                    "jaccard": shared / union if union > 0 else 0.0,
                    "pct_retained": shared / len(prev_set) if prev_set else 0.0,
                })
            prev_set = curr_set

    return pd.DataFrame(rows)


def build_category_sequences_batch(
    user_ids: list[int],
    metadata: dict,
    level: str,  # "aisle" or "department"
) -> pd.DataFrame:
    """Build category-level sequences for a batch of users."""
    orders = (
        pl.read_parquet(DATA_PROCESSED / "orders.parquet")
        .filter(pl.col("user_id").is_in(user_ids))
        .filter(pl.col("eval_set").is_in(["prior", "train"]))
        .select(["order_id", "user_id", "order_number"])
    )

    prior = (
        pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet")
        .select(["order_id", "product_id"])
        .join(orders, on="order_id", how="inner")
    )
    train = (
        pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet")
        .select(["order_id", "product_id"])
        .join(orders, on="order_id", how="inner")
    )
    purchases = pl.concat([prior, train])

    # Join with products to get category IDs
    products_pl = pl.from_pandas(metadata["products"])
    purchases = purchases.join(products_pl, on="product_id", how="left")

    cat_id = f"{level}_id"
    cat_name = level

    # Join category names
    if level == "aisle":
        cat_ref = pl.from_pandas(metadata["aisles"])
    else:
        cat_ref = pl.from_pandas(metadata["departments"])
    purchases = purchases.join(cat_ref, on=cat_id, how="left")

    # Deduplicate: one row per (user, order, category)
    cat_orders = (
        purchases
        .select(["user_id", "order_number", cat_id, cat_name])
        .unique(subset=["user_id", "order_number", cat_id])
    ).to_pandas()

    # Group by (user, category)
    seqs = cat_orders.groupby(["user_id", cat_id]).agg({
        "order_number": ["min", "max", "count", list],
        cat_name: "first",
    }).reset_index()

    seqs.columns = [
        "user_id", f"{level}_id",
        "first_order_num", "last_order_num", "total_purchases", "order_numbers",
        level,
    ]

    user_totals = cat_orders.groupby("user_id")["order_number"].max().to_dict()
    seqs["user_total_orders"] = seqs["user_id"].map(user_totals)
    seqs["selection_frequency"] = seqs["total_purchases"] / seqs["user_total_orders"]

    return seqs


def main():
    print("=" * 70)
    print("Phase 1 Remaining: Overlap + Category Sequences")
    print("=" * 70)

    metadata = load_metadata()
    valid_users = get_valid_user_ids(min_orders=4)
    print(f"Processing {len(valid_users):,} users")

    batches = [valid_users[i:i + BATCH_SIZE] for i in range(0, len(valid_users), BATCH_SIZE)]
    print(f"{len(batches)} batches of ~{BATCH_SIZE:,}")

    ANALYSIS_OUTPUTS.mkdir(parents=True, exist_ok=True)

    # --- Basket overlap ---
    print(f"\n[1/3] Basket overlap ({len(batches)} batches)...")
    overlap_parts = []
    for i, batch in enumerate(batches, 1):
        if i % 5 == 1:
            print(f"  Batch {i}/{len(batches)}...")
        overlap_parts.append(build_basket_overlap_batch(batch))

    overlap = pd.concat(overlap_parts, ignore_index=True)
    overlap.to_parquet(ANALYSIS_OUTPUTS / "basket_overlap.parquet", index=False)
    print(f"  Saved {len(overlap):,} order-pair rows")
    print(f"  Mean Jaccard: {overlap['jaccard'].mean():.3f}")
    print(f"  Mean % retained: {overlap['pct_retained'].mean():.3f}")

    del overlap, overlap_parts

    # --- Aisle-level sequences ---
    print(f"\n[2/3] Aisle-level sequences ({len(batches)} batches)...")
    aisle_parts = []
    for i, batch in enumerate(batches, 1):
        if i % 5 == 1:
            print(f"  Batch {i}/{len(batches)}...")
        aisle_parts.append(build_category_sequences_batch(batch, metadata, "aisle"))

    aisle_seqs = pd.concat(aisle_parts, ignore_index=True)
    aisle_seqs.to_parquet(ANALYSIS_OUTPUTS / "aisle_sequences.parquet", index=False)
    print(f"  Saved {len(aisle_seqs):,} user-aisle sequences")

    del aisle_seqs, aisle_parts

    # --- Department-level sequences ---
    print(f"\n[3/3] Department-level sequences ({len(batches)} batches)...")
    dept_parts = []
    for i, batch in enumerate(batches, 1):
        if i % 5 == 1:
            print(f"  Batch {i}/{len(batches)}...")
        dept_parts.append(build_category_sequences_batch(batch, metadata, "department"))

    dept_seqs = pd.concat(dept_parts, ignore_index=True)
    dept_seqs.to_parquet(ANALYSIS_OUTPUTS / "department_sequences.parquet", index=False)
    print(f"  Saved {len(dept_seqs):,} user-department sequences")

    print("\n✓ Phase 1 remaining complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
