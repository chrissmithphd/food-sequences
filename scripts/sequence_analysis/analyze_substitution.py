#!/usr/bin/env python3
"""
Within an ingredient: do customers stay with one product across orders, switch, or
buy several at once?

Two behaviors are kept separate:
  - coexistence (simultaneous): an order containing >=2 products of the same
    ingredient. Not a transition.
  - transition (sequential): consecutive ORDERS in which the ingredient appears.

The stay/switch rate is measured only on the clean subset of (customer, ingredient)
pairs whose every order used a single product (>=2 such orders), where a transition
is unambiguous. There, observed P(stay the same product) is compared to a shuffle
baseline that permutes the product labels across those orders (counts preserved):
expected P(stay) = sum_p c_p(c_p-1) / (m(m-1)) for m single-product orders. Observed >
expected = products come in runs; < expected = alternation; ~= chance = no structure.

Per-(customer, ingredient); each customer is whole within one burst, so partials sum.
"""
import sys
from pathlib import Path
from collections import defaultdict
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

SEQ = Path(__file__).parent.parent.parent / "analysis" / "sequences"
FOCUS = ["milk", "yogurt", "bread", "pasta", "banana", "ice_cream", "eggs", "cheese", "coffee", "chicken"]


def partials(d):
    """Return counters for one scope subset (rows: unique user,ingredient,order,product)."""
    o = (d.group_by(["user_id", "ingredient", "order_number"])
         .agg(pl.col("product_id").alias("prods"))
         .with_columns(pl.col("prods").list.len().alias("nprod"),
                       pl.col("prods").cast(pl.List(pl.Utf8)).list.sort().list.join("-").alias("sig")))
    n_ing_orders = o.height
    n_coexist = o.filter(pl.col("nprod") >= 2).height

    # clean subset: (user,ingredient) where every order is single-product and >=2 orders
    mx = o.group_by(["user_id", "ingredient"]).agg(
        pl.col("nprod").max().alias("mx"), pl.len().alias("m"))
    keys = mx.filter((pl.col("mx") == 1) & (pl.col("m") >= 2)).select(["user_id", "ingredient"])
    sp = (o.join(keys, on=["user_id", "ingredient"], how="inner")
          .sort(["user_id", "ingredient", "order_number"]))
    sp = sp.with_columns(pl.col("sig").shift(1).over(["user_id", "ingredient"]).alias("psig"))
    tr = sp.filter(pl.col("psig").is_not_null())
    sp_trans = tr.height
    sp_stay = tr.filter(pl.col("sig") == pl.col("psig")).height

    # Expected P(stay) under random permutation: for a (user, ingredient) pair with m
    # single-product orders and product p appearing c_p times, the exact expectation is
    # sum_p c_p(c_p-1) / (m(m-1)).  Aggregated transition-weighted: each transition
    # contributes equally (pairs with more transitions weigh more, matching observed).
    cnt = sp.group_by(["user_id", "ingredient", "sig"]).agg(pl.len().alias("c"))
    pa = cnt.group_by(["user_id", "ingredient"]).agg(
        (pl.col("c") * (pl.col("c") - 1)).sum().alias("same"), pl.col("c").sum().alias("m"))
    exp_num = pa.select((pl.col("same") / pl.col("m")).sum()).item() or 0.0
    exp_den = pa.select((pl.col("m") - 1).sum()).item() or 0
    return dict(n_ing_orders=n_ing_orders, n_coexist=n_coexist,
                sp_trans=sp_trans, sp_stay=sp_stay, exp_num=exp_num, exp_den=exp_den)


def main():
    acc = defaultdict(lambda: defaultdict(float))

    def add(scope, d):
        for k, v in partials(d).items():
            acc[scope][k] += v

    for chunk in iter_events():
        d = chunk.select(["user_id", "ingredient", "order_number", "product_id", "is_prepared_dish"]).unique()
        add("all", d)
        add("prepared", d.filter(pl.col("is_prepared_dish") == True))
        add("base", d.filter(pl.col("is_prepared_dish") == False))
        for ing in FOCUS:
            add(f"ing:{ing}", d.filter(pl.col("ingredient") == ing))

    def rep(scope):
        a = acc[scope]
        obs = a["sp_stay"] / a["sp_trans"] if a["sp_trans"] else float("nan")
        exp = a["exp_num"] / a["exp_den"] if a["exp_den"] else float("nan")
        coex = a["n_coexist"] / a["n_ing_orders"] if a["n_ing_orders"] else float("nan")
        return obs, exp, (obs / exp if exp else float("nan")), int(a["sp_trans"]), coex

    o, e, lift, n, coex = rep("all")
    print(f"ALL: single-product-subset P(stay)={o*100:.1f}%  shuffle-expected={e*100:.1f}%  "
          f"lift={lift:.3f}  (n_transitions={n:,})")
    print(f"Within-order coexistence (>=2 products of an ingredient in one order): {coex*100:.1f}% of ingredient-orders")
    for lbl in ["prepared", "base"]:
        o2, e2, l2, _, cx2 = rep(lbl)
        print(f"  {lbl:9s}: P(stay)={o2*100:.1f}%  expected={e2*100:.1f}%  lift={l2:.3f}  coexistence={cx2*100:.1f}%")

    print("\nBy ingredient (single-product subset; lift>1 = runs, <1 = alternation):")
    rows = []
    for ing in FOCUS:
        oi, ei, li, ni, cxi = rep(f"ing:{ing}")
        if ni < 1000:
            continue
        rows.append({"ingredient": ing, "obs_stay": oi, "exp_stay": ei, "lift": li,
                     "n_trans": ni, "coexistence": cxi})
        print(f"  {ing:12s} stay={oi*100:5.1f}%  exp={ei*100:5.1f}%  lift={li:.3f}  "
              f"coexist={cxi*100:4.1f}%  (n={ni:,})")

    pl.DataFrame(rows).write_csv(SEQ / "substitution_by_ingredient.csv")
    pl.DataFrame([{"scope": "all", "obs_stay": o, "exp_stay": e, "lift": lift, "coexistence": coex}]
                 ).write_csv(SEQ / "substitution_summary.csv")
    print("\nSaved substitution_by_ingredient.csv, substitution_summary.csv")


if __name__ == "__main__":
    main()
