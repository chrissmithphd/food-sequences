#!/usr/bin/env python3
"""
Generate pattern visualizations: prevalence chart and example sequences.
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import polars as pl
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
FIGURES_DIR = SEQ_ANALYSIS_DIR / "figures"
FIGURES_DIR.mkdir(exist_ok=True, parents=True)

sns.set_theme(style="whitegrid", font_scale=1.1)


def plot_pattern_prevalence():
    """Bar chart of pattern distribution."""
    df = pd.read_csv(SEQ_ANALYSIS_DIR / "pattern_distribution.csv")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0']
    ax.barh(df['pattern'], df['percentage'], color=colors)
    
    ax.set_xlabel('Percentage of User-Ingredient Pairs', fontsize=11)
    ax.set_title('Purchase Pattern Distribution', fontsize=13, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    # Add percentage labels
    for i, (pattern, pct) in enumerate(zip(df['pattern'], df['percentage'])):
        ax.text(pct + 1, i, f'{pct:.1f}%', va='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "pattern_prevalence.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved pattern_prevalence.png")


def plot_basket_composition():
    """Stacked bar chart of basket composition."""
    df = pd.read_csv(SEQ_ANALYSIS_DIR / "basket_composition_summary.csv")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(df['measure']))
    width = 0.6
    
    colors = ['#2196F3', '#4CAF50', '#FF9800']
    
    bottom = np.zeros(len(df))
    
    for i, (col, color, label) in enumerate([
        ('familiar_product_pct', colors[0], 'Familiar product\n(exact repeat)'),
        ('familiar_ingredient_pct', colors[1], 'Familiar ingredient\n(brand switch)'),
        ('new_ingredient_pct', colors[2], 'New ingredient\n(novel food)'),
    ]):
        values = df[col].values
        ax.bar(x, values, width, bottom=bottom, label=label, color=color)
        
        # Add percentage labels
        for j, (val, bot) in enumerate(zip(values, bottom)):
            if val > 5:  # Only label if segment is large enough
                ax.text(j, bot + val/2, f'{val:.1f}%', ha='center', va='center', 
                       fontsize=10, fontweight='bold', color='white')
        
        bottom += values
    
    ax.set_ylabel('Percentage of Basket Items', fontsize=11)
    ax.set_title('Basket Composition: How Much Variety is Novel?', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(df['measure'], fontsize=11)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "basket_composition.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved basket_composition.png")


def plot_prepared_vs_base():
    """Comparison of prepared dishes vs base ingredients."""
    df = pd.read_csv(SEQ_ANALYSIS_DIR / "prepared_vs_base.csv")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(df))
    width = 0.35
    
    ax.bar(x - width/2, df['immediate_pct'], width, label='Immediate (next order)', color='steelblue')
    ax.bar(x + width/2, df['delayed_pct'], width, label='Delayed (skip 1+ orders)', color='coral')
    
    ax.set_ylabel('Percentage of Reorders', fontsize=11)
    ax.set_title('Reorder Behavior: Prepared Dishes vs Base Ingredients', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(df['group'], fontsize=11)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "prepared_vs_base.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  Saved prepared_vs_base.png")


def main():
    print("Generating pattern and composition visualizations...")
    
    print("\n1. Pattern prevalence chart...")
    if (SEQ_ANALYSIS_DIR / "pattern_distribution.csv").exists():
        plot_pattern_prevalence()
    else:
        print("  Skipping - pattern_distribution.csv not found")
    
    print("\n2. Basket composition chart...")
    if (SEQ_ANALYSIS_DIR / "basket_composition_summary.csv").exists():
        plot_basket_composition()
    else:
        print("  Skipping - basket_composition_summary.csv not found")
    
    print("\n3. Prepared vs base comparison...")
    if (SEQ_ANALYSIS_DIR / "prepared_vs_base.csv").exists():
        plot_prepared_vs_base()
    else:
        print("  Skipping - prepared_vs_base.csv not found")
    
    print(f"\nFigures saved to: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
