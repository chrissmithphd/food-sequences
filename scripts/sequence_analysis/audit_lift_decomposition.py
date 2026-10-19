#!/usr/bin/env python3
"""
Part 1.2b: WHY does product-level lift (1.29x) exceed ingredient-level (1.15x)?

Caution (user): lift measures temporal clustering BEYOND stable preference (the
shuffle baseline holds each customer's basket frequencies fixed, so "always buys
dairy" is already removed). The product>ingredient ordering could be mechanical,
not evidence that customers "prefer exact products over ingredients."

Test: split (customer, ingredient) pairs into
  - single-product: customer only ever buys one product for that ingredient
    -> product grain == ingredient grain by construction (sanity check: equal lift)
  - multi-product: customer buys 2+ products for that ingredient
    -> product and ingredient grains diverge. If product lift > ingredient lift
       HERE, it means same-SKU purchases cluster in temporal RUNS within a stable
       ingredient (commit-then-switch), i.e. the gap is a substitution signature,
       not a general "product preference".
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
    # distinct products per (user, ingredient)
    npp = (purch.group_by(["user_id", "ingredient"])
           .agg(pl.col("product_id").n_unique().alias("n_prod")))
    purch = purch.join(npp, on=["user_id", "ingredient"], how="left")

    single = purch.filter(pl.col("n_prod") == 1)
    multi = purch.filter(pl.col("n_prod") >= 2)

    rows = []
    def record(name, df, grain):
        r = analyze_level(df, grain)
        r["subset"] = name
        r["grain"] = grain
        rows.append(r)
        print(f"{name:28s} [{grain:10s}] P(next)={r['p_next']*100:5.1f}%  "
              f"expected={r['expected_p_next_shuffle']*100:5.1f}%  lift={r['lift']:.3f}x")

    print("--- single-product (customer,ingredient): grains must coincide ---")
    record("single_product", single, "product_id")
    record("single_product", single, "ingredient")
    print("--- multi-product (customer,ingredient): grains diverge ---")
    record("multi_product", multi, "product_id")
    record("multi_product", multi, "ingredient")

    pl.DataFrame(rows).write_csv(SEQ / "lift_decomposition.csv")
    print(f"\nSaved {SEQ/'lift_decomposition.csv'}")
    # share of events in each subset
    tot = purch.height
    print(f"single-product events: {single.height/tot*100:.1f}%   "
          f"multi-product events: {multi.height/tot*100:.1f}%")


if __name__ == "__main__":
    main()
