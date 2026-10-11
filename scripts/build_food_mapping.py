#!/usr/bin/env python3
"""
Stage 1: build and inspect the versioned food-equivalence mapping (v1).

Outputs:
  analysis/outputs/food_mapping_v1.csv        full mapping (product catalog, reviewable)
  analysis/outputs/food_mapping_examples.md    representative + hard cases for review
  analysis/outputs/food_mapping_validation.md  stratified manual-check sample
Prints coverage statistics.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS
from food_sequences.food_mapping import build_mapping, FOOD_MAPPING_VERSION, FAMILY_CANDIDATE_AISLES


def main():
    print("=" * 70)
    print(f"Food-Equivalence Mapping {FOOD_MAPPING_VERSION}")
    print("=" * 70)

    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")

    m = build_mapping(products, aisles)
    ANALYSIS_OUTPUTS.mkdir(parents=True, exist_ok=True)
    m.to_csv(ANALYSIS_OUTPUTS / "food_mapping_v1.csv", index=False)

    print(f"\nCovered families: {list(FAMILY_CANDIDATE_AISLES)}")
    print(f"Candidate products mapped: {len(m):,}")

    print("\n--- Status by family ---")
    tab = m.groupby(["family", "status"]).size().unstack(fill_value=0)
    print(tab.to_string())

    print("\n--- Confidence by family (resolved only) ---")
    res = m[m["status"] == "resolved"]
    print(res.groupby(["family", "confidence"]).size().unstack(fill_value=0).to_string())

    print("\n--- Subgroups per family (resolved) ---")
    for fam in FAMILY_CANDIDATE_AISLES:
        sub = res[res["family"] == fam]["subgroup"].value_counts()
        print(f"\n  {fam}:")
        for s, c in sub.items():
            print(f"    {s:16s} {c:4d}")

    # Representative + hard-case examples
    lines = [f"# Food-Equivalence Mapping {FOOD_MAPPING_VERSION} — Examples for Review\n"]
    lines.append("Three levels: SKU (product) → equivalent food (`subgroup`) → family. "
                 "Brand and minor form are ignored at the subgroup level; attributes "
                 "(organic, dietary, flavor, physical form, prepared-vs-ingredient) are preserved.\n")

    lines.append("## Brand-equivalence: different SKUs, same equivalent food\n")
    for fam, sub in [("pasta", "spaghetti"), ("milk", "whole"), ("eggs", "large")]:
        ex = m[(m["family"] == fam) & (m["subgroup"] == sub)].head(5)
        lines.append(f"**{fam} / {sub}** — these distinct products map to one equivalent food:\n")
        for _, r in ex.iterrows():
            lines.append(f"- {r['original_name']}")
        lines.append("")

    lines.append("## Meaningful distinctions retained (same family, different subgroup/attribute)\n")
    lines.append("Shape kept as subgroup within the pasta family:\n")
    for sub in ["spaghetti", "penne", "macaroni", "lasagna_sheet"]:
        ex = m[(m["family"] == "pasta") & (m["subgroup"] == sub)].head(1)
        for _, r in ex.iterrows():
            lines.append(f"- `{sub}`: {r['original_name']}")
    lines.append("\nDietary distinction kept as attribute (same subgroup, flagged):\n")
    gf = m[(m["family"] == "pasta") & (m["attributes"].str.contains('"gluten_free": true'))].head(4)
    for _, r in gf.iterrows():
        lines.append(f"- {r['original_name']}  (gluten_free=true)")

    lines.append("\n## Hard cases / boundaries (left separate or flagged)\n")
    lines.append("**Ingredient vs. finished dish — excluded_prepared (NOT mapped as the ingredient):**\n")
    prep = m[m["status"] == "excluded_prepared"].head(8)
    for _, r in prep.iterrows():
        lines.append(f"- [{r['family']}] {r['original_name']} — {r['reason']}")
    lines.append("\n**Filled pasta (ravioli/tortellini) — distinct subgroup, medium confidence:**\n")
    for _, r in m[(m["family"] == "pasta") & (m["subgroup"] == "filled_pasta")].head(5).iterrows():
        lines.append(f"- {r['original_name']}")
    lines.append("\n**Ambiguous — left UNRESOLVED (no forced match):**\n")
    for _, r in m[m["status"] == "ambiguous"].head(8).iterrows():
        lines.append(f"- [{r['family']}] {r['original_name']} — {r['reason']}")
    (ANALYSIS_OUTPUTS / "food_mapping_examples.md").write_text("\n".join(lines))

    # Stratified validation sample (manual check): sample per family x status
    vlines = [f"# Food-Equivalence Mapping {FOOD_MAPPING_VERSION} — Stratified Validation Sample\n",
              "Manually check each row's `subgroup`/`status` against the name. "
              "Record disagreements. Sample is stratified by family × status (seed=0).\n"]
    sample_parts = []
    for (fam, st), g in m.groupby(["family", "status"]):
        sample_parts.append(g.sample(n=min(6, len(g)), random_state=0))
    vs = pd.concat(sample_parts)
    vlines.append("| family | subgroup | status | confidence | product name |")
    vlines.append("|---|---|---|---|---|")
    for _, r in vs.iterrows():
        vlines.append(f"| {r['family']} | {r['subgroup']} | {r['status']} | {r['confidence']} | {r['original_name']} |")
    (ANALYSIS_OUTPUTS / "food_mapping_validation.md").write_text("\n".join(vlines))

    print(f"\n✓ Mapping {FOOD_MAPPING_VERSION} written to analysis/outputs/")
    print("  food_mapping_v1.csv, food_mapping_examples.md, food_mapping_validation.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
