#!/usr/bin/env python3
"""
Phase 2: Full-scale pattern classification.

Steps:
  1. Load sequences, filter to classifiable subset
  2. Precompute list-derived features (batched, ~3-4 min)
  3. Classify with vectorized boolean masks (~instant)
  4. Detect replacements via merge (~seconds)
  5. Threshold sensitivity (~seconds per param)
  6. Save all results
"""

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import ANALYSIS_OUTPUTS
from food_sequences.patterns import (
    precompute_list_features,
    classify_vectorized,
    detect_replacements_vectorized,
    threshold_sensitivity_vectorized,
    DEFAULT_THRESHOLDS,
    PATTERN_NAMES,
)


def main():
    print("=" * 70)
    print("Phase 2: Pattern Classification (Full Scale)")
    print("=" * 70)

    # Step 1: Load
    print("\n[1/6] Loading sequences...")
    seqs = pd.read_parquet(ANALYSIS_OUTPUTS / "product_sequences.parquet")
    print(f"  Total: {len(seqs):,} sequences")

    # Two analysis populations:
    # "rich" — classifiable sequences (users >=10 orders, products bought >=2 times)
    # "all" — including sparse sequences, for prevalence denominators
    rich = seqs[(seqs["user_total_orders"] >= 10) & (seqs["total_purchases"] >= 2)].copy()
    print(f"  Classifiable (>=10 orders, >=2 purchases): {len(rich):,}")
    print(f"  Users: {rich['user_id'].nunique():,}")

    mem_mb = rich.memory_usage(deep=True).sum() / 1024**2
    print(f"  Memory: {mem_mb:.0f} MB")

    # Step 2: Precompute list features
    print("\n[2/6] Precomputing list-derived features...")
    t0 = time.time()
    rich = precompute_list_features(rich, batch_size=500_000)
    t1 = time.time()
    print(f"  Done in {t1-t0:.1f}s")

    # Step 3: Classify
    print("\n[3/6] Classifying patterns...")
    t0 = time.time()
    rich["pattern"] = classify_vectorized(rich)
    t1 = time.time()
    print(f"  Done in {t1-t0:.3f}s")

    counts = rich["pattern"].value_counts()
    total = len(rich)
    print("\n  Pattern prevalence (default thresholds):")
    for pat, cnt in counts.items():
        print(f"    {pat:30s} {cnt:>10,}  ({cnt/total*100:5.1f}%)")

    # Step 4: Replacement detection
    print("\n[4/6] Detecting replacements...")
    t0 = time.time()
    rich["pattern"] = detect_replacements_vectorized(rich, rich["pattern"], max_gap=3)
    t1 = time.time()
    print(f"  Done in {t1-t0:.1f}s")

    counts = rich["pattern"].value_counts()
    print("\n  Updated prevalence (with replacements):")
    for pat, cnt in counts.items():
        print(f"    {pat:30s} {cnt:>10,}  ({cnt/total*100:5.1f}%)")

    # Prepared vs non-prepared breakdown
    print("\n  By food type:")
    for is_prep, label in [(True, "Prepared"), (False, "Other groceries")]:
        sub = rich[rich["is_prepared_food"] == is_prep]
        sub_counts = sub["pattern"].value_counts()
        print(f"\n    {label} (n={len(sub):,}):")
        for pat, cnt in sub_counts.items():
            print(f"      {pat:30s} {cnt:>10,}  ({cnt/len(sub)*100:5.1f}%)")

    # Step 5: Save classified sequences
    print("\n[5/6] Saving classified sequences...")
    rich.to_parquet(ANALYSIS_OUTPUTS / "pattern_classification.parquet", index=False)
    print(f"  Saved {len(rich):,} rows")

    # Step 6: Threshold sensitivity
    print("\n[6/6] Threshold sensitivity analysis...")

    params_to_vary = {
        "staple_min_frequency": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        "staple_min_consecutive": [2, 3, 4, 5, 7],
        "rotation_max_frequency": [0.2, 0.3, 0.4, 0.5, 0.6],
        "rotation_max_gap_cv": [0.8, 1.0, 1.2, 1.5, 2.0],
        "burst_min_trailing_gap": [2, 3, 5, 8, 10],
        "burst_min_early_density": [0.2, 0.3, 0.4, 0.5, 0.6],
        "return_min_gap": [3, 5, 7, 10, 15],
    }

    # Run on full classified set (vectorized, so fast)
    sensitivity_results = []
    for param, values in params_to_vary.items():
        print(f"  {param}...")
        result = threshold_sensitivity_vectorized(rich, param, values)
        sensitivity_results.append(result)

    sensitivity = pd.concat(sensitivity_results, ignore_index=True)
    sensitivity.to_parquet(ANALYSIS_OUTPUTS / "threshold_sensitivity.parquet", index=False)

    # Print sensitivity summary
    for param in params_to_vary:
        subset = sensitivity[sensitivity["param"] == param]
        print(f"\n  {param}:")
        for _, row in subset.iterrows():
            parts = []
            for pat in PATTERN_NAMES:
                pct = row[f"{pat}_pct"]
                parts.append(f"{pat[:8]}={pct:4.1f}%")
            print(f"    {row['value']:6.1f} → {', '.join(parts)}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Classified {len(rich):,} sequences from {rich['user_id'].nunique():,} users")
    print(f"Patterns found: {(rich['pattern'] != 'unclassified').sum():,} ({(rich['pattern'] != 'unclassified').mean()*100:.1f}%)")
    print(f"Unclassified: {(rich['pattern'] == 'unclassified').sum():,} ({(rich['pattern'] == 'unclassified').mean()*100:.1f}%)")
    print(f"\n✓ Phase 2 complete. Results in {ANALYSIS_OUTPUTS}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
