#!/usr/bin/env python3
"""Score each customer's purchase history against the Food Profiles reference.

Strictly multi-label: every customer gets evidence on ALL profiles, never one bucket.
A customer "touches" a profile only through its DISTINCTIVE ingredients (lift >= 5,
support >= 30) — pantry staples like onion/oil/baking powder are excluded, so
breadth measures genuine sampling, not the fact that staples appear everywhere.

Because longer histories mechanically touch more profiles (the truncation confound
from the novelty work), everything is also reported within order-count bands.

Scores ingredient events (prior+train, food only) from analyze_reorder.iter_events()
against data/affinity/ingredient_associations.csv. Outputs summary CSVs to
analysis/food_profiles/ (no per-customer table committed):
  customer_profile_reach.csv    per-profile reach across customers
  customer_breadth.csv          breadth distribution by dimension and order-count band

Usage: uv run python -I scripts/affinity/customer_profiles.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "sequence_analysis"))
from analyze_reorder import iter_events  # noqa: E402

AFF = ROOT / "data" / "affinity"
OUT = ROOT / "analysis" / "food_profiles"
LIFT_MIN, SUPPORT_MIN = 5.0, 30   # lift>=5 excludes pantry staples that inflate reach
REGULAR_SHARE = 0.20          # "often" = profile evidence in >=20% of a customer's orders
CORE_SHARE = 0.50             # "core lean" = profile evidence in >=50% of a customer's orders
MIN_ORDERS = 10               # restrict to customers with enough history to be meaningful


def load_signatures():
    a = pl.read_csv(AFF / "ingredient_associations.csv")
    aff = pl.read_csv(AFF / "affinities.csv").select("affinity_id", "dimension")
    sig = (a.filter((pl.col("lift") >= LIFT_MIN) & (pl.col("support") >= SUPPORT_MIN))
           .select("affinity_id", "slug")
           .join(aff, on="affinity_id", how="left")
           .filter(pl.col("dimension").is_in(["meal_style", "composition", "cuisine"])))
    return sig


def main():
    sig = load_signatures()            # affinity_id, slug, dimension
    dim_of = dict(zip(sig["affinity_id"], sig["dimension"]))
    n_profiles = {d: sig.filter(pl.col("dimension") == d)["affinity_id"].n_unique()
                  for d in ("meal_style", "composition", "cuisine")}

    cust_orders_parts = []             # (user_id, n_orders)
    cust_prof_parts = []               # (user_id, affinity_id, n_hit_orders)
    cust_ings_parts = []               # (user_id, n_distinct_ingredients)

    for chunk in iter_events():
        ev = chunk.select("user_id", "order_number", "ingredient").unique()
        # total orders per customer
        co = ev.select("user_id", "order_number").unique().group_by("user_id").len().rename({"len": "n_orders"})
        cust_orders_parts.append(co)
        # distinct ingredients per customer
        ci = ev.group_by("user_id").agg(pl.col("ingredient").n_unique().alias("n_ings"))
        cust_ings_parts.append(ci)
        # orders that hit each profile via a distinctive ingredient
        hit = (ev.join(sig, left_on="ingredient", right_on="slug", how="inner")
               .select("user_id", "order_number", "affinity_id").unique()
               .group_by("user_id", "affinity_id").len().rename({"len": "n_hit_orders"}))
        cust_prof_parts.append(hit)

    cust_orders = pl.concat(cust_orders_parts).group_by("user_id").agg(pl.col("n_orders").sum())
    cust_orders = cust_orders.filter(pl.col("n_orders") >= MIN_ORDERS)
    cust_prof = (pl.concat(cust_prof_parts).group_by("user_id", "affinity_id")
                 .agg(pl.col("n_hit_orders").sum())
                 .join(cust_orders, on="user_id", how="inner"))
    cust_prof = cust_prof.with_columns(
        (pl.col("n_hit_orders") / pl.col("n_orders")).alias("order_share"),
        pl.col("affinity_id").replace_strict(dim_of, default=None).alias("dimension"),
    )
    n_cust = cust_orders.height
    print(f"customers (>= {MIN_ORDERS} orders): {n_cust:,}")

    # ---- per-profile reach ----
    reach = (cust_prof.group_by("affinity_id", "dimension").agg(
        pl.len().alias("n_touched"),
        (pl.col("order_share") >= REGULAR_SHARE).sum().alias("n_regular"),
        pl.col("order_share").median().alias("median_share_when_touched"),
    ).with_columns(
        (pl.col("n_touched") / n_cust).alias("ever_touched_frac"),
        (pl.col("n_regular") / n_cust).alias("regular_frac"),
    ).sort("ever_touched_frac", descending=True))
    reach.write_csv(OUT / "customer_profile_reach.csv")
    print("\nreach (ever-touched / regular) by profile:")
    for r in reach.iter_rows(named=True):
        print(f"  {r['dimension']:11s} {r['affinity_id']:16s} ever {r['ever_touched_frac']*100:5.1f}%  regular {r['regular_frac']*100:5.1f}%")

    # ---- breadth per customer, by dimension, and within order-count bands ----
    touched = cust_prof.group_by("user_id", "dimension").agg(
        pl.len().alias("n_touched"),
        (pl.col("order_share") >= REGULAR_SHARE).sum().alias("n_regular"),
    ).join(cust_orders, on="user_id", how="inner")
    bands = [(10, 14), (15, 19), (20, 29), (30, 49), (50, 10_000)]
    rows = []
    for dim in ("cuisine", "meal_style", "composition"):
        tot = n_profiles[dim]
        d = touched.filter(pl.col("dimension") == dim)
        for lo, hi in bands:
            b = d.filter((pl.col("n_orders") >= lo) & (pl.col("n_orders") <= hi))
            if b.height == 0:
                continue
            rows.append({
                "dimension": dim, "total_profiles": tot,
                "order_band": f"{lo}-{hi if hi < 10_000 else '+'}",
                "n_customers": b.height,
                "median_touched": float(b["n_touched"].median()),
                "median_regular": float(b["n_regular"].median()),
                "p90_touched": float(b["n_touched"].quantile(0.9)),
            })
    bl = pl.DataFrame(rows)
    bl.write_csv(OUT / "customer_breadth.csv")
    print("\nbreadth by dimension x order-count band (median profiles touched / regular):")
    for r in bl.iter_rows(named=True):
        print(f"  {r['dimension']:11s} {r['order_band']:>6} (n={r['n_customers']:>6}) "
              f"of {r['total_profiles']:>2}: touched~{r['median_touched']:.0f} regular~{r['median_regular']:.0f}")

    # ---- core profiles (>=50% of orders) per customer ----
    core = (cust_prof.filter(pl.col("order_share") >= CORE_SHARE)
            .group_by("user_id", "dimension").len().rename({"len": "n_core"}))
    # meal-style cores: distribution
    ms_core = core.filter(pl.col("dimension") == "meal_style").select("user_id", "n_core")
    # fill zeros for customers who have no core meal-style
    ms_core = (cust_orders.select("user_id").join(ms_core, on="user_id", how="left")
               .with_columns(pl.col("n_core").fill_null(0)))
    print("\n=== core meal-style profiles (in >=50% of orders) ===")
    for k in range(0, 10):
        n = ms_core.filter(pl.col("n_core") == k).height
        if n > 0:
            print(f"  {k:2d} core meal styles: {n:6,} customers ({n/n_cust*100:4.1f}%)")

    # ---- ingredient count × profile count ----
    cust_ings = (pl.concat(cust_ings_parts).group_by("user_id")
                 .agg(pl.col("n_ings").sum())
                 .join(cust_orders, on="user_id", how="inner"))
    ms_total = (cust_prof.filter(pl.col("dimension") == "meal_style")
                .group_by("user_id").len().rename({"len": "n_ms_touched"}))
    joined = (cust_ings.join(ms_total, on="user_id", how="left")
              .join(ms_core.rename({"n_core": "n_ms_core"}), on="user_id", how="left")
              .with_columns(pl.col("n_ms_touched").fill_null(0), pl.col("n_ms_core").fill_null(0)))

    # ingredient bands → profile stats
    ibands = [(1, 19), (20, 34), (35, 49), (50, 74), (75, 200)]
    irows = []
    for lo, hi in ibands:
        b = joined.filter((pl.col("n_ings") >= lo) & (pl.col("n_ings") <= hi))
        if b.height < 20:
            continue
        irows.append({
            "ing_band": f"{lo}-{hi}",
            "n_customers": b.height,
            "median_orders": int(b["n_orders"].median()),
            "median_ings": int(b["n_ings"].median()),
            "median_ms_touched": float(b["n_ms_touched"].median()),
            "median_ms_core": float(b["n_ms_core"].median()),
        })
    idf = pl.DataFrame(irows)
    idf.write_csv(OUT / "customer_pantry_vs_profiles.csv")
    print("\ningredient repertoire → meal-style profiles:")
    print(f"  {'band':>6} {'n_cust':>7} {'med_orders':>10} {'med_ings':>9} {'ms_touched':>10} {'ms_core':>8}")
    for r in idf.iter_rows(named=True):
        print(f"  {r['ing_band']:>6} {r['n_customers']:>7,} {r['median_orders']:>10} "
              f"{r['median_ings']:>9} {r['median_ms_touched']:>10.0f} {r['median_ms_core']:>8.0f}")

    # ---- top-profile intensity: per-customer, rank profiles by order_share, emit percentiles ----
    ranked = (cust_prof.filter(pl.col("dimension") == "meal_style")
              .sort(["user_id", "order_share"], descending=[False, True])
              .with_columns(pl.lit(1).cum_sum().over("user_id").alias("rank")))
    intensity_rows = []
    for rk in [1, 2, 3, 5]:
        s = ranked.filter(pl.col("rank") == rk)["order_share"]
        if len(s) < 100:
            continue
        intensity_rows.append({
            "rank": rk,
            "p10": round(float(s.quantile(0.1)), 3),
            "p25": round(float(s.quantile(0.25)), 3),
            "median": round(float(s.quantile(0.5)), 3),
            "p75": round(float(s.quantile(0.75)), 3),
            "p90": round(float(s.quantile(0.9)), 3),
        })
    pl.DataFrame(intensity_rows).write_csv(OUT / "customer_profile_intensity.csv")
    print("\nmeal-style intensity by rank (order-share for a customer's Nth strongest profile):")
    for r in intensity_rows:
        print(f"  rank {r['rank']}: p25 {r['p25']:.0%}  median {r['median']:.0%}  p75 {r['p75']:.0%}")

    # ---- engagement: orders, tenure-days, items/order by order-count band ----
    # tenure requires days_since_prior_order from orders.parquet
    tenure = pl.read_parquet(ROOT / "data" / "processed" / "orders.parquet",
                             columns=["user_id", "days_since_prior_order"]) \
               .group_by("user_id").agg(pl.col("days_since_prior_order").sum().alias("tenure_days"))
    basket = pl.read_parquet(ROOT / "data" / "processed" / "order_products_prior.parquet",
                             columns=["order_id", "product_id"])
    ord_info = pl.read_parquet(ROOT / "data" / "processed" / "orders.parquet",
                               columns=["order_id", "user_id"])
    bsize = (basket.group_by("order_id").len().rename({"len": "items"})
             .join(ord_info, on="order_id").group_by("user_id")
             .agg(pl.col("items").median().alias("med_basket_size")))
    engage = (cust_orders.join(tenure, on="user_id", how="left")
              .join(bsize, on="user_id", how="left"))
    erows = []
    for lo, hi in bands:
        b = engage.filter((pl.col("n_orders") >= lo) & (pl.col("n_orders") <= hi))
        if b.height < 20:
            continue
        erows.append({
            "order_band": f"{lo}-{hi if hi < 10_000 else '+'}",
            "n_customers": b.height,
            "median_tenure_days": int(b["tenure_days"].median()) if b["tenure_days"].null_count() < b.height else None,
            "median_basket": round(float(b["med_basket_size"].median()), 1),
        })
    pl.DataFrame(erows).write_csv(OUT / "customer_engagement.csv")
    print("\nengagement by order band:")
    for r in erows:
        print(f"  {r['order_band']:>6} n={r['n_customers']:>6,} tenure~{r['median_tenure_days']}d basket~{r['median_basket']} items")


if __name__ == "__main__":
    main()
