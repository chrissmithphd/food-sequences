#!/usr/bin/env python3
"""
Part 1.5 novelty audit. Recomputes the basket-composition split and stress-tests it.

Each item (deduped per order at product grain) in orders n>=2 is:
  familiar_product            : this product seen in an earlier order
  familiar_ingredient_new_prod: product new, but its ingredient seen earlier
  new_ingredient              : ingredient never seen before (for this customer)

Tests:
  - item-weighted vs order-weighted vs customer-weighted shares
  - novelty vs order position (exposes early-history TRUNCATION: order 1 is 100%
    "new" by construction; apparent novelty decays as the window lengthens)
  - repertoire: distinct products vs ingredients per customer; brand multiplier
    as MEDIAN OF PER-CUSTOMER RATIOS (not ratio of medians)
"""
import sys
from pathlib import Path
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import load_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"


def main():
    purch = load_events()
    d = purch.select(["user_id", "order_number", "product_id", "ingredient"]).unique()

    first_prod = d.group_by(["user_id", "product_id"]).agg(pl.col("order_number").min().alias("fp"))
    first_ing = d.group_by(["user_id", "ingredient"]).agg(pl.col("order_number").min().alias("fi"))
    d = d.join(first_prod, on=["user_id", "product_id"], how="left").join(first_ing, on=["user_id", "ingredient"], how="left")

    d = d.with_columns(
        pl.when(pl.col("order_number") > pl.col("fp")).then(pl.lit("familiar_product"))
        .when(pl.col("order_number") > pl.col("fi")).then(pl.lit("familiar_ingredient_new_prod"))
        .otherwise(pl.lit("new_ingredient")).alias("cls"))

    comp = d.filter(pl.col("order_number") >= 2)
    cats = ["familiar_product", "familiar_ingredient_new_prod", "new_ingredient"]

    # item-weighted
    iw = {r["cls"]: r["n"]/comp.height*100 for r in comp.group_by("cls").agg(pl.len().alias("n")).iter_rows(named=True)}
    print("Item-weighted: " + "  ".join(f"{c}={iw.get(c,0):.1f}%" for c in cats))

    # order-weighted: share within each order, averaged over orders
    per_order = (comp.group_by(["user_id", "order_number", "cls"]).agg(pl.len().alias("n"))
                 .with_columns((pl.col("n")/pl.col("n").sum().over(["user_id","order_number"])).alias("frac")))
    ow = {r["cls"]: r["frac"]*100 for r in per_order.group_by("cls").agg(pl.col("frac").mean().alias("frac")).iter_rows(named=True)}
    print("Order-weighted: " + "  ".join(f"{c}={ow.get(c,0):.1f}%" for c in cats))

    # customer-weighted: share within each customer, averaged over customers
    per_cust = (comp.group_by(["user_id", "cls"]).agg(pl.len().alias("n"))
                .with_columns((pl.col("n")/pl.col("n").sum().over("user_id")).alias("frac")))
    cw = {r["cls"]: r["frac"]*100 for r in per_cust.group_by("cls").agg(pl.col("frac").mean().alias("frac")).iter_rows(named=True)}
    print("Customer-weighted: " + "  ".join(f"{c}={cw.get(c,0):.1f}%" for c in cats))

    # novelty vs order position
    nov = (d.group_by("order_number").agg(
        (pl.col("cls") == "new_ingredient").mean().alias("new_ing"),
        (pl.col("cls") == "familiar_product").mean().alias("fam_prod"),
        pl.len().alias("n")).sort("order_number"))
    nov.write_csv(SEQ / "novelty_by_order_position.csv")
    print("\nNovelty (new-ingredient share) by order position:")
    for r in nov.filter(pl.col("order_number").is_in([1,2,3,5,10,20,30,40,50,60,70,80,90,100])).iter_rows(named=True):
        print(f"  order {r['order_number']:>3}: new_ingredient {r['new_ing']*100:5.1f}%  familiar_product {r['fam_prod']*100:5.1f}%  (n items={r['n']:,})")

    # repertoire ratio: median of per-customer ratios vs ratio of medians
    rep = purch.group_by("user_id").agg(
        pl.col("product_id").n_unique().alias("P"), pl.col("ingredient").n_unique().alias("I"))
    rep = rep.with_columns((pl.col("P")/pl.col("I")).alias("ratio"))
    medP = rep["P"].median(); medI = rep["I"].median()
    med_ratio = rep["ratio"].median(); mean_ratio = rep["ratio"].mean()
    print(f"\nRepertoire: median distinct products={medP:.0f}, median distinct ingredients={medI:.0f}")
    print(f"  ratio-of-medians = {medP/medI:.3f}x   median-of-ratios = {med_ratio:.3f}x   mean-of-ratios = {mean_ratio:.3f}x")

    pl.DataFrame([{"measure":"item_weighted", **{c:iw.get(c,0) for c in cats}},
                  {"measure":"order_weighted", **{c:ow.get(c,0) for c in cats}},
                  {"measure":"customer_weighted", **{c:cw.get(c,0) for c in cats}}]).write_csv(SEQ/"novelty_weighting.csv")
    print(f"\nSaved novelty_by_order_position.csv, novelty_weighting.csv")


if __name__ == "__main__":
    main()
