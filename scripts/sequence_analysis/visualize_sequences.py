#!/usr/bin/env python3
"""
Figures for the sequence analysis.

New figures (supplements existing visualize_audit.py, visualize_behavior.py,
generate_pattern_gallery.py):
1. return_curves        — P(return within k orders) for selected ingredients
2. run_length_comparison — observed vs shuffled run-length stats
3. gap_regularity       — gap CV distribution across ingredients
4. prediction_comparison — frequency vs recent-history prediction
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

SEQ = Path(__file__).parent.parent.parent / "analysis" / "sequences"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def fig_return_curves():
    """P(return within k orders) for selected ingredients."""
    df = pl.read_csv(SEQ / "return_curves.csv")
    showcase = ["banana", "milk", "yogurt", "eggs", "spinach", "ice_cream",
                "pasta", "frozen_meal", "avocado", "granola_bar"]
    showcase = [s for s in showcase if s in df["ingredient"].unique().to_list()]

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = plt.cm.tab10(np.linspace(0, 1, len(showcase)))
    for ing, color in zip(showcase, colors):
        sub = df.filter(pl.col("ingredient") == ing)
        k = sub["within_k"].to_numpy()
        p = sub["p_return"].to_numpy()
        ax.plot(k, p * 100, "o-", color=color, markersize=3, linewidth=1.5, label=ing)

    ax.set_xlabel("Orders ahead (k)")
    ax.set_ylabel("P(ingredient returns within k orders) %")
    ax.set_title("Return Probability by Ingredient\n"
                 "Conditioned on having ≥k future orders (right-censored)",
                 fontweight="bold")
    ax.legend(loc="lower right", fontsize=9, ncol=2)
    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0, 100)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "return_curves")


def fig_run_comparison():
    """Observed vs shuffled run lengths for top ingredients."""
    df = pl.read_csv(SEQ / "run_lengths.csv")
    # top 20 by number of runs
    df = df.head(20).sort("mean_run_obs", descending=True)

    names = df["ingredient"].to_list()
    obs = df["mean_run_obs"].to_list()
    shuf = df["mean_run_shuffled"].to_list()

    fig, ax = plt.subplots(figsize=(12, 7))
    y = np.arange(len(names))
    h = 0.35
    ax.barh(y - h/2, obs, h, color=BLUE, label="Observed", edgecolor="white")
    ax.barh(y + h/2, shuf, h, color=GRAY, label="Shuffled baseline", edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Mean consecutive-purchase run length")
    ax.set_title("Are Purchase Runs Longer Than Expected?\n"
                 "Observed vs frequency-preserving shuffled baseline",
                 fontweight="bold")
    ax.legend(loc="lower right")
    ax.axvline(1.0, color=RED, linestyle="--", linewidth=0.5, alpha=0.3)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "run_length_comparison")


def fig_gap_regularity():
    """Gap CV distribution: how regular are inter-purchase intervals?"""
    df = pl.read_csv(SEQ / "gap_distributions.csv")
    df = df.filter(pl.col("gap_cv").is_not_null() & (pl.col("n_gaps") >= 500))
    cv = df["gap_cv"].to_numpy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # histogram of CVs
    ax1.hist(cv, bins=30, color=BLUE, alpha=0.85, edgecolor="white")
    ax1.axvline(1.0, color=RED, linestyle="--", linewidth=1.5,
                label="CV=1 (exponential/random)")
    med_cv = float(np.median(cv))
    ax1.axvline(med_cv, color=GREEN, linestyle="--", linewidth=1.5,
                label=f"Median CV={med_cv:.2f}")
    ax1.set_xlabel("Coefficient of variation of inter-purchase gaps")
    ax1.set_ylabel("Ingredients")
    ax1.set_title("How Regular Are Repurchase Intervals?", fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    # mean gap vs CV scatter
    mean_g = df["mean_gap"].to_numpy()
    ax2.scatter(mean_g, cv, s=20, alpha=0.5, color=BLUE, edgecolors="none")
    ax2.axhline(1.0, color=RED, linestyle="--", linewidth=0.8, alpha=0.5)
    # label some extremes
    names = df["ingredient"].to_list()
    for i in range(len(names)):
        if cv[i] < 0.55 or cv[i] > 2.0 or mean_g[i] > 15:
            ax2.annotate(names[i], (mean_g[i], cv[i]), fontsize=7, alpha=0.7,
                         xytext=(3, 2), textcoords="offset points")
    ax2.set_xlabel("Mean inter-purchase gap (orders)")
    ax2.set_ylabel("Gap CV")
    ax2.set_title("Regularity vs Frequency", fontweight="bold")
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    fig.tight_layout()
    _save(fig, "gap_regularity")


def fig_prediction():
    """Frequency vs recent-history prediction comparison."""
    df = pl.read_csv(SEQ / "prediction_test.csv")
    models = df["model"].to_list()
    lls = df["mean_ll"].to_list()
    n = df["n_test_items"][0]

    labels = ["Overall frequency\n(how often in all history)",
              "Recent 2 orders\n(was it bought recently?)"]
    colors = [GRAY, BLUE]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(range(len(models)), [-l for l in lls], color=colors, edgecolor="white")
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Negative mean log-likelihood\n(lower = better prediction)")
    ax.set_title(f"Does Recent History Help Predict the Next Order?\n"
                 f"Tested on {n:,} held-out items from last orders",
                 fontweight="bold")
    for bar, ll in zip(bars, lls):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{-ll:.3f}", ha="center", fontsize=11, fontweight="bold")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "prediction_comparison")


def main():
    print("Generating sequence figures...")
    fig_return_curves()
    fig_run_comparison()
    fig_gap_regularity()
    fig_prediction()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
