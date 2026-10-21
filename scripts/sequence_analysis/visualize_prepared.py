#!/usr/bin/env python3
"""
Figures for the prepared-dish analysis.

1. prepared_basket_comparison — category composition: with vs without prepared
2. prepared_customer_dist     — customer prepared-share distribution
3. prepared_basket_dist       — how many prepared items per basket
4. prepared_assortment        — catalog products vs purchases per dish type
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

SEQ = Path(__file__).parent.parent.parent / "analysis" / "prepared"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def fig_basket_comparison():
    """Category composition in baskets with vs without prepared dishes."""
    df = pl.read_csv(SEQ / "basket_composition_comparison.csv")
    df = df.filter(
        ~pl.col("category").str.contains("NON-FOOD|PET|Unknown|BABY")
        & (pl.col("category") != "PREPARED DISHES & MEALS")
    ).sort("difference", descending=True)

    names = [n.title() for n in df["category"].to_list()]
    with_pct = df["pct_in_prep_baskets"].to_list()
    without_pct = df["pct_in_noprep_baskets"].to_list()

    fig, ax = plt.subplots(figsize=(13, 7))
    y = np.arange(len(names))
    h = 0.35
    ax.barh(y - h/2, with_pct, h, color=BLUE, label="Baskets with prepared dish", edgecolor="white")
    ax.barh(y + h/2, without_pct, h, color=GRAY, label="Baskets without", edgecolor="white")

    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Share of non-prepared items (%)")
    ax.set_title("What Else Is in the Basket?\n"
                 "Category composition of baskets with vs without prepared dishes\n"
                 "(prepared-dish items excluded from both)",
                 fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "prepared_basket_comparison")


def fig_customer_distribution():
    """Distribution of customer prepared-food share."""
    shares = np.load(SEQ / "customer_prep_shares.npy")
    shares = shares[np.isfinite(shares)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # all customers including zero
    ax1.hist(np.clip(shares, 0, 40), bins=np.arange(0, 41, 1),
             color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
    zero_pct = (shares == 0).mean() * 100
    ax1.annotate(f"{zero_pct:.0f}% buy\nzero prepared", xy=(0.5, ax1.get_ylim()[1] * 0.7),
                 fontsize=10, color=RED, fontweight="bold")
    ax1.set_xlabel("Prepared dishes as % of food items")
    ax1.set_ylabel("Customers")
    ax1.set_title("All Customers", fontweight="bold")
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    # buyers only
    nonzero = shares[shares > 0]
    ax2.hist(np.clip(nonzero, 0, 40), bins=np.arange(0, 41, 1),
             color=PURPLE, alpha=0.85, edgecolor="white", linewidth=0.3)
    med = float(np.median(nonzero))
    ax2.axvline(med, color=RED, linestyle="--", linewidth=2,
                label=f"Median {med:.0f}%")
    ax2.set_xlabel("Prepared dishes as % of food items")
    ax2.set_ylabel("Customers (buyers only)")
    ax2.set_title("Among Prepared-Dish Buyers", fontweight="bold")
    ax2.legend(loc="upper right")
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.suptitle("How Much Do Customers Rely on Prepared Food?",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    _save(fig, "prepared_customer_distribution")


def fig_basket_distribution():
    """How many prepared items per basket."""
    df = pl.read_csv(SEQ / "basket_prep_distribution.csv")
    items = df["prep_items"].to_list()
    pcts = df["pct"].to_list()

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [GRAY if i == 0 else BLUE for i in items]
    ax.bar(items, pcts, color=colors, edgecolor="white")
    ax.set_xlabel("Number of prepared items in basket")
    ax.set_ylabel("Share of baskets (%)")
    ax.set_title("Most Baskets Have Zero Prepared Items\n"
                 "When present, it's usually one or two",
                 fontweight="bold")
    for i, p in zip(items, pcts):
        if p > 0.3:
            ax.text(i, p + 0.5, f"{p:.1f}%", ha="center", fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "prepared_basket_distribution")


def fig_assortment_vs_demand():
    """Catalog products vs purchases per dish type."""
    df = pl.read_csv(SEQ / "assortment_vs_demand.csv")
    df = df.filter(pl.col("catalog_products") > 0).sort("customers", descending=True).head(12)

    names = df["dish_type"].to_list()
    products = df["catalog_products"].to_list()
    per_prod = df["purchases_per_product"].to_list()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    y = np.arange(len(names))
    ax1.barh(y, products, color=BLUE, edgecolor="white")
    ax1.set_yticks(y); ax1.set_yticklabels(names, fontsize=9); ax1.invert_yaxis()
    ax1.set_xlabel("Catalog products")
    ax1.set_title("Product Selection", fontweight="bold")
    for i, p in enumerate(products):
        ax1.text(p + 5, i, str(p), va="center", fontsize=8.5)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    ax2.barh(y, per_prod, color=GREEN, edgecolor="white")
    ax2.set_yticks(y); ax2.set_yticklabels(names, fontsize=9); ax2.invert_yaxis()
    ax2.set_xlabel("Purchases per product")
    ax2.set_title("Demand Concentration", fontweight="bold")
    for i, p in enumerate(per_prod):
        ax2.text(p + 10, i, f"{p:.0f}", va="center", fontsize=8.5)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.suptitle("Prepared-Dish Assortment vs. Demand",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    _save(fig, "prepared_assortment")


def main():
    print("Generating prepared-dish figures...")
    fig_basket_comparison()
    fig_customer_distribution()
    fig_basket_distribution()
    fig_assortment_vs_demand()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
