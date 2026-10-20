#!/usr/bin/env python3
"""
Basket contents: how big a basket is and what is in it.

Over all food item-events (one row per user/order/product), measure:
  - basket size: food items per order (distribution)
  - distinct ingredients per order (variety within a basket)
  - composition by department (share of all food items)
  - prepared-dish share: item share and share of baskets containing >=1 prepared dish

Streams the purchase table in user-id bursts; only compact per-order sizes and
department/prepared counters accumulate. Aggregate summary only (no user IDs).
"""
import sys
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

sns.set_theme(style="whitegrid", font_scale=1.1)
SEQ = Path(__file__).parent.parent.parent / "analysis" / "basket"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)
GREEN, ORANGE, BLUE = "#2E7D32", "#EF6C00", "#1565C0"
FRESH_DEPTS = {"produce", "meat seafood", "dairy eggs", "deli"}


def main():
    sizes = []                # food items per (user, order)
    distinct = []             # distinct ingredients per (user, order)
    dept_items = Counter()
    prep_items = 0
    total_items = 0
    baskets_with_prep = 0
    n_baskets = 0

    for chunk in iter_events():
        per_basket = chunk.group_by(["user_id", "order_number"]).agg(
            pl.len().alias("items"),
            pl.col("ingredient").n_unique().alias("distinct"),
            (pl.col("is_prepared_dish") == True).any().alias("has_prep"))
        sizes.append(per_basket["items"].to_numpy())
        distinct.append(per_basket["distinct"].to_numpy())
        n_baskets += per_basket.height
        baskets_with_prep += int(per_basket["has_prep"].sum())

        total_items += chunk.height
        prep_items += int((chunk["is_prepared_dish"] == True).sum())
        for dept, c in chunk.group_by("department").agg(pl.len().alias("c")).iter_rows():
            dept_items[dept if dept is not None else "unknown"] += c

    sizes = np.concatenate(sizes)
    distinct = np.concatenate(distinct)

    pct = lambda a, q: float(np.quantile(a, q))
    print(f"Baskets: {n_baskets:,}  food items: {total_items:,}")
    print(f"Basket size (food items): p10={pct(sizes,.1):.0f} p25={pct(sizes,.25):.0f} "
          f"median={pct(sizes,.5):.0f} p75={pct(sizes,.75):.0f} p90={pct(sizes,.9):.0f} mean={sizes.mean():.1f}")
    print(f"Distinct ingredients per basket: median={pct(distinct,.5):.0f} mean={distinct.mean():.1f}")
    print(f"Prepared-dish items: {prep_items/total_items*100:.1f}% of items; "
          f"baskets with >=1 prepared dish: {baskets_with_prep/n_baskets*100:.1f}%")

    dept_share = {d: c / total_items * 100 for d, c in dept_items.items()}
    top = sorted(dept_share.items(), key=lambda kv: kv[1], reverse=True)
    print("\nComposition by department (share of food items):")
    for d, s in top[:12]:
        print(f"  {d:16s} {s:5.1f}%")

    # summary CSV (aggregate)
    pl.DataFrame([{"department": d, "item_share_pct": s, "fresh": d in FRESH_DEPTS}
                  for d, s in top]).write_csv(SEQ / "basket_contents_summary.csv")

    _fig_size(sizes)
    _fig_composition(top)
    print("\nSaved basket_contents_summary.csv, figures")


def _fig_size(sizes):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(np.clip(sizes, 1, 30), bins=np.arange(1, 31), color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
    med = float(np.median(sizes))
    ax.axvline(med, color="#C62828", linestyle="--", linewidth=2, label=f"median {med:.0f} items")
    ax.set_xlabel("Food items per order"); ax.set_ylabel("Baskets")
    ax.set_title("How Big Is a Basket?", fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"basket_size.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved basket_size.png")


def _fig_composition(top):
    top = top[:12]
    names = [d for d, _ in top]
    shares = [s for _, s in top]
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
                       Patch(color=ORANGE, label="Packaged / pantry")], loc="lower right", frameon=True)
    ax.set_xlim(0, max(shares) * 1.18)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"basket_composition.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved basket_composition.png")


if __name__ == "__main__":
    main()
