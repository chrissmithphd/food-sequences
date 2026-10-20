#!/usr/bin/env python3
"""
Generate example sequence timelines showing real customer purchasing patterns.

Finds representative examples of different behaviors:
- Product repetition: buying same SKU repeatedly
- Brand switching: changing products within same ingredient
- Ingredient switching: changing to different ingredients
- Rotation: cycling through a small set
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


def find_example_sequences(classifications, pattern_type='product_repetition', n_examples=4):
    """
    Find real customer sequences that demonstrate a pattern.
    
    Returns list of dicts with user_id, orders, products, ingredients
    """
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
    users = purch.select("user_id").unique().to_series().sample(n=5000, seed=42).to_list()
    
    examples = []
    
    for user_id in users:
        if len(examples) >= n_examples:
            break
            
        user_df = purch.filter(pl.col("user_id") == user_id).sort("order_number")
        
        if len(user_df) == 0 or len(user_df) < 8:
            continue
            
        user_data = user_df.to_dicts()
        
        # Look for the requested pattern
        if pattern_type == 'product_repetition':
            # Find a product purchased 4+ times
            product_counts = {}
            for row in user_data:
                pid = row['product_id']
                product_counts[pid] = product_counts.get(pid, 0) + 1
            
            for pid, count in product_counts.items():
                if count >= 4:
                    # Found one - extract sequence
                    sequence = []
                    for row in user_data[:15]:  # First 15 orders
                        if row['product_id'] == pid:
                            sequence.append({
                                'order': row['order_number'],
                                'product': row['product_name'],
                                'ingredient': row['ingredient'],
                                'product_id': row['product_id']
                            })
                    
                    if len(sequence) >= 4:
                        examples.append({
                            'user_id': user_id,
                            'sequence': sequence,
                            'pattern': 'Product Repetition'
                        })
                        break
        
        elif pattern_type == 'brand_switching':
            # Find an ingredient purchased multiple times with different products
            ing_products = {}
            for row in user_data:
                ing = row['ingredient']
                pid = row['product_id']
                if ing not in ing_products:
                    ing_products[ing] = set()
                ing_products[ing].add(pid)
            
            for ing, pids in ing_products.items():
                if len(pids) >= 3:  # At least 3 different products of same ingredient
                    # Extract sequence
                    sequence = []
                    for row in user_data[:15]:
                        if row['ingredient'] == ing:
                            sequence.append({
                                'order': row['order_number'],
                                'product': row['product_name'],
                                'ingredient': row['ingredient'],
                                'product_id': row['product_id']
                            })
                    
                    if len(sequence) >= 3:
                        examples.append({
                            'user_id': user_id,
                            'sequence': sequence,
                            'pattern': 'Brand Switching'
                        })
                        break
    
    return examples


def plot_sequence_examples(examples, pattern_name):
    """Create a figure showing multiple sequence examples."""
    n_examples = len(examples)
    fig, axes = plt.subplots(n_examples, 1, figsize=(14, 3*n_examples))
    
    if n_examples == 1:
        axes = [axes]
    
    for idx, example in enumerate(examples):
        ax = axes[idx]
        sequence = example['sequence']
        
        orders = [s['order'] for s in sequence]
        
        # Assign colors to unique products
        unique_products = list(set(s['product_id'] for s in sequence))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_products)))
        product_colors = dict(zip(unique_products, colors))
        
        # Plot each purchase
        for i, item in enumerate(sequence):
            order = item['order']
            color = product_colors[item['product_id']]
            
            ax.scatter(order, 0, s=200, c=[color], edgecolors='black', linewidths=1.5, zorder=3)
            
            # Label
            label = item['product'][:25] + '...' if len(item['product']) > 25 else item['product']
            ax.text(order, -0.15, label, ha='center', va='top', fontsize=8, rotation=45)
        
        # Draw line connecting purchases
        ax.plot(orders, [0]*len(orders), 'k--', alpha=0.3, linewidth=1, zorder=1)
        
        ax.set_xlim(min(orders)-1, max(orders)+1)
        ax.set_ylim(-1, 0.5)
        ax.set_xlabel('Order Number', fontsize=10)
        ax.set_yticks([])
        ax.set_title(f'Customer {example["user_id"]} - {example["pattern"]} ({sequence[0]["ingredient"]})', 
                    fontsize=11, fontweight='bold')
        ax.grid(axis='x', alpha=0.2)
    
    plt.tight_layout()
    filename = pattern_name.lower().replace(' ', '_') + '_examples.png'
    plt.savefig(FIGURES_DIR / filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved {filename}")


def main():
    print("Generating sequence example visualizations...")
    
    print("\n1. Loading classifications...")
    classifications = load_classifications()
    
    print("\n2. Finding product repetition examples...")
    examples = find_example_sequences(classifications, 'product_repetition', n_examples=3)
    if examples:
        plot_sequence_examples(examples, 'Product Repetition')
    else:
        print("  No examples found")
    
    print("\n3. Finding brand switching examples...")
    examples = find_example_sequences(classifications, 'brand_switching', n_examples=3)
    if examples:
        plot_sequence_examples(examples, 'Brand Switching')
    else:
        print("  No examples found")
    
    print(f"\nFigures saved to: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
