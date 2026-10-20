#!/usr/bin/env python3
"""
Behavioral visualizations that show the data, not just summary statistics:

1. Purchase-history heatmaps — real example customers, ingredient x successive order,
   making repeats, gaps, switching, and exploration visible.
2. Ingredient transition matrix — P(ingredient B appears in order n+1 | A in order n)
   for the top ingredients, as a heatmap (observed conditional probability), plus the
   same normalized by B's overall next-order rate (association beyond base rate).
3. Return-probability curve — for repeat purchases, P(same ingredient returns within
   k further orders | still observable), by ingredient type, window-censored.

Full dataset via memory-safe bursts for the quantitative panels; the history heatmaps
use a handful of real customers as illustrations.
"""
import sys
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events, _user_final_order

sns.set_theme(style="white", font_scale=1.0)
ROOT = Path(__file__).parent.parent.parent
FIG = ROOT / "analysis" / "figures"
ING = ROOT / "analysis" / "ingredients"
FIG.mkdir(exist_ok=True, parents=True)


def top_ingredients(k=25):
    v = pl.read_csv(ING / "top_ingredients_by_volume.csv")
    return v["ingredient"].to_list()[:k]


def fig_history_heatmaps():
    """Grids of ingredient x order for a few real customers chosen to contrast styles."""
    # pull the first burst, pick customers with a usable history length
    chunk = next(iter_events())
    finals = _user_final_order()
    d = chunk.select(["user_id", "order_number", "ingredient"]).unique().join(finals, on="user_id")
    cand = d.filter((pl.col("N") >= 18) & (pl.col("N") <= 40))
    # per customer: distinct ingredients and orders
    stat = cand.group_by("user_id").agg(pl.col("ingredient").n_unique().alias("ri"),
                                        pl.col("N").first())
    # choose four customers spanning low->high ingredient variety
    stat = stat.sort("ri")
    picks = []
    for q in [0.2, 0.5, 0.8, 0.95]:
        uid = stat["user_id"][int(q * (stat.height - 1))]
        picks.append(uid)
    picks = list(dict.fromkeys(picks))

    fig, axes = plt.subplots(1, len(picks), figsize=(4.2 * len(picks), 6))
    if len(picks) == 1:
        axes = [axes]
    for ax, uid in zip(axes, picks):
        cu = cand.filter(pl.col("user_id") == uid)
        N = int(cu["N"][0])
        # top 15 ingredients for this customer by frequency, ordered by first appearance
        freq = cu.group_by("ingredient").agg(pl.len().alias("c"), pl.col("order_number").min().alias("fo"))
        freq = freq.sort(["c", "fo"], descending=[True, False]).head(15).sort("fo")
        ings = freq["ingredient"].to_list()
        grid = np.zeros((len(ings), N))
        present = {(r["ingredient"], r["order_number"]) for r in cu.iter_rows(named=True)}
        for i, ing in enumerate(ings):
            for o in range(1, N + 1):
                if (ing, o) in present:
                    grid[i, o - 1] = 1
        ax.imshow(grid, aspect="auto", cmap="Greens", vmin=0, vmax=1, interpolation="nearest")
        ax.set_yticks(range(len(ings))); ax.set_yticklabels(ings, fontsize=7)
        ax.set_xticks([0, N - 1]); ax.set_xticklabels(["order 1", f"order {N}"], fontsize=8)
        ax.set_title(f"customer (repertoire {len(ings)}+)", fontsize=9)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.suptitle("Purchase histories — ingredient (row) x order (column), ■ = bought",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"purchase_history_heatmap.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved purchase_history_heatmap.png")


def fig_transition_matrix(topk=20):
    """Observed P(B in order n+1 | A in order n) heatmap for the top ingredients."""
    tops = top_ingredients(topk)
    tset = set(tops)
    obs = Counter()           # (A,B) -> transitions with A at n and B at n+1
    rowtot = Counter()        # A -> transitions out of an order containing A (next order exists)
    bnext = Counter()         # B -> orders n+1 (with a predecessor) containing B
    ntrans = 0                # total order-to-order transitions (n, n+1 both exist)

    for chunk in iter_events():
        ev = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
              .filter(pl.col("ingredient").is_in(tops)))
        allo = chunk.select(["user_id", "order_number"]).unique()
        nxt = allo.with_columns((pl.col("order_number") - 1).alias("prev"))  # order_number is n+1
        # transitions (user, n) -> (n+1) that both exist
        trans = allo.rename({"order_number": "n"}).join(
            nxt.select(["user_id", "prev"]).rename({"prev": "n"}), on=["user_id", "n"], how="inner").unique()
        ntrans += trans.height
        # A at order n
        a = ev.rename({"order_number": "n", "ingredient": "A"}).join(trans, on=["user_id", "n"], how="inner")
        for A, c in a.group_by("A").len().iter_rows():
            rowtot[A] += c
        # B at order n+1
        b = ev.rename({"order_number": "np1", "ingredient": "B"}).with_columns((pl.col("np1") - 1).alias("n"))
        b = b.join(trans, on=["user_id", "n"], how="inner")
        for B, c in b.group_by("B").len().iter_rows():
            bnext[B] += c
        # pairs A@n, B@n+1
        j = a.join(b.select(["user_id", "n", "B"]), on=["user_id", "n"], how="inner")
        for A, B, c in j.group_by(["A", "B"]).len().iter_rows():
            obs[(A, B)] += c

    P = np.full((len(tops), len(tops)), np.nan)
    L = np.full((len(tops), len(tops)), np.nan)
    for i, A in enumerate(tops):
        for jx, B in enumerate(tops):
            if A == B:
                continue   # self-recurrence (diagonal) is the reorder result, not a transition
            if rowtot[A]:
                p = obs[(A, B)] / rowtot[A]
                P[i, jx] = p
                base = bnext[B] / ntrans if ntrans else np.nan   # B's overall next-order rate
                L[i, jx] = p / base if base else np.nan
    pl.DataFrame({"A": np.repeat(tops, len(tops)), "B": tops * len(tops),
                  "p_next": P.flatten(), "lift_vs_base": L.flatten()}
                 ).write_csv(ROOT / "analysis" / "sequences" / "ingredient_transitions.csv")

    fig, axes = plt.subplots(1, 2, figsize=(20, 9))
    im0 = axes[0].imshow(P * 100, cmap="magma", aspect="auto")
    axes[0].set_title("P(column ingredient in next order | row ingredient now)\ntransitions to a DIFFERENT ingredient (self-recurrence excluded), %", fontsize=10, fontweight="bold")
    im1 = axes[1].imshow(np.clip(L, 0, 3), cmap="RdBu_r", aspect="auto", vmin=0, vmax=2)
    axes[1].set_title("Association beyond base rate\nP(col next | row now) / P(col in any next order)", fontsize=10, fontweight="bold")
    for ax, im in [(axes[0], im0), (axes[1], im1)]:
        ax.set_xticks(range(len(tops))); ax.set_xticklabels(tops, rotation=90, fontsize=7)
        ax.set_yticks(range(len(tops))); ax.set_yticklabels(tops, fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Ingredient transition matrix (top ingredients, full dataset)", fontweight="bold", fontsize=14)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"ingredient_transition_matrix.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Saved ingredient_transition_matrix.png")


def main():
    print("Behavioral visualizations...")
    fig_history_heatmaps()
    fig_transition_matrix()
    print(f"Saved to {FIG}")


if __name__ == "__main__":
    main()
