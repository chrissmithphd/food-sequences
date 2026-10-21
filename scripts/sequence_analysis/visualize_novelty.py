#!/usr/bin/env python3
"""
Figures for the novelty analysis.

1. novelty_decay              — existing: new-ingredient share by order position
2. novelty_by_category        — ingredient vs product novelty rates by food category
3. novelty_vs_basket_size     — novelty rate and absolute discoveries by basket size
4. repertoire_growth_bands    — percentile bands for repertoire accumulation
5. discovery_popularity       — are discoveries common or rare ingredients?
6. customer_novelty_dist      — distribution of per-customer novelty rates
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

SEQ = Path(__file__).parent.parent.parent / "analysis" / "novelty"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def fig_novelty_decay():
    """Existing novelty-decay figure, regenerated."""
    d = pl.read_csv(SEQ / "novelty_by_order_position.csv").filter(pl.col("order_number") <= 80)
    x = d["order_number"].to_list()
    newi = [v * 100 for v in d["new_ing"].to_list()]
    famp = [v * 100 for v in d["fam_prod"].to_list()]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, newi, color=ORANGE, linewidth=2.5, label="New ingredient (never seen before)")
    ax.plot(x, famp, color=BLUE, linewidth=2.5, label="Familiar product (exact repeat)")
    ax.axhspan(5, 8, color=ORANGE, alpha=0.08)
    ax.annotate("steady-state exploration ≈ 5–7%", xy=(70, 6.5), xytext=(45, 20),
                fontsize=10, color=ORANGE,
                arrowprops=dict(arrowstyle="->", color=ORANGE))
    ax.annotate("order 1 is 100% 'new' by construction\n(we can't see prior history → truncation)",
                xy=(2, 90), xytext=(12, 88), fontsize=9, color="#555",
                arrowprops=dict(arrowstyle="->", color="#999"))
    ax.set_xlabel("Order position in observed history")
    ax.set_ylabel("Share of basket items (%)")
    ax.set_title("Apparent 'novelty' is mostly truncation\n"
                 "New-ingredient share decays from 100% to a ~6% floor as history lengthens",
                 fontweight="bold", fontsize=12)
    ax.legend(loc="center right")
    ax.set_ylim(0, 100)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "novelty_decay")


def fig_novelty_by_category():
    """Ingredient vs product novelty rates by food category."""
    df = pl.read_csv(SEQ / "novelty_by_category.csv")
    df = df.filter(
        ~pl.col("category").str.contains("NON-FOOD|PET|Unknown")
        & (pl.col("total_items") > 10000)
    ).sort("new_ingredient_rate", descending=True)

    names = [n.title() for n in df["category"].to_list()]
    ing_rate = df["new_ingredient_rate"].to_list()
    prod_only = df["product_novelty_minus_ingredient"].to_list()

    fig, ax = plt.subplots(figsize=(13, 7))
    y = np.arange(len(names))
    h = 0.7
    ax.barh(y, ing_rate, h, color=BLUE, label="New ingredient", edgecolor="white")
    ax.barh(y, prod_only, h, left=ing_rate, color=ORANGE,
            label="New product, familiar ingredient", edgecolor="white")

    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Share of items that are new (%)")
    ax.set_title("Where Does Novelty Happen?\n"
                 "Blue = new ingredient · Orange = new product for a familiar ingredient",
                 fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    for i, (ir, po) in enumerate(zip(ing_rate, prod_only)):
        ax.text(ir + po + 0.5, i, f"{ir + po:.0f}%", va="center", fontsize=8)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "novelty_by_category")


def fig_novelty_vs_basket():
    """Novelty rate and absolute count by basket size."""
    df = pl.read_csv(SEQ / "novelty_vs_basket_size.csv")
    sz = df["basket_size"].to_numpy()
    rate = df["new_ing_rate"].to_numpy()
    per_basket = df["new_ing_per_basket"].to_numpy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ax1.plot(sz, rate, "o-", color=BLUE, markersize=4, linewidth=1.5)
    ax1.set_xlabel("Basket size (food items)")
    ax1.set_ylabel("New-ingredient items (%)")
    ax1.set_title("Novelty Rate Is Flat Across Basket Sizes", fontweight="bold")
    ax1.set_ylim(0, max(rate) * 1.3)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    ax2.plot(sz, per_basket, "o-", color=GREEN, markersize=4, linewidth=1.5)
    ax2.set_xlabel("Basket size (food items)")
    ax2.set_ylabel("New ingredients per basket")
    ax2.set_title("But Bigger Baskets Discover More in Absolute Terms", fontweight="bold")
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.tight_layout()
    _save(fig, "novelty_vs_basket_size")


def fig_repertoire_bands():
    """Repertoire growth with percentile bands."""
    df = pl.read_csv(SEQ / "repertoire_growth_percentiles.csv")
    pos = df["order_position"].to_numpy()
    p10 = df["p10"].to_numpy()
    p25 = df["p25"].to_numpy()
    p50 = df["p50"].to_numpy()
    p75 = df["p75"].to_numpy()
    p90 = df["p90"].to_numpy()
    mean = df["mean"].to_numpy()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.fill_between(pos, p10, p90, color=BLUE, alpha=0.1, label="p10–p90")
    ax.fill_between(pos, p25, p75, color=BLUE, alpha=0.2, label="p25–p75")
    ax.plot(pos, p50, "o-", color=BLUE, linewidth=2, markersize=5, label="Median")
    ax.plot(pos, mean, "--", color=ORANGE, linewidth=1.5, label="Mean")

    ax.set_xlabel("Order position")
    ax.set_ylabel("Cumulative distinct ingredients")
    ax.set_title("Repertoire Growth: How Quickly Do Customers Accumulate Ingredients?\n"
                 "Bands show customer variation at each order position",
                 fontweight="bold")
    ax.legend(loc="upper left")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "repertoire_growth_bands")


def fig_discovery_popularity():
    """Are newly discovered ingredients popular or rare?"""
    df = pl.read_csv(SEQ / "discovery_popularity.csv")
    df = df.filter(pl.col("total_purchases") > 0)
    df = df.sort("total_purchases", descending=True)
    df = df.with_row_index("rank")

    # cumulative share curves
    purch_cum = np.cumsum(df["purchase_share_pct"].to_numpy())
    disc_cum = np.cumsum(df["discovery_share_pct"].to_numpy())
    ranks = np.arange(1, len(purch_cum) + 1)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(ranks, purch_cum, color=BLUE, linewidth=2, label="Cumulative purchase share")
    ax.plot(ranks, disc_cum, color=ORANGE, linewidth=2, label="Cumulative discovery share")
    ax.plot([0, len(ranks)], [0, 100], "--", color=GRAY, alpha=0.3, label="Uniform (all equal)")

    ax.set_xlabel("Ingredients (ranked by purchase volume)")
    ax.set_ylabel("Cumulative share (%)")
    ax.set_title("Discoveries Are Spread Toward the Long Tail\n"
                 "Orange below blue = rare ingredients contribute disproportionately to discoveries",
                 fontweight="bold")
    ax.legend(loc="lower right")
    ax.set_xlim(0, len(ranks))
    ax.set_ylim(0, 105)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "discovery_popularity")


def fig_customer_novelty_dist():
    """Distribution of per-customer novelty rates at controlled history length."""
    df = pl.read_csv(SEQ / "customer_novelty_rates.csv")
    ing_rates = df["new_ing_rate"].to_numpy()
    ing_rates = ing_rates[np.isfinite(ing_rates)]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(ing_rates * 100, bins=np.arange(0, 65, 2.5), color=BLUE, alpha=0.85,
            edgecolor="white", linewidth=0.3)
    med = float(np.median(ing_rates)) * 100
    ax.axvline(med, color=RED, linestyle="--", linewidth=2,
               label=f"Median {med:.0f}%")
    ax.set_xlabel("New-ingredient rate (%, orders 10–15)")
    ax.set_ylabel("Customers")
    ax.set_title("How Much Do Individual Customers Explore?\n"
                 "Per-customer new-ingredient rate at orders 10–15 (users with 15–25 total orders)",
                 fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "customer_novelty_distribution")


def main():
    print("Generating novelty figures...")
    fig_novelty_decay()
    fig_novelty_by_category()
    fig_novelty_vs_basket()
    fig_repertoire_bands()
    fig_discovery_popularity()
    fig_customer_novelty_dist()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
