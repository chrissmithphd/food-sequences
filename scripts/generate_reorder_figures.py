#!/usr/bin/env python3
"""
Figures that answer "when do customers reorder foods":
  reorder_curve_product_vs_aisle  — censoring-aware KM cumulative reorder prob
  reorder_cohort_comparison       — meal-like vs broad vs all (product-level)
  repeat_interval_distribution    — observed repeat intervals (histogram)

PNG + SVG to analysis/figures/.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import FIGURES_DIR, ANALYSIS_OUTPUTS
from food_sequences.reorder import T_MAX

sns.set_theme(style="whitegrid", font_scale=1.1)
HORIZONS = [1, 2, 3, 5, 10]


def save_fig(fig, name):
    for ext in ["png", "svg"]:
        fig.savefig(FIGURES_DIR / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {name}")


def curve_xy(row, xmax=30):
    xs = list(range(1, xmax + 1))
    ys = [row[f"p{n}"] * 100 for n in xs]
    return xs, ys


def fig_product_vs_aisle(curves):
    fig, ax = plt.subplots(figsize=(10, 6))
    for key, color, label in [
        ("product", "#2196F3", "Exact product (SKU) reorder"),
        ("aisle", "#4CAF50", "Same aisle (incl. different brand/variant)"),
    ]:
        row = curves[(curves["key"] == key) & (curves["cohort"] == "all") & (curves["weighting"] == "event")].iloc[0]
        xs, ys = curve_xy(row)
        ax.plot(xs, ys, color=color, linewidth=2, label=label)
        for n in HORIZONS:
            ax.scatter(n, row[f"p{n}"] * 100, color=color, zorder=5, s=35)

    ax.set_xlabel("Subsequent orders (n)")
    ax.set_ylabel("P(reordered within n orders)  [%]")
    ax.set_title("When Do Customers Reorder?\nCensoring-aware cumulative reorder probability (event-weighted)")
    ax.legend(loc="lower right")
    ax.set_xlim(1, 30)
    ax.set_ylim(0, 100)
    fig.text(0.5, -0.02,
             "Gap between the two lines = reorders of the same KIND of food via a different product (brand/variant switch).",
             ha="center", fontsize=8, style="italic", color="#555")
    save_fig(fig, "reorder_curve_product_vs_aisle")


def fig_cohort(curves):
    fig, ax = plt.subplots(figsize=(10, 6))
    for cohort, color, label in [
        ("all", "#607D8B", "All products"),
        ("meal_like", "#FF7043", "Meal-like aisles (primary cohort)"),
        ("broad", "#42A5F5", "Broad frozen+deli (comparison)"),
    ]:
        sub = curves[(curves["key"] == "product") & (curves["cohort"] == cohort) & (curves["weighting"] == "event")]
        if len(sub) == 0:
            continue
        row = sub.iloc[0]
        xs, ys = curve_xy(row)
        ax.plot(xs, ys, color=color, linewidth=2, label=label)
        for n in HORIZONS:
            ax.scatter(n, row[f"p{n}"] * 100, color=color, zorder=5, s=30)

    ax.set_xlabel("Subsequent orders (n)")
    ax.set_ylabel("P(reordered within n orders)  [%]")
    ax.set_title("Reorder Probability by Cohort (product-level, event-weighted)")
    ax.legend(loc="lower right")
    ax.set_xlim(1, 30)
    ax.set_ylim(0, 100)
    save_fig(fig, "reorder_cohort_comparison")


def fig_interval_distribution(events):
    fig, ax = plt.subplots(figsize=(10, 6))
    data = events["interval"].clip(upper=20)
    ax.hist(data, bins=range(1, 22), color="#9C27B0", alpha=0.8, edgecolor="white", align="left")
    ax.set_xlabel("Order interval between consecutive purchases (capped at 20)")
    ax.set_ylabel("Number of repeat events")
    ax.set_title("Observed Repeat-Interval Distribution\n"
                 f"{len(events):,} repeat events (single-purchase pairs excluded — interval is MISSING, not 0)")
    median = events["interval"].median()
    ax.axvline(median, color="black", linestyle="--", linewidth=1)
    ax.text(median + 0.3, ax.get_ylim()[1] * 0.9, f"median = {median:.0f}", fontsize=10)
    ax.set_xticks(range(1, 21))
    save_fig(fig, "repeat_interval_distribution")


def main():
    print("Generating reorder figures...")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    curves = pd.read_parquet(ANALYSIS_OUTPUTS / "reorder_curves.parquet")
    events = pd.read_parquet(ANALYSIS_OUTPUTS / "repeat_events.parquet")

    fig_product_vs_aisle(curves)
    fig_cohort(curves)
    fig_interval_distribution(events)
    print(f"\n✓ saved to {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
