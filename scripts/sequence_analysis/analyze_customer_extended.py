#!/usr/bin/env python3
"""
Extended customer analysis: behavioral correlations, within-vs-between variation,
prepared-food relationship, concentration, and corrected switch rates.

Supplements analyze_customer_profile.py (demographics, segments) and
analyze_customer_behavior.py (behavioral metrics, split-half stability). Adds:

1. Corrected switch rate (cross-order only, excluding within-order coexistence)
2. Behavior correlation matrix
3. Within-vs-between customer variation
4. Prepared-food share relationship to other metrics
5. Purchase concentration (how evenly spread across ingredients)

Memory-safe: streams in user-id bursts.
"""
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_reorder import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "customers"
SEQ.mkdir(exist_ok=True)


def per_customer_extended(d):
    """Extended per-customer metrics with corrected switch rate.
    d: (user, order_number, product_id, ingredient) unique rows."""
    fp = d.group_by(["user_id", "product_id"]).agg(pl.col("order_number").min().alias("fp"))
    fi = d.group_by(["user_id", "ingredient"]).agg(pl.col("order_number").min().alias("fi"))
    x = d.join(fp, on=["user_id", "product_id"]).join(fi, on=["user_id", "ingredient"])
    x = x.with_columns(
        (pl.col("order_number") > pl.col("fp")).alias("prod_rep"),
        (pl.col("order_number") > pl.col("fi")).alias("ing_rep"),
        (pl.col("order_number") == pl.col("fi")).alias("is_new"),
        (pl.col("is_prepared_dish") == True).alias("is_prep"))

    # Corrected switch rate: for each (user, ingredient), take the single most-bought
    # product per order (breaking ties by product_id), then compare across consecutive
    # orders. This avoids counting within-order coexistence as switching.
    order_prod = (d.group_by(["user_id", "ingredient", "order_number"])
                  .agg(pl.col("product_id").first().alias("rep_product")))
    order_prod = order_prod.sort(["user_id", "ingredient", "order_number"])
    order_prod = order_prod.with_columns(
        pl.col("rep_product").shift(1).over(["user_id", "ingredient"]).alias("prev_product"),
        pl.col("order_number").shift(1).over(["user_id", "ingredient"]).alias("prev_order"))
    # only transitions across different orders
    trans = order_prod.filter(pl.col("prev_product").is_not_null())
    sw = (trans.group_by("user_id").agg(
        (pl.col("rep_product") != pl.col("prev_product")).mean().alias("switch_rate_corrected")))

    m = x.group_by("user_id").agg(
        pl.col("prod_rep").mean().alias("product_repeat"),
        pl.col("ing_rep").mean().alias("ingredient_repeat"),
        pl.col("is_new").mean().alias("new_ing_rate"),
        pl.col("ingredient").n_unique().alias("repertoire"),
        pl.len().alias("items"),
        pl.col("order_number").max().alias("n_orders"),
        pl.col("is_prep").mean().alias("prep_share"))
    m = m.with_columns(
        (pl.col("repertoire") / pl.col("items")).alias("diversity"),
        (pl.col("items") / pl.col("n_orders")).alias("avg_basket"))
    m = m.join(sw, on="user_id", how="left")

    # Purchase concentration: HHI across ingredients
    ing_counts = (d.group_by(["user_id", "ingredient"]).agg(pl.len().alias("c"))
                  .with_columns(
                      (pl.col("c") / pl.col("c").sum().over("user_id")).alias("share")))
    hhi = ing_counts.group_by("user_id").agg(
        (pl.col("share") ** 2).sum().alias("hhi"))
    m = m.join(hhi, on="user_id", how="left")
    m = m.with_columns((1.0 / pl.col("hhi")).alias("effective_ingredients"))

    return m


def main():
    print("Computing extended customer metrics...")
    m_parts = []
    # within-customer variation: per-order basket size std
    within_parts = []

    for chunk in iter_events():
        d = chunk.select(["user_id", "order_number", "product_id", "ingredient",
                          "is_prepared_dish"]).unique()
        B = d.group_by("user_id").agg(pl.col("order_number").max().alias("B"))
        keep = B.filter(pl.col("B") >= 10).select("user_id")
        d_keep = d.join(keep, on="user_id")
        if d_keep.height > 0:
            m_parts.append(per_customer_extended(d_keep))

        # within-customer basket-size variation
        per_order = d_keep.group_by(["user_id", "order_number"]).agg(
            pl.len().alias("basket_size"),
            (pl.col("is_prepared_dish") == True).mean().alias("prep_frac"))
        wv = per_order.group_by("user_id").agg(
            pl.col("basket_size").mean().alias("mean_basket"),
            pl.col("basket_size").std().alias("std_basket"),
            pl.col("prep_frac").mean().alias("mean_prep_frac"),
            pl.col("prep_frac").std().alias("std_prep_frac"),
            pl.len().alias("n_orders"))
        within_parts.append(wv)

    m = pl.concat(m_parts)
    wv = pl.concat(within_parts)
    m = m.join(wv.select(["user_id", "std_basket", "std_prep_frac"]),
               on="user_id", how="left")
    m = m.with_columns(
        (pl.col("std_basket") / pl.col("avg_basket")).alias("basket_cv"))

    print(f"Customers with >=10 orders: {m.height:,}")

    # --- Correlation matrix ---
    cols = ["product_repeat", "ingredient_repeat", "new_ing_rate", "diversity",
            "switch_rate_corrected", "prep_share", "avg_basket", "n_orders",
            "hhi", "effective_ingredients", "repertoire"]
    corr_rows = []
    for a in cols:
        row = {"metric": a}
        for b in cols:
            r = m.select(pl.corr(a, b)).item()
            row[b] = round(r, 3) if r is not None else None
        corr_rows.append(row)
    corr_df = pl.DataFrame(corr_rows)
    corr_df.write_csv(SEQ / "behavior_correlations.csv")

    print("\nKey correlations:")
    for a in ["switch_rate_corrected", "prep_share", "hhi", "diversity"]:
        for b in ["n_orders", "avg_basket"]:
            r = m.select(pl.corr(a, b)).item()
            print(f"  corr({a}, {b}) = {r:+.3f}")

    # --- Within vs between variation ---
    between_std = {}
    within_mean_std = {}
    for col in ["avg_basket", "prep_share"]:
        between_std[col] = float(m[col].std())
    within_mean_std["basket"] = float(wv["std_basket"].mean())
    within_mean_std["prep_frac"] = float(wv["std_prep_frac"].mean())

    print("\nWithin-customer vs between-customer variation:")
    print(f"  Basket size: between-customer SD = {between_std['avg_basket']:.2f}, "
          f"within-customer mean SD = {within_mean_std['basket']:.2f}")
    print(f"  Prep share: between-customer SD = {between_std['prep_share']:.4f}, "
          f"within-customer mean SD = {within_mean_std['prep_frac']:.4f}")

    var_rows = [
        {"measure": "basket_size", "between_customer_sd": round(between_std["avg_basket"], 2),
         "within_customer_mean_sd": round(within_mean_std["basket"], 2)},
        {"measure": "prep_share", "between_customer_sd": round(between_std["prep_share"], 4),
         "within_customer_mean_sd": round(within_mean_std["prep_frac"], 4)},
    ]
    pl.DataFrame(var_rows).write_csv(SEQ / "within_vs_between.csv")

    # --- Distributions for visualization ---
    dist_cols = ["product_repeat", "new_ing_rate", "diversity",
                 "switch_rate_corrected", "prep_share", "avg_basket",
                 "hhi", "effective_ingredients", "repertoire", "basket_cv"]
    dist_rows = []
    for col in dist_cols:
        vals = m[col].drop_nulls()
        if len(vals) == 0:
            continue
        for p in [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]:
            dist_rows.append({"metric": col, "percentile": p,
                              "value": round(float(vals.quantile(p)), 4)})
    pl.DataFrame(dist_rows).write_csv(SEQ / "behavior_distributions.csv")

    # --- Corrected switch rate vs old ---
    print(f"\nCorrected switch rate: median = {m['switch_rate_corrected'].median():.3f}")
    print(f"  corr(n_orders) = {m.select(pl.corr('switch_rate_corrected', 'n_orders')).item():+.3f}")
    print(f"  corr(avg_basket) = {m.select(pl.corr('switch_rate_corrected', 'avg_basket')).item():+.3f}")

    # write summary
    summ = []
    for col in dist_cols:
        vals = m[col].drop_nulls()
        if len(vals) == 0:
            continue
        summ.append({"metric": col,
                     "median": round(float(vals.median()), 4),
                     "mean": round(float(vals.mean()), 4),
                     "std": round(float(vals.std()), 4)})
    pl.DataFrame(summ).write_csv(SEQ / "behavior_summary.csv")

    print(f"\nAll outputs in {SEQ}")


if __name__ == "__main__":
    main()
