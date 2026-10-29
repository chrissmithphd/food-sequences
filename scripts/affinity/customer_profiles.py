#!/usr/bin/env python3
"""Score each customer's purchase history against the Food Profiles reference.

Strictly multi-label: every customer gets evidence on ALL profiles, never one bucket.
A customer "touches" a profile only through its DISTINCTIVE ingredients (lift >= 2,
support >= 30) — staples like onion/oil (lift ~ 1) are excluded by construction, so
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
LIFT_MIN, SUPPORT_MIN = 2.0, 30
REGULAR_SHARE = 0.20          # "often" = profile evidence in >=20% of a customer's orders
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

    for chunk in iter_events():
        ev = chunk.select("user_id", "order_number", "ingredient").unique()
        # total orders per customer
        co = ev.select("user_id", "order_number").unique().group_by("user_id").len().rename({"len": "n_orders"})
        cust_orders_parts.append(co)
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


if __name__ == "__main__":
    main()
