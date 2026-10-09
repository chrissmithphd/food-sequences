"""
Observed purchase pattern classification.

Two-phase approach for memory efficiency on 4.5M+ sequences:
  Phase A: Precompute scalar features from order_numbers arrays (batched loop)
  Phase B: Classify using vectorized boolean masks (instant, re-runnable for sensitivity)

Rules are defined BEFORE examining examples. Each pattern has transparent
thresholds; sensitivity analysis re-runs the masks with different values.

Patterns are mutually exclusive (first match wins, priority order below).
Not every sequence must be categorized — "unclassified" is a valid outcome.
"""

import numpy as np
import pandas as pd


DEFAULT_THRESHOLDS = {
    "staple_min_frequency": 0.5,
    "staple_min_consecutive": 3,
    "rotation_min_purchases": 3,
    "rotation_max_frequency": 0.5,
    "rotation_min_spread": 0.5,
    "rotation_max_gap_cv": 1.5,
    "burst_min_purchases": 3,
    "burst_min_early_density": 0.4,
    "burst_max_late_density": 0.1,
    "burst_min_trailing_gap": 3,
    "return_min_gap": 5,
    "return_min_purchases_before": 2,
    "return_min_purchases_after": 1,
}

PATTERN_NAMES = [
    "persistent_staple",
    "regular_rotation",
    "burst_then_absence",
    "return_after_break",
    "unclassified",
]


def precompute_list_features(
    sequences: pd.DataFrame,
    batch_size: int = 500_000,
) -> pd.DataFrame:
    """
    Extract scalar features from order_numbers arrays.

    Adds columns: gap_cv, max_gap, purchases_before_max_gap, purchases_after_max_gap,
    early_half_count, late_half_count, early_density, late_density, spread.

    Processes in batches to limit memory pressure.
    """
    n = len(sequences)
    gap_cv = np.empty(n, dtype=np.float32)
    max_gap = np.empty(n, dtype=np.int32)
    purch_before_max_gap = np.empty(n, dtype=np.int32)
    purch_after_max_gap = np.empty(n, dtype=np.int32)
    early_half = np.empty(n, dtype=np.int32)
    late_half = np.empty(n, dtype=np.int32)
    early_dens = np.empty(n, dtype=np.float32)
    late_dens = np.empty(n, dtype=np.float32)

    for batch_start in range(0, n, batch_size):
        batch_end = min(batch_start + batch_size, n)
        sl = slice(batch_start, batch_end)

        order_arrays = sequences["order_numbers"].iloc[sl]
        first_orders = sequences["first_order_num"].values[sl]
        total_orders_arr = sequences["user_total_orders"].values[sl]

        for i, (arr, first_on, tot_ord) in enumerate(
            zip(order_arrays, first_orders, total_orders_arr)
        ):
            idx = batch_start + i
            sorted_arr = np.sort(arr)

            if len(sorted_arr) > 1:
                gaps = np.diff(sorted_arr)
                mean_g = gaps.mean()
                std_g = gaps.std()
                gap_cv[idx] = std_g / mean_g if mean_g > 0 else 999.0

                mg_idx = gaps.argmax()
                max_gap[idx] = int(gaps[mg_idx])
                purch_before_max_gap[idx] = mg_idx + 1
                purch_after_max_gap[idx] = len(sorted_arr) - mg_idx - 1
            else:
                gap_cv[idx] = 0.0
                max_gap[idx] = 0
                purch_before_max_gap[idx] = len(sorted_arr)
                purch_after_max_gap[idx] = 0

            midpoint = (first_on + tot_ord) / 2.0
            e = int(np.sum(sorted_arr <= midpoint))
            l = len(sorted_arr) - e
            early_half[idx] = e
            late_half[idx] = l

            early_window = midpoint - first_on + 1
            late_window = tot_ord - midpoint
            early_dens[idx] = e / early_window if early_window > 0 else 0.0
            late_dens[idx] = l / late_window if late_window > 0 else 0.0

    result = sequences.copy()
    result["gap_cv"] = gap_cv
    result["max_gap"] = max_gap
    result["purchases_before_max_gap"] = purch_before_max_gap
    result["purchases_after_max_gap"] = purch_after_max_gap
    result["early_half_count"] = early_half
    result["late_half_count"] = late_half
    result["early_density"] = early_dens
    result["late_density"] = late_dens
    result["spread"] = (
        (result["last_order_num"] - result["first_order_num"])
        / result["user_total_orders"]
    ).fillna(0).astype(np.float32)

    return result


def classify_vectorized(
    df: pd.DataFrame,
    thresholds: dict | None = None,
) -> pd.Series:
    """
    Classify sequences using vectorized boolean masks.

    Requires precomputed features from precompute_list_features().
    Priority: staple > rotation > burst > return > unclassified.
    """
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    n = len(df)
    labels = pd.Series("unclassified", index=df.index, dtype="object")

    # Work backwards from lowest priority so higher-priority overwrites
    # Return after break: max_gap >= threshold, with enough before/after
    is_return = (
        (df["max_gap"] >= t["return_min_gap"])
        & (df["purchases_before_max_gap"] >= t["return_min_purchases_before"])
        & (df["purchases_after_max_gap"] >= t["return_min_purchases_after"])
        & (df["total_purchases"] >= (t["return_min_purchases_before"] + t["return_min_purchases_after"]))
    )
    labels[is_return] = "return_after_break"

    # Burst then absence: concentrated early, absent late, trailing gap
    is_burst = (
        (df["total_purchases"] >= t["burst_min_purchases"])
        & (df["early_density"] >= t["burst_min_early_density"])
        & (df["late_density"] <= t["burst_max_late_density"])
        & (df["recency"] >= t["burst_min_trailing_gap"])
    )
    labels[is_burst] = "burst_then_absence"

    # Regular rotation: moderate frequency, spread, regular gaps.
    # Two exclusions prevent false rotations:
    # 1. Max gap can't dominate (> 3× mean) — that's a return, not rotation
    # 2. Max gap can't exceed 10 orders in absolute terms — with ~2-week order
    #    cycles, 10 orders ≈ 5 months, beyond which "rotation" loses meaning
    mean_gap_safe = df["mean_gap"].clip(lower=1)
    is_rotation = (
        (df["total_purchases"] >= t["rotation_min_purchases"])
        & (df["selection_frequency"] < t["rotation_max_frequency"])
        & (df["spread"] >= t["rotation_min_spread"])
        & (df["gap_cv"] < t["rotation_max_gap_cv"])
        & (df["total_purchases"] >= 3)
        & (df["max_gap"] <= mean_gap_safe * 3)
        & (df["max_gap"] <= 10)
    )
    labels[is_rotation] = "regular_rotation"

    # Persistent staple: high frequency + long consecutive run
    is_staple = (
        (df["selection_frequency"] >= t["staple_min_frequency"])
        & (df["max_consecutive"] >= t["staple_min_consecutive"])
    )
    labels[is_staple] = "persistent_staple"

    return labels


def detect_replacements_vectorized(
    df: pd.DataFrame,
    labels: pd.Series,
    max_gap: int = 3,
) -> pd.Series:
    """
    Detect replacement patterns via a self-merge.

    A sequence is "replacement_by_another" if:
    - It's currently burst_then_absence or unclassified
    - Same user has another product in the same aisle
    - That product's first_order_num is within max_gap of this product's last_order_num
    - The replacement product was purchased >= 2 times

    Uses a merge-based approach instead of nested loops.
    """
    updated = labels.copy()

    # Candidates: sequences where the product stopped being purchased
    candidate_mask = (
        labels.isin(["burst_then_absence", "unclassified"])
        & (df["recency"] >= 3)
        & (df["total_purchases"] >= 2)
    )
    candidates = df.loc[candidate_mask, ["user_id", "aisle", "last_order_num"]].copy()
    candidates["_cand_idx"] = candidates.index

    if len(candidates) == 0:
        return updated

    # Potential replacements: all sequences with >= 2 purchases
    replacements = df.loc[
        df["total_purchases"] >= 2,
        ["user_id", "aisle", "first_order_num", "product_id"]
    ].copy()
    replacements["_repl_idx"] = replacements.index

    # Merge on (user_id, aisle)
    merged = candidates.merge(replacements, on=["user_id", "aisle"], how="inner")

    # Filter: different products, start near stop
    merged = merged[
        (merged["_cand_idx"] != merged["_repl_idx"])
        & (merged["first_order_num"] >= merged["last_order_num"] - max_gap)
        & (merged["first_order_num"] <= merged["last_order_num"] + max_gap)
    ]

    replaced_indices = merged["_cand_idx"].unique()
    updated.iloc[updated.index.get_indexer(replaced_indices)] = "replacement_by_another"

    return updated


def threshold_sensitivity_vectorized(
    df: pd.DataFrame,
    param_name: str,
    values: list[float],
) -> pd.DataFrame:
    """
    Vary one threshold parameter and report pattern prevalence.

    Since classify_vectorized uses boolean masks, each run is subsecond.
    """
    results = []
    for val in values:
        thresholds = {param_name: val}
        pattern_labels = classify_vectorized(df, thresholds)
        counts = pattern_labels.value_counts()
        row = {"param": param_name, "value": val, "n_sequences": len(df)}
        for pattern in PATTERN_NAMES + ["replacement_by_another"]:
            row[pattern] = counts.get(pattern, 0)
            row[f"{pattern}_pct"] = counts.get(pattern, 0) / len(df) * 100
        results.append(row)
    return pd.DataFrame(results)
