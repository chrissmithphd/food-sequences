#!/usr/bin/env python3
"""Figure: what fraction of ingredients a customer tries are one-and-done vs adopted.

More truncation-resistant than raw novelty rates. Reads from iter_events() directly
(needs the full dataset). Writes analysis/figures/tried_once.png and
analysis/novelty/tried_once_summary.csv.
"""
import sys
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "sequence_analysis"))
from analyze_reorder import iter_events  # noqa: E402

FIG = ROOT / "analysis" / "figures"
NOV = ROOT / "analysis" / "novelty"
BLUE, GREEN, ORANGE, GRAY = "#1565C0", "#2E7D32", "#EF6C00", "#757575"


def main():
    once = Counter()
    twice = Counter()
    adopted = Counter()
    total_ings = Counter()
    order_counts = Counter()

    for chunk in iter_events():
        per = (chunk.select("user_id", "order_number", "ingredient").unique()
               .group_by("user_id", "ingredient")
               .agg(pl.len().alias("n_times")))
        oc = chunk.select("user_id", "order_number").unique().group_by("user_id").len()
        for uid, n in oc.iter_rows():
            order_counts[uid] += n
        for uid, ing, nt in per.iter_rows():
            total_ings[uid] += 1
            if nt == 1:
                once[uid] += 1
            elif nt == 2:
                twice[uid] += 1
            else:
                adopted[uid] += 1

    # By order-count band
    bands = [(10, 14), (15, 19), (20, 29), (30, 49), (50, 200)]
    rows = []
    for lo, hi in bands:
        users = [u for u in order_counts if lo <= order_counts[u] <= hi and total_ings[u] > 0]
        if len(users) < 50:
            continue
        o = [once.get(u, 0) / total_ings[u] * 100 for u in users]
        t = [twice.get(u, 0) / total_ings[u] * 100 for u in users]
        a = [adopted.get(u, 0) / total_ings[u] * 100 for u in users]
        rows.append({
            "order_band": f"{lo}-{hi if hi < 200 else '+'}",
            "n_customers": len(users),
            "tried_once_median": round(float(np.median(o)), 1),
            "tried_twice_median": round(float(np.median(t)), 1),
            "adopted_median": round(float(np.median(a)), 1),
        })
    df = pl.DataFrame(rows)
    df.write_csv(NOV / "tried_once_summary.csv")

    # Figure: stacked bar by order band
    labels = [r["order_band"] for r in rows]
    x = np.arange(len(labels))
    w = 0.55
    v_once = [r["tried_once_median"] for r in rows]
    v_twice = [r["tried_twice_median"] for r in rows]
    v_adopt = [r["adopted_median"] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 6))
    b1 = ax.bar(x, v_once, w, color=ORANGE, alpha=0.85, label="Tried once, never again")
    b2 = ax.bar(x, v_twice, w, bottom=v_once, color="#FDD835", alpha=0.85,
                label="Bought twice, then dropped")
    b3 = ax.bar(x, v_adopt, w,
                bottom=[a + b for a, b in zip(v_once, v_twice)],
                color=BLUE, alpha=0.85, label="Bought 3+ times (adopted)")
    # annotate each segment
    for i in range(len(labels)):
        ax.text(x[i], v_once[i] / 2, f"{v_once[i]:.0f}%", ha="center", va="center",
                fontsize=9, fontweight="bold", color="white")
        ax.text(x[i], v_once[i] + v_twice[i] / 2, f"{v_twice[i]:.0f}%", ha="center",
                va="center", fontsize=9, fontweight="bold")
        ax.text(x[i], v_once[i] + v_twice[i] + v_adopt[i] / 2, f"{v_adopt[i]:.0f}%",
                ha="center", va="center", fontsize=9, fontweight="bold", color="white")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Customer's observed order count")
    ax.set_ylabel("Share of a customer's distinct ingredients (%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("What happens after a customer tries a new ingredient?\n"
                 "About a third are one-and-done; ~16% get a second chance but don't stick; "
                 "the rest are adopted",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"tried_once.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved tried_once.png + tried_once_summary.csv")


if __name__ == "__main__":
    main()
