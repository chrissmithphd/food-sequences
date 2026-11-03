#!/usr/bin/env python3
"""Inter-purchase gap histograms for selected ingredients.

Shows how many orders pass between consecutive purchases — banana nearly every order,
steak every few, curry paste rarely. More intuitive than gap CV for a general audience.
Reads analysis/sequences/gap_histograms.csv, writes analysis/figures/gap_histograms.png.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SEQ = ROOT / "analysis" / "sequences"
FIG = ROOT / "analysis" / "figures"

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"

INGREDIENTS = ["banana", "milk", "eggs", "chicken_breast", "steak", "pasta", "curry_paste"]
COLORS = [BLUE, "#1976D2", "#42A5F5", GREEN, "#43A047", ORANGE, PURPLE]


def main():
    d = pl.read_csv(SEQ / "gap_histograms.csv")

    # Reconstruct raw gap values from histogram for boxplot
    data, labels = [], []
    for ing in INGREDIENTS:
        sub = d.filter(pl.col("ingredient") == ing)
        vals = []
        for g, c in sub.select("gap_orders", "count").iter_rows():
            vals.extend([g] * c)
        data.append(np.array(vals))
        labels.append(ing.replace("_", " "))

    fig, ax = plt.subplots(figsize=(11, 6))
    bp = ax.boxplot(data, vert=False, patch_artist=True, whis=(10, 90),
                    showfliers=False, widths=0.6,
                    medianprops=dict(color="white", linewidth=2))
    for patch, color in zip(bp["boxes"], COLORS):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("Orders between consecutive purchases (10th–90th percentile)")
    ax.set_xlim(0, 25)
    # annotate medians
    for i, vals in enumerate(data):
        med = float(np.median(vals))
        ax.text(med + 0.3, i + 1, f"med={med:.0f}", va="center", fontsize=8, color="#333")
    ax.set_title("How many orders pass between purchases?\n"
                 "Banana and milk return nearly every order; "
                 "steak and curry paste are spread across many",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"gap_histograms.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved gap_histograms.png")


if __name__ == "__main__":
    main()
