#!/usr/bin/env python3
"""
Classify ALL products with the v4 recipe-role classifier (code reproduction of the
LLM pilot judgment) and validate fidelity against the v3 LLM pilot gold labels.

Outputs:
  analysis/outputs/food_mapping_v4.csv        full frozen mapping (49,688 products)
  analysis/outputs/food_mapping_v4_sample.csv  random sample for manual review
Reports purchase-volume coverage AND agreement with the LLM pilot (the accuracy yardstick).
"""

import json
import sys
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS
from food_sequences.food_classifier import build, CLASSIFIER_VERSION

PILOT = Path(__file__).parent.parent / "analysis" / "food_classification" / "classifications_v3.jsonl"


def main():
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    departments = pd.read_parquet(DATA_PROCESSED / "departments.parquet")
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["product_id"])
    vol = pl.concat([prior, train]).group_by("product_id").len().rename({"len": "n"}).to_pandas()

    df = build(products, aisles, departments, volume=vol)
    ANALYSIS_OUTPUTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(ANALYSIS_OUTPUTS / "food_mapping_v4.csv", index=False)

    total_vol = df["purchase_count"].sum()
    resolved = df[df["status"] == "resolved"]
    oos = df[df["status"] == "out_of_scope"]
    print(f"Food mapping {CLASSIFIER_VERSION}: {len(df):,} products")
    print(f"  resolved in-scope: {len(resolved):,} ({resolved['purchase_count'].sum()/total_vol*100:.1f}% of volume)")
    print(f"  out_of_scope:      {len(oos):,} ({oos['purchase_count'].sum()/total_vol*100:.1f}% of volume)")
    unres = df[df["status"] == "unresolved"]
    print(f"  unresolved:        {len(unres):,} ({unres['purchase_count'].sum()/total_vol*100:.1f}% of volume)")
    print(f"  distinct clusters: {resolved['cluster'].nunique()}")

    # --- Fidelity vs LLM pilot gold ---
    gold = {}
    with open(PILOT) as f:
        for line in f:
            r = json.loads(line)
            gold[r["product_id"]] = r["recipe_group"]
    v4 = dict(zip(df["product_id"], df["cluster"]))
    exact = scope = 0
    mismatches = []
    for pid, g in gold.items():
        v = v4.get(pid)
        g_oos = str(g).startswith("OUT_OF_SCOPE")
        v_oos = str(v).startswith("OUT_OF_SCOPE")
        if v == g:
            exact += 1; scope += 1
        elif g_oos and v_oos:
            scope += 1  # both out-of-scope, subtype differs
        else:
            mismatches.append((pid, g, v))
    n = len(gold)
    print(f"\n--- Fidelity vs LLM pilot ({n} gold labels) ---")
    print(f"  exact group agreement: {exact}/{n} ({exact/n*100:.0f}%)")
    print(f"  scope agreement (resolved-vs-oos): {scope}/{n} ({scope/n*100:.0f}%)")
    if mismatches:
        print("  disagreements (gold -> v4):")
        names = dict(zip(df["product_id"], df["original_name"]))
        for pid, g, v in mismatches:
            print(f"    [{pid}] {names.get(pid,'?')[:40]:40s} gold={g} v4={v}")

    # random sample for manual review
    df.sample(n=40, random_state=0)[["product_id", "original_name", "aisle", "department",
        "cluster", "role_family", "status", "confidence"]].to_csv(
        ANALYSIS_OUTPUTS / "food_mapping_v4_sample.csv", index=False)

    print("\n  top unresolved by volume:")
    for _, r in unres.head(10).iterrows():
        print(f"    {r['purchase_count']:>8,}  [{r['aisle']}] {r['original_name']}")
    print(f"\n✓ wrote food_mapping_v4.csv (+ sample). COVERAGE above; ACCURACY = agreement with LLM pilot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
