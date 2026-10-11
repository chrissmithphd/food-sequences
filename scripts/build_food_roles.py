#!/usr/bin/env python3
"""
Build the frozen recipe-ingredient food-role labels (v2), volume-prioritized.

Outputs (analysis/outputs/):
  food_roles_v2.csv            frozen labels, one row per product, volume-ranked
  food_roles_examples.md       clusters with brand/form variation collapsed
  food_roles_validation.md     top-volume rows + stratified sample for manual check
Reports coverage as a share of PURCHASE VOLUME (what actually matters).
"""

import sys
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS
from food_sequences.food_roles import build_roles, FOOD_ROLES_VERSION


def main():
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["product_id"])
    vol = pl.concat([prior, train]).group_by("product_id").len().rename({"len": "n"}).to_pandas()

    df = build_roles(products, aisles, volume=vol)
    ANALYSIS_OUTPUTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(ANALYSIS_OUTPUTS / "food_roles_v2.csv", index=False)

    total_vol = df["purchase_count"].sum()
    resolved = df[df["status"] == "resolved"]
    print(f"Food roles {FOOD_ROLES_VERSION}: {len(df):,} products")
    print(f"  resolved: {len(resolved):,} products ({len(resolved)/len(df)*100:.1f}% of catalog)")
    print(f"  resolved PURCHASE VOLUME coverage: {resolved['purchase_count'].sum()/total_vol*100:.1f}%")
    print(f"  distinct clusters: {resolved['cluster'].nunique()}, role families: {resolved['role_family'].nunique()}")

    print("\n--- top clusters by purchase volume ---")
    cv = (resolved.groupby(["role_family", "cluster"])["purchase_count"].sum()
          .sort_values(ascending=False).head(25))
    for (fam, clu), v in cv.items():
        print(f"  {v/total_vol*100:5.2f}%  {fam:22s} {clu}")

    # unresolved share of volume (what we're missing)
    unres = df[df["status"] == "unresolved"]
    print(f"\n  unresolved volume share: {unres['purchase_count'].sum()/total_vol*100:.1f}%")
    print("  top unresolved by volume (candidates for next rules):")
    for _, r in unres.sort_values("purchase_count", ascending=False).head(12).iterrows():
        print(f"    {r['purchase_count']:>8,}  [{r['aisle']}] {r['original_name']}")

    # Examples: clusters collapsing brand/form variation
    lines = [f"# Recipe-Ingredient Food Roles {FOOD_ROLES_VERSION} — Cluster Examples\n",
             "Each cluster = one recipe-ingredient line. Brand, organic, size, fat level "
             "are attributes, not separate clusters.\n"]
    for clu in ["milk", "banana", "stock_or_broth", "cheese", "pasta", "boxed_mac_and_cheese", "plant_milk"]:
        ex = resolved[resolved["cluster"] == clu].head(6)
        if len(ex) == 0:
            continue
        lines.append(f"**{clu}** — distinct SKUs, one recipe ingredient:\n")
        for _, r in ex.iterrows():
            lines.append(f"- {r['original_name']}")
        lines.append("")
    (ANALYSIS_OUTPUTS / "food_roles_examples.md").write_text("\n".join(lines))

    # Validation: top-50 by volume + stratified sample across clusters
    v = ["# Recipe-Ingredient Food Roles — Validation\n",
         "## Top 50 products by purchase volume (highest-impact labels)\n",
         "| vol | aisle | product | cluster | status |", "|---|---|---|---|---|"]
    for _, r in df.head(50).iterrows():
        v.append(f"| {r['purchase_count']:,} | {r['aisle']} | {r['original_name']} | {r['cluster']} | {r['status']} |")
    v.append("\n## Stratified sample across clusters (seed=0)\n")
    v.append("| product | cluster | role_family | status |")
    v.append("|---|---|---|---|")
    strat = (resolved.sample(frac=1, random_state=0)
             .groupby("cluster", group_keys=False).head(2))
    for _, r in strat.iterrows():
        v.append(f"| {r['original_name']} | {r['cluster']} | {r['role_family']} | {r['status']} |")
    (ANALYSIS_OUTPUTS / "food_roles_validation.md").write_text("\n".join(v))

    print(f"\n✓ wrote food_roles_v2.csv + examples + validation ({FOOD_ROLES_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
