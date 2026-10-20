#!/usr/bin/env python3
"""
Prepared dishes vs base ingredients.

Split products by the authoritative is_prepared_dish flag and compare reorder
behavior at the exact-product and ingredient grain, using next-order PROBABILITY
and a shuffle-order baseline LIFT (the same definitions as the reorder analysis).
The exact-product grain is the fair comparison: it prevents the single giant
"frozen_meal" ingredient bucket from distorting the prepared group.

Full dataset, no subsampling. Every metric is a sum over per-(customer, value)
quantities, and each customer's history is whole within one user-id burst, so the
burst accumulation below is exact — identical to processing the whole table at once.
"""
import sys
from pathlib import Path
from collections import defaultdict
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from audit_reorder_probability import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"
K_HORIZONS = [2, 3, 5, 10]


def level_partials(d, level):
    """Component sums for one group subset at one grain, for a single burst.

    d has columns user_id, order_number, <level>. Returns a dict of integer/float
    partials that sum across bursts into the final probabilities and lift.
    """
    dd = (d.select(["user_id", "order_number", level])
          .filter(pl.col(level).is_not_null())
          .unique())
    umax = dd.group_by("user_id").agg(pl.col("order_number").max().alias("umax"))
    dd = dd.join(umax, on="user_id", how="left").sort(["user_id", level, "order_number"])
    dd = dd.with_columns(pl.col("order_number").shift(-1).over(["user_id", level]).alias("next_occ"))
    dd = dd.with_columns((pl.col("next_occ") - pl.col("order_number")).alias("gap"))

    observable = pl.col("order_number") < pl.col("umax")
    p = {"n_obs": dd.filter(observable).height,
         "n_gap1": dd.filter(observable & (pl.col("gap") == 1).fill_null(False)).height,
         "n_eventual": dd.filter(observable & pl.col("gap").is_not_null()).height,
         "n_repeated": dd.filter(pl.col("gap").is_not_null()).height,
         "n_rep_gap1": dd.filter(pl.col("gap").is_not_null() & (pl.col("gap") == 1)).height}
    for k in K_HORIZONS:
        obs_k = (pl.col("umax") - pl.col("order_number")) >= k
        p[f"n_obs_{k}"] = dd.filter(obs_k).height
        p[f"n_within_{k}"] = dd.filter(obs_k & pl.col("gap").is_not_null() & (pl.col("gap") <= k)).height

    bc = (dd.group_by(["user_id", level])
          .agg(pl.len().alias("b"), pl.col("umax").first().alias("B"))
          .filter(pl.col("B") > 1))
    agg = bc.select(
        (pl.col("b") * (pl.col("b") - 1) / pl.col("B")).sum().alias("num"),
        ((pl.col("B") - 1) * pl.col("b") / pl.col("B")).sum().alias("den"))
    p["exp_num"] = agg["num"][0] or 0.0
    p["exp_den"] = agg["den"][0] or 0.0
    return p


def main():
    acc = defaultdict(lambda: defaultdict(float))   # (group, level) -> partials
    products = defaultdict(set)                       # group -> set(product_id)

    for chunk in iter_events():
        for label, flag in [("prepared_dish", True), ("base_ingredient", False)]:
            sub = chunk.filter(pl.col("is_prepared_dish") == flag)
            products[label].update(sub["product_id"].unique().to_list())
            for level in ["product_id", "ingredient"]:
                part = level_partials(sub, level)
                for k, v in part.items():
                    acc[(label, level)][k] += v

    rows = []
    for (label, level), p in acc.items():
        n_obs = p["n_obs"]
        p_next = p["n_gap1"] / n_obs if n_obs else float("nan")
        expected = p["exp_num"] / p["exp_den"] if p["exp_den"] else float("nan")
        r = {"level": level,
             "n_events_observable_next": int(n_obs),
             "p_next": p_next,
             "p_eventual_given_observable": p["n_eventual"] / n_obs if n_obs else float("nan"),
             "old_interval_immediate_frac": p["n_rep_gap1"] / p["n_repeated"] if p["n_repeated"] else float("nan"),
             "expected_p_next_shuffle": expected,
             "lift": p_next / expected if expected else float("nan"),
             "group": label, "grain": level,
             "n_products_in_group": len(products[label])}
        for k in K_HORIZONS:
            r[f"p_within_{k}"] = p[f"n_within_{k}"] / p[f"n_obs_{k}"] if p[f"n_obs_{k}"] else float("nan")
        rows.append(r)
        print(f"{label:16s} [{level:10s}] P(next)={p_next*100:5.1f}%  lift={r['lift']:.2f}x  "
              f"within5={r['p_within_5']*100:4.1f}%  n_events={int(n_obs):,}")

    cols = ["level", "n_events_observable_next", "p_next", "p_within_2", "p_within_3",
            "p_within_5", "p_within_10", "p_eventual_given_observable",
            "old_interval_immediate_frac", "expected_p_next_shuffle", "lift",
            "group", "grain", "n_products_in_group"]
    pl.DataFrame(rows).select(cols).write_csv(SEQ / "prepared_food_audit.csv")
    print(f"\nSaved {SEQ / 'prepared_food_audit.csv'}")


if __name__ == "__main__":
    main()
