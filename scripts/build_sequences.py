#!/usr/bin/env python3
"""
Build customer-product purchase sequences and calculate features.

This script creates the foundational datasets for sequence analysis.
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import DATA_PROCESSED
from food_sequences.sequences import (
    load_data,
    build_full_order_product_table,
    build_product_sequences,
    calculate_sequence_features,
    calculate_basket_variety,
    build_user_order_sequences,
    identify_prepared_food_products,
)


def main():
    print("=" * 70)
    print("Building Purchase Sequences")
    print("=" * 70)

    # Load data
    print("\n[1/6] Loading data...")
    data = load_data()
    print(f"  Loaded {len(data['orders']):,} orders")
    print(f"  Loaded {len(data['products']):,} products")

    # Identify prepared foods
    print("\n[2/6] Identifying prepared food products...")
    prepared_foods = identify_prepared_food_products(data)
    print(f"  Identified {len(prepared_foods):,} prepared food products")

    # Build full table
    print("\n[3/6] Building full order-product table...")
    full = build_full_order_product_table(data)
    print(f"  Built table with {len(full):,} purchase records")
    print(f"  Covers {full['user_id'].nunique():,} users")

    # Build user order sequences
    print("\n[4/6] Building user order sequences...")
    user_orders = build_user_order_sequences(data)
    print(f"  Built sequences for {user_orders['user_id'].nunique():,} users")
    print(f"  Total orders: {len(user_orders):,}")

    # Calculate basket variety
    print("\n[5/6] Calculating basket variety metrics...")
    variety = calculate_basket_variety(full)
    print(f"  Calculated variety for {len(variety):,} orders")

    # Build product sequences
    print("\n[6/6] Building product purchase sequences...")
    sequences = build_product_sequences(full, min_orders=4)
    print(f"  Built {len(sequences):,} user-product sequences")
    print(f"  Covers {sequences['user_id'].nunique():,} users")
    print(f"  Covers {sequences['product_id'].nunique():,} products")

    # Calculate features
    print("\nCalculating sequence features...")
    sequences_with_features = calculate_sequence_features(sequences)

    # Add prepared food flag
    sequences_with_features["is_prepared_food"] = sequences_with_features["product_id"].isin(prepared_foods)

    # Save results
    print("\nSaving results...")
    output_dir = DATA_PROCESSED / "analysis"
    output_dir.mkdir(exist_ok=True)

    sequences_with_features.to_parquet(output_dir / "product_sequences.parquet", index=False)
    user_orders.to_parquet(output_dir / "user_orders.parquet", index=False)
    variety.to_parquet(output_dir / "basket_variety.parquet", index=False)

    print(f"  Saved to {output_dir}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("Summary Statistics")
    print("=" * 70)

    print("\nSequence Features:")
    print(f"  Mean selection frequency: {sequences_with_features['selection_frequency'].mean():.3f}")
    print(f"  Mean max consecutive: {sequences_with_features['max_consecutive'].mean():.1f}")
    print(f"  Mean gap between purchases: {sequences_with_features['mean_gap'].mean():.1f} orders")

    print("\nPrepared Foods:")
    prepared_seqs = sequences_with_features[sequences_with_features["is_prepared_food"]]
    print(f"  {len(prepared_seqs):,} user-prepared-food sequences")
    print(f"  {prepared_seqs['user_id'].nunique():,} users purchase prepared foods")
    print(f"  Mean selection frequency: {prepared_seqs['selection_frequency'].mean():.3f}")

    print("\nBasket Variety:")
    print(f"  Mean products per order: {variety['unique_products'].mean():.1f}")
    print(f"  Mean aisles per order: {variety['unique_aisles'].mean():.1f}")
    print(f"  Mean prepared foods per order: {variety['prepared_food_count'].mean():.1f}")

    print("\n✓ Sequence extraction complete")

    return 0


if __name__ == "__main__":
    sys.exit(main())
