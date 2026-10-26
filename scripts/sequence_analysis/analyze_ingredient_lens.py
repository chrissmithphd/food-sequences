#!/usr/bin/env python3
"""
The ingredient lens: what the grocery catalog offers vs. what customers buy.

1. Demand vs assortment — purchase volume and catalog product count per ingredient
2. Demand concentration — how many products capture most sales within each ingredient
3. Effective assortment — products needed for 50/80/95% of volume vs catalog size
4. Fresh vs packaged — catalog breadth and purchase share by category type
5. Category-level aggregation — demand and assortment across the ingredient taxonomy
6. Brand multiplier — distinct products vs distinct ingredients per customer

Memory-safe: purchase volume and per-customer repertoire stream in user-id bursts.
"""
import sys
from pathlib import Path
from collections import Counter, defaultdict
import re
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_reorder import iter_events, taxonomy_map
from config import DATA_PROCESSED

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "ingredients"
SEQ.mkdir(exist_ok=True)
CLF_PATH = ROOT / "analysis" / "classification" / "food_classification.csv"
TAX_PATH = ROOT / "data" / "INGREDIENT_TAXONOMY.md"


def load_clf():
    clf = pl.read_csv(CLF_PATH)
    food = clf.filter(
        (pl.col("is_food") == True)
        & pl.col("ingredient").is_not_null()
        & (pl.col("ingredient") != "unclassified")
    )
    return clf, food


def main():
    clf, food = load_clf()
    tax = taxonomy_map()
    pname = dict(zip(clf["product_id"].to_list(), clf["product_name"].to_list()))
    ping = dict(zip(clf["product_id"].to_list(), clf["ingredient"].to_list()))

    # --- catalog counts per ingredient ---
    catalog = food.group_by("ingredient").agg(pl.len().alias("catalog_products"))
    cat_map = dict(zip(catalog["ingredient"].to_list(), catalog["catalog_products"].to_list()))
    n_food_products = food.height

    # --- stream purchase volumes ---
    ing_vol, prod_vol, cust_parts, total = Counter(), Counter(), [], 0
    for chunk in iter_events():
        total += chunk.height
        for ing, c in chunk.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            ing_vol[ing] += c
        for pid, c in chunk.group_by("product_id").agg(pl.len().alias("c")).iter_rows():
            prod_vol[pid] += c
        cust_parts.append(chunk.group_by("user_id").agg(
            pl.col("product_id").n_unique().alias("n_products"),
            pl.col("ingredient").n_unique().alias("n_ingredients")))

    # --- 1. All-ingredient demand vs assortment table ---
    top_prods_by_ing = defaultdict(list)
    for pid, c in prod_vol.most_common():
        ing = ping.get(pid)
        if ing and len(top_prods_by_ing[ing]) < 8:
            top_prods_by_ing[ing].append((pname.get(pid, str(pid)), c))

    all_rows = []
    for ing in sorted(set(list(ing_vol.keys()) + list(cat_map.keys()))):
        pur = ing_vol.get(ing, 0)
        cprod = cat_map.get(ing, 0)
        cat = tax.get(ing, "Unknown")
        examples = top_prods_by_ing.get(ing, [])
        all_rows.append({
            "ingredient": ing,
            "category": cat,
            "purchases": pur,
            "purchase_pct": pur / total * 100 if total else 0,
            "catalog_products": cprod,
            "catalog_pct": cprod / n_food_products * 100 if n_food_products else 0,
            "top_products": " | ".join(f"{n}" for n, _ in examples[:5]),
        })
    all_ing = pl.DataFrame(all_rows).sort("purchases", descending=True)
    all_ing.write_csv(SEQ / "all_ingredients.csv")

    # also keep the top-25 for backward compat
    all_ing.head(25).write_csv(SEQ / "top_ingredients_by_volume.csv")

    print(f"Total food purchases: {total:,}")
    print(f"Distinct ingredients with purchases: {len(ing_vol):,}")
    print(f"Catalog food products (classified): {n_food_products:,}")
    print(f"\nTop 15 by volume:")
    for r in all_ing.head(15).iter_rows(named=True):
        print(f"  {r['ingredient']:16s} vol {r['purchase_pct']:4.1f}%  "
              f"catalog {r['catalog_pct']:4.1f}% ({r['catalog_products']} products)")

    # --- 2+3. Concentration and effective assortment per ingredient ---
    # group product volumes by ingredient
    ing_prod_vols = defaultdict(list)
    for pid, c in prod_vol.items():
        ing = ping.get(pid)
        if ing and ing in ing_vol:
            ing_prod_vols[ing].append(c)

    conc_rows = []
    for ing, vols in ing_prod_vols.items():
        vols_sorted = sorted(vols, reverse=True)
        tot = sum(vols_sorted)
        n = len(vols_sorted)
        if tot == 0:
            continue

        top1_share = vols_sorted[0] / tot
        top3_share = sum(vols_sorted[:3]) / tot if n >= 3 else 1.0
        top5_share = sum(vols_sorted[:5]) / tot if n >= 5 else 1.0

        # effective number of products (inverse HHI)
        shares = np.array(vols_sorted) / tot
        hhi = float((shares ** 2).sum())
        eff_n = 1.0 / hhi if hhi > 0 else n

        # products needed for 50/80/95% of volume
        cumshare = np.cumsum(vols_sorted) / tot
        n50 = int(np.searchsorted(cumshare, 0.50)) + 1
        n80 = int(np.searchsorted(cumshare, 0.80)) + 1
        n95 = int(np.searchsorted(cumshare, 0.95)) + 1

        # products with >0 purchases vs catalog
        purchased = sum(1 for v in vols_sorted if v > 0)
        catalog_n = cat_map.get(ing, n)
        never_bought = catalog_n - purchased

        conc_rows.append({
            "ingredient": ing,
            "category": tax.get(ing, "Unknown"),
            "total_purchases": tot,
            "catalog_products": catalog_n,
            "products_purchased": purchased,
            "products_never_bought": never_bought,
            "top1_share": round(top1_share, 4),
            "top3_share": round(top3_share, 4),
            "top5_share": round(top5_share, 4),
            "effective_n_products": round(eff_n, 1),
            "n_for_50pct": n50,
            "n_for_80pct": n80,
            "n_for_95pct": n95,
        })

    conc = pl.DataFrame(conc_rows).sort("total_purchases", descending=True)
    conc.write_csv(SEQ / "ingredient_concentration.csv")

    print(f"\nConcentration (top ingredients):")
    print(f"  {'ingredient':16s} {'prods':>5s} {'eff_n':>5s} {'top1':>5s} {'n50':>3s} {'n80':>3s} {'n95':>3s}")
    for r in conc.head(20).iter_rows(named=True):
        print(f"  {r['ingredient']:16s} {r['catalog_products']:5d} {r['effective_n_products']:5.1f} "
              f"{r['top1_share']:5.1%} {r['n_for_50pct']:3d} {r['n_for_80pct']:3d} {r['n_for_95pct']:3d}")

    # --- 4. Fresh vs packaged breakdown ---
    # Use taxonomy categories to define fresh vs packaged
    fresh_cats = {"PRODUCE - FRUIT", "PRODUCE - VEGETABLES", "DAIRY",
                  "PROTEIN - MEAT", "PROTEIN - SEAFOOD"}
    packaged_cats = {"SNACKS", "BEVERAGES", "FROZEN FOODS", "BREAKFAST",
                     "PREPARED DISHES & MEALS"}
    pantry_cats = {"GRAINS, PASTA & RICE", "BAKING", "CONDIMENTS & SAUCES",
                   "OILS, FATS & VINEGARS", "COOKING LIQUIDS", "SPREADS & JAMS",
                   "SPICES & SEASONINGS", "NUTS & SEEDS", "BREAD & BAKERY"}

    def classify_type(cat):
        if cat in fresh_cats:
            return "fresh"
        elif cat in packaged_cats:
            return "packaged"
        elif cat in pantry_cats:
            return "pantry"
        else:
            return "other"

    type_rows = []
    for r in all_ing.iter_rows(named=True):
        cat = r["category"]
        type_rows.append({
            "type": classify_type(cat),
            "purchases": r["purchases"],
            "catalog_products": r["catalog_products"],
        })
    type_df = pl.DataFrame(type_rows)
    type_agg = type_df.group_by("type").agg(
        pl.col("purchases").sum(),
        pl.col("catalog_products").sum(),
        pl.len().alias("n_ingredients"),
    ).with_columns(
        (pl.col("purchases") / pl.col("purchases").sum() * 100).alias("purchase_pct"),
        (pl.col("catalog_products") / pl.col("catalog_products").sum() * 100).alias("catalog_pct"),
    ).sort("purchases", descending=True)

    type_agg.write_csv(SEQ / "fresh_vs_packaged.csv")
    print("\nFresh vs packaged:")
    for r in type_agg.iter_rows(named=True):
        print(f"  {r['type']:10s} purchases {r['purchase_pct']:4.1f}%  "
              f"catalog {r['catalog_pct']:4.1f}%  ({r['n_ingredients']} ingredients)")

    # --- 5. Category-level aggregation ---
    cat_rows = []
    for cat_name in sorted(set(tax.values())):
        ings = [k for k, v in tax.items() if v == cat_name]
        pur = sum(ing_vol.get(i, 0) for i in ings)
        cprod = sum(cat_map.get(i, 0) for i in ings)
        n_ing = len(ings)
        # mean concentration for ingredients in this category (with purchases)
        cat_conc = conc.filter(pl.col("category") == cat_name)
        mean_eff_n = cat_conc["effective_n_products"].mean() if cat_conc.height > 0 else None
        mean_top1 = cat_conc["top1_share"].mean() if cat_conc.height > 0 else None
        cat_rows.append({
            "category": cat_name,
            "n_ingredients": n_ing,
            "purchases": pur,
            "purchase_pct": pur / total * 100 if total else 0,
            "catalog_products": cprod,
            "catalog_pct": cprod / n_food_products * 100 if n_food_products else 0,
            "mean_effective_n": round(mean_eff_n, 1) if mean_eff_n is not None else None,
            "mean_top1_share": round(mean_top1, 3) if mean_top1 is not None else None,
        })
    cat_df = pl.DataFrame(cat_rows).sort("purchases", descending=True)
    cat_df.write_csv(SEQ / "category_summary.csv")

    print(f"\nCategory summary:")
    for r in cat_df.head(15).iter_rows(named=True):
        print(f"  {r['category']:26s} vol {r['purchase_pct']:4.1f}%  "
              f"catalog {r['catalog_pct']:4.1f}%  "
              f"({r['n_ingredients']} ings, {r['catalog_products']} prods)")

    # --- 6. Organic penetration by ingredient ---
    clf_organic = food.with_columns(
        pl.col("product_name").str.to_lowercase().str.contains("organic").alias("is_organic")
    )
    organic_pids = set(
        clf_organic.filter(pl.col("is_organic"))["product_id"].to_list()
    )

    org_vol_ing = Counter()
    for pid, c in prod_vol.items():
        if pid in organic_pids:
            ing = ping.get(pid)
            if ing:
                org_vol_ing[ing] += c

    org_rows = []
    for ing in sorted(ing_vol.keys()):
        tot = ing_vol[ing]
        org = org_vol_ing.get(ing, 0)
        org_rows.append({
            "ingredient": ing,
            "category": tax.get(ing, "Unknown"),
            "organic_purchases": org,
            "total_purchases": tot,
            "organic_pct": round(org / tot * 100, 1) if tot else 0,
        })
    org_df = pl.DataFrame(org_rows).sort("total_purchases", descending=True)
    org_df.write_csv(SEQ / "organic_penetration.csv")

    total_org = sum(org_vol_ing.values())
    print(f"\nOrganic: {total_org:,} / {total:,} = {total_org/total*100:.1f}% of purchases")
    print("Top organic penetration (>50k purchases):")
    for r in org_df.filter(pl.col("total_purchases") > 50000).sort(
            "organic_pct", descending=True).head(10).iter_rows(named=True):
        print(f"  {r['ingredient']:16s} {r['organic_pct']:5.1f}% organic")

    # plant milk vs dairy
    pm = ing_vol.get("plant_milk", 0)
    dm = ing_vol.get("milk", 0)
    if pm and dm:
        print(f"\nPlant milk vs dairy: plant_milk={pm:,} ({pm/(pm+dm)*100:.0f}% of combined), "
              f"dairy milk={dm:,} ({dm/(pm+dm)*100:.0f}%)")

    # --- 7. Per-customer repertoire + brand multiplier ---
    per_cust = pl.concat(cust_parts).group_by("user_id").agg(
        pl.col("n_products").sum(), pl.col("n_ingredients").sum())
    per_cust = per_cust.with_columns(
        (pl.col("n_products") / pl.col("n_ingredients")).alias("brand_multiplier"))
    per_cust.write_parquet(SEQ / "per_customer_repertoire.parquet")

    med_prod = per_cust["n_products"].median()
    med_ing = per_cust["n_ingredients"].median()
    med_mult = per_cust["brand_multiplier"].median()
    print(f"\nPer-customer repertoire (medians): products {med_prod:.0f}, "
          f"ingredients {med_ing:.0f}, brand multiplier {med_mult:.2f}x")

    # summary stats
    pl.DataFrame({
        "metric": ["median_distinct_products", "median_distinct_ingredients",
                    "median_brand_multiplier", "total_food_purchases",
                    "distinct_ingredients_purchased", "distinct_ingredients_catalog",
                    "distinct_products_catalog_food", "n_customers"],
        "value": [med_prod, med_ing, round(med_mult, 3), total,
                  len(ing_vol), len(cat_map), n_food_products, per_cust.height],
    }).write_csv(SEQ / "ingredient_lens_summary.csv")
    print("\nSaved all_ingredients.csv, ingredient_concentration.csv, "
          "fresh_vs_packaged.csv, category_summary.csv, per_customer_repertoire.parquet")


if __name__ == "__main__":
    main()
