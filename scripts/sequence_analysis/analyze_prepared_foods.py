#!/usr/bin/env python3
"""
Prepared dishes vs base ingredients.

Split products by the authoritative is_prepared_dish flag and compare reorder
behavior at the exact-product and ingredient grain, using next-order PROBABILITY
and a shuffle-order baseline LIFT (the same definitions as the reorder analysis).
The exact-product grain is the fair comparison: it prevents the single giant
"frozen_meal" ingredient bucket from distorting the prepared group.

Full dataset, no subsampling, memory-safe via the shared burst-based analyze_level.
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import analyze_level, iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"


def main():
    # distinct purchased products per group (one burst pass)
    products = {"prepared_dish": set(), "base_ingredient": set()}
    for chunk in iter_events():
        for label, flag in [("prepared_dish", True), ("base_ingredient", False)]:
            products[label].update(
                chunk.filter(pl.col("is_prepared_dish") == flag)["product_id"].unique().to_list())

    rows = []
    for label, flag in [("prepared_dish", True), ("base_ingredient", False)]:
        keep = (lambda f: (lambda d: d.filter(pl.col("is_prepared_dish") == f)))(flag)
        for level in ["product_id", "ingredient"]:
            r = analyze_level(level, keep=keep)
            r["group"] = label
            r["grain"] = level
            r["n_products_in_group"] = len(products[label])
            rows.append(r)
            print(f"{label:16s} [{level:10s}] P(next)={r['p_next']*100:5.1f}%  lift={r['lift']:.2f}x  "
                  f"within5={r['p_within_5']*100:4.1f}%  n_events={r['n_events_observable_next']:,}")

    cols = ["level", "n_events_observable_next", "p_next", "p_within_2", "p_within_3",
            "p_within_5", "p_within_10", "p_eventual_given_observable",
            "old_interval_immediate_frac", "expected_p_next_shuffle", "lift",
            "group", "grain", "n_products_in_group"]
    pl.DataFrame(rows).select(cols).write_csv(SEQ / "prepared_food_audit.csv")
    print(f"\nSaved {SEQ / 'prepared_food_audit.csv'}")


if __name__ == "__main__":
    main()
