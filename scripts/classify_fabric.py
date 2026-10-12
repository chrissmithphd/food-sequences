#!/usr/bin/env python3
"""
Classify all products using fabric CLI + Claude LLM.

Sends batches of products through the classify_food fabric pattern,
parses the LLM output, and assembles the final classification CSV.

Requires: fabric CLI configured with a working Claude model.
Pattern: ~/.config/fabric/patterns/classify_food/system.md

Usage:
    uv run python scripts/classify_fabric.py              # full run
    uv run python scripts/classify_fabric.py --resume     # skip completed batches
    uv run python scripts/classify_fabric.py --batch 5    # run one batch only
"""

import sys
import re
import subprocess
import time
import argparse
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS

BATCH_SIZE = 500
BATCH_DIR = ANALYSIS_OUTPUTS / "fabric_batches"
OUTPUT_PATH = ANALYSIS_OUTPUTS / "food_classification_fabric.csv"


def load_products():
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    departments = pd.read_parquet(DATA_PROCESSED / "departments.parquet")

    products = products.merge(aisles, on="aisle_id", how="left")
    products = products.merge(departments, on="department_id", how="left")
    products["aisle"] = products["aisle"].fillna("unknown")
    products["department"] = products["department"].fillna("unknown")
    return products


def format_batch(products_batch):
    lines = []
    for _, row in products_batch.iterrows():
        lines.append(f"{row['product_id']}|{row['product_name']}|{row['aisle']}|{row['department']}")
    return "\n".join(lines)


def call_fabric(input_text):
    result = subprocess.run(
        ["fabric", "-p", "classify_food", "--maxTokens", "100000"],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"fabric failed: {result.stderr}")
    return result.stdout


def parse_output(raw_output, expected_ids):
    """Parse fabric output lines into classification records."""
    results = {}
    for line in raw_output.strip().split("\n"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid not in expected_ids:
            continue

        ingredient = parts[1].strip()
        is_food = parts[2].strip().lower() == "true"
        is_prepared = parts[3].strip().lower() == "true"
        results[pid] = {
            "ingredient": ingredient,
            "is_food": is_food,
            "is_prepared_dish": is_prepared,
        }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Skip completed batches")
    parser.add_argument("--batch", type=int, default=None, help="Run only this batch number")
    args = parser.parse_args()

    print("Loading products...")
    products = load_products()
    print(f"Total products: {len(products):,}")

    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    n_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Batches: {n_batches} x {BATCH_SIZE}")

    all_results = {}
    failed_batches = []

    for batch_num in range(n_batches):
        if args.batch is not None and batch_num != args.batch:
            continue

        batch_file = BATCH_DIR / f"batch_{batch_num:03d}.csv"

        if args.resume and batch_file.exists():
            cached = pd.read_csv(batch_file)
            for _, row in cached.iterrows():
                all_results[row["product_id"]] = {
                    "ingredient": row["ingredient"],
                    "is_food": row["is_food"],
                    "is_prepared_dish": row["is_prepared_dish"],
                }
            print(f"  Batch {batch_num:3d}: loaded {len(cached)} cached results")
            continue

        start = batch_num * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(products))
        batch = products.iloc[start:end]
        expected_ids = set(batch["product_id"].values)

        input_text = format_batch(batch)

        print(f"  Batch {batch_num:3d} ({start:,}-{end-1:,})...", end=" ", flush=True)
        t0 = time.time()

        try:
            raw_output = call_fabric(input_text)
            parsed = parse_output(raw_output, expected_ids)

            # Save raw output for debugging
            raw_file = BATCH_DIR / f"raw_{batch_num:03d}.txt"
            raw_file.write_text(raw_output)

            # Handle missing products in this batch
            for pid in expected_ids:
                if pid not in parsed:
                    row = batch[batch["product_id"] == pid].iloc[0]
                    parsed[pid] = {
                        "ingredient": "unclassified",
                        "is_food": True,
                        "is_prepared_dish": False,
                    }

            all_results.update(parsed)

            # Cache batch results
            batch_rows = []
            for pid, r in parsed.items():
                row = batch[batch["product_id"] == pid].iloc[0]
                batch_rows.append({
                    "product_id": pid,
                    "product_name": row["product_name"],
                    "aisle": row["aisle"],
                    "department": row["department"],
                    **r,
                })
            pd.DataFrame(batch_rows).to_csv(batch_file, index=False)

            elapsed = time.time() - t0
            parsed_count = sum(1 for v in parsed.values() if v["ingredient"] != "unclassified")
            print(f"{parsed_count}/{len(batch)} classified ({elapsed:.1f}s)")

        except Exception as e:
            elapsed = time.time() - t0
            print(f"FAILED ({elapsed:.1f}s): {e}")
            failed_batches.append(batch_num)
            for pid in expected_ids:
                row = batch[batch["product_id"] == pid].iloc[0]
                all_results[pid] = {
                    "ingredient": "unclassified",
                    "is_food": True,
                    "is_prepared_dish": False,
                }

    # Assemble final output
    print(f"\nAssembling final output...")
    rows = []
    for _, row in products.iterrows():
        pid = row["product_id"]
        r = all_results.get(pid, {"ingredient": "unclassified", "is_food": True, "is_prepared_dish": False})
        rows.append({
            "product_id": pid,
            "product_name": row["product_name"],
            "aisle": row["aisle"],
            "department": row["department"],
            "ingredient": r["ingredient"],
            "is_food": r["is_food"],
            "is_prepared_dish": r["is_prepared_dish"],
        })

    results_df = pd.DataFrame(rows)
    results_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved to {OUTPUT_PATH}")

    # Summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}")
    print(f"Total: {len(results_df):,}")
    print(f"Food: {results_df['is_food'].sum():,} ({results_df['is_food'].mean()*100:.1f}%)")
    print(f"Prepared: {results_df['is_prepared_dish'].sum():,}")
    unclassified = (results_df["ingredient"] == "unclassified").sum()
    print(f"Unclassified: {unclassified:,}")
    if failed_batches:
        print(f"Failed batches: {failed_batches}")
        print("Re-run with --resume to retry only failed batches")

    print(f"\nTop 25 ingredients:")
    for ing, cnt in results_df["ingredient"].value_counts().head(25).items():
        print(f"  {ing:30s} {cnt:>6,}")

    # Spot checks
    print(f"\nSpot checks:")
    for pid in [1, 4, 9, 33, 43, 59, 76, 148, 160, 175, 196]:
        r = results_df[results_df["product_id"] == pid].iloc[0]
        print(f"  {pid:3d}: {r['product_name'][:45]:45s} → {r['ingredient']}")


if __name__ == "__main__":
    main()
