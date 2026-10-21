#!/usr/bin/env python3
"""
Sequence analysis: temporal structure beyond purchase frequency.

Supplements the existing reorder/patterns/substitution/calendar scripts. Adds:
1. Return-probability curves (skip if already computed)
2. Run-length and gap distributions (vectorized)
3. Next-order prediction test (proper scoring: log-loss over all ingredients)

Memory-safe: streams in user-id bursts.
"""
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from analyze_reorder import iter_events, _user_final_order

ROOT = Path(__file__).parent.parent.parent
SEQ = ROOT / "analysis" / "sequences"
SEQ.mkdir(exist_ok=True)


def pass1_return_curves():
    """P(ingredient returns within k orders) — skip if already computed."""
    if (SEQ / "return_curves.csv").exists():
        print("Pass 1: return_curves.csv exists, skipping")
        return
    print("Pass 1: return-probability curves...")
    finals = _user_final_order()
    K_MAX = 20
    gap_events = defaultdict(lambda: np.zeros(K_MAX + 1))
    gap_returns = defaultdict(lambda: np.zeros(K_MAX + 1))

    for chunk in iter_events():
        d = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
             .join(finals, on="user_id", how="left")
             .sort(["user_id", "ingredient", "order_number"]))
        d = d.with_columns(
            (pl.col("order_number").shift(-1).over(["user_id", "ingredient"])
             - pl.col("order_number")).alias("gap_to_next"))
        obs = d.filter(pl.col("order_number") < pl.col("N"))

        for ing in set(obs["ingredient"].to_list()):
            sub = obs.filter(pl.col("ingredient") == ing)
            remaining = (sub["N"] - sub["order_number"]).to_numpy()
            gaps_raw = sub["gap_to_next"].to_numpy()
            gaps = np.where(gaps_raw is None, 9999,
                           np.where(np.isnan(gaps_raw.astype(float)), 9999, gaps_raw))
            for k in range(1, K_MAX + 1):
                has_k = remaining >= k
                gap_events[ing][k] += int(has_k.sum())
                gap_returns[ing][k] += int((has_k & (gaps <= k)).sum())

    rows = []
    for ing in sorted(gap_events.keys()):
        for k in range(1, K_MAX + 1):
            n = gap_events[ing][k]
            ret = gap_returns[ing][k]
            rows.append({"ingredient": ing, "within_k": k, "events": int(n),
                         "returns": int(ret),
                         "p_return": round(ret / n, 4) if n > 0 else None})
    pl.DataFrame(rows).write_csv(SEQ / "return_curves.csv")
    print(f"  Return curves for {len(gap_events)} ingredients")


def pass2_runs_and_gaps():
    """Run lengths, gap distributions, and regularity — all vectorized in Polars."""
    print("\nPass 2: run lengths and gap distributions...")
    finals = _user_final_order()

    ing_gap_sum = Counter()
    ing_gap_sq_sum = Counter()
    ing_gap_count = Counter()
    ing_gap1_count = Counter()
    ing_gap_ge5 = Counter()
    ing_run_sum = Counter()
    ing_run_count = Counter()
    ing_run_ge3 = Counter()
    ing_run_max = Counter()
    rng = np.random.default_rng(42)
    shuf_run_sum = Counter()
    shuf_run_count = Counter()
    shuf_run_ge3 = Counter()

    for chunk in iter_events():
        d = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
             .join(finals, on="user_id", how="left")
             .sort(["user_id", "ingredient", "order_number"]))
        d = d.with_columns(
            (pl.col("order_number") - pl.col("order_number").shift(1)
             .over(["user_id", "ingredient"])).alias("gap"))
        gaps = d.filter(pl.col("gap").is_not_null())

        gstats = gaps.group_by("ingredient").agg(
            pl.col("gap").sum().alias("gsum"),
            (pl.col("gap") ** 2).sum().alias("gsq"),
            pl.len().alias("gn"),
            (pl.col("gap") == 1).sum().alias("g1"),
            (pl.col("gap") >= 5).sum().alias("g5"))
        for r in gstats.iter_rows(named=True):
            ing = r["ingredient"]
            ing_gap_sum[ing] += r["gsum"]
            ing_gap_sq_sum[ing] += r["gsq"]
            ing_gap_count[ing] += r["gn"]
            ing_gap1_count[ing] += r["g1"]
            ing_gap_ge5[ing] += r["g5"]

        is_break = (pl.col("gap") != 1).fill_null(True)
        d2 = d.with_columns(is_break.cum_sum().over(["user_id", "ingredient"]).alias("run_id"))
        runs = d2.group_by(["user_id", "ingredient", "run_id"]).agg(pl.len().alias("rl"))
        rstats = runs.group_by("ingredient").agg(
            pl.col("rl").sum().alias("rsum"), pl.len().alias("rn"),
            (pl.col("rl") >= 3).sum().alias("rge3"), pl.col("rl").max().alias("rmax"))
        for r in rstats.iter_rows(named=True):
            ing = r["ingredient"]
            ing_run_sum[ing] += r["rsum"]
            ing_run_count[ing] += r["rn"]
            ing_run_ge3[ing] += r["rge3"]
            ing_run_max[ing] = max(ing_run_max.get(ing, 0), r["rmax"])

        ui = d.group_by(["user_id", "ingredient"]).agg(pl.len().alias("b"), pl.col("N").first())
        ui = ui.filter(pl.col("b") >= 2)
        sample = ui if ui.height <= 50000 else ui.sample(50000, seed=42)
        for row in sample.iter_rows(named=True):
            b, N = row["b"], row["N"]
            ing = row["ingredient"]
            if N < b:
                continue
            shuf_orders = sorted(rng.choice(N, size=b, replace=False) + 1)
            shuf_gaps = np.diff(shuf_orders)
            s_run = 1
            for g in shuf_gaps:
                if g == 1:
                    s_run += 1
                else:
                    shuf_run_sum[ing] += s_run; shuf_run_count[ing] += 1
                    shuf_run_ge3[ing] += (s_run >= 3); s_run = 1
            shuf_run_sum[ing] += s_run; shuf_run_count[ing] += 1
            shuf_run_ge3[ing] += (s_run >= 3)

    gap_rows = []
    for ing in sorted(ing_gap_count.keys()):
        n = ing_gap_count[ing]
        if n < 100:
            continue
        mean = ing_gap_sum[ing] / n
        var = ing_gap_sq_sum[ing] / n - mean ** 2
        std = var ** 0.5 if var > 0 else 0
        cv = std / mean if mean > 0 else None
        gap_rows.append({"ingredient": ing, "n_gaps": n, "mean_gap": round(mean, 2),
                         "gap_cv": round(cv, 3) if cv else None,
                         "pct_gap1": round(ing_gap1_count[ing] / n * 100, 1),
                         "pct_gap_ge5": round(ing_gap_ge5[ing] / n * 100, 1)})
    pl.DataFrame(gap_rows).sort("n_gaps", descending=True).write_csv(SEQ / "gap_distributions.csv")

    run_rows = []
    for ing in sorted(ing_run_count.keys()):
        n = ing_run_count[ing]
        if n < 100:
            continue
        sn = shuf_run_count.get(ing, 0)
        run_rows.append({"ingredient": ing, "n_runs": n,
                         "mean_run_obs": round(ing_run_sum[ing] / n, 2),
                         "mean_run_shuffled": round(shuf_run_sum[ing] / sn, 2) if sn else None,
                         "pct_run_ge3_obs": round(ing_run_ge3[ing] / n * 100, 1),
                         "pct_run_ge3_shuf": round(shuf_run_ge3[ing] / sn * 100, 1) if sn else None,
                         "max_run": int(ing_run_max.get(ing, 0))})
    pl.DataFrame(run_rows).sort("n_runs", descending=True).write_csv(SEQ / "run_lengths.csv")
    print(f"  Gap distributions for {len(gap_rows)} ingredients")
    print(f"  Run lengths for {len(run_rows)} ingredients")


def pass3_next_order_prediction():
    """Proper next-order prediction: score ALL ingredients (present and absent).

    For each customer's last order, compute the probability of each ingredient being
    present or absent under three models:
      A) Overall frequency: P = (orders containing ingredient) / (total history orders)
      B) Recency: P = frequency * 1.5 if in last 2 orders, * 0.5 otherwise (preserves
         calibration while incorporating recency)
      C) Last-2-orders binary: P = 0.5 if in last 2 orders, 0.05 otherwise

    Scores: mean log-loss over all (customer, ingredient) predictions (both present=1
    and absent=0 in the test order). Also Brier score.
    """
    print("\nPass 3: next-order prediction test (proper scoring)...")
    finals = _user_final_order()

    # first pass: collect the ingredient universe (top-100 by volume)
    ing_counts = Counter()
    for chunk in iter_events():
        for ing, c in chunk.group_by("ingredient").agg(pl.len().alias("c")).iter_rows():
            ing_counts[ing] += c
    top_ings = [ing for ing, _ in ing_counts.most_common(100)]
    top_set = set(top_ings)

    ll_freq, ll_recency, ll_binary = 0.0, 0.0, 0.0
    bs_freq, bs_recency, bs_binary = 0.0, 0.0, 0.0
    n_preds = 0
    n_customers = 0

    for chunk in iter_events():
        d = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
             .filter(pl.col("ingredient").is_in(top_ings))
             .join(finals, on="user_id", how="left")
             .filter(pl.col("N") >= 10))
        if d.height == 0:
            continue

        for uid in d["user_id"].unique().to_list():
            ug = d.filter(pl.col("user_id") == uid)
            N = int(ug["N"][0])
            hist = ug.filter(pl.col("order_number") < N)
            test_ings = set(ug.filter(pl.col("order_number") == N)["ingredient"].to_list())
            if hist.height == 0:
                continue

            n_hist = N - 1
            # frequency per ingredient
            freq_map = {}
            for ing, n_ord in hist.group_by("ingredient").agg(
                    pl.col("order_number").n_unique().alias("n")).iter_rows():
                freq_map[ing] = n_ord / n_hist

            # recent ingredients (last 2 orders)
            recent = set(hist.filter(pl.col("order_number") >= N - 2)["ingredient"].to_list())

            eps = 0.005
            for ing in top_ings:
                y = 1.0 if ing in test_ings else 0.0
                # Model A: overall frequency
                p_f = np.clip(freq_map.get(ing, eps), eps, 1 - eps)
                # Model B: frequency adjusted by recency
                if ing in recent:
                    p_r = np.clip(p_f * 1.5, eps, 1 - eps)
                else:
                    p_r = np.clip(p_f * 0.5, eps, 1 - eps)
                # Model C: binary recency
                p_b = 0.5 if ing in recent else 0.05

                ll_freq += y * np.log(p_f) + (1 - y) * np.log(1 - p_f)
                ll_recency += y * np.log(p_r) + (1 - y) * np.log(1 - p_r)
                ll_binary += y * np.log(p_b) + (1 - y) * np.log(1 - p_b)
                bs_freq += (p_f - y) ** 2
                bs_recency += (p_r - y) ** 2
                bs_binary += (p_b - y) ** 2
                n_preds += 1

            n_customers += 1
            if n_customers >= 50000:
                break
        if n_customers >= 50000:
            break

    avg = lambda x: x / n_preds if n_preds else 0
    print(f"  Customers: {n_customers:,}, predictions: {n_preds:,} "
          f"({n_preds // n_customers if n_customers else 0} ingredients/customer)")
    print(f"  Log-loss:  frequency={-avg(ll_freq):.4f}  "
          f"freq+recency={-avg(ll_recency):.4f}  binary_recency={-avg(ll_binary):.4f}")
    print(f"  Brier:     frequency={avg(bs_freq):.4f}  "
          f"freq+recency={avg(bs_recency):.4f}  binary_recency={avg(bs_binary):.4f}")

    improvement = (-avg(ll_freq) - (-avg(ll_recency))) / (-avg(ll_freq)) * 100
    print(f"  Recency improvement over frequency: {improvement:.1f}% (log-loss reduction)")

    pl.DataFrame([
        {"model": "overall_frequency", "log_loss": round(-avg(ll_freq), 4),
         "brier_score": round(avg(bs_freq), 5), "n_predictions": n_preds,
         "n_customers": n_customers},
        {"model": "frequency_plus_recency", "log_loss": round(-avg(ll_recency), 4),
         "brier_score": round(avg(bs_recency), 5), "n_predictions": n_preds,
         "n_customers": n_customers},
        {"model": "binary_recency", "log_loss": round(-avg(ll_binary), 4),
         "brier_score": round(avg(bs_binary), 5), "n_predictions": n_preds,
         "n_customers": n_customers},
    ]).write_csv(SEQ / "prediction_test.csv")


def main():
    pass1_return_curves()
    pass2_runs_and_gaps()
    pass3_next_order_prediction()
    print(f"\nAll outputs in {SEQ}")


if __name__ == "__main__":
    main()
