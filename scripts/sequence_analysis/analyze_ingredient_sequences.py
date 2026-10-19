#!/usr/bin/env python3
"""
Ingredient-based sequence analysis using LLM classifications.

Memory-efficient implementation using polars and incremental processing.
Analyzes customer purchasing patterns at multiple levels:
- Exact product (SKU)
- Recipe ingredient (e.g., milk regardless of brand)
- Ingredient category (e.g., DAIRY)
- Retail aisle

Output: analysis/sequence_analysis/ directory with statistics.
"""

import sys
from pathlib import Path
import polars as pl
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

# Output directory
SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
SEQ_ANALYSIS_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 5_000  # Users per batch
MIN_ORDERS = 4


def load_classifications():
    """Load ingredient classifications."""
    path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
    return pl.read_csv(path)


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


def get_valid_users(min_orders=MIN_ORDERS):
    """Get users with at least min_orders."""
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")
    uc = (orders.filter(pl.col("eval_set").is_in(["prior", "train"]))
          .group_by("user_id").agg(pl.col("order_number").max().alias("mx"))
          .filter(pl.col("mx") >= min_orders))
    return sorted(uc["user_id"].to_list())


def process_user_batch(user_ids, classifications):
    """
    Process a batch of users and return reorder statistics.
    Returns dict with level -> {intervals: [], immediate: count, delayed: count, never: count, total: count}
    """
    # Load orders for batch
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("user_id").is_in(user_ids))
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id", "order_number"]))

    # Load purchases
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

    purch = pl.concat([prior, train]).join(orders, on="order_id", how="inner")

    # Join classifications
    purch = purch.join(
        classifications.select(["product_id", "ingredient", "category", "is_food", "aisle"]),
        on="product_id",
        how="left"
    )

    # Filter to food only
    purch = purch.filter(pl.col("is_food") == True)

    # Initialize stats for each level
    levels = {
        'product_id': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
        'ingredient': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
        'category': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
        'aisle': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
    }

    # Process each user
    for user_id in user_ids:
        user_df = purch.filter(pl.col("user_id") == user_id).sort("order_number")

        if len(user_df) == 0:
            continue

        user_data = user_df.to_dicts()

        for level_col in levels.keys():
            # Track when each item was last seen
            last_seen = {}
            item_counts = defaultdict(int)

            current_order = None
            items_in_order = set()

            for row in user_data:
                order_num = row['order_number']
                item = row[level_col]

                if item is None:
                    continue

                # Start new order
                if order_num != current_order:
                    if current_order is not None:
                        # Process previous order's items
                        for prev_item in items_in_order:
                            last_seen[prev_item] = current_order

                    current_order = order_num
                    items_in_order = set()

                items_in_order.add(item)
                item_counts[item] += 1

                # Check if reorder
                if item in last_seen:
                    gap = order_num - last_seen[item]
                    levels[level_col]['intervals'].append(gap)

                    if gap == 1:
                        levels[level_col]['immediate'] += 1
                    else:
                        levels[level_col]['delayed'] += 1

            # Record last order
            if current_order is not None:
                for item in items_in_order:
                    last_seen[item] = current_order

            # Count never-reordered items
            levels[level_col]['never'] += sum(1 for count in item_counts.values() if count == 1)
            levels[level_col]['total'] += sum(item_counts.values())

    return levels


def main():
    print("="*70)
    print("INGREDIENT-BASED SEQUENCE ANALYSIS")
    print("="*70)

    print("\n1. Loading classifications and taxonomy...")
    classifications = load_classifications()
    taxonomy_categories = load_taxonomy_categories()

    # Add category to classifications
    classifications = classifications.with_columns(
        pl.col("ingredient").map_elements(
            lambda x: taxonomy_categories.get(x, "Unknown"),
            return_dtype=pl.Utf8
        ).alias("category")
    )

    print(f"   Products classified: {len(classifications):,}")

    print("\n2. Loading valid users...")
    users = get_valid_users(min_orders=MIN_ORDERS)
    print(f"   Users with {MIN_ORDERS}+ orders: {len(users):,}")

    # Initialize accumulators
    all_stats = {
        'product_id': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
        'ingredient': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
        'category': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
        'aisle': {'intervals': [], 'immediate': 0, 'delayed': 0, 'never': 0, 'total': 0},
    }

    # Process in batches
    print(f"\n3. Processing in batches of {BATCH_SIZE:,} users...")
    num_batches = (len(users) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(num_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_users = users[batch_start:batch_start + BATCH_SIZE]

        print(f"   Batch {batch_num + 1}/{num_batches}: {len(batch_users):,} users", flush=True)

        batch_stats = process_user_batch(batch_users, classifications)

        # Merge batch results
        for level in all_stats:
            all_stats[level]['intervals'].extend(batch_stats[level]['intervals'])
            all_stats[level]['immediate'] += batch_stats[level].get('immediate', 0)
            all_stats[level]['delayed'] += batch_stats[level].get('delayed', 0)
            all_stats[level]['never'] += batch_stats[level].get('never', 0)
            all_stats[level]['total'] += batch_stats[level].get('total', 0)

    print("\n4. Saving results...")

    # Save interval data
    for level, level_name in [
        ('product_id', 'Exact Product (SKU)'),
        ('ingredient', 'Recipe Ingredient'),
        ('category', 'Ingredient Category'),
        ('aisle', 'Retail Aisle'),
    ]:
        intervals = all_stats[level]['intervals']
        if intervals:
            pl.DataFrame({
                'gap': intervals,
                'level': [level] * len(intervals)
            }).write_csv(SEQ_ANALYSIS_DIR / f"reorder_intervals_{level}.csv")
            print(f"   Saved reorder_intervals_{level}.csv")

    # Save summary
    summary_rows = []
    for level, level_name in [
        ('product_id', 'Exact Product (SKU)'),
        ('ingredient', 'Recipe Ingredient'),
        ('category', 'Ingredient Category'),
        ('aisle', 'Retail Aisle'),
    ]:
        stats = all_stats[level]
        total_reorders = stats['immediate'] + stats['delayed']

        import numpy as np
        summary_rows.append({
            'level': level_name,
            'level_col': level,
            'total_items': stats['total'],
            'immediate_reorders': stats['immediate'],
            'delayed_reorders': stats['delayed'],
            'never_reordered': stats['never'],
            'total_reorders': total_reorders,
            'immediate_pct': stats['immediate'] / total_reorders * 100 if total_reorders > 0 else 0,
            'delayed_pct': stats['delayed'] / total_reorders * 100 if total_reorders > 0 else 0,
            'median_gap': np.median(stats['intervals']) if stats['intervals'] else None,
            'mean_gap': np.mean(stats['intervals']) if stats['intervals'] else None,
        })

        print(f"\n   {level_name}:")
        print(f"     Total items: {stats['total']:,}")
        print(f"     Immediate reorders: {stats['immediate']:,}")
        print(f"     Delayed reorders: {stats['delayed']:,}")
        print(f"     Never reordered: {stats['never']:,}")
        if stats['intervals']:
            print(f"     Median gap: {np.median(stats['intervals']):.1f} orders")

    pl.DataFrame(summary_rows).write_csv(SEQ_ANALYSIS_DIR / "reorder_summary.csv")
    print(f"\n   Saved reorder_summary.csv")

    print("\n" + "="*70)
    print("Analysis complete!")
    print(f"Results saved to: {SEQ_ANALYSIS_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()
