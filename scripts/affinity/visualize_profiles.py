#!/usr/bin/env python3
"""Figures for the Food Profiles analysis. Reproducible from the committed
data/affinity/ CSVs (no recipe corpus needed).

1. profiles_detectability      — held-out detectability (avg precision) vs prevalence
2. profiles_signatures         — top distinctive ingredients for flagship food styles
3. profiles_common_vs_distinct — common ≠ characteristic (Italian: garlic vs marinara)
4. profiles_cuisine_confusion  — where ingredient-based cuisine ID gets confused
5. profiles_combos_vs_singles  — do ingredient pairs beat single ingredients?
"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.05)

AFF = Path(__file__).parent.parent.parent / "data" / "affinity"
FIG = Path(__file__).parent.parent.parent / "analysis" / "figures"
FIG.mkdir(exist_ok=True, parents=True)

BLUE, GREEN, ORANGE, RED, PURPLE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#C62828", "#6A1B9A", "#757575"
DIM_COLOR = {"meal_style": BLUE, "composition": GREEN, "flavor": ORANGE}


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved {name}.png")


def fig_detectability():
    ev = pl.read_csv(AFF / "evaluation_report.csv").filter(pl.col("task") == "meal")
    cov = pl.read_csv(AFF / "coverage_report.csv").select("affinity_id", "dimension")
    d = ev.join(cov, left_on="method_or_profile", right_on="affinity_id", how="left")
    d = d.rename({"accuracy_or_prevalence": "prevalence", "f1_or_avgprec": "ap"})
    d = d.sort("ap", descending=True)
    names = d["method_or_profile"].to_list()
    ap = d["ap"].to_list()
    prev = d["prevalence"].to_list()
    dims = d["dimension"].to_list()
    y = np.arange(len(names))[::-1]
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.barh(y, ap, color=[DIM_COLOR.get(x, GRAY) for x in dims], alpha=0.9, zorder=3)
    ax.scatter(prev, y, color="black", s=32, zorder=4, label="prevalence (chance baseline)")
    for yi, a, p in zip(y, ap, prev):
        ax.text(a + 0.01, yi, f"{a:.2f}", va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Held-out average precision  (bar)   ·   prevalence = base rate (dot)")
    ax.set_xlim(0, 0.85)
    handles = [plt.Rectangle((0, 0), 1, 1, color=DIM_COLOR[k]) for k in DIM_COLOR]
    ax.legend(handles + [plt.Line2D([0], [0], marker="o", color="black", linestyle="")],
              list(DIM_COLOR) + ["prevalence (random-ranking AP)"], loc="lower right", fontsize=9)
    ax.set_title("How well do ingredients identify each food profile in held-out recipes?\n"
                 "Average precision (one-vs-rest) vs. prevalence, the score a random ranking gets",
                 fontweight="bold", fontsize=12)
    _save(fig, "profiles_detectability")


def fig_signatures():
    a = pl.read_csv(AFF / "ingredient_associations.csv")
    flagship = [("salads", "Salads"), ("curries", "Curries"), ("stir_fries", "Stir-fries"),
                ("sweet_baking", "Sweet baking"), ("legume_heavy", "Legume-heavy"),
                ("seafood_oriented", "Seafood-oriented")]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for ax, (aid, title) in zip(axes.flat, flagship):
        d = (a.filter((pl.col("affinity_id") == aid) & (pl.col("support") >= 40))
             .sort("lift", descending=True).head(8))
        slugs = d["slug"].to_list()[::-1]
        lifts = d["lift"].to_list()[::-1]
        supp = d["support"].to_list()[::-1]
        yy = np.arange(len(slugs))
        ax.barh(yy, lifts, color=BLUE, alpha=0.85, zorder=3)
        for yi, lf, s in zip(yy, lifts, supp):
            ax.text(lf, yi, f"  {lf:.0f}×  (n={s})", va="center", fontsize=8)
        ax.set_yticks(yy)
        ax.set_yticklabels(slugs, fontsize=9)
        ax.set_title(title, fontweight="bold", fontsize=11)
        ax.set_xlim(0, max(lifts) * 1.35)
    fig.suptitle("What distinguishes each food style — ingredients ranked by lift "
                 "(how many times more likely than chance), support shown",
                 fontweight="bold", fontsize=13, y=1.00)
    fig.tight_layout()
    _save(fig, "profiles_signatures")


def fig_common_vs_distinct():
    a = pl.read_csv(AFF / "ingredient_associations.csv").filter(
        (pl.col("affinity_id") == "c_italian") & (pl.col("support") >= 40))
    prev = a["prevalence"].to_list()
    lift = a["lift"].to_list()
    slugs = a["slug"].to_list()
    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.scatter([p * 100 for p in prev], lift, s=40, color=GRAY, alpha=0.6, zorder=3)
    hi = {"garlic", "olive_oil", "tomato", "onion", "parmesan",
          "marinara", "ricotta", "filled_pasta", "pesto", "mozzarella"}
    for p, lf, s in zip(prev, lift, slugs):
        if s in hi:
            color = RED if lf < 1.6 else GREEN
            ax.annotate(s, (p * 100, lf), fontsize=9, color=color,
                        xytext=(4, 2), textcoords="offset points")
            ax.scatter([p * 100], [lf], s=55, color=color, zorder=4)
    ax.axhline(1.0, color=GRAY, linestyle="--", linewidth=1)
    ax.set_xlabel("Prevalence in Italian recipes (%) — how common")
    ax.set_ylabel("Lift — how distinctive (1 = no better than chance)")
    ax.set_title("Common is not the same as characteristic (Italian cuisine)\n"
                 "Garlic, onion & tomato are everywhere but barely distinctive; "
                 "marinara, ricotta & filled pasta are the real signatures",
                 fontweight="bold", fontsize=12)
    _save(fig, "profiles_common_vs_distinct")


def fig_cuisine_confusion():
    c = pl.read_csv(AFF / "cuisine_confusion.csv")
    cuisines = sorted(set(c["true"].to_list()) | set(c["predicted"].to_list()))
    idx = {k: i for i, k in enumerate(cuisines)}
    M = np.zeros((len(cuisines), len(cuisines)))
    for t, p, n in c.iter_rows():
        M[idx[t], idx[p]] += n
    M = M / M.sum(axis=1, keepdims=True)  # row-normalize -> recall
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(M, xticklabels=cuisines, yticklabels=cuisines, cmap="magma_r",
                vmin=0, vmax=1, ax=ax, cbar_kws={"label": "share of true-cuisine recipes"})
    ax.set_xlabel("predicted cuisine")
    ax.set_ylabel("true cuisine")
    ax.set_title("Ingredient-based cuisine identification: diagonal = correct\n"
                 "Off-diagonal clusters (southern↔cajun, italian↔greek, japanese↔chinese) "
                 "are where ingredients alone can't separate cuisines",
                 fontweight="bold", fontsize=12)
    _save(fig, "profiles_cuisine_confusion")


def fig_combos_vs_singles():
    a = pl.read_csv(AFF / "ingredient_associations.csv")
    comb = pl.read_csv(AFF / "ingredient_combinations.csv")
    profiles = [("curries", "Curries"), ("stir_fries", "Stir-fries"), ("chili", "Chili"),
                ("salads", "Salads"), ("sweet_baking", "Sweet baking"),
                ("legume_heavy", "Legume-heavy")]
    names, single_max, pair_max = [], [], []
    for aid, title in profiles:
        s = a.filter((pl.col("affinity_id") == aid) & (pl.col("support") >= 40))
        p = comb.filter((pl.col("affinity_id") == aid) & (pl.col("support") >= 25))
        if s.height == 0 or p.height == 0:
            continue
        names.append(title)
        single_max.append(s["lift"].max())
        pair_max.append(p["lift"].max())
    y = np.arange(len(names))
    h = 0.38
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(y + h / 2, single_max, h, color=GRAY, label="best single ingredient")
    ax.barh(y - h / 2, pair_max, h, color=PURPLE, label="best ingredient pair")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel("Lift — association strength (log scale)")
    ax.set_xscale("log")
    ax.legend(loc="lower right")
    ax.set_title("Some ingredient pairs are more distinctive than any single ingredient\n"
                 "Best-pair vs best-single lift per food style — a stronger association, "
                 "not a demonstrated classification gain",
                 fontweight="bold", fontsize=12)
    _save(fig, "profiles_combos_vs_singles")


def main():
    print("Generating Food Profiles figures...")
    fig_detectability()
    fig_signatures()
    fig_common_vs_distinct()
    fig_cuisine_confusion()
    fig_combos_vs_singles()
    print(f"All figures saved to {FIG}")


if __name__ == "__main__":
    main()
