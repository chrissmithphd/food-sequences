#!/usr/bin/env python3
"""Figures for the Part 1 audit: lift-by-level and novelty decay."""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)
ANALYSIS = Path(__file__).parent.parent.parent / "analysis"
FIG = ANALYSIS / "figures"
FIG.mkdir(exist_ok=True, parents=True)


def fig_lift():
    d = pl.read_csv(ANALYSIS / "sequences" / "reorder_probability_audit.csv")
    order = ["product_id", "ingredient", "aisle", "category"]
    labels = {"product_id": "Product\n(exact SKU)", "ingredient": "Ingredient",
              "aisle": "Aisle", "category": "Category"}
    d = d.with_columns(pl.col("level").replace_strict({l: i for i, l in enumerate(order)}).alias("o")).sort("o")
    lvl = [labels[x] for x in d["level"]]
    obs = (d["p_next"] * 100).to_list()
    exp = (d["expected_p_next_shuffle"] * 100).to_list()
    lift = d["lift"].to_list()

    x = np.arange(len(lvl)); w = 0.38
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - w/2, obs, w, label="Observed P(next order)", color="#1565C0")
    ax.bar(x + w/2, exp, w, label="Expected if basket order were random", color="#B0BEC5")
    for i, lf in enumerate(lift):
        ax.text(i, max(obs[i], exp[i]) + 1.5, f"lift {lf:.2f}×", ha="center",
                fontweight="bold", color="#C62828" if lf < 1.1 else "#2E7D32")
    ax.set_xticks(x); ax.set_xticklabels(lvl)
    ax.set_ylabel("Next-order repeat probability (%)")
    ax.set_title("Raw persistence rises with aggregation — but the signal above chance falls\n"
                 "Category recurrence is almost all popularity; the real habit is at the product level",
                 fontweight="bold", fontsize=12)
    ax.legend(loc="upper left")
    ax.set_ylim(0, 70)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for e in ("png", "svg"):
        fig.savefig(FIG / f"reorder_lift_by_level.{e}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved reorder_lift_by_level.png")


def fig_novelty():
    d = pl.read_csv(ANALYSIS / "novelty" / "novelty_by_order_position.csv").filter(pl.col("order_number") <= 80)
    x = d["order_number"].to_list()
    newi = (d["new_ing"] * 100).to_list()
    famp = (d["fam_prod"] * 100).to_list()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, newi, color="#EF6C00", linewidth=2.5, label="New ingredient (never seen before)")
    ax.plot(x, famp, color="#1565C0", linewidth=2.5, label="Familiar product (exact repeat)")
    ax.axhspan(5, 8, color="#EF6C00", alpha=0.08)
    ax.annotate("steady-state exploration ≈ 5–7%", xy=(70, 6.5), xytext=(45, 20),
                fontsize=10, color="#EF6C00",
                arrowprops=dict(arrowstyle="->", color="#EF6C00"))
    ax.annotate("order 1 is 100% 'new' by construction\n(we can't see prior history → truncation)",
                xy=(2, 90), xytext=(12, 88), fontsize=9, color="#555",
                arrowprops=dict(arrowstyle="->", color="#999"))
    ax.set_xlabel("Order position in observed history")
    ax.set_ylabel("Share of basket items (%)")
    ax.set_title("Apparent 'novelty' is mostly truncation\n"
                 "New-ingredient share decays from 100% to a ~6% floor as history lengthens",
                 fontweight="bold", fontsize=12)
    ax.legend(loc="center right")
    ax.set_ylim(0, 100)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for e in ("png", "svg"):
        fig.savefig(FIG / f"novelty_decay.{e}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved novelty_decay.png")


if __name__ == "__main__":
    fig_lift()
    fig_novelty()
    print(f"saved to {FIG}")
