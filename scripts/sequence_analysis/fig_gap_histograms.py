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

GROUPS = [
    ("Staples", ["banana", "milk", "eggs"], [BLUE, "#1976D2", "#42A5F5"]),
    ("Proteins", ["chicken_breast", "ground_beef", "steak", "salmon"], [GREEN, "#43A047", "#66BB6A", "#A5D6A7"]),
    ("Occasional / specialty", ["pasta", "ice_cream", "curry_paste"], [ORANGE, RED, PURPLE]),
]


def main():
    d = pl.read_csv(SEQ / "gap_histograms.csv")
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), sharey=True)

    for ax, (title, ings, colors) in zip(axes, GROUPS):
        for ing, color in zip(ings, colors):
            sub = d.filter(pl.col("ingredient") == ing).sort("gap_orders")
            gaps = sub["gap_orders"].to_list()
            counts = sub["count"].to_list()
            total = sum(counts)
            if total == 0:
                continue
            pcts = [c / total * 100 for c in counts]
            label = ing.replace("_", " ")
            ax.plot(gaps[:15], pcts[:15], "-o", color=color, markersize=4,
                    linewidth=2, label=f"{label} (n={total:,})", alpha=0.85)
        ax.set_xlabel("Orders between purchases")
        ax.set_title(title, fontweight="bold", fontsize=11)
        ax.legend(fontsize=8, loc="upper right")
        ax.set_xlim(0.5, 15.5)
        ax.set_xticks(range(1, 16))

    axes[0].set_ylabel("Share of repurchase events (%)")
    fig.suptitle("How often do customers repurchase each ingredient?\n"
                 "Banana and milk appear nearly every order; steak and curry paste are "
                 "separated by many orders",
                 fontweight="bold", fontsize=12, y=1.02)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"gap_histograms.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved gap_histograms.png")


if __name__ == "__main__":
    main()
