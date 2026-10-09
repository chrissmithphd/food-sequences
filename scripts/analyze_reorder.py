#!/usr/bin/env python3
"""
Delayed-reordering analysis (corrected).

Measures reordering using full purchase history + Instacart's `reordered` field,
with right-censoring. Runs at two granularities:
  - product_id: exact SKU reorder
  - aisle_id:   same kind of food (possibly a different brand/variant)
The gap between the two curves quantifies brand/variant switching.

Outputs (analysis/outputs/):
  repeat_events.parquet            repeat-event table (product-level)
  reorder_reconciliation.md        history-indicator vs `reordered` field
  basket_composition.md            from-prior / older-absent / first-observed
  reorder_curves.parquet           KM P(reorder within n) per cohort/weighting/key
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import (
    DATA_PROCESSED, ANALYSIS_OUTPUTS, MEAL_LIKE_AISLES, BROAD_PREPARED_DEPARTMENTS,
)
from food_sequences.reorder import (
    build_cohort_maps, ReorderAccumulator, process_user_batch, km_reorder_probability, T_MAX,
)

BATCH_SIZE = 10_000
HORIZONS = [1, 2, 3, 5, 10]


def get_valid_users(min_orders=4):
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")
    uc = (orders.filter(pl.col("eval_set").is_in(["prior", "train"]))
          .group_by("user_id").agg(pl.col("order_number").max().alias("mx"))
          .filter(pl.col("mx") >= min_orders))
    return sorted(uc["user_id"].to_list())


def load_batch_purchases(user_ids, product_aisle):
    """Load purchases (prior+train) for a user batch, joined to order_number + aisle_id."""
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("user_id").is_in(user_ids))
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id", "order_number"]))
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(
        ["order_id", "product_id", "reordered"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(
        ["order_id", "product_id", "reordered"])
    purch = pl.concat([prior, train]).join(orders, on="order_id", how="inner")
    purch = purch.join(product_aisle, on="product_id", how="left")
    return purch.select(["user_id", "order_number", "product_id", "aisle_id", "reordered"]).to_pandas()


def run_pass(users, batches, product_aisle, cohort_meal, cohort_broad,
             item_col, do_composition, collect_events):
    acc = ReorderAccumulator()
    event_rows = [] if collect_events else None
    for i, batch in enumerate(batches, 1):
        if i % 5 == 1:
            print(f"    batch {i}/{len(batches)}")
        purch = load_batch_purchases(batch, product_aisle)
        process_user_batch(purch, cohort_meal, cohort_broad, acc, event_rows,
                            item_col=item_col, do_composition=do_composition)
    return acc, event_rows


def curves_table(acc, key_label):
    rows = []
    for cohort in acc.cohorts:
        for w in acc.weightings:
            prob, _ = km_reorder_probability(acc.events[(cohort, w)], acc.censored[(cohort, w)])
            row = {"key": key_label, "cohort": cohort, "weighting": w}
            for n in HORIZONS:
                row[f"within_{n}"] = prob[n]
            for n in range(1, T_MAX):
                row[f"p{n}"] = prob[n]
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("Delayed-Reorder Analysis (corrected)")
    print("=" * 70)

    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    departments = pd.read_parquet(DATA_PROCESSED / "departments.parquet")
    product_aisle = pl.from_pandas(products[["product_id", "aisle_id"]])

    meal_products, broad_products = build_cohort_maps(
        products, aisles, departments, MEAL_LIKE_AISLES, BROAD_PREPARED_DEPARTMENTS)
    print(f"Meal-like products: {len(meal_products):,}  Broad (frozen+deli): {len(broad_products):,}")

    # Aisle-level cohort id sets
    aisle_name_to_id = dict(zip(aisles["aisle"], aisles["aisle_id"]))
    meal_aisles = {aisle_name_to_id[a] for a in MEAL_LIKE_AISLES if a in aisle_name_to_id}
    dept_name_to_id = dict(zip(departments["department"], departments["department_id"]))
    broad_dept_ids = {dept_name_to_id[d] for d in BROAD_PREPARED_DEPARTMENTS if d in dept_name_to_id}
    broad_aisles = set(products.loc[products["department_id"].isin(broad_dept_ids), "aisle_id"])

    users = get_valid_users(min_orders=4)
    batches = [users[i:i + BATCH_SIZE] for i in range(0, len(users), BATCH_SIZE)]
    print(f"Users: {len(users):,} in {len(batches)} batches")

    # --- Product pass (with reconciliation + composition) ---
    print("\n[1/2] Product-level pass...")
    acc_p, event_rows = run_pass(users, batches, product_aisle, meal_products, broad_products,
                                 item_col="product_id", do_composition=True, collect_events=True)

    # --- Aisle pass ---
    print("\n[2/2] Aisle-level pass...")
    acc_a, _ = run_pass(users, batches, product_aisle, meal_aisles, broad_aisles,
                        item_col="aisle_id", do_composition=False, collect_events=False)

    ANALYSIS_OUTPUTS.mkdir(parents=True, exist_ok=True)

    # Save repeat-event table
    print("\nSaving outputs...")
    ev = pd.DataFrame(event_rows, columns=[
        "user_id", "product_id", "prev_order", "next_order", "interval",
        "intervening", "is_meal_like", "is_broad_prepared"]).astype({
        "prev_order": "int32", "next_order": "int32", "interval": "int32", "intervening": "int32",
        "is_meal_like": "int8", "is_broad_prepared": "int8"})
    ev.to_parquet(ANALYSIS_OUTPUTS / "repeat_events.parquet", index=False)
    print(f"  repeat_events.parquet: {len(ev):,} events")
    print(f"  single-purchase (customer,product) pairs: {acc_p.n_single_pairs:,} (interval = MISSING, not 0)")
    print(f"  multi-purchase pairs: {acc_p.n_multi_pairs:,}")

    # Curves
    cp = curves_table(acc_p, "product")
    ca = curves_table(acc_a, "aisle")
    curves = pd.concat([cp, ca], ignore_index=True)
    curves.to_parquet(ANALYSIS_OUTPUTS / "reorder_curves.parquet", index=False)

    # Reconciliation report
    r = acc_p.recon
    total = sum(r.values())
    agree = r["agree_1"] + r["agree_0"]
    recon_md = f"""# Reorder Reconciliation: History Indicator vs Instacart `reordered`

For every purchase row, a history-based indicator (product seen in any earlier
order by this customer) is compared to Instacart's `reordered` field.

| Case | Count | % of all purchase rows |
|---|---|---|
| Both say reorder (hist=1, field=1) | {r['agree_1']:,} | {r['agree_1']/total*100:.2f}% |
| Both say first-time (hist=0, field=0) | {r['agree_0']:,} | {r['agree_0']/total*100:.2f}% |
| History=reorder, field=first | {r['hist1_field0']:,} | {r['hist1_field0']/total*100:.4f}% |
| History=first, field=reorder | {r['hist0_field1']:,} | {r['hist0_field1']/total*100:.4f}% |
| **Agreement** | **{agree:,}** | **{agree/total*100:.3f}%** |

Total purchase rows: {total:,}

A history indicator built from the data reproduces Instacart's `reordered` field
to within {100 - agree/total*100:.3f}% of rows, confirming the two measure the
same thing. All later reorder analysis uses the full-history indicator so it can
also measure *delayed* reorders (gaps of several orders), which the `reordered`
flag marks but does not quantify.
"""
    (ANALYSIS_OUTPUTS / "reorder_reconciliation.md").write_text(recon_md)

    # Basket composition
    pooled = acc_p.comp_pooled
    ptot = sum(pooled.values())
    cust = np.array(acc_p.cust_comp_rows)
    cust_mean = cust.mean(axis=0)
    comp_md = f"""# Basket Composition (orders with a preceding order)

Each item in a basket (for orders 2..N) is classified as:
- **from immediately prior order** — also in order n-1
- **older, absent from prior** — bought earlier but not in order n-1 (a *delayed* reorder)
- **first observed** — never bought before by this customer

## Item-weighted (pool all items across all qualifying baskets)
Denominator = {ptot:,} basket items.

| Composition | Share |
|---|---|
| From immediately prior order | {pooled['from_prior']/ptot*100:.1f}% |
| Older, absent from prior (delayed reorder) | {pooled['older_absent']/ptot*100:.1f}% |
| First observed | {pooled['first_observed']/ptot*100:.1f}% |

## Customer-weighted (each customer's mean, then averaged; n={len(cust):,})

| Composition | Share |
|---|---|
| From immediately prior order | {cust_mean[0]*100:.1f}% |
| Older, absent from prior (delayed reorder) | {cust_mean[1]*100:.1f}% |
| First observed | {cust_mean[2]*100:.1f}% |

**Why two denominators:** item-weighting lets large baskets and heavy buyers
dominate; customer-weighting gives every customer equal say. The *older-absent*
share is the key quantity the earlier adjacent-overlap analysis missed entirely:
these are reorders of items skipped in the immediately preceding order.
"""
    (ANALYSIS_OUTPUTS / "basket_composition.md").write_text(comp_md)

    # Print headline tables
    print("\n--- P(reorder within n orders), event-weighted, cohort=all ---")
    print(f"{'key':8s} " + " ".join(f"n={n:<5d}" for n in HORIZONS))
    for key, acc in [("product", acc_p), ("aisle", acc_a)]:
        prob, _ = km_reorder_probability(acc.events[("all", "event")], acc.censored[("all", "event")])
        print(f"{key:8s} " + " ".join(f"{prob[n]*100:5.1f}%" for n in HORIZONS))

    print("\n--- Weighting comparison (product, cohort=all) ---")
    for w, lbl in [("event", "event-weighted"), ("cp", "customer-product"), ("cust", "customer")]:
        prob, _ = km_reorder_probability(acc_p.events[("all", w)], acc_p.censored[("all", w)])
        print(f"  {lbl:18s} " + " ".join(f"n={n}:{prob[n]*100:4.1f}%" for n in HORIZONS))

    print("\n--- Cohort comparison (product, event-weighted) ---")
    for cohort in ["all", "meal_like", "broad"]:
        prob, _ = km_reorder_probability(acc_p.events[(cohort, "event")], acc_p.censored[(cohort, "event")])
        print(f"  {cohort:10s} " + " ".join(f"n={n}:{prob[n]*100:4.1f}%" for n in HORIZONS))

    print("\n✓ Reorder analysis complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
