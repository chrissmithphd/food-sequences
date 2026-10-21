#!/usr/bin/env python3
"""
Basket contents: what grocery baskets contain and what travels together.

Passes are run sequentially, each writing its output before the next starts.
Each pass streams the full dataset in user-id bursts.

Pass 1: Basket metrics — size, composition, diversity, dominant category
Pass 2: Ingredient co-occurrence pairs (reuses analyze_cooccurrence logic)
Pass 3: Category co-occurrence matrix
Pass 4: Ingredient triplets (restricted to top-60 ingredients)
Pass 5: Conditional companions for selected ingredients
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
SEQ = ROOT / "analysis" / "basket"
SEQ.mkdir(exist_ok=True)
FRESH_DEPTS = {"produce", "meat seafood", "dairy eggs", "deli"}


def pass1_metrics():
    """Basket size, composition, diversity, dominant category."""
    print("Pass 1: basket metrics...")
    sizes, distincts, cat_counts = [], [], []
    dept_items = Counter()
    total_items = 0
    n_baskets = 0

    size_bins = {"1-3": (1, 3), "4-6": (4, 6), "7-10": (7, 10),
                 "11-15": (11, 15), "16+": (16, 999)}
    size_dept = {b: Counter() for b in size_bins}
    size_cat = {b: Counter() for b in size_bins}
    size_dept_n = {b: 0 for b in size_bins}
    dom_cat_counter = Counter()

    for chunk in iter_events():
        per_basket = chunk.group_by(["user_id", "order_number"]).agg(
            pl.len().alias("items"),
            pl.col("ingredient").n_unique().alias("distinct_ingredients"),
            pl.col("category").n_unique().alias("distinct_categories"),
            (pl.col("is_prepared_dish") == True).any().alias("has_prep"))
        sizes.append(per_basket["items"].to_numpy())
        distincts.append(per_basket["distinct_ingredients"].to_numpy())
        cat_counts.append(per_basket["distinct_categories"].to_numpy())
        n_baskets += per_basket.height
        total_items += chunk.height

        for dept, c in chunk.group_by("department").agg(pl.len().alias("c")).iter_rows():
            dept_items[dept if dept is not None else "unknown"] += c

        bsizes = per_basket.select(["user_id", "order_number", "items"])
        tagged = chunk.join(bsizes, on=["user_id", "order_number"], how="left")
        for bname, (lo, hi) in size_bins.items():
            sub = tagged.filter((pl.col("items") >= lo) & (pl.col("items") <= hi))
            if sub.height == 0:
                continue
            size_dept_n[bname] += sub.height
            for dept, c in sub.group_by("department").agg(pl.len().alias("c")).iter_rows():
                size_dept[bname][dept if dept is not None else "unknown"] += c
            for cat, c in sub.group_by("category").agg(pl.len().alias("c")).iter_rows():
                size_cat[bname][cat if cat is not None else "Unknown"] += c

        basket_cats = chunk.group_by(["user_id", "order_number", "category"]).agg(pl.len().alias("n"))
        dom = (basket_cats.sort(["user_id", "order_number", "n"], descending=[False, False, True])
               .group_by(["user_id", "order_number"]).first())
        for cat, c in dom.group_by("category").agg(pl.len().alias("c")).iter_rows():
            dom_cat_counter[cat] += c

    sizes = np.concatenate(sizes)
    distincts = np.concatenate(distincts)
    cat_counts = np.concatenate(cat_counts)

    pct = lambda a, q: float(np.quantile(a, q))
    print(f"Baskets: {n_baskets:,}  food items: {total_items:,}")
    print(f"Basket size: median={pct(sizes,.5):.0f} mean={sizes.mean():.1f}")
    print(f"Distinct ingredients: median={pct(distincts,.5):.0f}")

    top_depts = sorted(dept_items.items(), key=lambda kv: kv[1], reverse=True)
    pl.DataFrame([{"department": d, "item_share_pct": round(c / total_items * 100, 2),
                    "fresh": d in FRESH_DEPTS} for d, c in top_depts]
                 ).write_csv(SEQ / "basket_contents_summary.csv")

    comp_rows = []
    for bname in size_bins:
        n = size_dept_n[bname]
        if n == 0:
            continue
        row = {"basket_size": bname, "n_items": n}
        for dept, c in size_dept[bname].items():
            row[f"dept_{dept}"] = round(c / n * 100, 2)
        for cat, c in size_cat[bname].items():
            row[f"cat_{cat}"] = round(c / n * 100, 2)
        comp_rows.append(row)
    pl.DataFrame(comp_rows).write_csv(SEQ / "composition_by_size.csv")

    dom_rows = [{"category": c, "baskets": n, "pct": round(n / n_baskets * 100, 1)}
                for c, n in dom_cat_counter.most_common()]
    pl.DataFrame(dom_rows).write_csv(SEQ / "dominant_category.csv")

    div_rows = []
    for sz in range(1, 31):
        mask = sizes == sz
        if mask.sum() < 100:
            continue
        div_rows.append({
            "basket_size": sz, "n_baskets": int(mask.sum()),
            "mean_ingredients": round(float(distincts[mask].mean()), 2),
            "mean_categories": round(float(cat_counts[mask].mean()), 2),
            "ingredients_per_item": round(float(distincts[mask].mean()) / sz, 3),
        })
    pl.DataFrame(div_rows).write_csv(SEQ / "diversity_by_size.csv")
    print("  Saved basket_contents_summary, composition_by_size, dominant_category, diversity_by_size")
    return n_baskets


def pass2_cooccurrence():
    """Ingredient pair co-occurrence with support, lift, conditional probability."""
    print("\nPass 2a: ingredient frequencies...")
    ing_orders = Counter()
    n_orders = 0
    for chunk in iter_events():
        oi = chunk.select(["user_id", "order_number", "ingredient"]).unique()
        n_orders += oi.select(["user_id", "order_number"]).unique().height
        for ing, c in oi.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            ing_orders[ing] += c

    pmap = {ing: c / n_orders for ing, c in ing_orders.items()}
    print(f"  orders={n_orders:,}  distinct ingredients={len(ing_orders):,}")

    print("Pass 2b: ingredient pair counts...")
    pair = Counter()
    for chunk in iter_events():
        oi = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
              .with_columns((pl.col("user_id").cast(pl.Int64) * 100000
                             + pl.col("order_number")).alias("oid"))
              .select(["oid", "ingredient"]))
        a = oi.rename({"ingredient": "a"})
        b = oi.rename({"ingredient": "b"})
        pairs = a.join(b, on="oid").filter(pl.col("a") < pl.col("b"))
        for ar, br, c in pairs.group_by(["a", "b"]).agg(pl.len().alias("c")).iter_rows():
            pair[(ar, br)] += c

    MIN_SUPPORT = 500
    rows = []
    for (a, b), co in pair.items():
        if co < MIN_SUPPORT:
            continue
        pa, pb = pmap.get(a, 0), pmap.get(b, 0)
        p_ab = co / n_orders
        lift = p_ab / (pa * pb) if pa * pb > 0 else 0
        p_b_given_a = co / ing_orders[a] if ing_orders[a] else 0
        p_a_given_b = co / ing_orders[b] if ing_orders[b] else 0
        rows.append({
            "a": a, "b": b, "support": co, "p_ab": round(p_ab, 6),
            "pa": round(pa, 4), "pb": round(pb, 4), "lift": round(lift, 2),
            "p_b_given_a": round(p_b_given_a, 4),
            "p_a_given_b": round(p_a_given_b, 4),
        })
    co_df = pl.DataFrame(rows).sort("lift", descending=True)
    co_df.write_csv(SEQ / "cooccurrence_pairs.csv")
    print(f"  Pairs (support>={MIN_SUPPORT}): {co_df.height:,}")

    # conditional companions for selected ingredients
    focus = ["banana", "yogurt", "milk", "eggs", "chicken", "pasta",
             "rice", "onion", "garlic", "butter"]
    comp_rows = []
    for ing in focus:
        ing_n = ing_orders.get(ing, 0)
        if ing_n < 1000:
            continue
        companions = []
        for (a, b), co in pair.items():
            partner = None
            if a == ing:
                partner = b
            elif b == ing:
                partner = a
            if partner and co >= 100:
                p_partner_given = co / ing_n
                p_partner = pmap.get(partner, 0)
                lift = p_partner_given / p_partner if p_partner > 0 else 0
                companions.append({
                    "ingredient": ing, "companion": partner,
                    "p_companion_given_ingredient": round(p_partner_given, 4),
                    "p_companion_marginal": round(p_partner, 4),
                    "lift": round(lift, 2), "support": co,
                })
        companions.sort(key=lambda r: r["lift"], reverse=True)
        comp_rows.extend(companions[:20])
    pl.DataFrame(comp_rows).write_csv(SEQ / "conditional_companions.csv")
    print("  Saved cooccurrence_pairs, conditional_companions")
    return n_orders, ing_orders, pmap, pair


def pass3_category_cooccurrence(n_orders):
    """Category-level co-occurrence matrix."""
    print("\nPass 3: category co-occurrence...")
    cat_orders = Counter()
    cat_pair = Counter()
    for chunk in iter_events():
        oi = (chunk.select(["user_id", "order_number", "category"]).unique()
              .with_columns((pl.col("user_id").cast(pl.Int64) * 100000
                             + pl.col("order_number")).alias("oid"))
              .select(["oid", "category"]))
        for cat, c in oi.group_by("category").agg(pl.len().alias("c")).iter_rows():
            cat_orders[cat] += c
        a = oi.rename({"category": "a"})
        b = oi.rename({"category": "b"})
        cpairs = a.join(b, on="oid").filter(pl.col("a") < pl.col("b"))
        for ar, br, c in cpairs.group_by(["a", "b"]).agg(pl.len().alias("c")).iter_rows():
            cat_pair[(ar, br)] += c

    cat_pmap = {c: n / n_orders for c, n in cat_orders.items()}
    rows = []
    for (a, b), co in cat_pair.items():
        pa, pb = cat_pmap.get(a, 0), cat_pmap.get(b, 0)
        lift = (co / n_orders) / (pa * pb) if pa * pb > 0 else 0
        rows.append({"a": a, "b": b, "support": co, "lift": round(lift, 3)})
    pl.DataFrame(rows).write_csv(SEQ / "category_cooccurrence.csv")
    print("  Saved category_cooccurrence")


def pass4_triplets(n_orders, ing_orders, pmap):
    """Ingredient triplets among top-60 ingredients."""
    print("\nPass 4: ingredient triplets (top-60 ingredients)...")
    MIN_TRIP = 300
    top60 = set(sorted(ing_orders, key=ing_orders.get, reverse=True)[:60])
    trip_counter = Counter()
    for chunk in iter_events():
        oi = (chunk.filter(pl.col("ingredient").is_in(top60))
              .select(["user_id", "order_number", "ingredient"]).unique()
              .with_columns((pl.col("user_id").cast(pl.Int64) * 100000
                             + pl.col("order_number")).alias("oid"))
              .select(["oid", "ingredient"]))
        basket_ings = oi.group_by("oid").agg(pl.col("ingredient").alias("ings"))
        for row in basket_ings.filter(
                (pl.col("ings").list.len() >= 3) & (pl.col("ings").list.len() <= 15)
        ).iter_rows():
            ings = sorted(set(row[1]))
            n = len(ings)
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        trip_counter[(ings[i], ings[j], ings[k])] += 1

    rows = []
    for (a, b, c), co in trip_counter.most_common(500):
        if co < MIN_TRIP:
            break
        pa, pb, pc = pmap.get(a, 0), pmap.get(b, 0), pmap.get(c, 0)
        expected = pa * pb * pc * n_orders
        lift3 = co / expected if expected > 0 else 0
        rows.append({"a": a, "b": b, "c": c, "support": co,
                     "lift3": round(lift3, 1)})
    trip_df = pl.DataFrame(rows).sort("lift3", descending=True)
    trip_df.write_csv(SEQ / "ingredient_triplets.csv")
    print(f"  Triplets (support>={MIN_TRIP}): {trip_df.height}")
    for r in trip_df.head(10).iter_rows(named=True):
        print(f"    {r['a']:14s} + {r['b']:14s} + {r['c']:14s}  "
              f"support={r['support']:,}  lift3={r['lift3']:.0f}")


def main():
    pass1_metrics()
    n_orders, ing_orders, pmap, pair = pass2_cooccurrence()
    pass3_category_cooccurrence(n_orders)
    pass4_triplets(n_orders, ing_orders, pmap)
    print(f"\nAll outputs in {SEQ}")


if __name__ == "__main__":
    main()
