#!/usr/bin/env python3
"""Generate food-profile timeline heatmaps for example customers.

Each panel shows one customer: orders (columns) × food profiles (rows), colored by
whether that order contained distinctive ingredients for that profile. Shows real
purchasing sequences — consistency, shifts, and breadth patterns.

Finds specific example customers matching criteria:
  - roasts: minimal engagement (barely touches roasts)
  - meat-centered vs seafood-oriented: two customers with opposite leans
  - consistent curry buyer
  - broad omnivore
  - someone who shifts styles over time

Usage: uv run python -I scripts/affinity/profile_timelines.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "sequence_analysis"))
from analyze_reorder import iter_events  # noqa: E402

AFF = ROOT / "data" / "affinity"
FIG = ROOT / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"
LIFT_MIN, SUPPORT_MIN = 2.0, 30

# meal-style profiles to show (most interpretable subset)
SHOW_PROFILES = [
    "breakfast", "salads", "soups_stews", "pasta_dishes", "curries",
    "stir_fries", "chili", "sweet_baking", "bread_baking",
    "grilling_bbq", "pizza", "sandwiches", "casseroles", "roasts",
]


def load_signatures():
    a = pl.read_csv(AFF / "ingredient_associations.csv")
    aff = pl.read_csv(AFF / "affinities.csv").select("affinity_id", "dimension")
    return (a.filter((pl.col("lift") >= LIFT_MIN) & (pl.col("support") >= SUPPORT_MIN))
            .select("affinity_id", "slug")
            .join(aff, on="affinity_id", how="left")
            .filter(pl.col("dimension") == "meal_style"))


def build_order_profile_matrix():
    """Return (user_id, order_number, affinity_id) triples + order counts."""
    sig = load_signatures()
    parts = []
    order_parts = []
    for chunk in iter_events():
        ev = chunk.select("user_id", "order_number", "ingredient").unique()
        order_parts.append(ev.select("user_id", "order_number").unique()
                           .group_by("user_id").agg(pl.col("order_number").max().alias("n_orders")))
        hit = (ev.join(sig, left_on="ingredient", right_on="slug", how="inner")
               .select("user_id", "order_number", "affinity_id").unique())
        parts.append(hit)
    hits = pl.concat(parts)
    orders = pl.concat(order_parts).group_by("user_id").agg(pl.col("n_orders").max())
    return hits, orders


def find_examples(hits, orders):
    """Find specific example customers."""
    # Join to get per-customer stats
    cust = orders.filter(pl.col("n_orders") >= 20)  # need enough history
    user_ids = set(cust["user_id"].to_list())

    # Per customer per profile: count of orders hitting it
    cp = (hits.filter(pl.col("user_id").is_in(user_ids))
          .group_by("user_id", "affinity_id")
          .agg(pl.col("order_number").n_unique().alias("n_hit"))
          .join(cust, on="user_id"))
    cp = cp.with_columns((pl.col("n_hit") / pl.col("n_orders")).alias("share"))

    # pivot to wide: one row per user, one col per profile
    wide = (cp.pivot(values="share", index="user_id", on="affinity_id").fill_null(0.0)
            .with_columns(pl.col("user_id").cast(pl.Int32))
            .join(cust, on="user_id"))

    examples = {}

    # 1. Roasts minimal: someone who barely ever triggers roasts
    roast_col = "roasts" if "roasts" in wide.columns else None
    if roast_col:
        roast_low = wide.filter(pl.col(roast_col) <= 0.05).sort("n_orders", descending=True)
        if roast_low.height > 0:
            examples["Rare roaster"] = roast_low["user_id"][0]

    # 2. Meat-heavy: high meat_centered, low seafood
    if "grilling_bbq" in wide.columns and "sweet_baking" in wide.columns:
        meat = wide.filter((pl.col("grilling_bbq") >= 0.4))
        if meat.height > 0:
            examples["Grill-focused"] = meat.sort("grilling_bbq", descending=True)["user_id"][0]

    # 3. Seafood-heavy (via pasta_dishes as proxy — we need seafood in meal_style...
    # Actually seafood is composition, not meal_style. Let me use curry-heavy instead.
    if "curries" in wide.columns:
        curry = wide.filter(pl.col("curries") >= 0.6).sort("curries", descending=True)
        if curry.height > 0:
            examples["Curry enthusiast"] = curry["user_id"][0]

    # 4. Baker: sweet_baking dominant
    if "sweet_baking" in wide.columns:
        baker = wide.filter(pl.col("sweet_baking") >= 0.7).sort("sweet_baking", descending=True)
        if baker.height > 0:
            examples["Dedicated baker"] = baker["user_id"][0]

    # 5. Broad omnivore: many profiles all above 0.3, exclude already-chosen users
    profile_cols = [c for c in SHOW_PROFILES if c in wide.columns]
    used = set(examples.values())
    if profile_cols:
        wide2 = wide.with_columns(
            pl.concat_list([pl.col(c) >= 0.3 for c in profile_cols]).list.sum().alias("n_broad")
        )
        omni = (wide2.filter((pl.col("n_broad") >= 10) & (~pl.col("user_id").is_in(used)))
                .sort("n_broad", descending=True))
        if omni.height > 0:
            examples["Omnivore"] = omni["user_id"][0]

    # 6. Stir-fry focused
    if "stir_fries" in wide.columns:
        sf = wide.filter(pl.col("stir_fries") >= 0.5).sort("stir_fries", descending=True)
        if sf.height > 0:
            examples["Stir-fry focused"] = sf["user_id"][0]

    # 7. Profile switcher: someone with 2-3 strong profiles that alternate in clusters
    # measured by high variance in rolling-window profile shares
    # find someone with >=40 orders and 2+ profiles each above 0.3 but neither above 0.7
    if profile_cols:
        multi = wide.filter(pl.col("n_orders") >= 40)
        multi = multi.with_columns(
            pl.concat_list([pl.col(c) >= 0.3 for c in profile_cols]).list.sum().alias("n_strong"),
            pl.max_horizontal([pl.col(c) for c in profile_cols]).alias("max_share"),
        )
        switcher = (multi.filter((pl.col("n_strong") >= 3) & (pl.col("max_share") <= 0.70))
                    .sort("n_orders", descending=True))
        if switcher.height > 0:
            examples["Multi-style switcher"] = switcher["user_id"][0]

    print(f"Found {len(examples)} example customers:")
    for label, uid in examples.items():
        row = wide.filter(pl.col("user_id") == uid)
        n = int(row["n_orders"][0]) if "n_orders" in row.columns else "?"
        print(f"  {label}: user_id={uid}, {n} orders")

    return examples


def plot_timelines(hits, orders, examples):
    """One heatmap per example customer."""
    n_examples = len(examples)
    fig, axes = plt.subplots(n_examples, 1, figsize=(16, 2.8 * n_examples + 1.5),
                             gridspec_kw={"hspace": 0.5})
    if n_examples == 1:
        axes = [axes]

    for ax, (label, uid) in zip(axes, examples.items()):
        n_ord = int(orders.filter(pl.col("user_id") == uid)["n_orders"][0])
        user_hits = hits.filter(pl.col("user_id") == uid)

        # build binary matrix: profiles × orders
        order_nums = list(range(1, n_ord + 1))
        matrix = np.zeros((len(SHOW_PROFILES), len(order_nums)))
        for row in user_hits.iter_rows(named=True):
            if row["affinity_id"] in SHOW_PROFILES:
                pi = SHOW_PROFILES.index(row["affinity_id"])
                oi = row["order_number"] - 1
                if 0 <= oi < len(order_nums):
                    matrix[pi, oi] = 1.0

        ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1,
                  interpolation="nearest")
        ax.set_yticks(range(len(SHOW_PROFILES)))
        ax.set_yticklabels([p.replace("_", " ") for p in SHOW_PROFILES], fontsize=8)
        ax.set_xlabel("Order number" if ax == axes[-1] else "")

        # summary: how many profiles appear in >30% of orders
        active = sum(1 for p in SHOW_PROFILES
                     if matrix[SHOW_PROFILES.index(p), :].sum() / n_ord >= 0.3)
        ax.set_title(f"{label}  —  {n_ord} orders, {active} food styles active in ≥30% of orders",
                     fontweight="bold", fontsize=11, loc="left")

        # light gridlines between profiles
        for i in range(len(SHOW_PROFILES) - 1):
            ax.axhline(i + 0.5, color="white", linewidth=0.5)

    fig.suptitle("Food-profile timelines: what each customer buys, order by order\n"
                 "Blue = order contained distinctive ingredients for that food style; "
                 "white = absent",
                 fontweight="bold", fontsize=13, y=1.01)
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"profiles_timelines.{ext}", dpi=200, bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)
    print(f"Saved profiles_timelines.png")


def main():
    print("Building per-order profile matrix (full dataset)...")
    hits, orders = build_order_profile_matrix()
    print(f"  {hits.height:,} order-profile hits across {orders.height:,} customers")
    examples = find_examples(hits, orders)
    plot_timelines(hits, orders, examples)


if __name__ == "__main__":
    main()
