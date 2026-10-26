#!/usr/bin/env python3
"""
Extended prepared-dish analysis: basket context, customer distribution,
assortment vs demand, and what prepared-heavy baskets look like.

Supplements analyze_prepared_foods.py. Adds:
1. Basket composition: with vs without prepared dishes
2. Customer participation distribution
3. Assortment vs demand per dish type
4. Prepared-heavy basket profiles
5. Complete meals vs components/convenience

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
SEQ = ROOT / "analysis" / "prepared"
SEQ.mkdir(exist_ok=True)
CLF_PATH = ROOT / "data" / "food_classification.csv"
TAX = taxonomy_map()


def main():
    clf = pl.read_csv(CLF_PATH)
    prep_products = set(clf.filter(pl.col("is_prepared_dish") == True)["product_id"].to_list())
    cat_products = clf.filter(
        (pl.col("is_food") == True) & pl.col("ingredient").is_not_null()
    ).group_by("ingredient").agg(pl.len().alias("catalog_products"))
    cat_prod_map = dict(zip(cat_products["ingredient"].to_list(),
                            cat_products["catalog_products"].to_list()))

    # --- Accumulators ---
    # Basket comparison: with vs without prepared dishes
    basket_with = {"items": [], "ingredients": [], "categories": [], "n": 0}
    basket_without = {"items": [], "ingredients": [], "categories": [], "n": 0}
    # Category shares in baskets with/without prepared
    cat_with = Counter()
    cat_without = Counter()
    items_with = 0
    items_without = 0

    # Customer prepared-share distribution (all customers)
    cust_prep_share = []

    # Per basket: prepared item count, total items, for concentration
    basket_prep_counts = []

    # Prepared-heavy basket profiles
    heavy_cat = Counter()
    heavy_items = 0
    light_cat = Counter()
    light_items = 0

    for chunk in iter_events():
        per_basket = chunk.group_by(["user_id", "order_number"]).agg(
            pl.len().alias("items"),
            pl.col("ingredient").n_unique().alias("ingredients"),
            pl.col("category").n_unique().alias("categories"),
            (pl.col("is_prepared_dish") == True).sum().alias("prep_items"))

        has_prep = per_basket.filter(pl.col("prep_items") > 0)
        no_prep = per_basket.filter(pl.col("prep_items") == 0)

        basket_with["items"].extend(has_prep["items"].to_list())
        basket_with["ingredients"].extend(has_prep["ingredients"].to_list())
        basket_with["categories"].extend(has_prep["categories"].to_list())
        basket_with["n"] += has_prep.height
        basket_without["items"].extend(no_prep["items"].to_list())
        basket_without["ingredients"].extend(no_prep["ingredients"].to_list())
        basket_without["categories"].extend(no_prep["categories"].to_list())
        basket_without["n"] += no_prep.height

        # category shares within each type of basket
        tagged = chunk.join(
            per_basket.select(["user_id", "order_number", "prep_items"]),
            on=["user_id", "order_number"])
        with_items = tagged.filter(pl.col("prep_items") > 0)
        without_items = tagged.filter(pl.col("prep_items") == 0)
        items_with += with_items.height
        items_without += without_items.height
        for cat, c in with_items.group_by("category").agg(pl.len().alias("c")).iter_rows():
            cat_with[cat] += c
        for cat, c in without_items.group_by("category").agg(pl.len().alias("c")).iter_rows():
            cat_without[cat] += c

        # heavy vs light baskets (>= 3 prepared items vs 0)
        heavy = tagged.filter(pl.col("prep_items") >= 3)
        light = tagged.filter(pl.col("prep_items") == 0)
        heavy_items += heavy.height
        light_items += light.height
        for cat, c in heavy.group_by("category").agg(pl.len().alias("c")).iter_rows():
            heavy_cat[cat] += c
        for cat, c in light.group_by("category").agg(pl.len().alias("c")).iter_rows():
            light_cat[cat] += c

        # per-customer stats
        per_cust = chunk.group_by("user_id").agg(
            pl.len().alias("items"),
            (pl.col("is_prepared_dish") == True).sum().alias("prep"))
        cust_prep_share.extend(
            (per_cust["prep"] / per_cust["items"] * 100).to_list())

        # basket-level prep counts
        basket_prep_counts.extend(per_basket["prep_items"].to_list())

    # --- Basket comparison ---
    def bstats(d):
        return {k: (round(np.median(d[k]), 1), round(np.mean(d[k]), 1)) for k in ["items", "ingredients", "categories"]}

    ws = bstats(basket_with)
    wos = bstats(basket_without)
    print(f"Baskets with prepared dish: {basket_with['n']:,}")
    print(f"  items: median {ws['items'][0]}, mean {ws['items'][1]}")
    print(f"  ingredients: median {ws['ingredients'][0]}")
    print(f"Baskets without: {basket_without['n']:,}")
    print(f"  items: median {wos['items'][0]}, mean {wos['items'][1]}")

    comp_rows = []
    all_cats = sorted(set(list(cat_with.keys()) + list(cat_without.keys())))
    for cat in all_cats:
        cw = cat_with.get(cat, 0) / items_with * 100 if items_with else 0
        co = cat_without.get(cat, 0) / items_without * 100 if items_without else 0
        hw = heavy_cat.get(cat, 0) / heavy_items * 100 if heavy_items else 0
        comp_rows.append({
            "category": cat,
            "pct_in_prep_baskets": round(cw, 2),
            "pct_in_noprep_baskets": round(co, 2),
            "pct_in_heavy_prep_baskets": round(hw, 2),
            "difference": round(cw - co, 2),
        })
    comp_df = pl.DataFrame(comp_rows).sort("difference", descending=True)
    comp_df.write_csv(SEQ / "basket_composition_comparison.csv")

    print("\nCategory shares: prepared baskets vs non-prepared baskets:")
    for r in comp_df.filter(
        ~pl.col("category").str.contains("NON-FOOD|PET|Unknown")
    ).head(15).iter_rows(named=True):
        print(f"  {r['category']:26s} with_prep={r['pct_in_prep_baskets']:5.1f}%  "
              f"without={r['pct_in_noprep_baskets']:5.1f}%  "
              f"diff={r['difference']:+5.1f}")

    # --- Customer distribution ---
    shares = np.array(cust_prep_share)
    shares = shares[np.isfinite(shares)]
    zero_pct = (shares == 0).mean() * 100
    nonzero = shares[shares > 0]
    print(f"\nCustomer distribution: {zero_pct:.1f}% buy zero prepared dishes")
    if len(nonzero) > 0:
        print(f"  Among buyers: median={np.median(nonzero):.1f}%, "
              f"p75={np.quantile(nonzero, 0.75):.1f}%, p90={np.quantile(nonzero, 0.9):.1f}%")
    np.save(SEQ / "customer_prep_shares.npy", shares)

    # --- Basket prep-item distribution ---
    bpc = np.array(basket_prep_counts)
    total_baskets = len(bpc)
    dist_rows = []
    for n_prep in range(0, min(int(bpc.max()) + 1, 11)):
        c = int((bpc == n_prep).sum())
        dist_rows.append({"prep_items": n_prep, "baskets": c,
                          "pct": round(c / total_baskets * 100, 2)})
    pl.DataFrame(dist_rows).write_csv(SEQ / "basket_prep_distribution.csv")
    print(f"\nBasket prepared-item distribution:")
    for r in dist_rows[:6]:
        print(f"  {r['prep_items']} prepared items: {r['pct']:.1f}% of baskets")

    # --- Assortment vs demand per dish type ---
    topics = pl.read_csv(SEQ / "prepared_topics.csv")
    assort_rows = []
    for r in topics.iter_rows(named=True):
        dt = r["dish_type"]
        cprod = cat_prod_map.get(dt, 0)
        assort_rows.append({
            "dish_type": dt,
            "catalog_products": cprod,
            "customers": r["customers"],
            "purchases": r["items"],
            "purchases_per_product": round(r["items"] / cprod, 1) if cprod else 0,
        })
    assort_df = pl.DataFrame(assort_rows).sort("customers", descending=True)
    assort_df.write_csv(SEQ / "assortment_vs_demand.csv")
    print("\nAssortment vs demand:")
    for r in assort_df.head(10).iter_rows(named=True):
        print(f"  {r['dish_type']:18s} products={r['catalog_products']:>4d}  "
              f"purchases={r['purchases']:>9,}  per_product={r['purchases_per_product']:.0f}")

    pl.DataFrame([
        {"metric": "baskets_with_prepared", "value": basket_with["n"]},
        {"metric": "baskets_without_prepared", "value": basket_without["n"]},
        {"metric": "median_size_with", "value": ws["items"][0]},
        {"metric": "median_size_without", "value": wos["items"][0]},
        {"metric": "pct_customers_zero_prepared", "value": round(zero_pct, 1)},
    ]).write_csv(SEQ / "prepared_extended_summary.csv")

    print(f"\nAll outputs in {SEQ}")


if __name__ == "__main__":
    main()
