#!/usr/bin/env python3
"""
Novelty / basket-composition analysis.

Each item (deduped per order at product grain) in orders n>=2 is:
  familiar_product            : this product seen in an earlier order
  familiar_ingredient_new_prod: product new, but its ingredient seen earlier
  new_ingredient              : ingredient never seen before (for this customer)

Reports item-/order-/customer-weighted shares, novelty vs order position (which
exposes the early-history truncation: order 1 is 100% "new" by construction), and
the per-customer product/ingredient repertoire ratio.

Full dataset, memory-safe: all quantities are per-customer, and each customer's
history is whole within one user-id burst, so the accumulation below is exact.
"""
import sys
from pathlib import Path
from collections import defaultdict
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "novelty"

CATS = ["familiar_product", "familiar_ingredient_new_prod", "new_ingredient"]


def main():
    cls_count = defaultdict(int)          # item-weighted numerators
    total_items = 0
    ow_sum = defaultdict(float); n_comp_orders = [0]   # order-weighted (common denominator)
    cw_sum = defaultdict(float); n_comp_customers = [0]   # customer-weighted (common denominator)
    pos = defaultdict(lambda: [0, 0, 0])  # order_number -> [n, n_new, n_famprod]
    rep_parts = []

    for chunk in iter_events():
        d = chunk.select(["user_id", "order_number", "product_id", "ingredient"]).unique()
        fp = d.group_by(["user_id", "product_id"]).agg(pl.col("order_number").min().alias("fp"))
        fi = d.group_by(["user_id", "ingredient"]).agg(pl.col("order_number").min().alias("fi"))
        d = (d.join(fp, on=["user_id", "product_id"], how="left")
             .join(fi, on=["user_id", "ingredient"], how="left")
             .with_columns(
                 pl.when(pl.col("order_number") > pl.col("fp")).then(pl.lit("familiar_product"))
                 .when(pl.col("order_number") > pl.col("fi")).then(pl.lit("familiar_ingredient_new_prod"))
                 .otherwise(pl.lit("new_ingredient")).alias("cls")))

        # novelty by order position (all orders, incl 1)
        for r in d.group_by("order_number").agg(
                pl.len().alias("n"),
                (pl.col("cls") == "new_ingredient").sum().alias("new"),
                (pl.col("cls") == "familiar_product").sum().alias("fam")).iter_rows(named=True):
            a = pos[r["order_number"]]; a[0] += r["n"]; a[1] += r["new"]; a[2] += r["fam"]

        comp = d.filter(pl.col("order_number") >= 2)
        total_items += comp.height
        for cls, n in comp.group_by("cls").agg(pl.len().alias("n")).iter_rows():
            cls_count[cls] += n

        # order-weighted: each (user,order)'s category shares (0 for absent) averaged
        # over ALL comp orders -> shares sum to 100%. Denominator is the common order count.
        per_order = (comp.group_by(["user_id", "order_number", "cls"]).agg(pl.len().alias("n"))
                     .with_columns((pl.col("n") / pl.col("n").sum().over(["user_id", "order_number"])).alias("frac")))
        n_comp_orders[0] += comp.select(["user_id", "order_number"]).unique().height
        for cls, s in per_order.group_by("cls").agg(pl.col("frac").sum().alias("s")).iter_rows():
            ow_sum[cls] += s

        per_cust = (comp.group_by(["user_id", "cls"]).agg(pl.len().alias("n"))
                    .with_columns((pl.col("n") / pl.col("n").sum().over("user_id")).alias("frac")))
        n_comp_customers[0] += comp.select("user_id").n_unique()
        for cls, s in per_cust.group_by("cls").agg(pl.col("frac").sum().alias("s")).iter_rows():
            cw_sum[cls] += s

        rep_parts.append(chunk.group_by("user_id").agg(
            pl.col("product_id").n_unique().alias("P"), pl.col("ingredient").n_unique().alias("I")))

    iw = {c: cls_count[c] / total_items * 100 for c in CATS}
    ow = {c: (ow_sum[c] / n_comp_orders[0] * 100 if n_comp_orders[0] else 0) for c in CATS}
    cw = {c: (cw_sum[c] / n_comp_customers[0] * 100 if n_comp_customers[0] else 0) for c in CATS}
    print("Item-weighted:     " + "  ".join(f"{c}={iw[c]:.1f}%" for c in CATS))
    print("Order-weighted:    " + "  ".join(f"{c}={ow[c]:.1f}%" for c in CATS))
    print("Customer-weighted: " + "  ".join(f"{c}={cw[c]:.1f}%" for c in CATS))

    nov = pl.DataFrame([{"order_number": k, "new_ing": v[1] / v[0], "fam_prod": v[2] / v[0], "n": v[0]}
                        for k, v in sorted(pos.items())])
    nov.write_csv(SEQ / "novelty_by_order_position.csv")
    print("\nNovelty (new-ingredient share) by order position:")
    for r in nov.filter(pl.col("order_number").is_in([1, 2, 3, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])).iter_rows(named=True):
        print(f"  order {r['order_number']:>3}: new_ingredient {r['new_ing']*100:5.1f}%  "
              f"familiar_product {r['fam_prod']*100:5.1f}%  (n items={r['n']:,})")

    rep = pl.concat(rep_parts).with_columns((pl.col("P") / pl.col("I")).alias("ratio"))
    medP, medI = rep["P"].median(), rep["I"].median()
    print(f"\nRepertoire: median distinct products={medP:.0f}, median distinct ingredients={medI:.0f}")
    print(f"  ratio-of-medians = {medP/medI:.3f}x   median-of-ratios = {rep['ratio'].median():.3f}x   "
          f"mean-of-ratios = {rep['ratio'].mean():.3f}x")

    pl.DataFrame([{"measure": "item_weighted", **{c: iw[c] for c in CATS}},
                  {"measure": "order_weighted", **{c: ow[c] for c in CATS}},
                  {"measure": "customer_weighted", **{c: cw[c] for c in CATS}}]).write_csv(SEQ / "novelty_weighting.csv")
    print("\nSaved novelty_by_order_position.csv, novelty_weighting.csv")


if __name__ == "__main__":
    main()
