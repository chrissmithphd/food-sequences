#!/usr/bin/env python3
"""Figures for the ingredient lens: purchase-volume ranking and brand multiplier."""

import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

SEQ = Path(__file__).parent.parent.parent / "analysis" / "ingredients"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

# Fresh / whole foods vs packaged, for color coding
FRESH = {"yogurt", "banana", "milk", "water", "apple", "plant_milk", "avocado",
         "onion", "strawberry", "tomato", "lettuce", "fresh_herbs", "carrot",
         "eggs", "spinach", "deli_meat"}


def fig_catalog_vs_volume():
    """Paired bars: purchase-volume share vs catalog product-count share, per
    ingredient (top by volume). Shows the catalog-size bias — fresh staples are a
    large share of purchases but a tiny share of the catalog, and vice versa."""
    vol = pl.read_csv(SEQ / "top_ingredients_by_volume.csv").head(15)
    names = vol["ingredient"].to_list()
    v = vol["pct"].to_list()
    c = vol["catalog_pct"].to_list()
    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(10, 7.5))
    ax.barh(y - 0.2, v, height=0.4, color="#2E7D32", edgecolor="white", label="Share of purchases (what customers buy)")
    ax.barh(y + 0.2, c, height=0.4, color="#EF6C00", edgecolor="white", label="Share of catalog products (what's stocked)")
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("Share (%)")
    ax.set_title("What Customers Buy vs. What the Catalog Stocks\n"
                 "top ingredients by purchase volume", fontweight="bold")
    ax.legend(loc="lower right", frameon=True)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"catalog_vs_volume.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved catalog_vs_volume.png")


def fig_volume():
    vol = pl.read_csv(SEQ / "top_ingredients_by_volume.csv")
    names = vol["ingredient"].to_list()
    pcts = vol["pct"].to_list()
    colors = ["#2E7D32" if n in FRESH else "#EF6C00" for n in names]

    fig, ax = plt.subplots(figsize=(10, 7))
    y = np.arange(len(names))
    ax.barh(y, pcts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("Share of all food purchases (%)")
    ax.set_title("What Customers Actually Buy, by Ingredient\n"
                 "(purchase volume — not catalog product count)", fontweight="bold")
    for i, p in enumerate(pcts):
        ax.text(p + 0.03, i, f"{p:.1f}%", va="center", fontsize=9)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#2E7D32", label="Fresh / whole food"),
                       Patch(color="#EF6C00", label="Packaged")],
              loc="lower right", frameon=True)
    ax.set_xlim(0, max(pcts) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"ingredients_by_volume.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved ingredients_by_volume.png")


def fig_multiplier():
    rep = pl.read_parquet(SEQ / "per_customer_repertoire.parquet")
    mult = rep["brand_multiplier"].to_numpy()
    mult = mult[np.isfinite(mult)]
    med = float(np.median(mult))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(np.clip(mult, 1, 3), bins=np.arange(1, 3.05, 0.1),
            color="#1565C0", alpha=0.85, edgecolor="white")
    ax.axvline(med, color="#C62828", linestyle="--", linewidth=2,
               label=f"Median = {med:.2f}× products per ingredient")
    ax.set_xlabel("Distinct products ÷ distinct ingredients per customer")
    ax.set_ylabel("Customers")
    ax.set_title("How Much 'Variety' Is Just Brand Multiplicity?\n"
                 "Values >1 mean a customer buys several products that map to the same ingredient",
                 fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"brand_multiplier.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved brand_multiplier.png")


def main():
    print("Generating ingredient-lens figures...")
    fig_volume()
    fig_catalog_vs_volume()
    fig_multiplier()
    print(f"Saved to {FIG}")


if __name__ == "__main__":
    main()
