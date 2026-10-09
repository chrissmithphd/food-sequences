#!/usr/bin/env python3
"""
Memory-efficient sequence builder using user batches.

Processes users in chunks to avoid loading entire dataset into memory.
"""

import sys
from pathlib import Path

import pandas as pd
import polars as pl

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS


BATCH_SIZE = 10_000  # Users per batch


def load_metadata() -> dict[str, pd.DataFrame]:
    """Load small reference tables (products, aisles, departments)."""
    return {
        "products": pd.read_parquet(DATA_PROCESSED / "products.parquet"),
        "aisles": pd.read_parquet(DATA_PROCESSED / "aisles.parquet"),
        "departments": pd.read_parquet(DATA_PROCESSED / "departments.parquet"),
    }


def identify_prepared_foods(metadata: dict) -> set[int]:
    """Identify prepared food product IDs."""
    products = metadata["products"]
    aisles = metadata["aisles"]
    departments = metadata["departments"]

    keywords_aisle = [
        "frozen pizza", "frozen meals", "prepared meals",
        "prepared soups salads", "fresh pasta", "hot dogs bacon sausage"
    ]
    keywords_dept = ["frozen", "deli"]

    prepared_aisles = set()
    for kw in keywords_aisle:
        matches = aisles[aisles["aisle"].str.contains(kw, case=False, na=False)]
        prepared_aisles.update(matches["aisle_id"])

    prepared_depts = set()
    for kw in keywords_dept:
        matches = departments[departments["department"].str.contains(kw, case=False, na=False)]
        prepared_depts.update(matches["department_id"])

    prepared = products[
        products["aisle_id"].isin(prepared_aisles) |
        products["department_id"].isin(prepared_depts)
    ]

    return set(prepared["product_id"])


def get_user_batches(min_orders: int = 4) -> list[list[int]]:
    """
    Split users into batches based on order count threshold.

    Returns list of user_id lists, each with BATCH_SIZE users.
    """
    print(f"  Loading orders to identify users with >={min_orders} orders...")

    # Use Polars for fast filtering
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")

    # Count orders per user
    user_counts = (
        orders
        .filter(pl.col("eval_set").is_in(["prior", "train"]))
        .group_by("user_id")
        .agg(pl.col("order_number").max().alias("max_order"))
        .filter(pl.col("max_order") >= min_orders)
    )

    valid_users = sorted(user_counts["user_id"].to_list())
    print(f"  Found {len(valid_users):,} users with >={min_orders} orders")

    # Split into batches
    batches = []
    for i in range(0, len(valid_users), BATCH_SIZE):
        batches.append(valid_users[i:i + BATCH_SIZE])

    print(f"  Split into {len(batches)} batches of ~{BATCH_SIZE:,} users")
    return batches


def process_user_batch(
    user_ids: list[int],
    metadata: dict,
    prepared_foods: set[int]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Process one batch of users.

    Returns: (product_sequences, user_orders, basket_variety)
    """
    # Load only this batch's data using Polars for speed
    orders = (
        pl.read_parquet(DATA_PROCESSED / "orders.parquet")
        .filter(pl.col("user_id").is_in(user_ids))
        .filter(pl.col("eval_set").is_in(["prior", "train"]))
    )

    # Load purchases for these users
    prior = (
        pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet")
        .join(orders.select(["order_id", "user_id"]), on="order_id", how="inner")
    )

    train = (
        pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet")
        .join(orders.select(["order_id", "user_id"]), on="order_id", how="inner")
    )

    purchases = pl.concat([prior, train])

    # Join with orders
    full = purchases.join(orders, on="order_id", how="left")

    # Join with products (convert to Polars)
    products_pl = pl.from_pandas(metadata["products"])
    full = full.join(products_pl, on="product_id", how="left")

    # Join with aisles and departments
    aisles_pl = pl.from_pandas(metadata["aisles"])
    departments_pl = pl.from_pandas(metadata["departments"])
    full = full.join(aisles_pl, on="aisle_id", how="left")
    full = full.join(departments_pl, on="department_id", how="left")

    # Add prepared food flag early to reduce memory
    full = full.with_columns(
        pl.col("product_id").is_in(list(prepared_foods)).alias("is_prepared_food")
    )

    # Convert to pandas for existing functions (could optimize further with Polars)
    full_pd = full.to_pandas()

    # Build product sequences
    sequences = build_product_sequences_batch(full_pd, prepared_foods)

    # Build user orders
    user_orders = build_user_orders_batch(full_pd)

    # Calculate basket variety
    variety = calculate_basket_variety_batch(full_pd)

    return sequences, user_orders, variety


def build_product_sequences_batch(full_data: pd.DataFrame, prepared_foods: set) -> pd.DataFrame:
    """Build product sequences for this batch of users."""
    # Only keep columns we need
    df = full_data[[
        "user_id", "product_id", "product_name", "order_number",
        "aisle", "department", "is_prepared_food"
    ]].copy()

    # Group by user-product
    sequences = df.groupby(["user_id", "product_id"]).agg({
        "order_number": ["min", "max", "count", list],
        "product_name": "first",
        "aisle": "first",
        "department": "first",
        "is_prepared_food": "first",
    }).reset_index()

    sequences.columns = [
        "user_id", "product_id",
        "first_order_num", "last_order_num", "total_purchases", "order_numbers",
        "product_name", "aisle", "department", "is_prepared_food"
    ]

    # Add user total orders
    user_totals = df.groupby("user_id")["order_number"].max().to_dict()
    sequences["user_total_orders"] = sequences["user_id"].map(user_totals)

    # Simple features
    sequences["selection_frequency"] = sequences["total_purchases"] / sequences["user_total_orders"]
    sequences["recency"] = sequences["user_total_orders"] - sequences["last_order_num"]

    # Sequence-shape features (required by task step 1): consecutive runs,
    # intervening-order gaps, recent vs long-term frequency. Looping over tuples
    # is much faster than DataFrame.apply(axis=1) at this row count.
    max_consec, mean_gaps, recent_f, longterm_f = [], [], [], []
    for order_nums, total_orders, sel_freq in zip(
        sequences["order_numbers"], sequences["user_total_orders"], sequences["selection_frequency"]
    ):
        order_nums = sorted(order_nums)

        mc = cur = 1
        for i in range(1, len(order_nums)):
            if order_nums[i] == order_nums[i - 1] + 1:
                cur += 1
                mc = max(mc, cur)
            else:
                cur = 1

        if len(order_nums) > 1:
            total_gap = order_nums[-1] - order_nums[0] - (len(order_nums) - 1)
            mg = total_gap / (len(order_nums) - 1)
        else:
            mg = 0.0

        recent_threshold = total_orders - 5
        recent = sum(1 for o in order_nums if o > recent_threshold)
        longterm = len(order_nums) - recent

        max_consec.append(mc)
        mean_gaps.append(mg)
        recent_f.append(recent / 5 if total_orders >= 5 else sel_freq)
        longterm_f.append(longterm / (total_orders - 5) if total_orders > 5 else 0.0)

    sequences["max_consecutive"] = max_consec
    sequences["mean_gap"] = mean_gaps
    sequences["recent_frequency"] = recent_f
    sequences["longterm_frequency"] = longterm_f

    return sequences


def build_user_orders_batch(full_data: pd.DataFrame) -> pd.DataFrame:
    """Build user order metadata for this batch."""
    orders = full_data[["user_id", "order_id", "order_number", "days_since_prior_order"]].drop_duplicates()
    orders = orders.sort_values(["user_id", "order_number"])

    # Cumulative days
    orders["cumulative_days"] = orders.groupby("user_id")["days_since_prior_order"].cumsum()

    # User total orders
    orders["user_total_orders"] = orders.groupby("user_id")["order_id"].transform("count")

    return orders


def calculate_basket_variety_batch(full_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate basket variety for this batch."""
    variety = full_data.groupby(["user_id", "order_id", "order_number"]).agg({
        "product_id": "nunique",
        "aisle": "nunique",
        "department": "nunique",
        "is_prepared_food": ["sum", "mean"],
    }).reset_index()

    variety.columns = [
        "user_id", "order_id", "order_number",
        "unique_products", "unique_aisles", "unique_departments",
        "prepared_food_count", "prepared_food_ratio"
    ]

    return variety


def main():
    print("=" * 70)
    print("Building Purchase Sequences (Batched)")
    print("=" * 70)

    # Load metadata
    print("\n[1/5] Loading metadata...")
    metadata = load_metadata()
    print(f"  Loaded {len(metadata['products']):,} products")

    # Identify prepared foods
    print("\n[2/5] Identifying prepared foods...")
    prepared_foods = identify_prepared_foods(metadata)
    print(f"  Identified {len(prepared_foods):,} prepared food products")

    # Get user batches
    print("\n[3/5] Planning user batches...")
    user_batches = get_user_batches(min_orders=4)

    # Process batches
    print(f"\n[4/5] Processing {len(user_batches)} batches...")

    output_dir = ANALYSIS_OUTPUTS
    output_dir.mkdir(parents=True, exist_ok=True)

    all_sequences = []
    all_user_orders = []
    all_variety = []

    for i, batch_users in enumerate(user_batches, 1):
        print(f"\n  Batch {i}/{len(user_batches)}: {len(batch_users):,} users")

        sequences, user_orders, variety = process_user_batch(
            batch_users, metadata, prepared_foods
        )

        print(f"    Sequences: {len(sequences):,}")
        print(f"    Orders: {len(user_orders):,}")
        print(f"    Variety: {len(variety):,}")

        all_sequences.append(sequences)
        all_user_orders.append(user_orders)
        all_variety.append(variety)

        # Save checkpoint every 10 batches
        if i % 10 == 0:
            print(f"    Checkpoint: saving {i} batches...")
            pd.concat(all_sequences, ignore_index=True).to_parquet(
                output_dir / "product_sequences_checkpoint.parquet", index=False
            )

    # Combine all batches
    print("\n[5/5] Combining batches...")
    final_sequences = pd.concat(all_sequences, ignore_index=True)
    final_user_orders = pd.concat(all_user_orders, ignore_index=True)
    final_variety = pd.concat(all_variety, ignore_index=True)

    # Save final results
    print("\nSaving final results...")
    final_sequences.to_parquet(output_dir / "product_sequences.parquet", index=False)
    final_user_orders.to_parquet(output_dir / "user_orders.parquet", index=False)
    final_variety.to_parquet(output_dir / "basket_variety.parquet", index=False)

    # Clean up checkpoint
    checkpoint = output_dir / "product_sequences_checkpoint.parquet"
    if checkpoint.exists():
        checkpoint.unlink()

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\nSequences: {len(final_sequences):,}")
    print(f"  Users: {final_sequences['user_id'].nunique():,}")
    print(f"  Products: {final_sequences['product_id'].nunique():,}")
    print(f"  Mean selection frequency: {final_sequences['selection_frequency'].mean():.3f}")

    prepared = final_sequences[final_sequences["is_prepared_food"]]
    print(f"\nPrepared foods: {len(prepared):,} sequences")
    print(f"  Users: {prepared['user_id'].nunique():,}")
    print(f"  Mean selection frequency: {prepared['selection_frequency'].mean():.3f}")

    print(f"\nBasket variety: {len(final_variety):,} orders")
    print(f"  Mean products/order: {final_variety['unique_products'].mean():.1f}")
    print(f"  Mean prepared foods/order: {final_variety['prepared_food_count'].mean():.2f}")

    print(f"\n✓ Complete. Output saved to {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
