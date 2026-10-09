#!/usr/bin/env python3
"""
Generate Phase 2 figures: pattern prevalence, example timelines,
threshold sensitivity, and prepared vs non-prepared comparison.

Outputs PNG + SVG to analysis/figures/.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import FIGURES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Consistent style
sns.set_theme(style="whitegrid", font_scale=1.1)
PATTERN_COLORS = {
    "persistent_staple": "#2196F3",
    "regular_rotation": "#4CAF50",
    "burst_then_absence": "#FF9800",
    "return_after_break": "#9C27B0",
    "replacement_by_another": "#F44336",
    "unclassified": "#9E9E9E",
}
PATTERN_ORDER = [
    "persistent_staple", "regular_rotation", "burst_then_absence",
    "return_after_break", "replacement_by_another", "unclassified",
]
PATTERN_LABELS = {
    "persistent_staple": "Persistent Staple",
    "regular_rotation": "Regular Rotation",
    "burst_then_absence": "Burst then Absence",
    "return_after_break": "Return after Break",
    "replacement_by_another": "Replacement by Another",
    "unclassified": "Unclassified",
}


def save_fig(fig, name):
    for ext in ["png", "svg"]:
        path = FIGURES_DIR / f"{name}.{ext}"
        fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png/svg")


def fig1_pattern_prevalence(classified):
    """Bar chart of pattern prevalence."""
    counts = classified["pattern"].value_counts()
    total = len(classified)

    patterns = [p for p in PATTERN_ORDER if p in counts]
    values = [counts[p] for p in patterns]
    pcts = [counts[p] / total * 100 for p in patterns]
    colors = [PATTERN_COLORS[p] for p in patterns]
    labels = [PATTERN_LABELS[p] for p in patterns]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(range(len(patterns)), pcts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(patterns)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Percentage of Classifiable Sequences")
    ax.set_title("Purchase Pattern Prevalence\n(4.5M user-product sequences, users with ≥10 orders)")
    ax.invert_yaxis()

    for bar, pct, count in zip(bars, pcts, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{pct:.1f}% ({count:,})", va="center", fontsize=9)

    ax.set_xlim(0, max(pcts) * 1.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "pattern_prevalence")


def fig2_pattern_gallery(classified):
    """
    Gallery showing 5 example sequences per pattern.
    Order columns, food rows, colored marks.
    """
    fig, axes = plt.subplots(5, 1, figsize=(14, 14), gridspec_kw={"hspace": 0.4})

    patterns_to_show = [
        "persistent_staple", "regular_rotation", "burst_then_absence",
        "return_after_break", "replacement_by_another",
    ]

    for ax_idx, pattern in enumerate(patterns_to_show):
        ax = axes[ax_idx]
        subset = classified[classified["pattern"] == pattern]
        if len(subset) == 0:
            ax.set_visible(False)
            continue

        # Pick 5 diverse examples: sample from different total_orders ranges
        examples = subset.sample(n=min(5, len(subset)), random_state=42 + ax_idx)

        color = PATTERN_COLORS[pattern]
        max_orders = 0

        for row_idx, (_, row) in enumerate(examples.iterrows()):
            nums = set(sorted(row["order_numbers"]))
            total = int(row["user_total_orders"])
            display_total = min(total, 50)
            max_orders = max(max_orders, display_total)

            for o in range(1, display_total + 1):
                if o in nums:
                    ax.scatter(o, row_idx, color=color, s=30, zorder=3, marker="s")
                else:
                    ax.scatter(o, row_idx, color="#E0E0E0", s=8, zorder=2, marker=".")

        # Labels
        y_labels = []
        for _, row in examples.iterrows():
            name = str(row["product_name"])[:30]
            freq = row["selection_frequency"]
            y_labels.append(f"{name} ({freq:.0%})")

        ax.set_yticks(range(len(examples)))
        ax.set_yticklabels(y_labels, fontsize=8)
        ax.set_title(f"{PATTERN_LABELS[pattern]}", fontweight="bold", fontsize=11,
                      color=color)
        ax.set_xlim(0, max_orders + 2)
        ax.set_xlabel("Order Number" if ax_idx == 4 else "")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.invert_yaxis()

    fig.suptitle("Gallery of Observed Purchase Patterns\n"
                 "Each row = one product for one customer. ■ = purchased, · = not purchased.",
                 fontsize=13, fontweight="bold", y=1.01)
    save_fig(fig, "pattern_gallery")


def fig3_prepared_vs_other(classified):
    """Side-by-side pattern comparison for prepared foods vs other groceries."""
    patterns_ordered = [p for p in PATTERN_ORDER if p != "unclassified"]

    prep = classified[classified["is_prepared_food"]]
    other = classified[~classified["is_prepared_food"]]

    prep_pcts = []
    other_pcts = []
    for p in patterns_ordered:
        prep_pcts.append((prep["pattern"] == p).mean() * 100)
        other_pcts.append((other["pattern"] == p).mean() * 100)

    x = np.arange(len(patterns_ordered))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    bars1 = ax.bar(x - width / 2, prep_pcts, width, label="Prepared Foods",
                    color="#FF7043", edgecolor="white")
    bars2 = ax.bar(x + width / 2, other_pcts, width, label="Other Groceries",
                    color="#42A5F5", edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels([PATTERN_LABELS[p] for p in patterns_ordered], rotation=25, ha="right")
    ax.set_ylabel("Percentage of Sequences")
    ax.set_title("Pattern Prevalence: Prepared Foods vs. Other Groceries")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    save_fig(fig, "prepared_vs_other_patterns")


def fig4_threshold_sensitivity(sensitivity):
    """Multi-panel sensitivity plot."""
    params = sensitivity["param"].unique()
    n_params = len(params)
    cols = 3
    rows = (n_params + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
    axes = axes.flatten()

    patterns_to_plot = ["persistent_staple", "regular_rotation", "burst_then_absence",
                        "return_after_break", "unclassified"]

    for i, param in enumerate(params):
        ax = axes[i]
        sub = sensitivity[sensitivity["param"] == param].sort_values("value")

        for pat in patterns_to_plot:
            ax.plot(sub["value"], sub[f"{pat}_pct"],
                    color=PATTERN_COLORS[pat], marker="o", markersize=4,
                    label=PATTERN_LABELS[pat])

        ax.set_xlabel(param.replace("_", " ").title(), fontsize=9)
        ax.set_ylabel("% of sequences")
        ax.set_title(param, fontsize=10)

    # Legend on last visible axes
    handles, labels_legend = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_legend, loc="lower center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, -0.02))

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Threshold Sensitivity Analysis\n"
                 "How pattern prevalence changes when varying each classification threshold",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    save_fig(fig, "threshold_sensitivity")


def fig5_sequence_features_by_pattern(classified):
    """Box plots of key features by pattern."""
    patterns_to_show = [p for p in PATTERN_ORDER if p != "unclassified" and p in classified["pattern"].values]

    # Sample for plotting (box plots on 4.5M rows is slow)
    sample = classified[classified["pattern"].isin(patterns_to_show)].sample(
        n=min(200_000, len(classified)), random_state=42
    )

    features = ["selection_frequency", "max_consecutive", "mean_gap", "recency"]
    feature_titles = ["Selection Frequency", "Max Consecutive", "Mean Gap (orders)", "Recency (orders since last)"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, (feat, title) in enumerate(zip(features, feature_titles)):
        ax = axes[idx]
        data_for_plot = []
        labels_for_plot = []
        colors_for_plot = []

        for p in patterns_to_show:
            sub = sample[sample["pattern"] == p]
            data_for_plot.append(sub[feat].clip(upper=sub[feat].quantile(0.95)))
            labels_for_plot.append(PATTERN_LABELS[p])
            colors_for_plot.append(PATTERN_COLORS[p])

        bp = ax.boxplot(data_for_plot, tick_labels=labels_for_plot, patch_artist=True,
                        showfliers=False, widths=0.6)
        for patch, color in zip(bp["boxes"], colors_for_plot):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_title(title)
        ax.tick_params(axis="x", rotation=30)

    fig.suptitle("Sequence Feature Distributions by Pattern", fontsize=13, fontweight="bold")
    fig.tight_layout()
    save_fig(fig, "features_by_pattern")


def main():
    print("Generating Phase 2 figures...")

    classified = pd.read_parquet("analysis/outputs/pattern_classification.parquet")
    sensitivity = pd.read_parquet("analysis/outputs/threshold_sensitivity.parquet")

    print(f"  Loaded {len(classified):,} classified sequences")

    fig1_pattern_prevalence(classified)
    fig2_pattern_gallery(classified)
    fig3_prepared_vs_other(classified)
    fig4_threshold_sensitivity(sensitivity)
    fig5_sequence_features_by_pattern(classified)

    print(f"\n✓ All figures saved to {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
