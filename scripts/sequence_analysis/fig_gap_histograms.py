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
    fig, ax = plt.subplots(figsize=(11, 6.5))

    for ing, color in zip(INGREDIENTS, COLORS):
        sub = d.filter(pl.col("ingredient") == ing).sort("gap_orders")
        gaps = sub["gap_orders"].to_list()
        counts = sub["count"].to_list()
        total = sum(counts)
        if total == 0:
            continue
        pcts = [c / total * 100 for c in counts]
        label = ing.replace("_", " ")
        ax.plot(gaps[:12], pcts[:12], "-o", color=color, markersize=5,
                linewidth=2.2, label=label, alpha=0.85)

    ax.set_xlabel("Orders between consecutive purchases")
    ax.set_ylabel("Share of repurchase events (%)")
    ax.legend(fontsize=9, loc="upper right")
    ax.set_xlim(0.5, 12.5)
    ax.set_xticks(range(1, 13))
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
