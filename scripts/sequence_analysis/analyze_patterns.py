#!/usr/bin/env python3
"""
Pattern classification: staples, rotation, bursts, returns.

For each user-ingredient pair (with 2+ purchases), classify the pattern:
- Persistent staple: purchased in >50% of orders with runs of 3+ consecutive
- Regular rotation: appears every few orders with consistent gaps
- Burst then absence: multiple purchases clustered early, then stops
- Return after break: purchases, gap of 5+ orders, then resumes
- Irregular/mixed: doesn't fit clear patterns

This reveals how customers use different ingredients over time.
"""

import sys
from pathlib import Path
import polars as pl
import numpy as np
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
SEQ_ANALYSIS_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 5_000
MIN_ORDERS = 10  # Need enough history to see patterns
MIN_PURCHASES = 2  # Need at least 2 purchases to have a pattern


def load_classifications():
    """Load ingredient classifications."""
    path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
    return pl.read_csv(path)


def classify_pattern(purchase_orders, total_orders):
    """
    Classify a user-ingredient purchase pattern.
    
    Args:
        purchase_orders: list of order numbers where ingredient was purchased
        total_orders: total number of orders by this user
    
    Returns:
        pattern name
    """
    n_purchases = len(purchase_orders)
    
    if n_purchases < 2:
        return "single_purchase"
    
    # Calculate gaps between purchases
    gaps = [purchase_orders[i+1] - purchase_orders[i] for i in range(n_purchases - 1)]
    
    # Purchase frequency
    purchase_rate = n_purchases / total_orders
    
    # Check for consecutive runs
    max_consecutive = 1
    current_consecutive = 1
    for i in range(len(gaps)):
        if gaps[i] == 1:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 1
    
    # Persistent staple: >50% of orders, with runs of 3+
    if purchase_rate > 0.5 and max_consecutive >= 3:
        return "persistent_staple"
    
    # Return after break: gap of 5+ orders, then resumes
    if max(gaps) >= 5:
        # Check if there are purchases both before and after the big gap
        big_gap_idx = gaps.index(max(gaps))
        if big_gap_idx > 0 and big_gap_idx < len(gaps):
            return "return_after_break"
    
    # Burst then absence: most purchases in first 30% of orders, few after
    early_cutoff = max(3, int(total_orders * 0.3))
    early_purchases = sum(1 for o in purchase_orders if o <= early_cutoff)
    if early_purchases >= n_purchases * 0.7 and n_purchases >= 3:
        return "burst_then_absence"
    
    # Regular rotation: consistent gaps (low variance)
    if len(gaps) >= 2:
        gap_mean = np.mean(gaps)
        gap_std = np.std(gaps)
        if gap_std / gap_mean < 0.5 and 2 <= gap_mean <= 5:  # Consistent gaps of 2-5 orders
            return "regular_rotation"
    
    # Everything else
    return "irregular_mixed"


def analyze_patterns(user_ids, classifications):
    """
    Analyze patterns for all user-ingredient pairs.
    
    Returns dict of pattern -> count
    """
    # Load orders
    orders = (pl.read_parquet(DATA_PROCESSED / "orders.parquet")
              .filter(pl.col("user_id").is_in(user_ids))
              .filter(pl.col("eval_set").is_in(["prior", "train"]))
              .select(["order_id", "user_id", "order_number"]))

    # Load purchases
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["order_id", "product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["order_id", "product_id"])

    purch = pl.concat([prior, train]).join(orders, on="order_id", how="inner")

    # Join classifications
    purch = purch.join(
        classifications.select(["product_id", "ingredient", "is_food"]),
        on="product_id",
        how="left"
    )

    # Filter to food only
    purch = purch.filter(pl.col("is_food") == True)

    pattern_counts = Counter()
    
    # Process each user
    for user_id in user_ids:
        user_df = purch.filter(pl.col("user_id") == user_id).sort("order_number")

        if len(user_df) == 0:
            continue

        # Get total orders for this user
        user_orders = orders.filter(pl.col("user_id") == user_id)
        total_orders = user_orders.select(pl.col("order_number").max()).item()

        if total_orders < MIN_ORDERS:
            continue

        user_data = user_df.to_dicts()

        # Group by ingredient
        ingredient_orders = {}
        for row in user_data:
            ing = row['ingredient']
            if ing is None:
                continue
            
            order_num = row['order_number']
            if ing not in ingredient_orders:
                ingredient_orders[ing] = []
            if order_num not in ingredient_orders[ing]:
                ingredient_orders[ing].append(order_num)

        # Classify each ingredient pattern
        for ing, orders_list in ingredient_orders.items():
            if len(orders_list) >= MIN_PURCHASES:
                pattern = classify_pattern(sorted(orders_list), total_orders)
                pattern_counts[pattern] += 1

    return pattern_counts


def main():
    print("="*70)
    print("PATTERN CLASSIFICATION ANALYSIS")
    print("="*70)

    print("\n1. Loading classifications...")
    classifications = load_classifications()
    print(f"   Products classified: {len(classifications):,}")

    print("\n2. Loading valid users...")
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")
    users = (orders.filter(pl.col("eval_set").is_in(["prior", "train"]))
             .group_by("user_id").agg(pl.col("order_number").max().alias("mx"))
             .filter(pl.col("mx") >= MIN_ORDERS)
             .select("user_id").to_series().to_list())
    
    print(f"   Users with {MIN_ORDERS}+ orders: {len(users):,}")

    # Process in batches
    print(f"\n3. Processing in batches of {BATCH_SIZE:,} users...")
    num_batches = (len(users) + BATCH_SIZE - 1) // BATCH_SIZE

    all_patterns = Counter()

    for batch_num in range(num_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_users = users[batch_start:batch_start + BATCH_SIZE]

        print(f"   Batch {batch_num + 1}/{num_batches}: {len(batch_users):,} users", flush=True)

        batch_patterns = analyze_patterns(batch_users, classifications)
        all_patterns.update(batch_patterns)

    print("\n4. Pattern distribution...")
    
    total = sum(all_patterns.values())
    print(f"\n   Total user-ingredient pairs analyzed: {total:,}")
    print(f"   (Users with {MIN_ORDERS}+ orders, ingredients with {MIN_PURCHASES}+ purchases)\n")

    pattern_names = {
        'persistent_staple': 'Persistent Staple',
        'regular_rotation': 'Regular Rotation',
        'burst_then_absence': 'Burst then Absence',
        'return_after_break': 'Return after Break',
        'irregular_mixed': 'Irregular/Mixed',
    }

    for pattern_key, pattern_name in pattern_names.items():
        count = all_patterns[pattern_key]
        pct = count / total * 100 if total > 0 else 0
        print(f"   {pattern_name:25s}: {count:,} ({pct:.1f}%)")

    print("\n5. Saving results...")

    # Save detailed report
    report = f"""# Purchase Pattern Classification

For each user-ingredient pair with {MIN_PURCHASES}+ purchases (users with {MIN_ORDERS}+ orders), classify the purchasing pattern:

## Pattern Definitions

- **Persistent Staple**: Purchased in >50% of orders with runs of 3+ consecutive purchases
- **Regular Rotation**: Appears every few orders with consistent gaps (2-5 orders between purchases, low variance)
- **Burst then Absence**: Multiple purchases clustered early (<30% of order history), then stops
- **Return after Break**: Purchases, gap of 5+ orders, then resumes
- **Irregular/Mixed**: Doesn't fit clear patterns above

## Results

Total user-ingredient pairs analyzed: {total:,}

| Pattern | Count | Percentage |
|---------|-------|------------|
"""

    for pattern_key, pattern_name in pattern_names.items():
        count = all_patterns[pattern_key]
        pct = count / total * 100 if total > 0 else 0
        report += f"| {pattern_name} | {count:,} | {pct:.1f}% |\n"

    report += f"""
## Interpretation

1. **Most ingredients show irregular usage:** {all_patterns['irregular_mixed']/total*100:.1f}% don't fit clean patterns, suggesting complex purchasing behavior.

2. **True staples are rare:** Only {all_patterns['persistent_staple']/total*100:.1f}% of ingredients are persistent staples bought in >50% of orders.

3. **Returns are common:** {all_patterns['return_after_break']/total*100:.1f}% show breaks of 5+ orders followed by resumption, suggesting ingredients are revisited after long gaps.

4. **Meal subscription implications:** Customers don't settle into fixed routines. They rotate through ingredients, take breaks, and return. Meal services should expect similar variety-seeking behavior.

## Methodology

- Analysis limited to users with {MIN_ORDERS}+ orders (need sufficient history)
- Only user-ingredient pairs with {MIN_PURCHASES}+ purchases (need repeat behavior)
- Patterns are mutually exclusive and exhaustive
- Classification based on purchase frequency, gap patterns, and timing
"""

    (SEQ_ANALYSIS_DIR / "PATTERN_ANALYSIS.md").write_text(report)
    print(f"   Saved PATTERN_ANALYSIS.md")

    # Save CSV
    pattern_data = []
    for pattern_key, pattern_name in pattern_names.items():
        pattern_data.append({
            'pattern': pattern_name,
            'count': all_patterns[pattern_key],
            'percentage': all_patterns[pattern_key] / total * 100 if total > 0 else 0
        })

    pl.DataFrame(pattern_data).write_csv(SEQ_ANALYSIS_DIR / "pattern_distribution.csv")
    print(f"   Saved pattern_distribution.csv")

    print("\n" + "="*70)
    print("Pattern analysis complete!")
    print("="*70)


if __name__ == "__main__":
    main()
