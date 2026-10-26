#!/usr/bin/env python3
"""
Figures for the ingredient lens analysis.

1. ingredients_by_volume     — top 25 ingredients by purchase share (existing, improved)
2. stores_stock              — top 25 ingredients by catalog product count (existing, improved)
3. demand_vs_assortment      — scatterplot of all ingredients: catalog products vs purchases
4. ingredient_concentration  — how concentrated demand is within selected ingredients
5. effective_assortment      — products needed for 80% of volume vs catalog size
6. fresh_vs_packaged         — catalog breadth vs purchase share by food type
7. brand_multiplier          — per-customer products ÷ ingredients (existing, kept)
8. category_comparison       — demand vs assortment by taxonomy category
"""

import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

SEQ = Path(__file__).parent.parent.parent / "analysis" / "ingredients"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
CLF = Path(__file__).parent.parent.parent / "data" / "food_classification.csv"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"

FRESH_INGS = {
    "yogurt", "banana", "milk", "water", "apple", "plant_milk", "avocado",
    "onion", "strawberry", "tomato", "lettuce", "fresh_herbs", "carrot",
    "eggs", "spinach", "cucumber", "blueberry", "pepper", "potato",
    "chicken", "lemon", "garlic", "mushroom", "broccoli", "celery",
    "grapes", "pear", "ginger", "cheese", "butter", "sour_cream",
    "cream_cheese", "ground_beef", "salmon", "shrimp", "pork", "turkey",
    "deli_meat", "juice", "coffee", "tea",
}


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def _color(ing):
    return GREEN if ing in FRESH_INGS else ORANGE


def _legend_fresh_packaged(ax):
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GREEN, label="Fresh / whole food"),
                       Patch(color=ORANGE, label="Packaged / processed")],
              loc="lower right", frameon=True)


def fig_volume():
    vol = pl.read_csv(SEQ / "top_ingredients_by_volume.csv")
    names = vol["ingredient"].to_list()
    pcts = vol["purchase_pct"].to_list()
    colors = [_color(n) for n in names]

    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(names))
    ax.barh(y, pcts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("Share of all food purchases (%)")
    ax.set_title("What Customers Buy, by Ingredient\n"
                 "(purchase volume — not catalog product count)", fontweight="bold")
    for i, (p, r) in enumerate(zip(pcts, vol.iter_rows(named=True))):
        ax.text(p + 0.03, i, f"{p:.1f}%  ({r['catalog_products']} products)", va="center", fontsize=8)
    _legend_fresh_packaged(ax)
    ax.set_xlim(0, max(pcts) * 1.2)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "ingredients_by_volume")


def fig_stores_stock():
    clf = (pl.read_csv(CLF).filter((pl.col("is_food") == True)
           & pl.col("ingredient").is_not_null() & (pl.col("ingredient") != "unclassified")))
    cat = clf.group_by("ingredient").agg(pl.len().alias("n")).sort("n", descending=True).head(25)
    total = clf.height
    names = cat["ingredient"].to_list()
    pcts = [n / total * 100 for n in cat["n"].to_list()]
    colors = [_color(n) for n in names]

    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(names))
    ax.barh(y, pcts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("Share of catalog food products (%)")
    ax.set_title("What Stores Stock, by Ingredient\n"
                 "(catalog product count — not purchase volume)", fontweight="bold")
    for i, p in enumerate(pcts):
        ax.text(p + 0.03, i, f"{p:.1f}%  ({cat['n'].to_list()[i]:,})", va="center", fontsize=8)
    _legend_fresh_packaged(ax)
    ax.set_xlim(0, max(pcts) * 1.15)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "stores_stock")


def fig_demand_vs_assortment():
    """Scatterplot: catalog product count vs purchase volume, all ingredients."""
    df = pl.read_csv(SEQ / "all_ingredients.csv").filter(pl.col("purchases") > 0)
    x = df["catalog_products"].to_numpy()
    y = df["purchases"].to_numpy()
    names = df["ingredient"].to_list()
    colors = [_color(n) for n in names]

    fig, ax = plt.subplots(figsize=(11, 9))
    ax.scatter(x, y, c=colors, s=30, alpha=0.6, edgecolors="white", linewidth=0.3)

    # label interesting outliers
    labeled = set()
    for i, name in enumerate(names):
        ratio = y[i] / max(x[i], 1)
        inv_ratio = x[i] / max(y[i] / 1000, 1)
        is_high_demand_low_sku = ratio > 15000 and y[i] > 200000
        is_high_sku_low_demand = inv_ratio > 3 and x[i] > 200
        is_top = y[i] > 450000 or x[i] > 800
        if is_high_demand_low_sku or is_high_sku_low_demand or is_top:
            if name not in labeled:
                ax.annotate(name, (x[i], y[i]), fontsize=7.5, alpha=0.85,
                            xytext=(5, 3), textcoords="offset points")
                labeled.add(name)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Catalog products (log scale)")
    ax.set_ylabel("Total purchases (log scale)")
    ax.set_title("Demand vs. Assortment: Every Ingredient\n"
                 "Upper-left = high demand, few products · Lower-right = wide selection, low demand",
                 fontweight="bold")
    _legend_fresh_packaged(ax)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "demand_vs_assortment")


def fig_concentration():
    """Ranked product-share curves for selected ingredients."""
    conc = pl.read_csv(SEQ / "ingredient_concentration.csv")
    clf = pl.read_csv(CLF).filter(
        (pl.col("is_food") == True) & pl.col("ingredient").is_not_null())

    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analyze_reorder import iter_events

    # collect per-product volumes
    prod_vol = {}
    for chunk in iter_events():
        for pid, c in chunk.group_by("product_id").agg(pl.len().alias("c")).iter_rows():
            prod_vol[pid] = prod_vol.get(pid, 0) + c

    ping = dict(zip(clf["product_id"].to_list(), clf["ingredient"].to_list()))

    showcase = ["banana", "yogurt", "milk", "ice_cream", "coffee", "pasta",
                "crackers", "spinach", "granola_bar"]
    showcase = [s for s in showcase if s in set(ping.values())]

    fig, axes = plt.subplots(3, 3, figsize=(14, 11))
    for ax, ing in zip(axes.ravel(), showcase):
        vols = sorted(
            [prod_vol.get(pid, 0) for pid, i in ping.items() if i == ing],
            reverse=True
        )
        if not vols:
            continue
        tot = sum(vols)
        cumshare = np.cumsum(vols) / tot * 100
        ranks = np.arange(1, len(cumshare) + 1)

        ax.fill_between(ranks, cumshare, alpha=0.3, color=BLUE)
        ax.plot(ranks, cumshare, color=BLUE, linewidth=1.5)
        ax.axhline(80, color=RED, linestyle="--", linewidth=0.8, alpha=0.5)

        n80 = int(np.searchsorted(cumshare, 80)) + 1
        ax.axvline(n80, color=RED, linestyle=":", linewidth=0.8, alpha=0.5)
        cr = conc.filter(pl.col("ingredient") == ing).row(0, named=True)
        eff = cr["effective_n_products"]

        ax.set_title(f"{ing}\n{len(vols)} products, eff.N={eff:.0f}, "
                     f"80% in {n80}", fontsize=10, fontweight="bold")
        ax.set_xlabel("Products (ranked)" if ax in axes[-1] else "")
        ax.set_ylabel("Cumulative % of purchases" if ax in axes[:, 0] else "")
        ax.set_xlim(0, min(len(vols), max(n80 * 3, 20)))
        ax.set_ylim(0, 105)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    fig.suptitle("Demand Concentration Within Ingredients\n"
                 "How many products capture most of the purchases?",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    _save(fig, "ingredient_concentration")


def fig_effective_assortment():
    """For selected ingredients: total catalog vs products needed for 80% of volume."""
    conc = pl.read_csv(SEQ / "ingredient_concentration.csv")

    showcase = ["banana", "spinach", "eggs", "milk", "apple", "lettuce",
                "coffee", "pasta", "ice_cream", "crackers", "frozen_meal",
                "granola_bar", "candy", "yogurt"]
    df = conc.filter(pl.col("ingredient").is_in(showcase))
    # sort by catalog size for visual flow
    df = df.sort("catalog_products", descending=True)

    names = df["ingredient"].to_list()
    total = df["catalog_products"].to_list()
    n80 = df["n_for_80pct"].to_list()

    fig, ax = plt.subplots(figsize=(12, 7))
    y = np.arange(len(names))
    h = 0.4

    ax.barh(y, total, h, color=GRAY, alpha=0.4, edgecolor="white", label="Total catalog products")
    bars = ax.barh(y, n80, h, color=BLUE, edgecolor="white", label="Products needed for 80% of purchases")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Number of products")
    ax.set_title("How Much of the Catalog Captures 80% of Demand?\n"
                 "Gray = full catalog · Blue = products needed for 80% of purchases",
                 fontweight="bold")
    ax.legend(loc="lower right", frameon=True)

    for i, (t, n) in enumerate(zip(total, n80)):
        pct = n / t * 100
        ax.text(t + 8, i, f"{n} of {t}  ({pct:.0f}%)", va="center", fontsize=8.5)

    ax.set_xlim(0, max(total) * 1.35)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "effective_assortment")


def fig_fresh_vs_packaged():
    """Side-by-side bars: catalog share vs purchase share by food type."""
    fp = pl.read_csv(SEQ / "fresh_vs_packaged.csv")
    fp = fp.filter(pl.col("type") != "other").sort("purchases", descending=True)

    types = fp["type"].to_list()
    pur_pct = fp["purchase_pct"].to_list()
    cat_pct = fp["catalog_pct"].to_list()
    n_ings = fp["n_ingredients"].to_list()

    fig, ax = plt.subplots(figsize=(10, 5))
    y = np.arange(len(types))
    h = 0.35
    bars1 = ax.barh(y - h/2, pur_pct, h, color=BLUE, label="Share of purchases", edgecolor="white")
    bars2 = ax.barh(y + h/2, cat_pct, h, color=ORANGE, label="Share of catalog products", edgecolor="white")

    ax.set_yticks(y)
    ax.set_yticklabels([f"{t}\n({n} ingredients)" for t, n in zip(types, n_ings)])
    ax.set_xlabel("Percentage (%)")
    ax.set_title("Fresh Foods Dominate Purchases; Packaged Foods Dominate the Catalog",
                 fontweight="bold")
    ax.legend(loc="lower right", frameon=True)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    max_val = max(max(pur_pct), max(cat_pct))
    for bar, pct in zip(bars1, pur_pct):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{pct:.0f}%", va="center", fontsize=9, color=BLUE)
    for bar, pct in zip(bars2, cat_pct):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{pct:.0f}%", va="center", fontsize=9, color=ORANGE)
    ax.set_xlim(0, max_val * 1.2)

    fig.tight_layout()
    _save(fig, "fresh_vs_packaged")


def fig_multiplier():
    rep = pl.read_parquet(SEQ / "per_customer_repertoire.parquet")
    mult = rep["brand_multiplier"].to_numpy()
    mult = mult[np.isfinite(mult)]
    med = float(np.median(mult))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(np.clip(mult, 1, 3), bins=np.arange(1, 3.05, 0.1),
            color=BLUE, alpha=0.85, edgecolor="white")
    ax.axvline(med, color=RED, linestyle="--", linewidth=2,
               label=f"Median = {med:.2f}× products per ingredient")
    ax.set_xlabel("Distinct products ÷ distinct ingredients per customer")
    ax.set_ylabel("Customers")
    ax.set_title("How Much 'Variety' Is Just Brand Multiplicity?\n"
                 "Values >1 mean a customer buys several products that map to the same ingredient",
                 fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "brand_multiplier")


def fig_category_comparison():
    """Two side-by-side panels: what people buy vs what the catalog offers, by category."""
    cat = pl.read_csv(SEQ / "category_summary.csv")
    cat = cat.filter(
        ~pl.col("category").str.contains("NON-FOOD|PET|BABY")
        & (pl.col("purchases") > 0)
    ).sort("purchases", descending=True)

    names = [n.title() for n in cat["category"].to_list()]
    pur_pct = cat["purchase_pct"].to_list()
    cat_pct = cat["catalog_pct"].to_list()
    max_pct = max(max(pur_pct), max(cat_pct)) * 1.15

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8), sharey=True)
    y = np.arange(len(names))

    ax1.barh(y, pur_pct, color=BLUE, edgecolor="white", linewidth=0.5)
    ax1.set_yticks(y); ax1.set_yticklabels(names, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("Share of purchases (%)")
    ax1.set_title("What People Buy", fontweight="bold", fontsize=13)
    ax1.set_xlim(0, max_pct)
    for i, p in enumerate(pur_pct):
        ax1.text(p + 0.2, i, f"{p:.1f}%", va="center", fontsize=8)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    ax2.barh(y, cat_pct, color=ORANGE, edgecolor="white", linewidth=0.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("Share of catalog products (%)")
    ax2.set_title("What the Catalog Stocks", fontweight="bold", fontsize=13)
    ax2.set_xlim(0, max_pct)
    for i, p in enumerate(cat_pct):
        ax2.text(p + 0.2, i, f"{p:.1f}%", va="center", fontsize=8)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.suptitle("Demand vs. Catalog Share by Category", fontweight="bold", fontsize=14, y=0.98)
    fig.tight_layout()
    _save(fig, "category_comparison")


def main():
    print("Generating ingredient-lens figures...")
    fig_volume()
    fig_stores_stock()
    fig_demand_vs_assortment()
    fig_fresh_vs_packaged()
    fig_multiplier()
    fig_effective_assortment()
    fig_category_comparison()
    # concentration is slow (re-streams purchase data), run last
    fig_concentration()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
