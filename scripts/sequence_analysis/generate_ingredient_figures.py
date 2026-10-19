#!/usr/bin/env python3
"""
Generate figures for ingredient-based sequence analysis.

Creates visualizations comparing reorder behavior at:
- Product level (exact SKU)
- Ingredient level (recipe ingredient)
- Category level (ingredient family)
- Aisle level (retail organization)
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Paths
SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
FIGURES_DIR = SEQ_ANALYSIS_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True, parents=True)

sns.set_theme(style="whitegrid", font_scale=1.1)


def load_reorder_data():
    """Load reorder interval and summary data."""
    summary = pd.read_csv(SEQ_ANALYSIS_DIR / "reorder_summary.csv")

    intervals = {}
    for level in ['product_id', 'ingredient', 'category', 'aisle']:
        path = SEQ_ANALYSIS_DIR / f"reorder_intervals_{level}.csv"
        if path.exists():
            intervals[level] = pd.read_csv(path)

    return summary, intervals


def plot_reorder_comparison(summary):
    """Bar chart comparing immediate vs delayed reorders across levels."""
    fig, ax = plt.subplots(figsize=(10, 6))

    levels = summary['level'].values
    immediate = summary['immediate_pct'].values
    delayed = summary['delayed_pct'].values

    x = np.arange(len(levels))
    width = 0.35

    ax.bar(x - width/2, immediate, width, label='Immediate (next order)', color='steelblue')
    ax.bar(x + width/2, delayed, width, label='Delayed (skip 1+ orders)', color='coral')

    ax.set_ylabel('Percentage of Reorders', fontsize=11)
    ax.set_title('Immediate vs. Delayed Reordering by Level', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(levels, rotation=15, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "reorder_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved reorder_comparison.png")


def plot_interval_distributions(intervals):
    """Histogram of reorder intervals for each level."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    level_names = {
        'product_id': 'Exact Product',
        'ingredient': 'Recipe Ingredient',
        'category': 'Ingredient Category',
        'aisle': 'Retail Aisle',
    }

    colors = ['steelblue', 'seagreen', 'coral', 'mediumpurple']

    for idx, (level, name) in enumerate(level_names.items()):
        ax = axes[idx]

        if level in intervals and len(intervals[level]) > 0:
            gaps = intervals[level]['gap'].values
            gaps_capped = np.minimum(gaps, 20)  # Cap at 20 for visualization

            ax.hist(gaps_capped, bins=range(1, 22), alpha=0.7, color=colors[idx], edgecolor='black')
            ax.axvline(np.median(gaps), color='red', linestyle='--', linewidth=2,
                      label=f'Median: {np.median(gaps):.1f} orders')

            ax.set_xlabel('Orders Between Reorders', fontsize=10)
            ax.set_ylabel('Frequency', fontsize=10)
            ax.set_title(name, fontsize=11, fontweight='bold')
            ax.legend(fontsize=9)
            ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "interval_distributions.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved interval_distributions.png")


def plot_reorder_rates_comparison(summary):
    """Line plot showing reorder rates across levels."""
    fig, ax = plt.subplots(figsize=(10, 6))

    levels = summary['level'].values
    total_items = summary['total_items'].values
    reorders = summary['total_reorders'].values
    reorder_rates = (reorders / total_items) * 100

    ax.plot(levels, reorder_rates, marker='o', linewidth=2.5, markersize=10, color='darkblue')

    for i, rate in enumerate(reorder_rates):
        ax.text(i, rate + 1, f'{rate:.1f}%', ha='center', fontsize=10, fontweight='bold')

    ax.set_ylabel('Reorder Rate (%)', fontsize=11)
    ax.set_title('Overall Reorder Rates by Analysis Level', fontsize=13, fontweight='bold')
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels(levels, rotation=15, ha='right')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "reorder_rates.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved reorder_rates.png")


def main():
    print("Generating ingredient-based sequence figures...")

    print("\n1. Loading data...")
    summary, intervals = load_reorder_data()

    print("\n2. Creating visualizations...")
    plot_reorder_comparison(summary)
    plot_interval_distributions(intervals)
    plot_reorder_rates_comparison(summary)

    print(f"\nFigures saved to: {FIGURES_DIR}")
    print("="*70)


if __name__ == "__main__":
    main()
