#!/usr/bin/env python3
"""
Analyze ingredient classification results.

Generates statistics, distributions, and visualizations for the
classification taxonomy and results.

Usage:
    uv run python scripts/classification/analyze_classification.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANALYSIS_OUTPUTS

# Set visualization style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def load_classification():
    """Load final classification results."""
    path = Path(__file__).parent.parent.parent / "data" / "food_classification.csv"
    return pd.read_csv(path)


def load_taxonomy():
    """Load ingredient taxonomy."""
    from collections import defaultdict

    taxonomy_path = Path(__file__).parent.parent.parent / "data" / "INGREDIENT_TAXONOMY.md"

    with open(taxonomy_path) as f:
        content = f.read()

    ingredients = {}
    categories = defaultdict(list)
    current_category = None

    for line in content.split('\n'):
        if line.startswith('### '):
            current_category = line.replace('###', '').strip()
        elif line.startswith('- `') and current_category:
            import re
            if match := re.match(r'^- `([a-z_]+)`: (.+)$', line):
                ing_name = match.group(1)
                description = match.group(2)
                ingredients[ing_name] = {
                    'category': current_category,
                    'description': description
                }
                categories[current_category].append(ing_name)

    return ingredients, dict(categories)


def basic_statistics(df, taxonomy_ingredients):
    """Generate basic classification statistics."""
    stats = {
        'total_products': len(df),
        'total_ingredients_used': df['ingredient'].nunique(),
        'total_ingredients_defined': len(taxonomy_ingredients),
        'food_products': df['is_food'].sum(),
        'non_food_products': (~df['is_food']).sum(),
        'prepared_dishes': df['is_prepared_dish'].sum(),
        'unclassified': (df['ingredient'] == 'unclassified').sum(),
    }

    stats['food_pct'] = stats['food_products'] / stats['total_products'] * 100
    stats['prepared_pct'] = stats['prepared_dishes'] / stats['total_products'] * 100
    stats['unclassified_pct'] = stats['unclassified'] / stats['total_products'] * 100

    return stats


def ingredient_distribution(df):
    """Analyze distribution of products across ingredients."""
    dist = df['ingredient'].value_counts()

    # Concentration metrics
    top_10_pct = dist.head(10).sum() / len(df) * 100
    top_25_pct = dist.head(25).sum() / len(df) * 100
    top_50_pct = dist.head(50).sum() / len(df) * 100

    # Gini coefficient for inequality
    sorted_counts = np.sort(dist.values)
    n = len(sorted_counts)
    cumsum = np.cumsum(sorted_counts)
    gini = (2 * np.sum((np.arange(1, n+1)) * sorted_counts)) / (n * cumsum[-1]) - (n + 1) / n

    return {
        'distribution': dist,
        'top_10_pct': top_10_pct,
        'top_25_pct': top_25_pct,
        'top_50_pct': top_50_pct,
        'gini': gini,
        'singleton_ingredients': (dist == 1).sum(),
        'median_products_per_ingredient': dist.median(),
    }


def category_analysis(df, taxonomy_categories):
    """Analyze category-level patterns."""
    # Map ingredients to categories
    taxonomy_ingredients, _ = load_taxonomy()

    df['category'] = df['ingredient'].map(
        lambda ing: taxonomy_ingredients.get(ing, {}).get('category', 'Unknown')
    )

    category_dist = df['category'].value_counts()

    return {
        'distribution': category_dist,
        'df_with_categories': df,
    }


def aisle_ingredient_cross_tabulation(df):
    """Analyze which ingredients appear in which aisles."""
    # Get top aisles and ingredients
    top_aisles = df['aisle'].value_counts().head(20).index
    top_ingredients = df['ingredient'].value_counts().head(30).index

    # Filter to top aisles/ingredients
    df_filtered = df[df['aisle'].isin(top_aisles) & df['ingredient'].isin(top_ingredients)]

    # Create cross-tabulation
    crosstab = pd.crosstab(df_filtered['aisle'], df_filtered['ingredient'])

    return crosstab


def find_ingredient_examples(df, ingredient, n=10):
    """Find example products for an ingredient."""
    examples = df[df['ingredient'] == ingredient][['product_name', 'aisle', 'department']].head(n)
    return examples


def unused_taxonomy_ingredients(df, taxonomy_ingredients):
    """Find taxonomy ingredients not used in classification."""
    used = set(df['ingredient'].unique())
    defined = set(taxonomy_ingredients.keys())
    unused = defined - used
    return sorted(unused)


def plot_top_ingredients(dist, n=30, output_path=None):
    """Plot top N ingredients by product count."""
    fig, ax = plt.subplots(figsize=(12, 8))

    top_n = dist.head(n)
    ax.barh(range(len(top_n)), top_n.values, color='steelblue')
    ax.set_yticks(range(len(top_n)))
    ax.set_yticklabels(top_n.index, fontsize=9)
    ax.set_xlabel('Number of Products', fontsize=11)
    ax.set_title(f'Top {n} Ingredient Categories by Product Count', fontsize=13, fontweight='bold')
    ax.invert_yaxis()

    # Add counts to bars
    for i, v in enumerate(top_n.values):
        ax.text(v + 20, i, str(int(v)), va='center', fontsize=8)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved to {output_path}")

    return fig


def plot_ingredient_concentration(dist, output_path=None):
    """Plot cumulative distribution showing concentration."""
    fig, ax = plt.subplots(figsize=(10, 6))

    sorted_counts = dist.sort_values(ascending=False)
    cumulative_pct = (sorted_counts.cumsum() / sorted_counts.sum() * 100).values

    ax.plot(range(1, len(cumulative_pct) + 1), cumulative_pct, linewidth=2, color='darkblue')
    ax.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50% of products')
    ax.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='80% of products')

    ax.set_xlabel('Number of Ingredient Categories (ranked by frequency)', fontsize=11)
    ax.set_ylabel('Cumulative % of Products', fontsize=11)
    ax.set_title('Ingredient Concentration: How Many Categories Cover What % of Products?',
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # Annotate key points
    idx_50 = np.searchsorted(cumulative_pct, 50)
    idx_80 = np.searchsorted(cumulative_pct, 80)
    ax.annotate(f'{idx_50 + 1} categories\ncover 50%', xy=(idx_50 + 1, 50),
                xytext=(idx_50 + 30, 40), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='red', alpha=0.7))
    ax.annotate(f'{idx_80 + 1} categories\ncover 80%', xy=(idx_80 + 1, 80),
                xytext=(idx_80 + 30, 70), fontsize=9,
                arrowprops=dict(arrowstyle='->', color='orange', alpha=0.7))

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved to {output_path}")

    return fig


def plot_category_distribution(category_dist, output_path=None):
    """Plot high-level category distribution."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Filter out Unknown and sort
    filtered = category_dist[category_dist.index != 'Unknown'].sort_values(ascending=True)

    ax.barh(range(len(filtered)), filtered.values, color='teal')
    ax.set_yticks(range(len(filtered)))
    ax.set_yticklabels(filtered.index, fontsize=9)
    ax.set_xlabel('Number of Products', fontsize=11)
    ax.set_title('Product Distribution Across Ingredient Categories', fontsize=13, fontweight='bold')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved to {output_path}")

    return fig


def main():
    print("Loading classification data...")
    df = load_classification()

    print("Loading taxonomy...")
    taxonomy_ingredients, taxonomy_categories = load_taxonomy()

    print("\n" + "="*70)
    print("CLASSIFICATION ANALYSIS")
    print("="*70)

    # Basic statistics
    print("\n### Basic Statistics")
    stats = basic_statistics(df, taxonomy_ingredients)
    print(f"Total products: {stats['total_products']:,}")
    print(f"Ingredients used: {stats['total_ingredients_used']:,} of {stats['total_ingredients_defined']:,} defined")
    print(f"Food products: {stats['food_products']:,} ({stats['food_pct']:.1f}%)")
    print(f"Non-food products: {stats['non_food_products']:,}")
    print(f"Prepared dishes: {stats['prepared_dishes']:,} ({stats['prepared_pct']:.1f}%)")
    print(f"Unclassified: {stats['unclassified']:,} ({stats['unclassified_pct']:.1f}%)")

    # Distribution analysis
    print("\n### Ingredient Distribution")
    dist_analysis = ingredient_distribution(df)
    print(f"Unique ingredients used: {len(dist_analysis['distribution'])}")
    print(f"Top 10 ingredients cover: {dist_analysis['top_10_pct']:.1f}% of products")
    print(f"Top 25 ingredients cover: {dist_analysis['top_25_pct']:.1f}% of products")
    print(f"Top 50 ingredients cover: {dist_analysis['top_50_pct']:.1f}% of products")
    print(f"Gini coefficient: {dist_analysis['gini']:.3f}")
    print(f"Singleton ingredients (1 product): {dist_analysis['singleton_ingredients']}")
    print(f"Median products per ingredient: {dist_analysis['median_products_per_ingredient']:.0f}")

    print("\n### Top 20 Ingredients:")
    for i, (ing, count) in enumerate(dist_analysis['distribution'].head(20).items(), 1):
        pct = count / len(df) * 100
        print(f"  {i:2d}. {ing:30s} {count:>5,} ({pct:>5.2f}%)")

    # Category analysis
    print("\n### Category Analysis")
    cat_analysis = category_analysis(df, taxonomy_categories)
    print(f"Unique categories: {len(cat_analysis['distribution'])}")
    print("\nTop 15 Categories:")
    for i, (cat, count) in enumerate(cat_analysis['distribution'].head(15).items(), 1):
        pct = count / len(df) * 100
        print(f"  {i:2d}. {cat:40s} {count:>5,} ({pct:>5.2f}%)")

    # Unused taxonomy ingredients
    print("\n### Taxonomy Coverage")
    unused = unused_taxonomy_ingredients(df, taxonomy_ingredients)
    print(f"Unused taxonomy ingredients: {len(unused)}")
    if len(unused) <= 20:
        print(f"Unused: {', '.join(unused)}")
    else:
        print(f"First 20 unused: {', '.join(unused[:20])}")

    # Generate visualizations
    print("\n### Generating Visualizations")
    figures_dir = Path(__file__).parent.parent.parent / "analysis" / "classification" / "figures"
    figures_dir.mkdir(exist_ok=True)

    plot_top_ingredients(dist_analysis['distribution'], n=30,
                        output_path=figures_dir / "top_ingredients.png")

    plot_ingredient_concentration(dist_analysis['distribution'],
                                 output_path=figures_dir / "ingredient_concentration.png")

    plot_category_distribution(cat_analysis['distribution'],
                              output_path=figures_dir / "category_distribution.png")

    # Example products for interesting categories
    print("\n### Example Classifications")
    for ing in ['yogurt', 'pasta', 'cookies', 'frozen_meal', 'unclassified']:
        if ing in df['ingredient'].values:
            examples = find_ingredient_examples(df, ing, n=5)
            print(f"\n{ing}:")
            for _, ex in examples.iterrows():
                print(f"  - {ex['product_name']} ({ex['aisle']})")

    print("\n" + "="*70)
    print("Analysis complete. Figures saved to analysis/classification/figures/")
    print("="*70)


if __name__ == "__main__":
    main()
