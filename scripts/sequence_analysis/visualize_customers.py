#!/usr/bin/env python3
"""
Figures for the customer analysis.

1. behavior_correlation_heatmap — which customer measures move together
2. within_vs_between            — within-customer vs between-customer variation
3. switch_rate_distribution     — corrected switch rate distribution
4. behavior_vs_volume           — key behaviors vs n_orders (volume dependency)
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

SEQ = Path(__file__).parent.parent.parent / "analysis" / "customers"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def fig_correlation_heatmap():
    """Behavior correlation matrix as heatmap."""
    df = pl.read_csv(SEQ / "behavior_correlations.csv")
    show_cols = ["product_repeat", "new_ing_rate", "diversity",
                 "switch_rate_corrected", "prep_share", "avg_basket",
                 "n_orders", "effective_ingredients"]
    labels = {"product_repeat": "Product\nrepeat", "new_ing_rate": "New ingredient\nrate",
              "diversity": "Diversity", "switch_rate_corrected": "Switch rate\n(corrected)",
              "prep_share": "Prepared\nfood share", "avg_basket": "Basket\nsize",
              "n_orders": "Order\ncount", "effective_ingredients": "Effective\ningredients"}

    n = len(show_cols)
    matrix = np.zeros((n, n))
    for i, a in enumerate(show_cols):
        row = df.filter(pl.col("metric") == a)
        for j, b in enumerate(show_cols):
            if b in row.columns:
                val = row[b][0]
                matrix[i, j] = val if val is not None else 0

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    short = [labels.get(c, c) for c in show_cols]
    ax.set_xticks(range(n)); ax.set_xticklabels(short, fontsize=8, rotation=45, ha="right")
    ax.set_yticks(range(n)); ax.set_yticklabels(short, fontsize=8)

    for i in range(n):
        for j in range(n):
            v = matrix[i, j]
            color = "white" if abs(v) > 0.5 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color=color)

    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("Pearson correlation")
    ax.set_title("Which Customer Behaviors Move Together?\n"
                 "Red = positive correlation, Blue = negative",
                 fontweight="bold")
    fig.tight_layout()
    _save(fig, "behavior_correlations")


def fig_within_vs_between():
    """Within-customer vs between-customer variation."""
    df = pl.read_csv(SEQ / "within_vs_between.csv")

    measures = df["measure"].to_list()
    between = df["between_customer_sd"].to_list()
    within = df["within_customer_mean_sd"].to_list()
    labels = {"basket_size": "Basket size", "prep_share": "Prepared-food share"}

    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(measures))
    h = 0.35
    ax.barh(y - h/2, between, h, color=BLUE, label="Between customers (SD)", edgecolor="white")
    ax.barh(y + h/2, within, h, color=ORANGE, label="Within customer (mean SD)", edgecolor="white")
    ax.set_yticks(y); ax.set_yticklabels([labels.get(m, m) for m in measures])
    ax.set_xlabel("Standard deviation")
    ax.set_title("How Much of Shopping Variation Is Between vs. Within Customers?\n"
                 "Similar bars = most variation is order-to-order, not person-to-person",
                 fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    for i, (b, w) in enumerate(zip(between, within)):
        ax.text(max(b, w) + 0.001, i, f"ratio {b/w:.2f}×" if w > 0 else "", va="center", fontsize=9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "within_vs_between")


def fig_switch_distribution():
    """Corrected switch rate distribution."""
    df = pl.read_csv(SEQ / "behavior_distributions.csv")
    sw = df.filter(pl.col("metric") == "switch_rate_corrected")
    med = sw.filter(pl.col("percentile") == 0.5)["value"][0]

    # We need the raw data for a histogram; read from the summary
    # and construct from the percentiles as a quick approximation
    # Actually, let's just read the parquet if available
    pq = SEQ / "customer_metrics.parquet"
    if pq.exists():
        m = pl.read_parquet(pq)
        if "switch_rate" in m.columns:
            vals = m["switch_rate"].drop_nulls().to_numpy()
        else:
            vals = None
    else:
        vals = None

    fig, ax = plt.subplots(figsize=(10, 6))
    if vals is not None:
        ax.hist(np.clip(vals, 0, 0.8), bins=np.arange(0, 0.82, 0.02),
                color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.3)
        actual_med = float(np.median(vals))
        ax.axvline(actual_med, color=RED, linestyle="--", linewidth=2,
                   label=f"Median {actual_med:.2f}")
    else:
        ax.text(0.5, 0.5, "Raw data not available", transform=ax.transAxes,
                ha="center", va="center")

    ax.set_xlabel("Within-ingredient product switch rate")
    ax.set_ylabel("Customers (≥10 orders)")
    ax.set_title("Product Switching: A Volume-Independent Customer Trait\n"
                 "How often do customers change products within an ingredient?",
                 fontweight="bold")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save(fig, "switch_rate_distribution")


def fig_volume_dependency():
    """Key behaviors vs order count — which depend on volume?"""
    pq = SEQ / "customer_metrics.parquet"
    if not pq.exists():
        print("  Skipping volume dependency (no parquet)")
        return

    m = pl.read_parquet(pq)
    # sample for scatter readability
    sample = m.sample(n=min(10000, m.height), seed=42)

    metrics = [("new_ing_rate", "New-ingredient rate", ORANGE),
               ("diversity", "Diversity (ings ÷ items)", GREEN),
               ("switch_rate", "Switch rate", PURPLE)]
    available = [(col, label, c) for col, label, c in metrics if col in sample.columns]

    fig, axes = plt.subplots(1, len(available), figsize=(5 * len(available), 5))
    if len(available) == 1:
        axes = [axes]

    for ax, (col, label, color) in zip(axes, available):
        x = sample["n_orders"].to_numpy()
        y = sample[col].drop_nulls().to_numpy()[:len(x)]
        ax.scatter(x[:len(y)], y, s=3, alpha=0.15, color=color, edgecolors="none")
        r = m.select(pl.corr("n_orders", col)).item()
        ax.set_xlabel("Number of orders")
        ax.set_ylabel(label)
        ax.set_title(f"r = {r:+.2f}", fontsize=11, fontweight="bold")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    fig.suptitle("Which Behaviors Depend on Shopping Volume?",
                 fontweight="bold", fontsize=14)
    fig.tight_layout()
    _save(fig, "behavior_vs_volume")


def main():
    print("Generating customer figures...")
    fig_correlation_heatmap()
    fig_within_vs_between()
    fig_switch_distribution()
    fig_volume_dependency()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
