#!/usr/bin/env python3
"""
Stage 1 figures:
  equivalence_reorder_bars   — P(reorder within 10) by grouping level, per family
  pasta_sku_vs_family_example — one customer's pasta history: churny SKUs collapse
                                into a steady family staple (example chosen by rule)

Example selection rule (explicit, not random): among users with >=20 total orders,
pick the one with the most DISTINCT pasta SKUs that also span >=3 shapes and buy
pasta in >=6 distinct orders — the clearest "SKU churn hides a family staple" case.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS, FIGURES_DIR

sns.set_theme(style="whitegrid", font_scale=1.05)
FAMILY_COLOR = {"pasta": "#8E24AA", "milk": "#1E88E5", "eggs": "#FDD835"}


def save_fig(fig, name):
    for ext in ["png", "svg"]:
        fig.savefig(FIGURES_DIR / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved {name}")


def fig_bars():
    df = pd.read_csv(ANALYSIS_OUTPUTS / "equivalence_reorder.csv")
    fams = ["pasta", "milk", "eggs"]
    levels = ["sku", "equivalent_food", "family"]
    level_lbl = {"sku": "Exact SKU", "equivalent_food": "Equivalent food", "family": "Family"}
    x = np.arange(len(fams))
    w = 0.26
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, lv in enumerate(levels):
        vals = [df[(df.family == f) & (df.level == lv)]["within_10"].iloc[0] for f in fams]
        bars = ax.bar(x + (i - 1) * w, vals, w, label=level_lbl[lv],
                      color=["#C5CAE9", "#7986CB", "#303F9F"][i], edgecolor="white")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f.capitalize() for f in fams])
    ax.set_ylabel("P(reordered within 10 orders)  [%]")
    ax.set_title("Equivalence Grouping Raises Measured Reordering\n"
                 "Same corrected KM measure; brand/shape/fat-level switches become 'same food' reorders")
    ax.set_ylim(0, 100)
    ax.legend(title="Grouping level")
    save_fig(fig, "equivalence_reorder_bars")


def pick_and_plot_customer():
    mapping = pd.read_csv(ANALYSIS_OUTPUTS / "food_mapping_v1.csv")
    pasta = mapping[(mapping.family == "pasta") & (mapping.status == "resolved")]
    pid2sub = dict(zip(pasta.product_id, pasta.subgroup))
    pid2name = dict(zip(pasta.product_id, pasta.original_name))
    pids = list(pasta.product_id)

    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet").filter(
        pl.col("eval_set").is_in(["prior", "train"])).select(["order_id", "user_id", "order_number"])
    user_total = dict(orders.group_by("user_id").agg(pl.col("order_number").max().alias("mx")).iter_rows())
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])
    pp = (pl.concat([prior, train]).filter(pl.col("product_id").is_in(pids))
          .join(orders, on="order_id", how="inner")).to_pandas()
    pp["subgroup"] = pp["product_id"].map(pid2sub)

    # Explicit selection
    g = pp.groupby("user_id")
    stats = pd.DataFrame({
        "n_sku": g["product_id"].nunique(),
        "n_shape": g["subgroup"].nunique(),
        "n_orders_with_pasta": g["order_number"].nunique(),
    })
    stats = stats[(stats.index.map(user_total) >= 20)]
    cand = stats[(stats.n_shape >= 3) & (stats.n_orders_with_pasta >= 6)]
    cand = cand.sort_values(["n_sku", "n_orders_with_pasta"], ascending=False)
    uid = cand.index[0]
    print(f"  example customer: {cand.iloc[0].to_dict()} (user hidden -> 'Customer A')")

    cust = pp[pp.user_id == uid].sort_values("order_number")
    total = user_total[uid]

    # Build SKU rows (each distinct SKU a row) and the single family row
    skus = list(dict.fromkeys(cust["product_id"]))  # order of first appearance
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), gridspec_kw={"height_ratios": [len(skus), 1.4], "hspace": 0.35})

    palette = sns.color_palette("husl", len(skus))
    for i, sku in enumerate(skus):
        oc = cust[cust.product_id == sku]["order_number"].tolist()
        for o in range(1, total + 1):
            ax1.scatter(o, i, color=palette[i] if o in oc else "#ECECEC",
                        s=42 if o in oc else 6, marker="s" if o in oc else ".", zorder=3 if o in oc else 1)
    ax1.set_yticks(range(len(skus)))
    ax1.set_yticklabels([f"{pid2name[s][:34]} [{pid2sub[s]}]" for s in skus], fontsize=8)
    ax1.set_ylim(-0.5, len(skus) - 0.5)
    ax1.invert_yaxis()
    ax1.set_title("Exact-SKU view: looks like constant churn (each row a different product)", fontsize=11)
    ax1.set_xlim(0, total + 1)

    fam_orders = set(cust["order_number"])
    for o in range(1, total + 1):
        ax2.scatter(o, 0, color=FAMILY_COLOR["pasta"] if o in fam_orders else "#ECECEC",
                    s=60 if o in fam_orders else 6, marker="s" if o in fam_orders else ".", zorder=3)
    ax2.set_yticks([0]); ax2.set_yticklabels(["pasta (family)"], fontsize=10)
    ax2.set_xlabel("Order number (complete history shown)")
    ax2.set_title("Family view: the SAME purchases are a steady pasta staple", fontsize=11)
    ax2.set_xlim(0, total + 1)

    fig.suptitle("Customer A: SKU churn collapses into a family staple under food-equivalence grouping",
                 fontsize=13, fontweight="bold")
    save_fig(fig, "pasta_sku_vs_family_example")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating stage-1 equivalence figures...")
    fig_bars()
    pick_and_plot_customer()
    print(f"✓ saved to {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
