#!/usr/bin/env python3
"""
Extended novelty analysis: where customers explore, how discovery is distributed,
and what separates product novelty from ingredient novelty.

Supplements analyze_novelty.py (classifications, weighting, position curves) and
analyze_exploration.py (repertoire growth, half-split stability). Adds:

1. Category-level novelty: which food categories contribute most discoveries
2. Discovery popularity: are new ingredients common or rare foods?
3. Per-customer novelty rates at comparable history lengths
4. Novelty vs basket size (opportunity vs preference)
5. Repertoire growth percentiles (not just means)
6. Product novelty vs ingredient novelty by category

Memory-safe: streams in user-id bursts.
"""
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_reorder import iter_events, taxonomy_map

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "novelty"
SEQ.mkdir(exist_ok=True)
TAX = taxonomy_map()


def main():
    # --- Accumulators ---
    # Category-level novelty: which categories contribute new ingredients?
    cat_new_ings = Counter()       # category -> count of (user, ingredient) first-seen events
    cat_new_prods = Counter()      # category -> count of (user, product) first-seen events
    cat_total_items = Counter()    # category -> total item-events

    # Discovery popularity: how popular are newly discovered ingredients?
    ing_total_purchases = Counter()
    discovery_ing_counts = Counter()  # ingredient -> times it was someone's first purchase of it

    # Per-customer novelty rates (for users with 15-25 orders, at order positions 10-15)
    cust_novelty_rates = []

    # Novelty vs basket size
    basket_novelty = defaultdict(lambda: [0, 0, 0])  # basket_size -> [total_items, new_ing, new_prod]

    # Repertoire growth percentiles
    growth_by_pos = defaultdict(list)  # order_number -> list of cumulative distinct ingredients

    # Category breadth of exploration
    cust_cat_breadth = []

    for chunk in iter_events():
        d = chunk.select(["user_id", "order_number", "product_id", "ingredient", "category"]).unique()

        # first-seen order for each (user, product) and (user, ingredient)
        fp = d.group_by(["user_id", "product_id"]).agg(pl.col("order_number").min().alias("fp"))
        fi = d.group_by(["user_id", "ingredient"]).agg(pl.col("order_number").min().alias("fi"))
        d = (d.join(fp, on=["user_id", "product_id"], how="left")
             .join(fi, on=["user_id", "ingredient"], how="left")
             .with_columns(
                 (pl.col("order_number") == pl.col("fp")).alias("is_new_prod"),
                 (pl.col("order_number") == pl.col("fi")).alias("is_new_ing")))

        # --- Category-level novelty ---
        for cat, total, new_i, new_p in d.group_by("category").agg(
                pl.len().alias("total"),
                pl.col("is_new_ing").sum().alias("new_i"),
                pl.col("is_new_prod").sum().alias("new_p")).iter_rows():
            cat_total_items[cat] += total
            cat_new_ings[cat] += new_i
            cat_new_prods[cat] += new_p

        # --- Discovery popularity ---
        for ing, c in d.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            ing_total_purchases[ing] += c
        new_ing_events = d.filter(pl.col("is_new_ing"))
        for ing, c in new_ing_events.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            discovery_ing_counts[ing] += c

        # --- Per-customer novelty at controlled history length ---
        B = d.group_by("user_id").agg(pl.col("order_number").max().alias("B"))
        mid_users = B.filter((pl.col("B") >= 15) & (pl.col("B") <= 25))
        mid = d.join(mid_users, on="user_id").filter(
            (pl.col("order_number") >= 10) & (pl.col("order_number") <= 15))
        if mid.height > 0:
            per_cust = mid.group_by("user_id").agg(
                pl.col("is_new_ing").mean().alias("new_ing_rate"),
                pl.col("is_new_prod").mean().alias("new_prod_rate"),
                pl.len().alias("items"))
            cust_novelty_rates.append(per_cust)

        # --- Novelty vs basket size ---
        per_basket = d.group_by(["user_id", "order_number"]).agg(
            pl.len().alias("items"),
            pl.col("is_new_ing").sum().alias("new_ings"),
            pl.col("is_new_prod").sum().alias("new_prods"))
        # exclude order 1 (100% new by construction)
        per_basket = per_basket.filter(pl.col("order_number") >= 2)
        for sz, real_n, ni, np_ in per_basket.select(
                pl.col("items").clip(1, 30).alias("sz"), pl.col("items").alias("real_n"),
                "new_ings", "new_prods"
        ).iter_rows():
            a = basket_novelty[sz]
            a[0] += real_n
            a[1] += ni
            a[2] += np_

        # --- Repertoire growth percentiles (reached-subset) ---
        # At each order position k, include only customers whose observed history
        # actually reaches k orders (B >= k), and record their cumulative distinct-
        # ingredient count as of order k. Short-history customers are excluded, not
        # carried forward: carrying them forward would freeze each at their final
        # repertoire and drag the later-position percentiles down toward the mass of
        # customers who never reached that depth. n_customers is therefore "customers
        # with at least k orders", matching the README's "customers reaching it".
        first_order = fi.rename({"fi": "fo"})
        new_per = first_order.group_by(["user_id", "fo"]).agg(pl.len().alias("new"))
        cum2 = (new_per.sort(["user_id", "fo"])
                .with_columns(pl.col("new").cum_sum().over("user_id").alias("cum")))
        for order_num in [1, 2, 3, 5, 10, 15, 20, 30, 50]:
            at_pos = (cum2.filter(pl.col("fo") <= order_num)
                      .group_by("user_id").agg(pl.col("cum").max().alias("rep"))
                      .join(B.filter(pl.col("B") >= order_num), on="user_id", how="inner"))
            if at_pos.height > 0:
                growth_by_pos[order_num].extend(at_pos["rep"].to_list())

        # --- Category breadth of exploration ---
        new_cats = (d.filter(pl.col("is_new_ing"))
                    .group_by("user_id").agg(
                        pl.col("category").n_unique().alias("cat_breadth"),
                        pl.col("ingredient").n_unique().alias("ing_breadth")))
        cust_cat_breadth.append(new_cats)

    # --- Write category novelty ---
    cat_rows = []
    for cat in sorted(cat_total_items.keys()):
        tot = cat_total_items[cat]
        ni = cat_new_ings[cat]
        np_ = cat_new_prods[cat]
        cat_rows.append({
            "category": cat,
            "total_items": tot,
            "new_ingredient_events": ni,
            "new_product_events": np_,
            "new_ingredient_rate": round(ni / tot * 100, 2) if tot else 0,
            "new_product_rate": round(np_ / tot * 100, 2) if tot else 0,
            "product_novelty_minus_ingredient": round((np_ - ni) / tot * 100, 2) if tot else 0,
        })
    cat_df = pl.DataFrame(cat_rows).sort("total_items", descending=True)
    cat_df.write_csv(SEQ / "novelty_by_category.csv")
    print("Category novelty rates:")
    for r in cat_df.head(15).iter_rows(named=True):
        print(f"  {r['category']:26s} new_ing={r['new_ingredient_rate']:5.1f}%  "
              f"new_prod={r['new_product_rate']:5.1f}%  "
              f"(product-only novelty: {r['product_novelty_minus_ingredient']:.1f}%)")

    # --- Write discovery popularity ---
    total_disc = sum(discovery_ing_counts.values())
    total_purch = sum(ing_total_purchases.values())
    disc_rows = []
    for ing in sorted(ing_total_purchases.keys()):
        purch = ing_total_purchases[ing]
        disc = discovery_ing_counts.get(ing, 0)
        disc_rows.append({
            "ingredient": ing,
            "total_purchases": purch,
            "purchase_share_pct": round(purch / total_purch * 100, 4),
            "discovery_events": disc,
            "discovery_share_pct": round(disc / total_disc * 100, 4) if total_disc else 0,
        })
    disc_df = pl.DataFrame(disc_rows).sort("total_purchases", descending=True)
    disc_df.write_csv(SEQ / "discovery_popularity.csv")
    # top discovery share vs top purchase share
    top20_purch = disc_df.head(20).select(pl.col("purchase_share_pct").sum()).item()
    top20_disc = disc_df.sort("discovery_events", descending=True).head(20).select(
        pl.col("discovery_share_pct").sum()).item()
    print(f"\nTop 20 ingredients: {top20_purch:.1f}% of purchases, {top20_disc:.1f}% of discoveries")

    # --- Write per-customer novelty rates ---
    if cust_novelty_rates:
        rates = pl.concat(cust_novelty_rates)
        for col in ["new_ing_rate", "new_prod_rate"]:
            q = [rates.select(pl.col(col).quantile(p)).item() for p in [0.1, 0.25, 0.5, 0.75, 0.9]]
            print(f"  {col} (orders 10-15, users with 15-25 orders): "
                  f"p10={q[0]:.3f} p50={q[2]:.3f} p90={q[4]:.3f}")
        rates.write_csv(SEQ / "customer_novelty_rates.csv")

    # --- Write novelty vs basket size ---
    bask_rows = []
    for sz in sorted(basket_novelty.keys()):
        t, ni, np_ = basket_novelty[sz]
        if t < 1000:
            continue
        bask_rows.append({
            "basket_size": sz, "total_items": t,
            "new_ing_rate": round(ni / t * 100, 2),
            "new_prod_rate": round(np_ / t * 100, 2),
            "new_ing_per_basket": round(ni / (t / sz), 2) if sz > 0 else 0,
        })
    pl.DataFrame(bask_rows).write_csv(SEQ / "novelty_vs_basket_size.csv")
    print("\nNovelty vs basket size:")
    for r in bask_rows:
        if r["basket_size"] in [2, 5, 8, 12, 15, 20, 25, 30]:
            print(f"  size {r['basket_size']:2d}: new_ing {r['new_ing_rate']:.1f}%  "
                  f"new_prod {r['new_prod_rate']:.1f}%  "
                  f"new_ings/basket {r['new_ing_per_basket']:.1f}")

    # --- Write repertoire growth percentiles ---
    growth_rows = []
    for pos in sorted(growth_by_pos.keys()):
        vals = np.array(growth_by_pos[pos])
        if len(vals) < 100:
            continue
        growth_rows.append({
            "order_position": pos,
            "n_customers": len(vals),
            "p10": int(np.quantile(vals, 0.1)),
            "p25": int(np.quantile(vals, 0.25)),
            "p50": int(np.quantile(vals, 0.5)),
            "p75": int(np.quantile(vals, 0.75)),
            "p90": int(np.quantile(vals, 0.9)),
            "mean": round(float(vals.mean()), 1),
        })
    pl.DataFrame(growth_rows).write_csv(SEQ / "repertoire_growth_percentiles.csv")

    # --- Write category breadth ---
    cb = pl.concat(cust_cat_breadth)
    med_cat = cb["cat_breadth"].median()
    med_ing = cb["ing_breadth"].median()
    print(f"\nExploration breadth: median {med_cat:.0f} categories, {med_ing:.0f} ingredients")
    cb.write_csv(SEQ / "exploration_breadth.csv")

    print(f"\nAll outputs in {SEQ}")


if __name__ == "__main__":
    main()
