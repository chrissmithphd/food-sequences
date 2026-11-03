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
    one_and_done = Counter()
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
                one_and_done[uid] += 1
            elif nt >= 3:
                adopted[uid] += 1

    # By order-count band
    bands = [(10, 14), (15, 19), (20, 29), (30, 49), (50, 200)]
    rows = []
    for lo, hi in bands:
        users = [u for u in order_counts if lo <= order_counts[u] <= hi and total_ings[u] > 0]
        if len(users) < 50:
            continue
        oad = [one_and_done.get(u, 0) / total_ings[u] * 100 for u in users]
        adp = [adopted.get(u, 0) / total_ings[u] * 100 for u in users]
        rows.append({
            "order_band": f"{lo}-{hi if hi < 200 else '+'}",
            "n_customers": len(users),
            "tried_once_median": round(float(np.median(oad)), 1),
            "tried_once_p25": round(float(np.percentile(oad, 25)), 1),
            "tried_once_p75": round(float(np.percentile(oad, 75)), 1),
            "adopted_median": round(float(np.median(adp)), 1),
            "adopted_p25": round(float(np.percentile(adp, 25)), 1),
            "adopted_p75": round(float(np.percentile(adp, 75)), 1),
        })
    df = pl.DataFrame(rows)
    df.write_csv(NOV / "tried_once_summary.csv")

    # Figure: grouped bar by order band
    labels = [r["order_band"] for r in rows]
    x = np.arange(len(labels))
    w = 0.35
    tried = [r["tried_once_median"] for r in rows]
    adopt = [r["adopted_median"] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 6))
    b1 = ax.bar(x - w/2, tried, w, color=ORANGE, alpha=0.85, label="Tried once, never again")
    b2 = ax.bar(x + w/2, adopt, w, color=BLUE, alpha=0.85, label="Bought 3+ times (adopted)")
    for bar, val in zip(b1, tried):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.8, f"{val:.0f}%", ha="center", fontsize=9)
    for bar, val in zip(b2, adopt):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.8, f"{val:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Customer's observed order count")
    ax.set_ylabel("Share of a customer's distinct ingredients (%)")
    ax.set_ylim(0, 70)
    ax.legend(loc="upper right", fontsize=10)
    ax.set_title("What happens after a customer tries a new ingredient?\n"
                 "About a third are tried once and never bought again; "
                 "the rest become part of the repertoire",
                 fontweight="bold", fontsize=12)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"tried_once.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Saved tried_once.png + tried_once_summary.csv")


if __name__ == "__main__":
    main()
