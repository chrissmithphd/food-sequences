#!/usr/bin/env python3
"""
Figures for the basket contents analysis.

1. basket_size           — distribution of food items per order
2. basket_composition    — department share of items
3. composition_by_size   — how department mix shifts with basket size
4. diversity_vs_size     — ingredients and categories per basket vs basket size
5. dominant_category     — what category dominates each basket
6. cooccurrence_support_lift — support vs lift scatterplot
7. category_heatmap      — category-level co-occurrence lift matrix
8. conditional_companions — top companions for selected ingredients
9. triplets              — recognizable three-ingredient combinations
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

SEQ = Path(__file__).parent.parent.parent / "analysis" / "basket"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"
FRESH_DEPTS = {"produce", "meat seafood", "dairy eggs", "deli"}


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def fig_basket_size():
    """Basket size distribution — reuses data from analyze_basket_contents pass 1."""
    # We need the raw sizes; re-stream a quick pass for just sizes
    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analyze_reorder import iter_events
    sizes = []
    for chunk in iter_events():
        per = chunk.group_by(["user_id", "order_number"]).agg(pl.len().alias("items"))
        sizes.append(per["items"].to_numpy())
    sizes = np.concatenate(sizes)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(np.clip(sizes, 1, 30), bins=np.arange(1, 31),
            color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
    med = float(np.median(sizes))
    ax.axvline(med, color=RED, linestyle="--", linewidth=2,
               label=f"Median {med:.0f} food items")
    ax.set_xlabel("Food items per order")
    ax.set_ylabel("Baskets")
    ax.set_title("How Big Is a Basket?", fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "basket_size")
    return sizes


def fig_composition():
    df = pl.read_csv(SEQ / "basket_contents_summary.csv")
    df = df.sort("item_share_pct", descending=True).head(12)
    names = df["department"].to_list()
    shares = df["item_share_pct"].to_list()
    colors = [GREEN if d in FRESH_DEPTS else ORANGE for d in names]

    fig, ax = plt.subplots(figsize=(10, 6.5))
    y = np.arange(len(names))
    ax.barh(y, shares, color=colors, edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("Share of all food items (%)")
    ax.set_title("What's in the Basket? Item share by department", fontweight="bold")
    for i, s in enumerate(shares):
        ax.text(s + 0.3, i, f"{s:.1f}%", va="center", fontsize=9)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GREEN, label="Fresh (produce, meat, dairy, deli)"),
                       Patch(color=ORANGE, label="Packaged / pantry")],
              loc="lower right", frameon=True)
    ax.set_xlim(0, max(shares) * 1.18)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "basket_composition")


def fig_composition_by_size():
    """How basket composition shifts with size."""
    df = pl.read_csv(SEQ / "composition_by_size.csv")
    # extract department columns
    dept_cols = [c for c in df.columns if c.startswith("dept_")]
    top_depts = ["produce", "dairy eggs", "snacks", "beverages", "frozen", "pantry"]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(df.height)
    labels = df["basket_size"].to_list()
    bottom = np.zeros(df.height)
    colors = {"produce": GREEN, "dairy eggs": "#1565C0", "snacks": ORANGE,
              "beverages": "#7B1FA2", "frozen": "#0097A7", "pantry": "#795548"}

    for dept in top_depts:
        col = f"dept_{dept}"
        if col not in df.columns:
            continue
        vals = df[col].fill_null(0).to_numpy()
        ax.bar(x, vals, bottom=bottom, label=dept,
               color=colors.get(dept, GRAY), edgecolor="white", linewidth=0.5)
        bottom += vals

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("Basket size (food items)")
    ax.set_ylabel("Share of items (%)")
    ax.set_title("How Basket Composition Shifts with Size", fontweight="bold")
    ax.legend(loc="upper right", frameon=True, fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "composition_by_size")


def fig_diversity_vs_size():
    """Ingredients and categories per basket vs basket size."""
    df = pl.read_csv(SEQ / "diversity_by_size.csv")
    sz = df["basket_size"].to_numpy()
    ings = df["mean_ingredients"].to_numpy()
    cats = df["mean_categories"].to_numpy()
    ratio = df["ingredients_per_item"].to_numpy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ax1.plot(sz, ings, "o-", color=BLUE, markersize=4, label="Distinct ingredients")
    ax1.plot(sz, cats, "s-", color=ORANGE, markersize=4, label="Distinct categories")
    ax1.plot(sz, sz, "--", color=GRAY, alpha=0.4, label="y = x (one ingredient per item)")
    ax1.set_xlabel("Basket size (food items)")
    ax1.set_ylabel("Mean distinct count")
    ax1.set_title("Basket Diversity vs. Size", fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    ax2.plot(sz, ratio, "o-", color=PURPLE, markersize=4)
    ax2.axhline(1.0, color=GRAY, linestyle="--", alpha=0.4)
    ax2.set_xlabel("Basket size (food items)")
    ax2.set_ylabel("Distinct ingredients ÷ items")
    ax2.set_title("Ingredient Density Drops in Larger Baskets", fontweight="bold")
    ax2.set_ylim(0.5, 1.05)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.tight_layout()
    _save(fig, "basket_diversity")


def fig_dominant_category():
    df = pl.read_csv(SEQ / "dominant_category.csv").head(12)
    names = [n.title() for n in df["category"].to_list()]
    pcts = df["pct"].to_list()

    fig, ax = plt.subplots(figsize=(11, 6))
    y = np.arange(len(names))
    ax.barh(y, pcts, color=BLUE, edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9); ax.invert_yaxis()
    ax.set_xlabel("Share of baskets (%)")
    ax.set_title("What Category Dominates Each Basket?\n"
                 "(category with the most items in each order)",
                 fontweight="bold")
    for i, p in enumerate(pcts):
        ax.text(p + 0.3, i, f"{p:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, max(pcts) * 1.15)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "dominant_category")


def fig_support_vs_lift():
    """Scatterplot: support vs lift for all ingredient pairs."""
    co = pl.read_csv(SEQ / "cooccurrence_pairs.csv")
    x = co["support"].to_numpy()
    y = co["lift"].to_numpy()
    names_a = co["a"].to_list()
    names_b = co["b"].to_list()

    fig, ax = plt.subplots(figsize=(11, 8))
    ax.scatter(x, y, s=15, alpha=0.4, color=BLUE, edgecolors="none")

    # label interesting points
    labeled = set()
    for i in range(len(x)):
        label = f"{names_a[i]}+{names_b[i]}"
        if y[i] > 40 or (y[i] > 15 and x[i] > 1000) or x[i] > 200000:
            if label not in labeled:
                ax.annotate(f"{names_a[i]} +\n{names_b[i]}", (x[i], y[i]),
                            fontsize=7, alpha=0.8, xytext=(5, 3),
                            textcoords="offset points")
                labeled.add(label)

    ax.set_xscale("log")
    ax.set_xlabel("Support (orders containing both)")
    ax.set_ylabel("Lift")
    ax.set_title("Ingredient Pair Associations: Support vs. Lift\n"
                 "Upper-left = rare but strongly associated · Lower-right = common but expected",
                 fontweight="bold")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "cooccurrence_support_lift")


def fig_category_heatmap():
    """Category-level co-occurrence lift as a heatmap."""
    cat_co = pl.read_csv(SEQ / "category_cooccurrence.csv")
    # filter to food categories
    food_cats = {c for c in cat_co["a"].unique().to_list()
                 if "NON-FOOD" not in c and "PET" not in c}
    food_cats |= {c for c in cat_co["b"].unique().to_list()
                  if "NON-FOOD" not in c and "PET" not in c}
    cat_co = cat_co.filter(pl.col("a").is_in(food_cats) & pl.col("b").is_in(food_cats))

    all_cats = sorted(food_cats)
    n = len(all_cats)
    cat_idx = {c: i for i, c in enumerate(all_cats)}
    matrix = np.ones((n, n))
    for r in cat_co.iter_rows(named=True):
        i, j = cat_idx.get(r["a"]), cat_idx.get(r["b"])
        if i is not None and j is not None:
            matrix[i, j] = r["lift"]
            matrix[j, i] = r["lift"]

    short_names = [c.replace("PRODUCE - ", "").replace("PROTEIN - ", "")
                   .replace(" & ", "/").title() for c in all_cats]

    fig, ax = plt.subplots(figsize=(13, 10))
    im = ax.imshow(matrix, cmap="RdYlBu_r", vmin=0.6, vmax=1.6, aspect="auto")
    ax.set_xticks(range(n)); ax.set_xticklabels(short_names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n)); ax.set_yticklabels(short_names, fontsize=8)
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("Lift (>1 = co-occur more than expected)")
    ax.set_title("Which Food Categories Travel Together?\n"
                 "Lift > 1 (warm) = appear together more than expected",
                 fontweight="bold")
    fig.tight_layout()
    _save(fig, "category_heatmap")


def fig_conditional_companions():
    """Top companions for selected ingredients, by lift."""
    comp = pl.read_csv(SEQ / "conditional_companions.csv")
    focus = ["banana", "pasta", "eggs", "garlic"]
    focus = [f for f in focus if f in comp["ingredient"].unique().to_list()]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, ing in zip(axes.ravel(), focus):
        sub = comp.filter(pl.col("ingredient") == ing).sort("lift", descending=True).head(12)
        if sub.height == 0:
            continue
        names = sub["companion"].to_list()[::-1]
        lifts = sub["lift"].to_list()[::-1]
        supports = sub["support"].to_list()[::-1]

        colors = [BLUE if l > 1.5 else GRAY for l in lifts]
        y = np.arange(len(names))
        ax.barh(y, lifts, color=colors, edgecolor="white")
        ax.axvline(1.0, color=RED, linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("Lift")
        ax.set_title(f"Given {ing}, what else appears?", fontweight="bold", fontsize=11)
        for i, (l, s) in enumerate(zip(lifts, supports)):
            ax.text(l + 0.03, i, f"{l:.1f}× ({s:,})", va="center", fontsize=7.5)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    fig.suptitle("Conditional Companions: What Travels With Each Ingredient?",
                 fontweight="bold", fontsize=14, y=0.98)
    fig.tight_layout()
    _save(fig, "conditional_companions")


def fig_triplets():
    """Top ingredient triplets by lift."""
    trip = pl.read_csv(SEQ / "ingredient_triplets.csv")
    trip = trip.sort("lift3", descending=True).head(15)

    labels = [f"{r['a']} + {r['b']} + {r['c']}" for r in trip.iter_rows(named=True)][::-1]
    lifts = trip["lift3"].to_list()[::-1]
    supports = trip["support"].to_list()[::-1]

    fig, ax = plt.subplots(figsize=(12, 7))
    y = np.arange(len(labels))
    ax.barh(y, lifts, color=BLUE, edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Three-way lift")
    ax.set_title("Three-Ingredient Combinations Above Chance\n"
                 "Lift = how many times more common than if each ingredient were independent",
                 fontweight="bold")
    max_lift = max(lifts)
    for i, (l, s) in enumerate(zip(lifts, supports)):
        ax.text(l + max_lift * 0.02, i, f"{s:,} baskets", va="center", fontsize=8.5)
    ax.set_xlim(0, max_lift * 1.25)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "ingredient_triplets")


def main():
    print("Generating basket figures...")
    fig_composition()
    fig_composition_by_size()
    fig_diversity_vs_size()
    fig_dominant_category()
    fig_support_vs_lift()
    fig_category_heatmap()
    fig_conditional_companions()
    fig_triplets()
    # basket_size needs a full data pass, run last
    fig_basket_size()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
