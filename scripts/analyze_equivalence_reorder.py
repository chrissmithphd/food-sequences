#!/usr/bin/env python3
"""
Stage 1 payoff: does food-equivalence grouping change measured reordering?

Runs the corrected censoring-aware KM reorder measure at three grouping levels,
for each covered family (resolved products only):
  - SKU             : exact product_id
  - equivalent food : subgroup (brand/minor-form collapsed)
  - family          : whole family (shape/fat-level/size collapsed too)

Within-basket dedup: an item/subgroup/family appearing twice in one order counts
once (prevents inflating repeat counts). Terminal purchases are right-censored.
"""

import sys
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS
from food_sequences.reorder import km_reorder_probability, T_MAX
import numpy as np

HORIZONS = [1, 2, 3, 5, 10]
FAMILIES = ["pasta", "milk", "eggs"]


def km_from_series(key_orders, user_total):
    """key_orders: dict (user,key)->sorted distinct order list. Returns KM prob dict."""
    events = np.zeros(T_MAX)
    censored = np.zeros(T_MAX)
    for (user, _key), onums in key_orders.items():
        k = len(onums)
        for i in range(k - 1):
            d = onums[i + 1] - onums[i]
            events[min(d, T_MAX - 1)] += 1
        c = user_total[user] - onums[-1]
        censored[min(c, T_MAX - 1)] += 1
    prob, _ = km_reorder_probability(events, censored)
    return prob


def main():
    print("Stage 1: equivalence-level reorder comparison")
    mapping = pd.read_csv(ANALYSIS_OUTPUTS / "food_mapping_v1.csv")
    resolved = mapping[mapping["status"] == "resolved"].copy()
    resolved["family_key"] = resolved["family"]
    resolved["subgroup_key"] = resolved["family"] + ":" + resolved["subgroup"].astype(str)
    pid2fam = dict(zip(resolved["product_id"], resolved["family"]))
    pid2sub = dict(zip(resolved["product_id"], resolved["subgroup_key"]))

    # user totals (all prior+train orders)
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet").filter(
        pl.col("eval_set").is_in(["prior", "train"]))
    user_total = dict(orders.group_by("user_id").agg(
        pl.col("order_number").max().alias("mx")).iter_rows())
    order_user = orders.select(["order_id", "user_id", "order_number"])

    # purchases of resolved products only
    pids = list(resolved["product_id"])
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])
    purch = (pl.concat([prior, train]).filter(pl.col("product_id").is_in(pids))
             .join(order_user, on="order_id", how="inner")).to_pandas()
    purch["family"] = purch["product_id"].map(pid2fam)
    purch["subgroup_key"] = purch["product_id"].map(pid2sub)
    print(f"  resolved-product purchase rows: {len(purch):,}")

    rows = []
    for fam in FAMILIES:
        fp = purch[purch["family"] == fam]
        for level, keycol in [("sku", "product_id"), ("equivalent_food", "subgroup_key"), ("family", "family")]:
            # within-basket dedup on (user, order, key)
            dedup = fp.drop_duplicates(["user_id", "order_number", keycol])
            key_orders = (dedup.groupby(["user_id", keycol])["order_number"]
                          .apply(lambda s: sorted(set(s))).to_dict())
            prob = km_from_series(key_orders, user_total)
            n_units = len(key_orders)
            row = {"family": fam, "level": level, "n_user_key_pairs": n_units}
            for n in HORIZONS:
                row[f"within_{n}"] = round(prob[n] * 100, 1)
            rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(ANALYSIS_OUTPUTS / "equivalence_reorder.csv", index=False)

    print("\nP(reorder within n orders) by grouping level, event-weighted:\n")
    for fam in FAMILIES:
        print(f"  {fam}:")
        sub = out[out["family"] == fam]
        print("    " + f"{'level':16s}" + " ".join(f"n={n:<4d}" for n in HORIZONS) + "  (units)")
        for _, r in sub.iterrows():
            print("    " + f"{r['level']:16s}" + " ".join(f"{r[f'within_{n}']:5.1f}" for n in HORIZONS)
                  + f"  ({r['n_user_key_pairs']:,})")
        print()

    # Markdown table for the report
    md = ["# Stage 1: Equivalence-Level Reorder Comparison\n",
          "Censoring-aware P(reorder within n orders), event-weighted, within-basket deduplicated. "
          "Higher levels collapse brand/shape/fat-level switches into 'same food' reorders.\n"]
    for fam in FAMILIES:
        md.append(f"## {fam}\n")
        md.append("| grouping level | n=1 | n=2 | n=3 | n=5 | n=10 | user-key pairs |")
        md.append("|---|---|---|---|---|---|---|")
        for _, r in out[out["family"] == fam].iterrows():
            md.append(f"| {r['level']} | {r['within_1']}% | {r['within_2']}% | {r['within_3']}% | "
                      f"{r['within_5']}% | {r['within_10']}% | {r['n_user_key_pairs']:,} |")
        md.append("")
    (ANALYSIS_OUTPUTS / "equivalence_reorder.md").write_text("\n".join(md))
    print("✓ wrote equivalence_reorder.csv / .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
