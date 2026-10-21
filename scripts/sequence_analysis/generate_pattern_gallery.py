#!/usr/bin/env python3
"""
Generate a pattern gallery: 5 panels × 5 rows, each row a different (customer, product)
pair that clearly demonstrates the pattern. Strict selection criteria so every row
is an unambiguous example.
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED

FIGURES_DIR = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIGURES_DIR.mkdir(exist_ok=True, parents=True)
CLF_PATH = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"

PATTERNS = {
    "Persistent Staple": {"color": "#1565C0"},
    "Regular Rotation": {"color": "#2E7D32"},
    "Burst then Absence": {"color": "#EF6C00"},
    "Return after Break": {"color": "#6A1B9A"},
    "Replacement by Another": {"color": "#C62828"},
}
ROWS_PER = 5


def load_purchase_data(n_users=15000, seed=42):
    """Load purchases for a sample of users with 20-60 orders."""
    clf = pl.read_csv(CLF_PATH).select(["product_id", "product_name", "ingredient", "is_food"])
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id", "order_number"]))
    user_N = orders.group_by("user_id").agg(pl.col("order_number").max().alias("N"))
    good = user_N.filter((pl.col("N") >= 20) & (pl.col("N") <= 60))
    sample_uids = good["user_id"].sample(n=min(n_users, good.height), seed=seed).to_list()
    orders = orders.filter(pl.col("user_id").is_in(sample_uids))

    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])
    purch = (pl.concat([prior, train]).join(orders, on="order_id", how="inner")
             .join(clf, on="product_id", how="left").filter(pl.col("is_food") == True))
    return purch


def find_examples(purch):
    """Find clear examples for each pattern."""
    user_N = purch.group_by("user_id").agg(pl.col("order_number").max().alias("N"))
    sub = purch.join(user_N, on="user_id")

    # per (user, product): order list
    up = (sub.group_by(["user_id", "product_id"]).agg(
        pl.col("order_number").sort().alias("orders"),
        pl.col("N").first(),
        pl.col("product_name").first(),
        pl.col("ingredient").first()))

    results = {k: [] for k in PATTERNS}
    used_users = {k: set() for k in PATTERNS}
    used_products = {k: set() for k in PATTERNS}

    for row in up.iter_rows(named=True):
        if all(len(v) >= ROWS_PER for v in results.values()):
            break
        uid = row["user_id"]
        orders = row["orders"]
        N = row["N"]
        n = len(orders)
        name = row["product_name"]
        if name is None or n < 2:
            continue

        freq = n / N
        gaps = [orders[i+1] - orders[i] for i in range(n - 1)]
        max_gap = max(gaps) if gaps else 0

        # consecutive runs
        max_run = cur_run = 1
        for g in gaps:
            if g == 1:
                cur_run += 1
                max_run = max(max_run, cur_run)
            else:
                cur_run = 1

        rec = {"user_id": uid, "product_name": name, "orders": orders, "N": N,
               "ingredient": row["ingredient"]}

        ing = row["ingredient"]

        def _ok(pat):
            return (len(results[pat]) < ROWS_PER
                    and uid not in used_users[pat]
                    and ing not in used_products[pat])

        def _add(pat):
            results[pat].append(rec)
            used_users[pat].add(uid)
            used_products[pat].add(ing)

        # --- Persistent Staple ---
        # Bought in ≥65% of orders, run of ≥5, spread across full history
        pat = "Persistent Staple"
        if (_ok(pat) and freq >= 0.65 and max_run >= 5 and n >= 12
                and orders[-1] >= N - 2 and orders[0] <= 3):
            _add(pat)

        # --- Regular Rotation ---
        # ≥6 purchases, gap CV < 0.35, mean gap 2–5, spread ≥70% of history
        pat = "Regular Rotation"
        if _ok(pat) and n >= 6 and len(gaps) >= 5:
            gm = np.mean(gaps)
            gs = np.std(gaps)
            cv = gs / gm if gm > 0 else 99
            spread = (orders[-1] - orders[0]) / N
            if cv < 0.35 and 2 <= gm <= 5 and spread >= 0.7:
                _add(pat)

        # --- Burst then Absence ---
        # ≥4 purchases, ALL in first 35% of history, last purchase ≥10 orders before end
        pat = "Burst then Absence"
        if _ok(pat) and n >= 4 and N >= 20:
            early_cut = max(5, int(N * 0.35))
            all_early = all(o <= early_cut for o in orders)
            trailing = N - orders[-1]
            if all_early and trailing >= 10:
                _add(pat)

        # --- Return after Break ---
        # ≥3 before gap, gap ≥8, ≥2 after gap
        pat = "Return after Break"
        if _ok(pat) and n >= 5 and max_gap >= 8:
            big_idx = gaps.index(max_gap)
            before = big_idx + 1
            after = n - big_idx - 1
            if before >= 3 and after >= 2:
                _add(pat)

    # --- Replacement by Another ---
    # Two products of the same ingredient for the same customer where one stops and
    # the other starts near the same order
    pat = "Replacement by Another"
    ui = (up.filter(
        (pl.col("orders").list.len() >= 3)
        & pl.col("ingredient").is_not_null()
        & (pl.col("ingredient") != "unclassified"))
          .select(["user_id", "product_id", "product_name", "ingredient", "orders", "N"]))
    used_repl_ings = set()
    for (uid, ing), group in ui.group_by(["user_id", "ingredient"]):
        if len(results[pat]) >= ROWS_PER:
            break
        if uid in used_users[pat] or ing in used_repl_ings:
            continue
        rows_list = group.to_dicts()
        if len(rows_list) < 2:
            continue
        for i in range(len(rows_list)):
            for j in range(len(rows_list)):
                if i == j:
                    continue
                a = rows_list[i]
                b = rows_list[j]
                a_last = max(a["orders"])
                b_first = min(b["orders"])
                gap = b_first - a_last
                # exclude near-identical names (organic/conventional variants)
                a_clean = a["product_name"].lower().replace("organic ", "").strip()
                b_clean = b["product_name"].lower().replace("organic ", "").strip()
                if a_clean == b_clean:
                    continue
                if -3 <= gap <= 3 and len(a["orders"]) >= 3 and len(b["orders"]) >= 3:
                    results[pat].append({
                        "user_id": uid, "N": a["N"], "ingredient": ing,
                        "product_name_a": a["product_name"],
                        "product_name_b": b["product_name"],
                        "orders_a": a["orders"], "orders_b": b["orders"],
                    })
                    used_users[pat].add(uid)
                    used_repl_ings.add(ing)
                    break
            if uid in used_users[pat]:
                break

    return results


def plot_gallery(results):
    n_patterns = len(PATTERNS)
    fig, axes = plt.subplots(n_patterns, 1, figsize=(14, 3.0 * n_patterns))

    for ax, (pat, style) in zip(axes, PATTERNS.items()):
        color = style["color"]
        examples = results.get(pat, [])
        if not examples:
            ax.text(0.5, 0.5, f"No examples found for {pat}",
                    ha="center", va="center", transform=ax.transAxes)
            ax.axis("off")
            continue

        max_N = max(e["N"] for e in examples)

        if pat == "Replacement by Another":
            for i, ex in enumerate(examples):
                y = len(examples) - 1 - i
                N = ex["N"]
                # dropped product in red, replacement in blue
                for o in ex["orders_a"]:
                    ax.scatter(o, y, s=70, c="#C62828", marker="s",
                               edgecolors="white", linewidth=0.5, zorder=3)
                for o in ex["orders_b"]:
                    ax.scatter(o, y, s=70, c="#1565C0", marker="s",
                               edgecolors="white", linewidth=0.5, zorder=3)
                trunc = lambda s: s[:30] + "…" if len(s) > 30 else s
                label = f"{ex['ingredient']}: {trunc(ex['product_name_a'])} → {trunc(ex['product_name_b'])}"
                ax.text(-0.5, y, label, ha="right", va="center", fontsize=7,
                        clip_on=False)
        else:
            for i, ex in enumerate(examples):
                y = len(examples) - 1 - i
                N = ex["N"]
                orders = ex["orders"]
                freq = len(orders) / N
                # background: faint dots for all orders
                ax.scatter(range(1, N + 1), [y] * N, s=8, c="#E0E0E0",
                           marker=".", zorder=1)
                # purchased orders
                ax.scatter(orders, [y] * len(orders), s=70, c=color, marker="s",
                           edgecolors="white", linewidth=0.5, zorder=3)
                trunc = lambda s: s[:38] + "…" if len(s) > 38 else s
                label = f"{trunc(ex['product_name'])} ({freq:.0%})"
                ax.text(-0.5, y, label, ha="right", va="center", fontsize=7,
                        clip_on=False)

        ax.set_xlim(0, max_N + 1)
        ax.set_ylim(-0.5, len(examples) - 0.5)
        ax.set_yticks([])
        ax.set_xlabel("Order Number", fontsize=9)
        ax.set_title(pat, fontsize=12, fontweight="bold", color=color, loc="left")
        ax.spines["left"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.grid(axis="x", alpha=0.15, linestyle="--")

    fig.suptitle("Gallery of Observed Purchase Patterns\n"
                 "Each row = one product for one customer. ■ = purchased, · = not purchased.",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIGURES_DIR / f"pattern_gallery.{ext}", dpi=200,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved pattern_gallery.png")


def main():
    print("Generating pattern gallery...")
    purch = load_purchase_data()
    results = find_examples(purch)
    for pat, exs in results.items():
        print(f"  {pat}: {len(exs)} examples")
        for e in exs:
            if "orders_a" in e:
                print(f"    {e['ingredient']}: {e['product_name_a'][:40]} → {e['product_name_b'][:40]}")
            else:
                print(f"    {e['product_name'][:50]} ({len(e['orders'])}/{e['N']} orders)")
    plot_gallery(results)
    print(f"Saved to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
