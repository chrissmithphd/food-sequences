#!/usr/bin/env python3
"""
Prepared dishes: reach, engagement, dish-type popularity, repeat behavior, and a
reorder comparison against base ingredients.

"Prepared dish" = the classifier's is_prepared_dish flag: ready-to-eat / heat-and-eat
products (frozen meals, pizza, soup, deli-prepared, mac & cheese, plus ready-to-eat
packaged snacks). The dish "type" is the ingredient label within that flag.

Metrics (all per-customer, each customer whole within one user-id burst -> exact):
  reach          : share of customers buying >=1 prepared dish
  prepared share : prepared items / all food items, per customer
  prepared orders: share of a customer's orders containing >=1 prepared dish
  dish types     : distinct prepared dish types per customer
  topics         : per dish type - items, customer reach, repeat-buyer rate
  reorder        : next-order probability + shuffle lift, prepared vs base (product grain)

Aggregate summaries only (no user IDs) are written.
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
from analyze_reorder import analyze_level, iter_events

sns.set_theme(style="whitegrid", font_scale=1.1)
SEQ = Path(__file__).parent.parent.parent / "analysis" / "prepared"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)
BLUE, GREEN, ORANGE, RED, PURPLE = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A"


def engagement_and_topics():
    per_user = []
    topic_items = Counter()
    topic_customers = Counter()
    topic_repeat = Counter()   # customers who bought the type in >=2 orders
    prod_items = Counter()     # product-level purchases (prepared only)
    prod_customers = Counter() # product-level distinct buyers (users disjoint across bursts)

    for chunk in iter_events():
        prep = chunk.with_columns((pl.col("is_prepared_dish") == True).alias("p"))
        g = prep.group_by("user_id").agg(
            pl.len().alias("items"),
            pl.col("p").sum().alias("prep_items"),
            pl.col("order_number").n_unique().alias("n_orders"))
        po = (prep.filter(pl.col("p")).select(["user_id", "order_number"]).unique()
              .group_by("user_id").agg(pl.len().alias("prep_orders")))
        pt = (prep.filter(pl.col("p")).group_by("user_id").agg(pl.col("ingredient").n_unique().alias("prep_types")))
        g = g.join(po, on="user_id", how="left").join(pt, on="user_id", how="left").with_columns(
            pl.col("prep_orders").fill_null(0), pl.col("prep_types").fill_null(0))
        per_user.append(g)

        p = prep.filter(pl.col("p"))
        for ing, c in p.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            topic_items[ing] += c
        # per (type, user) distinct orders -> reach and repeat-buyer counts
        ut = (p.select(["user_id", "order_number", "ingredient"]).unique()
              .group_by(["ingredient", "user_id"]).agg(pl.len().alias("norders")))
        for ing, nc in ut.group_by("ingredient").agg(pl.len().alias("nc")).iter_rows():
            topic_customers[ing] += nc
        for ing, rc in ut.filter(pl.col("norders") >= 2).group_by("ingredient").agg(pl.len().alias("rc")).iter_rows():
            topic_repeat[ing] += rc

        for pid, c in p.group_by("product_id").agg(pl.len().alias("c")).iter_rows():
            prod_items[pid] += c
        for pid, nu in p.group_by("product_id").agg(pl.col("user_id").n_unique().alias("nu")).iter_rows():
            prod_customers[pid] += nu

    u = pl.concat(per_user)
    return u, topic_items, topic_customers, topic_repeat, prod_items, prod_customers


def main():
    u, topic_items, topic_customers, topic_repeat, prod_items, prod_customers = engagement_and_topics()
    n = u.height
    buyers = u.filter(pl.col("prep_items") > 0)
    reach = buyers.height / n * 100
    print(f"Customers: {n:,}")
    print(f"Reach: {buyers.height:,} ({reach:.1f}%) buy >=1 prepared dish")

    b = buyers.with_columns(
        (pl.col("prep_items") / pl.col("items") * 100).alias("prep_item_pct"),
        (pl.col("prep_orders") / pl.col("n_orders") * 100).alias("prep_order_pct"))
    print("\nAmong prepared-dish buyers (percentiles):")
    eng_rows = []
    for col, label in [("prep_item_pct", "prepared % of items"),
                       ("prep_order_pct", "orders with a prepared dish (%)"),
                       ("prep_types", "distinct prepared dish types")]:
        q = [b.select(pl.col(col).quantile(x)).item() for x in (0.1, 0.25, 0.5, 0.75, 0.9)]
        print(f"  {label:32s} p10={q[0]:.1f} p25={q[1]:.1f} p50={q[2]:.1f} p75={q[3]:.1f} p90={q[4]:.1f}")
        eng_rows.append({"metric": label, **{f"p{int(x*100)}": v for x, v in zip((.1,.25,.5,.75,.9), q)}})

    # does prepared engagement track overall volume?
    cN = b.select(pl.corr("n_orders", "prep_item_pct")).item()
    print(f"\ncorr(prepared % of items, n_orders) = {cN:+.3f}  (near 0 => not just heavy shoppers)")

    # topics
    rows = []
    for ing in topic_items:
        cust = topic_customers.get(ing, 0)
        rep = topic_repeat.get(ing, 0)
        rows.append({"dish_type": ing, "items": topic_items[ing], "customers": cust,
                     "repeat_buyer_pct": (rep / cust * 100 if cust else 0.0),
                     "items_per_buyer": (topic_items[ing] / cust if cust else 0.0)})
    topics = pl.DataFrame(rows).sort("customers", descending=True)
    print(f"\nPrepared dish types: {topics.height}. Top 15 by customer reach:")
    for r in topics.head(15).iter_rows(named=True):
        print(f"  {r['dish_type']:18s} customers={r['customers']:>7,}  items={r['items']:>9,}  "
              f"repeat-buyers={r['repeat_buyer_pct']:4.0f}%")

    # product-level dive: which specific products within each dish type
    clf = pl.read_csv(Path(__file__).parent.parent.parent / "data" / "food_classification.csv")
    pname = dict(zip(clf["product_id"].to_list(), clf["product_name"].to_list()))
    ping = dict(zip(clf["product_id"].to_list(), clf["ingredient"].to_list()))
    prod_rows = [{"dish_type": ping.get(pid, "?"), "product_id": pid,
                  "product_name": pname.get(pid, str(pid)),
                  "purchases": prod_items[pid], "customers": prod_customers.get(pid, 0)}
                 for pid in prod_items]
    products = pl.DataFrame(prod_rows).sort("purchases", descending=True)
    products.write_csv(SEQ / "prepared_products.csv")
    print("\nMost-bought individual products within the big dish types:")
    for dt in ["frozen_meal", "soup", "deli_prepared"]:
        print(f"  {dt}:")
        for r in products.filter(pl.col("dish_type") == dt).head(5).iter_rows(named=True):
            print(f"    {r['customers']:>6,} buyers  {r['product_name'][:54]}")

    # reorder comparison (product grain), prepared vs base
    print("\nReorder (product grain):")
    reorder_rows = []
    for label, flag in [("prepared_dish", True), ("base_ingredient", False)]:
        keep = (lambda f: (lambda d: d.filter(pl.col("is_prepared_dish") == f)))(flag)
        r = analyze_level("product_id", keep=keep)
        reorder_rows.append({"group": label, "p_next": r["p_next"], "lift": r["lift"],
                             "p_within_5": r["p_within_5"], "n_events": r["n_events_observable_next"]})
        print(f"  {label:16s} P(next)={r['p_next']*100:5.1f}%  lift={r['lift']:.2f}x  within5={r['p_within_5']*100:4.1f}%")

    # write aggregate summaries
    topics.write_csv(SEQ / "prepared_topics.csv")
    pl.DataFrame([{"stat": "reach_pct", "value": reach},
                  {"stat": "corr_prepshare_norders", "value": cN}]
                 ).write_csv(SEQ / "prepared_engagement.csv")
    pl.DataFrame(eng_rows).write_csv(SEQ / "prepared_engagement_percentiles.csv")
    pl.DataFrame(reorder_rows).write_csv(SEQ / "prepared_food_audit.csv")

    _fig_topics(topics)
    _fig_engagement(b, reach)
    _fig_products(products)
    print("\nSaved prepared_topics.csv, prepared_engagement*.csv, prepared_food_audit.csv, figures")


MEALY = {"frozen_meal", "soup", "frozen_pizza", "deli_prepared", "mac_and_cheese",
         "frozen_appetizer", "chicken_nuggets", "frozen_burrito", "pot_pie", "lasagna",
         "sushi", "frozen_waffles", "baby_food"}


def _fig_topics(topics):
    t = topics.sort("customers", descending=True).head(15)
    names = t["dish_type"].to_list()
    cust = [c / 1000 for c in t["customers"].to_list()]
    colors = [GREEN if n in MEALY else ORANGE for n in names]
    fig, ax = plt.subplots(figsize=(10, 7))
    y = np.arange(len(names))
    ax.barh(y, cust, color=colors, edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("Customers who bought it (thousands)")
    ax.set_title("Prepared Dish Types by Customer Reach", fontweight="bold")
    for i, (c, r) in enumerate(zip(cust, t.iter_rows(named=True))):
        ax.text(c + 0.5, i, f"{c:.0f}k · {r['repeat_buyer_pct']:.0f}% rebuy", va="center", fontsize=8.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GREEN, label="Heat-and-eat meal"),
                       Patch(color=ORANGE, label="Ready-to-eat snack / other")],
              loc="lower right", frameon=True)
    ax.set_xlim(0, max(cust) * 1.25)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"prepared_topics.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved prepared_topics.png")


def _fig_products(products):
    """Top individual products within the three largest meal dish types."""
    dish = [("frozen_meal", GREEN), ("soup", ORANGE), ("deli_prepared", BLUE)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    for ax, (dt, color) in zip(axes, dish):
        top = products.filter(pl.col("dish_type") == dt).head(8)
        names = [n[:34] for n in top["product_name"].to_list()][::-1]
        cust = [c / 1000 for c in top["customers"].to_list()][::-1]
        y = np.arange(len(names))
        ax.barh(y, cust, color=color, edgecolor="white")
        ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8)
        ax.set_xlabel("buyers (thousands)")
        ax.set_title(dt, fontweight="bold")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.suptitle("Most-Bought Products Within the Big Prepared Dish Types", fontweight="bold", fontsize=14)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"prepared_products.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved prepared_products.png")


def _fig_engagement(b, reach):
    v = b["prep_item_pct"].to_numpy()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(np.clip(v, 0, 60), bins=np.arange(0, 61, 2), color=PURPLE, alpha=0.85, edgecolor="white", linewidth=0.3)
    med = float(np.median(v))
    ax.axvline(med, color=RED, linestyle="--", linewidth=2, label=f"median {med:.0f}% of items")
    ax.set_xlabel("Prepared dishes as % of a customer's food items")
    ax.set_ylabel("Customers (prepared-dish buyers)")
    ax.set_title(f"How Much Do Prepared-Dish Buyers Rely on Them?\n{reach:.0f}% of all customers buy prepared dishes",
                 fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"prepared_engagement.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved prepared_engagement.png")


if __name__ == "__main__":
    main()
