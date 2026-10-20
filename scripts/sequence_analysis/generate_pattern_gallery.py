#!/usr/bin/env python3
"""
Generate a pattern gallery showing different purchasing behaviors.

Creates a 2x2 grid showing 4 clear examples:
- Persistent Staple: Same product bought frequently across many orders
- Regular Rotation: Cycling through a small set of related products
- Burst then Absence: Multiple purchases early, then stops
- Return after Break: Long gap, then resumes
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import polars as pl
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
FIGURES_DIR = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIGURES_DIR.mkdir(exist_ok=True, parents=True)


def load_classifications():
    """Load ingredient classifications."""
    path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
    return pl.read_csv(path)


def find_pattern_examples():
    """Find one clear example of each pattern type."""
    classifications = load_classifications()

    # Load data
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id", "order_number"]))

    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

    purch = pl.concat([prior, train]).join(orders, on="order_id", how="inner")
    purch = purch.join(
        classifications.select(["product_id", "product_name", "ingredient", "is_food"]),
        on="product_id",
        how="left"
    )

    purch = purch.filter(pl.col("is_food") == True)

    # Sample users
    users = purch.select("user_id").unique().to_series().sample(n=10000, seed=42).to_list()

    examples = {
        'persistent_staple': None,
        'regular_rotation': None,
        'burst_then_absence': None,
        'return_after_break': None,
    }

    for user_id in users:
        if all(v is not None for v in examples.values()):
            break

        user_df = purch.filter(pl.col("user_id") == user_id).sort("order_number")

        if len(user_df) < 15:
            continue

        # Get max order number
        max_order = user_df.select(pl.col("order_number").max()).item()

        # Build order presence map for each product
        product_orders = {}
        for row in user_df.iter_rows(named=True):
            pid = row['product_id']
            order_num = row['order_number']
            product_name = row['product_name']

            if pid not in product_orders:
                product_orders[pid] = {'orders': [], 'name': product_name}
            product_orders[pid]['orders'].append(order_num)

        # Look for patterns
        for pid, data in product_orders.items():
            orders_list = sorted(data['orders'])
            n_orders = len(orders_list)

            if n_orders < 2:
                continue

            # Persistent staple: bought in many orders with consecutive runs
            if examples['persistent_staple'] is None:
                if n_orders >= 8 and max(orders_list) - min(orders_list) <= 12:
                    # Check for consecutive runs
                    consecutive = 1
                    max_consecutive = 1
                    for i in range(len(orders_list) - 1):
                        if orders_list[i+1] - orders_list[i] == 1:
                            consecutive += 1
                            max_consecutive = max(max_consecutive, consecutive)
                        else:
                            consecutive = 1

                    if max_consecutive >= 4:
                        examples['persistent_staple'] = {
                            'user_id': user_id,
                            'product_name': data['name'],
                            'orders': orders_list,
                            'max_order': max_order,
                            'pattern': 'Persistent Staple'
                        }

            # Regular rotation: consistent gaps
            if examples['regular_rotation'] is None:
                if n_orders >= 5:
                    gaps = [orders_list[i+1] - orders_list[i] for i in range(len(orders_list) - 1)]
                    if len(gaps) >= 4:
                        gap_mean = np.mean(gaps)
                        gap_std = np.std(gaps)
                        if 2 <= gap_mean <= 4 and gap_std / gap_mean < 0.4:
                            examples['regular_rotation'] = {
                                'user_id': user_id,
                                'product_name': data['name'],
                                'orders': orders_list,
                                'max_order': max_order,
                                'pattern': 'Regular Rotation'
                            }

            # Burst then absence: early purchases, then stops
            if examples['burst_then_absence'] is None:
                if n_orders >= 4 and max_order >= 12:
                    early_cutoff = max(4, int(max_order * 0.3))
                    early_count = sum(1 for o in orders_list if o <= early_cutoff)
                    late_count = sum(1 for o in orders_list if o > early_cutoff)

                    if early_count >= 4 and late_count == 0 and max(orders_list) < max_order - 5:
                        examples['burst_then_absence'] = {
                            'user_id': user_id,
                            'product_name': data['name'],
                            'orders': orders_list,
                            'max_order': max_order,
                            'pattern': 'Burst then Absence'
                        }

            # Return after break: gap, then resumes
            if examples['return_after_break'] is None:
                if n_orders >= 4:
                    gaps = [orders_list[i+1] - orders_list[i] for i in range(len(orders_list) - 1)]
                    if max(gaps) >= 6 and len(orders_list) >= 4:
                        # Find the big gap
                        big_gap_idx = gaps.index(max(gaps))
                        before_gap = orders_list[:big_gap_idx+1]
                        after_gap = orders_list[big_gap_idx+1:]

                        if len(before_gap) >= 2 and len(after_gap) >= 2:
                            examples['return_after_break'] = {
                                'user_id': user_id,
                                'product_name': data['name'],
                                'orders': orders_list,
                                'max_order': max_order,
                                'pattern': 'Return after Break'
                            }

    return examples


def plot_pattern_gallery(examples):
    """Create a 2x2 gallery of pattern examples."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Purchase Pattern Gallery', fontsize=16, fontweight='bold', y=0.995)

    pattern_order = [
        'persistent_staple',
        'regular_rotation',
        'burst_then_absence',
        'return_after_break',
    ]

    for idx, pattern_key in enumerate(pattern_order):
        row = idx // 2
        col = idx % 2
        ax = axes[row, col]

        example = examples.get(pattern_key)

        if example is None:
            ax.text(0.5, 0.5, f'No example found\nfor {pattern_key.replace("_", " ").title()}',
                   ha='center', va='center', fontsize=12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            continue

        # Plot the order timeline
        max_order = example['max_order']
        orders = example['orders']

        # Draw timeline
        ax.plot([1, max_order], [0, 0], 'k-', linewidth=2, alpha=0.3, zorder=1)

        # Mark all orders as tick marks
        for o in range(1, max_order + 1):
            ax.plot([o, o], [-0.05, 0.05], 'k-', linewidth=0.5, alpha=0.2, zorder=1)

        # Highlight purchase orders
        for o in orders:
            ax.scatter(o, 0, s=200, c='#2196F3', edgecolors='black', linewidths=2, zorder=3)

        # Add order numbers on purchases
        for o in orders:
            ax.text(o, 0.15, str(o), ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Title and product name
        ax.set_title(example['pattern'], fontsize=13, fontweight='bold', pad=15)

        # Product name (truncated)
        product_name = example['product_name']
        if len(product_name) > 40:
            product_name = product_name[:37] + '...'
        ax.text(0.02, 0.98, product_name, transform=ax.transAxes,
               fontsize=10, va='top', style='italic',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        # Format
        ax.set_xlim(0, max_order + 1)
        ax.set_ylim(-0.3, 0.5)
        ax.set_xlabel('Order Number', fontsize=10)
        ax.set_yticks([])
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

        # Add grid
        ax.grid(axis='x', alpha=0.2, linestyle='--')

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "pattern_gallery.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved pattern_gallery.png")


def main():
    print("Generating pattern gallery...")

    print("\n1. Finding pattern examples...")
    examples = find_pattern_examples()

    found = sum(1 for v in examples.values() if v is not None)
    print(f"   Found {found}/4 pattern examples")

    print("\n2. Creating gallery...")
    plot_pattern_gallery(examples)

    print(f"\nFigure saved to: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
