#!/usr/bin/env python3
"""
Part 6: substitution vs coexistence within an ingredient.

When a customer buys an ingredient again, do they keep the SAME product (serial
commitment), switch (replacement), or alternate? For each consecutive pair of
purchases of the same ingredient by a customer, stay = same product.

Baseline: if the products a customer buys for an ingredient were ordered at
random (labels shuffled over that ingredient's purchase slots, counts preserved),
expected P(stay) = sum_p c_p(c_p-1) / (n(n-1)). Compare observed vs expected:
  observed > expected  -> runs / serial commitment (stickier than chance)
  observed < expected  -> alternation (switch more than chance)
Also: among multi-product pairs, how often does an earlier product REAPPEAR after
the customer moved to a later one (reversion vs sustained replacement).

Every statistic is per-(customer, ingredient); each customer's history is whole
within one user-id burst, so accumulating partial counts across bursts is exact.
"""
import sys
from pathlib import Path
from collections import defaultdict
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from analyze_reorder import iter_events

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequence_analysis"
FOCUS = ["milk", "yogurt", "bread", "pasta", "banana", "ice_cream", "eggs", "cheese", "coffee", "chicken"]


def partials(d):
    """Return (stay_count, trans_count, exp_numer, exp_denom) for one scope subset.

    observed P(stay) = stay_count / trans_count (summed across bursts).
    expected P(stay) = exp_numer / exp_denom, where per (user, ingredient) with
    n>=2 purchases the shuffle baseline contributes same_pairs/n to the numerator
    and (n-1) to the denominator (weighted by transitions).
    """
    d = d.sort(["user_id", "ingredient", "order_number"])
    t = d.with_columns(pl.col("product_id").shift(1).over(["user_id", "ingredient"]).alias("prev"))
    trans = t.filter(pl.col("prev").is_not_null())
    stay_count = trans.filter(pl.col("product_id") == pl.col("prev")).height
    trans_count = trans.height

    counts = d.group_by(["user_id", "ingredient", "product_id"]).agg(pl.len().alias("c"))
    pair = (counts.group_by(["user_id", "ingredient"])
            .agg((pl.col("c") * (pl.col("c") - 1)).sum().alias("same_pairs"), pl.col("c").sum().alias("n"))
            .filter(pl.col("n") >= 2))
    exp_numer = pair.select((pl.col("same_pairs") / pl.col("n")).sum()).item() or 0.0
    exp_denom = pair.select((pl.col("n") - 1).sum()).item() or 0
    return stay_count, trans_count, exp_numer, exp_denom


def main():
    # accumulators: scope -> [stay, trans, exp_num, exp_den]
    acc = defaultdict(lambda: [0, 0, 0.0, 0])
    n_revert_pairs = 0
    n_multi_pairs = 0

    def add(scope, d):
        s, t, en, ed = partials(d)
        a = acc[scope]
        a[0] += s; a[1] += t; a[2] += en; a[3] += ed

    for chunk in iter_events():
        d = chunk.select(["user_id", "ingredient", "order_number", "product_id", "is_prepared_dish"]).unique()

        add("all", d)

        npp = d.group_by(["user_id", "ingredient"]).agg(pl.col("product_id").n_unique().alias("np"))
        dm = d.join(npp, on=["user_id", "ingredient"]).filter(pl.col("np") >= 2)
        add("multi", dm)

        add("prepared", d.filter(pl.col("is_prepared_dish") == True))
        add("base", d.filter(pl.col("is_prepared_dish") == False))

        for ing in FOCUS:
            add(f"ing:{ing}", d.filter(pl.col("ingredient") == ing))

        # reversion: among multi-product (user,ingredient), does an earlier product
        # persist past a later product's debut (coexistence) vs clean handoff
        fl = dm.group_by(["user_id", "ingredient", "product_id"]).agg(
            pl.col("order_number").min().alias("fp"), pl.col("order_number").max().alias("lp"))
        second = fl.group_by(["user_id", "ingredient"]).agg(
            pl.col("fp").sort().get(1, null_on_oob=True).alias("second_start"))
        ov = fl.join(second, on=["user_id", "ingredient"])
        reverts = ov.filter((pl.col("lp") > pl.col("second_start")) & (pl.col("fp") < pl.col("second_start")))
        n_revert_pairs += reverts.select(["user_id", "ingredient"]).unique().height
        n_multi_pairs += dm.select(["user_id", "ingredient"]).unique().height

    def report(scope):
        s, t, en, ed = acc[scope]
        obs = s / t if t else float("nan")
        exp = en / ed if ed else float("nan")
        return obs, exp, (obs / exp if exp else float("nan")), t

    o, e, lift, n = report("all")
    print(f"ALL ingredients: observed P(stay)={o*100:.1f}%  expected(shuffle)={e*100:.1f}%  lift={lift:.3f}  (n_transitions={n:,})")
    om, em, liftm, nm = report("multi")
    print(f"MULTI-product pairs: observed P(stay)={om*100:.1f}%  expected={em*100:.1f}%  lift={liftm:.3f}  (n_transitions={nm:,})")
    for lbl in ["prepared", "base"]:
        o2, e2, l2, _ = report(lbl)
        print(f"  {lbl:9s}: observed P(stay)={o2*100:.1f}%  expected={e2*100:.1f}%  lift={l2:.3f}")

    print("\nBy ingredient (observed vs expected P(stay); lift>1 = serial commitment):")
    rows = []
    for ing in FOCUS:
        oi, ei, li, ni = report(f"ing:{ing}")
        if ni < 1000:
            continue
        rows.append({"ingredient": ing, "obs_stay": oi, "exp_stay": ei, "lift": li, "n_trans": ni})
        print(f"  {ing:12s} obs={oi*100:5.1f}%  exp={ei*100:5.1f}%  lift={li:.3f}  (n={ni:,})")

    pct = n_revert_pairs / n_multi_pairs * 100
    print(f"\nMulti-product pairs where an earlier product persists past a later product's debut "
          f"(coexistence/reversion): {n_revert_pairs:,}/{n_multi_pairs:,} = {pct:.1f}%")
    print(f"  => the rest ({100 - pct:.1f}%) are clean sustained handoffs (A-run then B-run)")

    pl.DataFrame(rows).write_csv(SEQ / "substitution_by_ingredient.csv")
    pl.DataFrame([{"scope": "all", "obs": o, "exp": e, "lift": lift},
                  {"scope": "multi_product", "obs": om, "exp": em, "lift": liftm}]).write_csv(SEQ / "substitution_summary.csv")
    print("\nSaved substitution_by_ingredient.csv, substitution_summary.csv")


if __name__ == "__main__":
    main()
