#!/usr/bin/env python3
"""
Customer profile: descriptive "who are the customers" statistics and segments.

Per customer (all prior+train customers):
  n_orders     : observed orders (order_number is 1..N consecutive)
  tenure_days  : sum of days_since_prior_order (capped at 30/order -> lower bound)
  cadence_days : median days between orders
  items        : total food item-events
  basket_size  : food items per order

Segments customers by two interpretable axes split at their medians:
  frequency (cadence) x basket size -> 4 groups.

Order-level fields come from the lightweight orders table; item counts stream the
purchase table in user-id bursts. Aggregate summary only (no user IDs) is written.
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
from food_sequences.config import DATA_PROCESSED

sns.set_theme(style="whitegrid", font_scale=1.1)
SEQ = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
FIG = SEQ / "figures"
FIG.mkdir(exist_ok=True, parents=True)
BLUE, GREEN, ORANGE, RED = "#1565C0", "#2E7D32", "#EF6C00", "#C62828"


def build_profile():
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["user_id", "order_number", "days_since_prior_order"]))
    per_order = orders.group_by("user_id").agg(
        pl.col("order_number").max().alias("n_orders"),
        pl.col("days_since_prior_order").fill_null(0).sum().alias("tenure_days"),
        pl.col("days_since_prior_order").median().alias("cadence_days"))

    items = []
    for chunk in iter_events():
        items.append(chunk.group_by("user_id").agg(pl.len().alias("items")))
    items = pl.concat(items).group_by("user_id").agg(pl.col("items").sum())

    p = per_order.join(items, on="user_id", how="left").with_columns(
        pl.col("items").fill_null(0))
    return p.with_columns((pl.col("items") / pl.col("n_orders")).alias("basket_size"))


def main():
    p = build_profile()
    n = p.height
    print(f"Customers: {n:,}")

    cols = ["n_orders", "tenure_days", "items", "basket_size", "cadence_days"]
    qs = [0.1, 0.25, 0.5, 0.75, 0.9]
    print("\nDistribution (percentiles):")
    rows = []
    for c in cols:
        vals = [p.select(pl.col(c).quantile(q)).item() for q in qs]
        print(f"  {c:13s} p10={vals[0]:.1f} p25={vals[1]:.1f} p50={vals[2]:.1f} p75={vals[3]:.1f} p90={vals[4]:.1f}")
        rows.append({"metric": c, **{f"p{int(q*100)}": v for q, v in zip(qs, vals)}})

    med_cad = p.select(pl.col("cadence_days").median()).item()
    med_bask = p.select(pl.col("basket_size").median()).item()
    p = p.with_columns(
        pl.when(pl.col("cadence_days") <= med_cad).then(pl.lit("frequent")).otherwise(pl.lit("occasional")).alias("freq"),
        pl.when(pl.col("basket_size") >= med_bask).then(pl.lit("big-basket")).otherwise(pl.lit("small-basket")).alias("size"))
    p = p.with_columns((pl.col("freq") + " / " + pl.col("size")).alias("segment"))

    seg = (p.group_by("segment").agg(
        pl.len().alias("customers"),
        pl.col("n_orders").mean().alias("mean_orders"),
        pl.col("basket_size").mean().alias("mean_basket"),
        pl.col("cadence_days").mean().alias("mean_cadence"),
        pl.col("tenure_days").mean().alias("mean_tenure")).sort("customers", descending=True))
    print(f"\nSegments (median split: cadence {med_cad:.0f}d, basket {med_bask:.1f} items):")
    for r in seg.iter_rows(named=True):
        print(f"  {r['segment']:26s} {r['customers']:>7,} ({r['customers']/n*100:4.1f}%)  "
              f"orders~{r['mean_orders']:4.1f}  basket~{r['mean_basket']:4.1f}  cadence~{r['mean_cadence']:4.1f}d")

    # summary CSV (aggregate, no user IDs)
    summ = pl.DataFrame(rows)
    seg.with_columns((pl.col("customers") / n * 100).alias("pct")).write_csv(SEQ / "customer_segments.csv")
    summ.write_csv(SEQ / "customer_profile_summary.csv")

    # figures
    _fig_distributions(p)
    _fig_segments(seg, n)
    print("\nSaved customer_profile_summary.csv, customer_segments.csv, figures")


def _fig_distributions(p):
    specs = [("n_orders", "Orders per customer", BLUE, (0, 100)),
             ("tenure_days", "Observed tenure (days)", GREEN, (0, 400)),
             ("basket_size", "Food items per order", ORANGE, (0, 25)),
             ("cadence_days", "Median days between orders", RED, (0, 30))]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, (col, label, color, xlim) in zip(axes.ravel(), specs):
        v = p[col].to_numpy()
        v = v[np.isfinite(v)]
        ax.hist(np.clip(v, xlim[0], xlim[1]), bins=40, color=color, alpha=0.85, edgecolor="white", linewidth=0.3)
        med = float(np.median(v))
        ax.axvline(med, color="black", linestyle="--", linewidth=1.5, label=f"median {med:.0f}")
        ax.set_xlabel(label); ax.set_ylabel("Customers"); ax.legend(loc="upper right")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.suptitle("Who Are the Customers? Order volume, tenure, basket size, cadence",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"customer_profile_distributions.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved customer_profile_distributions.png")


def _fig_segments(seg, n):
    s = seg.sort("customers", descending=True)
    labels = s["segment"].to_list()
    sizes = [c / n * 100 for c in s["customers"].to_list()]
    colors = [BLUE, GREEN, ORANGE, RED][:len(labels)]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    y = np.arange(len(labels))
    ax.barh(y, sizes, color=colors, edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.invert_yaxis()
    ax.set_xlabel("Share of customers (%)")
    ax.set_title("Customer Segments — frequency × basket size (median split)", fontweight="bold")
    for i, (pct, r) in enumerate(zip(sizes, s.iter_rows(named=True))):
        ax.text(pct + 0.3, i, f"{pct:.0f}%  (orders~{r['mean_orders']:.0f}, basket~{r['mean_basket']:.0f})",
                va="center", fontsize=9)
    ax.set_xlim(0, max(sizes) * 1.4)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"customer_segments.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved customer_segments.png")


if __name__ == "__main__":
    main()
