#!/usr/bin/env python3
"""
The ingredient lens: what an ingredient is, and why ingredient-level views differ
from product-level ones.

1. What is inside an ingredient — how many products collapse into each, and the
   products customers actually buy for it (an ingredient is a recipe role, not a SKU).
2. What customers buy vs. what the catalog stocks — purchase volume share per
   ingredient alongside catalog product-count share (the catalog-size bias).
3. Distinct products vs distinct ingredients per customer (brand multiplier).

Memory-safe: purchase volume and per-customer repertoire stream in user-id bursts.
"""
import sys
from pathlib import Path
from collections import Counter
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

SEQ = Path(__file__).parent.parent.parent / "analysis" / "ingredients"
SEQ.mkdir(exist_ok=True)
CLF = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
N_TOP = 25
N_EXAMPLES = 5


def main():
    clf = pl.read_csv(CLF).filter(pl.col("is_food") == True)
    # catalog: how many products per ingredient
    catalog = (clf.filter(pl.col("ingredient").is_not_null() & (pl.col("ingredient") != "unclassified"))
               .group_by("ingredient").agg(pl.len().alias("catalog_products")))
    n_catalog = catalog.select(pl.col("catalog_products").sum()).item()
    pname = dict(zip(clf["product_id"].to_list(), clf["product_name"].to_list()))
    ping = dict(zip(clf["product_id"].to_list(), clf["ingredient"].to_list()))

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

    # View 1+2: volume + catalog share + examples for top ingredients by volume
    cat_map = dict(zip(catalog["ingredient"], catalog["catalog_products"]))
    # most-bought product per ingredient
    top_prod_by_ing = {}
    for pid, c in prod_vol.most_common():
        ing = ping.get(pid)
        if ing and len(top_prod_by_ing.setdefault(ing, [])) < N_EXAMPLES:
            top_prod_by_ing[ing].append(pname.get(pid, str(pid)))

    rows = []
    for ing, pur in ing_vol.most_common(N_TOP):
        rows.append({"ingredient": ing, "purchases": pur,
                     "pct": pur / total * 100,
                     "catalog_products": cat_map.get(ing, 0),
                     "catalog_pct": cat_map.get(ing, 0) / n_catalog * 100,
                     "examples": " | ".join(top_prod_by_ing.get(ing, [])[:N_EXAMPLES])})
    vol = pl.DataFrame(rows)
    vol.write_csv(SEQ / "top_ingredients_by_volume.csv")
    print(f"Top {N_TOP} ingredients by purchase volume (vs catalog share):")
    for r in vol.iter_rows(named=True):
        print(f"  {r['ingredient']:16s} vol {r['pct']:4.1f}%  catalog {r['catalog_pct']:4.1f}% "
              f"({r['catalog_products']} products)  e.g. {r['examples'][:60]}")

    # per-customer repertoire + brand multiplier
    per_cust = (pl.concat(cust_parts).group_by("user_id").agg(
        pl.col("n_products").sum(), pl.col("n_ingredients").sum()))  # users disjoint across bursts
    per_cust = per_cust.with_columns((pl.col("n_products") / pl.col("n_ingredients")).alias("brand_multiplier"))
    per_cust.write_parquet(SEQ / "per_customer_repertoire.parquet")
    med_prod = per_cust["n_products"].median()
    med_ing = per_cust["n_ingredients"].median()
    med_mult = per_cust["brand_multiplier"].median()
    print(f"\nPer-customer repertoire (medians): products {med_prod:.0f}, ingredients {med_ing:.0f}, "
          f"brand multiplier {med_mult:.2f}x")

    pl.DataFrame({"metric": ["median_distinct_products", "median_distinct_ingredients",
                             "median_brand_multiplier", "total_food_purchases",
                             "distinct_ingredients_catalog", "distinct_products_catalog_food"],
                  "value": [med_prod, med_ing, round(med_mult, 3), total,
                            catalog.height, clf.height]}).write_csv(SEQ / "ingredient_lens_summary.csv")
    print("\nSaved top_ingredients_by_volume.csv, per_customer_repertoire.parquet, ingredient_lens_summary.csv")


if __name__ == "__main__":
    main()
