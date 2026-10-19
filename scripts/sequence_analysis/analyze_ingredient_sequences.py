#!/usr/bin/env python3
"""
Ingredient-based sequence analysis using LLM classifications.

Analyzes customer purchasing patterns at multiple levels:
- Exact product (SKU)
- Recipe ingredient (e.g., milk regardless of brand)
- Ingredient category (e.g., DAIRY)

Computes reorder probabilities, repeat intervals, and sequence patterns
using the full customer order history joined to ingredient classifications.

Output: analysis/sequence_analysis/ directory with figures and statistics.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS

# Output directory
SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
SEQ_ANALYSIS_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 10_000
MIN_ORDERS = 4


def load_classifications():
    """Load ingredient classifications."""
    path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
    return pd.read_csv(path)


def load_taxonomy_categories():
    """Map ingredients to categories."""
    taxonomy_path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "INGREDIENT_TAXONOMY.md"

    with open(taxonomy_path) as f:
        content = f.read()

    ingredients = {}
    current_category = None

    for line in content.split('\n'):
        if line.startswith('### '):
            current_category = line.replace('###', '').strip()
        elif line.startswith('- `') and current_category:
            import re
            if match := re.match(r'^- `([a-z_]+)`: (.+)$', line):
                ing_name = match.group(1)
                ingredients[ing_name] = current_category

    return ingredients


def build_product_ingredient_map(classifications, taxonomy_categories):
    """Build product_id → (ingredient, category, is_food) mapping."""
    product_map = {}

    for _, row in classifications.iterrows():
        category = taxonomy_categories.get(row['ingredient'], 'Unknown')
        product_map[row['product_id']] = {
            'ingredient': row['ingredient'],
            'category': category,
            'is_food': row['is_food'],
            'aisle': row['aisle'],
        }

    return product_map


def get_valid_users(min_orders=MIN_ORDERS):
    """Get users with at least min_orders in prior+train."""
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")
    uc = (orders.filter(pl.col("eval_set").is_in(["prior", "train"]))
          .group_by("user_id").agg(pl.col("order_number").max().alias("mx"))
          .filter(pl.col("mx") >= min_orders))
    return sorted(uc["user_id"].to_list())


def load_user_sequences(user_ids, product_map):
    """
    Load full purchase sequences for users with ingredient classifications.

    Returns DataFrame with columns:
    - user_id, order_number, product_id, ingredient, category, is_food, aisle
    """
    # Load orders
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("user_id").is_in(user_ids))
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id", "order_number"]))

    # Load purchases
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

    purch = pl.concat([prior, train]).join(orders, on="order_id", how="inner")
    df = purch.select(["user_id", "order_number", "product_id"]).to_pandas()

    # Add ingredient classifications
    df['ingredient'] = df['product_id'].map(lambda pid: product_map.get(pid, {}).get('ingredient', 'unknown'))
    df['category'] = df['product_id'].map(lambda pid: product_map.get(pid, {}).get('category', 'Unknown'))
    df['is_food'] = df['product_id'].map(lambda pid: product_map.get(pid, {}).get('is_food', True))
    df['aisle'] = df['product_id'].map(lambda pid: product_map.get(pid, {}).get('aisle', 'unknown'))

    return df


def compute_reorder_statistics(sequences, level_col):
    """
    Compute reorder statistics at a given level (product_id, ingredient, category, aisle).

    Returns dict with:
    - reorder_intervals: list of gaps between consecutive purchases
    - immediate_reorders: count of items reordered in next order
    - delayed_reorders: count of items reordered after skipping orders
    - never_reordered: count of items purchased only once
    """
    stats = {
        'reorder_intervals': [],
        'immediate_count': 0,
        'delayed_count': 0,
        'never_reordered_count': 0,
        'total_items': 0,
    }

    for user_id, user_df in sequences.groupby('user_id'):
        user_df = user_df.sort_values('order_number')

        # Track when each item was last seen
        last_seen = {}

        for order_num, order_df in user_df.groupby('order_number'):
            items_in_order = set(order_df[level_col].unique())

            for item in items_in_order:
                if item in last_seen:
                    gap = order_num - last_seen[item]
                    stats['reorder_intervals'].append(gap)

                    if gap == 1:
                        stats['immediate_count'] += 1
                    else:
                        stats['delayed_count'] += 1

                last_seen[item] = order_num

        # Items seen only once
        stats['never_reordered_count'] += sum(1 for item, count in user_df[level_col].value_counts().items() if count == 1)
        stats['total_items'] += len(user_df)

    return stats


def main():
    print("="*70)
    print("INGREDIENT-BASED SEQUENCE ANALYSIS")
    print("="*70)

    print("\n1. Loading classifications and taxonomy...")
    classifications = load_classifications()
    taxonomy_categories = load_taxonomy_categories()
    product_map = build_product_ingredient_map(classifications, taxonomy_categories)

    print(f"   Products classified: {len(product_map):,}")
    print(f"   Unique ingredients: {len(set(p['ingredient'] for p in product_map.values())):,}")
    print(f"   Unique categories: {len(set(p['category'] for p in product_map.values())):,}")

    print("\n2. Loading valid users...")
    users = get_valid_users(min_orders=MIN_ORDERS)
    print(f"   Users with {MIN_ORDERS}+ orders: {len(users):,}")

    # Process in batches to manage memory
    print("\n3. Loading purchase sequences (batched)...")
    all_sequences = []

    for batch_num, batch_start in enumerate(range(0, len(users), BATCH_SIZE), 1):
        batch_users = users[batch_start:batch_start + BATCH_SIZE]
        print(f"   Batch {batch_num}/{(len(users) + BATCH_SIZE - 1) // BATCH_SIZE}: "
              f"{len(batch_users):,} users", end=" ")

        batch_seq = load_user_sequences(batch_users, product_map)
        all_sequences.append(batch_seq)
        print(f"→ {len(batch_seq):,} items")

    sequences = pd.concat(all_sequences, ignore_index=True)
    print(f"\n   Total items: {len(sequences):,}")
    print(f"   Food items: {sequences['is_food'].sum():,} ({sequences['is_food'].mean()*100:.1f}%)")

    # Filter to food items only
    food_sequences = sequences[sequences['is_food']].copy()
    print(f"   Analyzing food items only: {len(food_sequences):,}")

    print("\n4. Computing reorder statistics at multiple levels...")

    levels = {
        'product_id': 'Exact Product (SKU)',
        'ingredient': 'Recipe Ingredient',
        'category': 'Ingredient Category',
        'aisle': 'Retail Aisle',
    }

    results = {}

    for level_col, level_name in levels.items():
        print(f"\n   {level_name}:")
        stats = compute_reorder_statistics(food_sequences, level_col)
        results[level_col] = stats

        total_reorders = stats['immediate_count'] + stats['delayed_count']
        if total_reorders > 0:
            immediate_pct = stats['immediate_count'] / total_reorders * 100
            delayed_pct = stats['delayed_count'] / total_reorders * 100

            print(f"     Immediate reorders (next order): {stats['immediate_count']:,} ({immediate_pct:.1f}%)")
            print(f"     Delayed reorders (skip 1+ orders): {stats['delayed_count']:,} ({delayed_pct:.1f}%)")
            print(f"     Never reordered: {stats['never_reordered_count']:,}")

            if stats['reorder_intervals']:
                intervals = stats['reorder_intervals']
                print(f"     Median reorder gap: {np.median(intervals):.1f} orders")
                print(f"     Mean reorder gap: {np.mean(intervals):.1f} orders")

    # Save detailed results
    print("\n5. Saving results...")

    # Save reorder intervals for each level
    for level_col, level_name in levels.items():
        intervals = results[level_col]['reorder_intervals']
        if intervals:
            df_intervals = pd.DataFrame({
                'gap': intervals,
                'level': level_col,
            })
            output_path = SEQ_ANALYSIS_DIR / f"reorder_intervals_{level_col}.csv"
            df_intervals.to_csv(output_path, index=False)
            print(f"   Saved {output_path.name}")

    # Save summary statistics
    summary_rows = []
    for level_col, level_name in levels.items():
        stats = results[level_col]
        total_reorders = stats['immediate_count'] + stats['delayed_count']

        summary_rows.append({
            'level': level_name,
            'level_col': level_col,
            'total_items': stats['total_items'],
            'immediate_reorders': stats['immediate_count'],
            'delayed_reorders': stats['delayed_count'],
            'never_reordered': stats['never_reordered_count'],
            'total_reorders': total_reorders,
            'immediate_pct': stats['immediate_count'] / total_reorders * 100 if total_reorders > 0 else 0,
            'delayed_pct': stats['delayed_count'] / total_reorders * 100 if total_reorders > 0 else 0,
            'median_gap': np.median(stats['reorder_intervals']) if stats['reorder_intervals'] else np.nan,
            'mean_gap': np.mean(stats['reorder_intervals']) if stats['reorder_intervals'] else np.nan,
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_path = SEQ_ANALYSIS_DIR / "reorder_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"   Saved {summary_path.name}")

    print("\n" + "="*70)
    print("Analysis complete!")
    print(f"Results saved to: {SEQ_ANALYSIS_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()
