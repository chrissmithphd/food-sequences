#!/usr/bin/env python3
"""
Sequence analysis: temporal structure beyond purchase frequency.

Supplements the existing reorder/patterns/substitution/calendar scripts. Adds:
1. Return-probability curves (already computed if return_curves.csv exists)
2. Run-length and gap distributions (vectorized)
3. Next-order prediction test

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

    # Accumulate per-ingredient gap and run stats across bursts
    ing_gap_sum = Counter()
    ing_gap_sq_sum = Counter()
    ing_gap_count = Counter()
    ing_gap1_count = Counter()
    ing_gap_ge5 = Counter()

    ing_run_sum = Counter()
    ing_run_count = Counter()
    ing_run_ge3 = Counter()
    ing_run_max = Counter()

    # shuffled baseline for runs
    rng = np.random.default_rng(42)
    shuf_run_sum = Counter()
    shuf_run_count = Counter()
    shuf_run_ge3 = Counter()

    for chunk in iter_events():
        d = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
             .join(finals, on="user_id", how="left")
             .sort(["user_id", "ingredient", "order_number"]))

        # gaps: difference between consecutive purchases of same (user, ingredient)
        d = d.with_columns(
            (pl.col("order_number") - pl.col("order_number").shift(1)
             .over(["user_id", "ingredient"])).alias("gap"))
        gaps = d.filter(pl.col("gap").is_not_null())

        # aggregate gap stats per ingredient (vectorized)
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

        # runs: consecutive purchases (gap==1) streaks
        # A run starts where gap != 1 or is the first purchase
        is_break = (pl.col("gap") != 1).fill_null(True)
        d2 = d.with_columns(is_break.cum_sum().over(["user_id", "ingredient"]).alias("run_id"))
        runs = d2.group_by(["user_id", "ingredient", "run_id"]).agg(
            pl.len().alias("rl"))
        rstats = runs.group_by("ingredient").agg(
            pl.col("rl").sum().alias("rsum"),
            pl.len().alias("rn"),
            (pl.col("rl") >= 3).sum().alias("rge3"),
            pl.col("rl").max().alias("rmax"))
        for r in rstats.iter_rows(named=True):
            ing = r["ingredient"]
            ing_run_sum[ing] += r["rsum"]
            ing_run_count[ing] += r["rn"]
            ing_run_ge3[ing] += r["rge3"]
            ing_run_max[ing] = max(ing_run_max.get(ing, 0), r["rmax"])

        # shuffled baseline: per (user, ingredient), scatter b purchases in N slots
        ui = d.group_by(["user_id", "ingredient"]).agg(
            pl.len().alias("b"), pl.col("N").first())
        ui = ui.filter(pl.col("b") >= 2)
        # sample up to 50k pairs per chunk to keep runtime bounded
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
                    shuf_run_sum[ing] += s_run
                    shuf_run_count[ing] += 1
                    shuf_run_ge3[ing] += (s_run >= 3)
                    s_run = 1
            shuf_run_sum[ing] += s_run
            shuf_run_count[ing] += 1
            shuf_run_ge3[ing] += (s_run >= 3)

    # Write gap distributions
    gap_rows = []
    for ing in sorted(ing_gap_count.keys()):
        n = ing_gap_count[ing]
        if n < 100:
            continue
        mean = ing_gap_sum[ing] / n
        var = ing_gap_sq_sum[ing] / n - mean ** 2
        std = var ** 0.5 if var > 0 else 0
        cv = std / mean if mean > 0 else None
        gap_rows.append({
            "ingredient": ing, "n_gaps": n,
            "mean_gap": round(mean, 2), "gap_cv": round(cv, 3) if cv else None,
            "pct_gap1": round(ing_gap1_count[ing] / n * 100, 1),
            "pct_gap_ge5": round(ing_gap_ge5[ing] / n * 100, 1),
        })
    pl.DataFrame(gap_rows).sort("n_gaps", descending=True).write_csv(SEQ / "gap_distributions.csv")

    # Write run lengths
    run_rows = []
    for ing in sorted(ing_run_count.keys()):
        n = ing_run_count[ing]
        if n < 100:
            continue
        sn = shuf_run_count.get(ing, 0)
        run_rows.append({
            "ingredient": ing, "n_runs": n,
            "mean_run_obs": round(ing_run_sum[ing] / n, 2),
            "mean_run_shuffled": round(shuf_run_sum[ing] / sn, 2) if sn else None,
            "pct_run_ge3_obs": round(ing_run_ge3[ing] / n * 100, 1),
            "pct_run_ge3_shuf": round(shuf_run_ge3[ing] / sn * 100, 1) if sn else None,
            "max_run": int(ing_run_max.get(ing, 0)),
        })
    pl.DataFrame(run_rows).sort("n_runs", descending=True).write_csv(SEQ / "run_lengths.csv")

    print(f"  Gap distributions for {len(gap_rows)} ingredients")
    print(f"  Run lengths for {len(run_rows)} ingredients")
    for ing in ["banana", "yogurt", "ice_cream", "pasta"]:
        r = [x for x in run_rows if x["ingredient"] == ing]
        if r:
            r = r[0]
            print(f"    {ing}: mean run {r['mean_run_obs']:.1f} (shuffled {r['mean_run_shuffled']}), "
                  f"runs>=3: {r['pct_run_ge3_obs']}% (shuffled {r['pct_run_ge3_shuf']}%)")


def pass3_next_order_prediction():
    """Does recent history predict the next order better than overall frequency?"""
    print("\nPass 3: next-order prediction test...")
    finals = _user_final_order()
    ll_freq, ll_recent, n_test = 0.0, 0.0, 0

    for chunk in iter_events():
        d = (chunk.select(["user_id", "order_number", "ingredient"]).unique()
             .join(finals, on="user_id", how="left")
             .filter(pl.col("N") >= 10))
        if d.height == 0:
            continue

        # vectorized: per user, compute frequency and recent presence
        for uid in d["user_id"].unique().to_list():
            ug = d.filter(pl.col("user_id") == uid)
            N = int(ug["N"][0])
            hist = ug.filter(pl.col("order_number") < N)
            test = ug.filter(pl.col("order_number") == N)
            if hist.height == 0 or test.height == 0:
                continue

            n_hist = N - 1
            freq_map = dict(zip(*hist.group_by("ingredient").agg(
                pl.col("order_number").n_unique().alias("n")).select(
                ["ingredient", (pl.col("n") / n_hist).alias("p")]).get_columns()))

            recent_ings = set(
                hist.filter(pl.col("order_number") >= N - 2)["ingredient"].to_list())

            eps = 0.01
            for ing in test["ingredient"].to_list():
                p_f = max(freq_map.get(ing, eps), eps)
                p_r = 0.7 if ing in recent_ings else 0.1
                ll_freq += np.log(p_f)
                ll_recent += np.log(p_r)
                n_test += 1

        if n_test > 500000:
            break

    avg_freq = ll_freq / n_test if n_test else 0
    avg_recent = ll_recent / n_test if n_test else 0
    print(f"  Test items: {n_test:,}")
    print(f"  Mean log-likelihood (overall frequency): {avg_freq:.4f}")
    print(f"  Mean log-likelihood (recent 2 orders):   {avg_recent:.4f}")

    pl.DataFrame([
        {"model": "overall_frequency", "mean_ll": round(avg_freq, 4), "n_test_items": n_test},
        {"model": "recent_2_orders", "mean_ll": round(avg_recent, 4), "n_test_items": n_test},
    ]).write_csv(SEQ / "prediction_test.csv")


def main():
    pass1_return_curves()
    pass2_runs_and_gaps()
    pass3_next_order_prediction()
    print(f"\nAll outputs in {SEQ}")


if __name__ == "__main__":
    main()
