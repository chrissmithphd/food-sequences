#!/usr/bin/env python3
"""Individual novelty timelines: how specific customers explore over time.

Companion to the population-level novelty decay chart. Shows cumulative distinct
ingredients and per-order new-ingredient counts for a few example customers with
different exploration styles.

Usage: uv run python -I scripts/sequence_analysis/fig_novelty_individuals.py
"""
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

FIG = ROOT / "analysis" / "figures"
BLUE, GREEN, ORANGE, RED, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#757575"


def main():
    # Collect per-order novelty for all customers with 30+ orders
    cust_data = {}  # user_id -> list of (order_number, n_items, n_new, cum_distinct)

    for chunk in iter_events():
        ev = chunk.select("user_id", "order_number", "ingredient").unique()
        # per (user, ingredient): first order
        first = ev.group_by("user_id", "ingredient").agg(
            pl.col("order_number").min().alias("first_order"))
        # per (user, order): total items, new items
        per_order = ev.group_by("user_id", "order_number").agg(pl.len().alias("n_items"))
        new_per_order = (first.rename({"first_order": "order_number"})
                         .group_by("user_id", "order_number").len()
                         .rename({"len": "n_new"}))
        merged = per_order.join(new_per_order, on=["user_id", "order_number"], how="left")
        merged = merged.with_columns(pl.col("n_new").fill_null(0))
        # max order per user
        max_ord = ev.group_by("user_id").agg(pl.col("order_number").max().alias("max_ord"))
        merged = merged.join(max_ord, on="user_id")
        merged = merged.filter(pl.col("max_ord") >= 30)

        for uid in merged["user_id"].unique().to_list():
            sub = merged.filter(pl.col("user_id") == uid).sort("order_number")
            orders = sub["order_number"].to_list()
            items = sub["n_items"].to_list()
            news = sub["n_new"].to_list()
            if uid not in cust_data:
                cust_data[uid] = []
            for o, it, nw in zip(orders, items, news):
                cust_data[uid].append((o, it, nw))

    # Compute cumulative distinct + novelty rate per customer
    profiles = {}
    for uid, records in cust_data.items():
        records.sort(key=lambda x: x[0])
        if len(records) < 30:
            continue
        cum = 0
        cum_list, rate_list, orders = [], [], []
        for o, it, nw in records:
            cum += nw
            cum_list.append(cum)
            rate_list.append(nw / it * 100 if it > 0 else 0)
            orders.append(o)
        # characterize: mean late novelty rate (orders 20+)
        late = [r for o, r in zip(orders, rate_list) if o >= 20]
        late_rate = np.mean(late) if late else 0
        final_cum = cum_list[-1]
        profiles[uid] = {
            "orders": orders, "cum": cum_list, "rate": rate_list,
            "late_rate": late_rate, "final_cum": final_cum, "n_orders": len(records)
        }

    print(f"Customers with 30+ orders: {len(profiles):,}")

    # Find examples: high explorer, low explorer, medium, one who slows dramatically
    by_late = sorted(profiles.items(), key=lambda kv: kv[1]["late_rate"])
    # low explorer: bottom 5%
    low_idx = len(by_late) // 20
    low_uid, low = by_late[low_idx]
    # high explorer: top 5%
    high_idx = len(by_late) - len(by_late) // 20
    high_uid, high = by_late[high_idx]
    # medium: near median
    med_idx = len(by_late) // 2
    med_uid, med = by_late[med_idx]
    # dramatic slowdown: high early rate, low late rate
    candidates = [(uid, p) for uid, p in profiles.items()
                  if p["n_orders"] >= 40]
    if candidates:
        early_rates = []
        for uid, p in candidates:
            early = [r for o, r in zip(p["orders"], p["rate"]) if o <= 10]
            late = [r for o, r in zip(p["orders"], p["rate"]) if o >= 30]
            if early and late:
                early_rates.append((uid, p, np.mean(early) - np.mean(late)))
        early_rates.sort(key=lambda x: -x[2])
        slow_uid, slow = early_rates[0][0], early_rates[0][1]
    else:
        slow_uid, slow = med_uid, med

    examples = [
        ("Active explorer", high_uid, high, GREEN),
        ("Moderate explorer", med_uid, med, BLUE),
        ("Low explorer", low_uid, low, ORANGE),
        ("Fast slowdown", slow_uid, slow, RED),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for ax, (label, uid, p, color) in zip(axes.flat, examples):
        orders = p["orders"][:60]  # cap display at 60
        cum = p["cum"][:60]
        rate = p["rate"][:60]

        ax2 = ax.twinx()
        ax.plot(orders, cum, "-", color=color, linewidth=2.5, label="cumulative ingredients")
        ax2.bar(orders, rate, color=color, alpha=0.25, width=0.8, label="% new this order")
        ax.set_xlabel("Order number")
        ax.set_ylabel("Cumulative distinct ingredients", color=color)
        ax2.set_ylabel("New ingredients this order (%)", color=GRAY)
        ax2.set_ylim(0, 105)
        ax.set_title(f"{label} — {p['n_orders']} orders, {p['final_cum']} ingredients",
                     fontweight="bold", fontsize=11)

    fig.suptitle("How individual customers explore over time\n"
                 "Line = cumulative ingredients discovered; bars = % new in each order",
                 fontweight="bold", fontsize=13, y=1.01)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"novelty_individuals.{ext}", dpi=200, bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)
    print("Saved novelty_individuals.png")


if __name__ == "__main__":
    main()
