#!/usr/bin/env python3
"""
Part 1.4 audit: prepared dishes vs base ingredients, done right.

Fixes: use the authoritative is_prepared_dish flag (8,019 products) instead of a
hardcoded 18-ingredient list (1,749). Compare with the corrected next-order
PROBABILITY + shuffle-baseline LIFT, at the fair EXACT-PRODUCT grain (so
"frozen_meal = many dishes" vs "milk = one ingredient" cannot distort it).
Full dataset; no 10K sampling.
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from audit_reorder_probability import load_events, analyze_level

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"


def main():
    purch = load_events()
    rows = []
    for label, flag in [("prepared_dish", True), ("base_ingredient", False)]:
        sub = purch.filter(pl.col("is_prepared_dish") == flag)
        n_products = sub.select("product_id").n_unique()
        for level in ["product_id", "ingredient"]:
            r = analyze_level(sub, level)
            r["group"] = label
            r["grain"] = level
            r["n_products_in_group"] = n_products
            rows.append(r)
            print(f"{label:16s} [{level:10s}] P(next)={r['p_next']*100:5.1f}%  "
                  f"lift={r['lift']:.2f}x  within5={r['p_within_5']*100:4.1f}%  "
                  f"n_events={r['n_events_observable_next']:,}")
    out = pl.DataFrame(rows)
    out.write_csv(SEQ / "prepared_food_audit.csv")
    print(f"\nSaved {SEQ/'prepared_food_audit.csv'}")


if __name__ == "__main__":
    main()
