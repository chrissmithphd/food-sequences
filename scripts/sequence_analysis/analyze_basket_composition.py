#!/usr/bin/env python3
"""
Basket composition analysis: familiar products, familiar ingredients, new ingredients.

For each order (after the first), classify each item as:
- Familiar product: exact SKU purchased before
- Familiar ingredient, new product: same ingredient but different product (brand switching)
- New ingredient: never purchased this ingredient before

This reveals how much variety comes from brand switching vs actual dietary change.
"""

import sys
from pathlib import Path
import polars as pl
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

SEQ_ANALYSIS_DIR = Path(__file__).parent.parent.parent / "analysis" / "sequence_analysis"
SEQ_ANALYSIS_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 5_000
MIN_ORDERS = 4


def load_classifications():
    """Load ingredient classifications."""
    path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "food_classification.csv"
    return pl.read_csv(path)


def load_taxonomy_categories():
    """Map ingredients to categories."""
    taxonomy_path = Path(__file__).parent.parent.parent / "analysis" / "classification" / "INGREDIENT_TAXONOMY.md"

    with open(taxonomy_path) as f:
        content = f.read()

    ingredients = {}
    current_category = None

    for line in content.split('\n'):
        if line.startswith('### '):
            current_category = line.replace('###', '').strip()
        elif line.startswith('- `') and current_category:
            import re
            if match := re.match(r'^- `([a-z_]+)`: (.+)$', line):
                ing_name = match.group(1)
                ingredients[ing_name] = current_category

    return ingredients


def get_valid_users(min_orders=MIN_ORDERS):
    """Get users with at least min_orders."""
    orders = pl.read_parquet(DATA_PROCESSED / "orders.parquet")
    uc = (orders.filter(pl.col("eval_set").is_in(["prior", "train"]))
          .group_by("user_id").agg(pl.col("order_number").max().alias("mx"))
          .filter(pl.col("mx") >= min_orders))
    return sorted(uc["user_id"].to_list())


def analyze_basket_composition(user_ids, classifications):
    """
    Analyze composition of each basket (order 2+).

    Returns:
    - item_counts: dict with 'familiar_product', 'familiar_ingredient', 'new_ingredient'
    - customer_means: array of [familiar_product_%, familiar_ingredient_%, new_ingredient_%] per customer
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

    # Aggregate counts
    item_counts = {
        'familiar_product': 0,
        'familiar_ingredient': 0,
        'new_ingredient': 0,
        'total_items': 0,
    }

    customer_compositions = []

    # Process each user
    for user_id in user_ids:
        user_df = purch.filter(pl.col("user_id") == user_id).sort("order_number")

        if len(user_df) == 0:
            continue

        user_data = user_df.to_dicts()

        # Track history
        seen_products = set()
        seen_ingredients = set()

        # Customer-level counts
        cust_familiar_product = 0
        cust_familiar_ingredient = 0
        cust_new_ingredient = 0

        current_order = None
        order_items = []

        for row in user_data:
            order_num = row['order_number']
            product_id = row['product_id']
            ingredient = row['ingredient']

            if ingredient is None:
                continue

            # Process previous order when we hit a new one
            if order_num != current_order:
                if current_order is not None and current_order > 1:
                    # Classify items from previous order
                    for item in order_items:
                        pid, ing = item

                        if pid in seen_products:
                            item_counts['familiar_product'] += 1
                            cust_familiar_product += 1
                        elif ing in seen_ingredients:
                            item_counts['familiar_ingredient'] += 1
                            cust_familiar_ingredient += 1
                        else:
                            item_counts['new_ingredient'] += 1
                            cust_new_ingredient += 1

                        item_counts['total_items'] += 1

                        # Update history
                        seen_products.add(pid)
                        seen_ingredients.add(ing)

                elif current_order == 1:
                    # First order - just record history
                    for item in order_items:
                        pid, ing = item
                        seen_products.add(pid)
                        seen_ingredients.add(ing)

                current_order = order_num
                order_items = []

            order_items.append((product_id, ingredient))

        # Process final order
        if current_order is not None and current_order > 1:
            for item in order_items:
                pid, ing = item

                if pid in seen_products:
                    item_counts['familiar_product'] += 1
                    cust_familiar_product += 1
                elif ing in seen_ingredients:
                    item_counts['familiar_ingredient'] += 1
                    cust_familiar_ingredient += 1
                else:
                    item_counts['new_ingredient'] += 1
                    cust_new_ingredient += 1

                item_counts['total_items'] += 1

        # Store customer percentages
        cust_total = cust_familiar_product + cust_familiar_ingredient + cust_new_ingredient
        if cust_total > 0:
            customer_compositions.append([
                cust_familiar_product / cust_total * 100,
                cust_familiar_ingredient / cust_total * 100,
                cust_new_ingredient / cust_total * 100,
            ])

    return item_counts, np.array(customer_compositions) if customer_compositions else None


def main():
    print("="*70)
    print("BASKET COMPOSITION ANALYSIS")
    print("="*70)

    print("\n1. Loading classifications and taxonomy...")
    classifications = load_classifications()
    taxonomy_categories = load_taxonomy_categories()

    classifications = classifications.with_columns(
        pl.col("ingredient").map_elements(
            lambda x: taxonomy_categories.get(x, "Unknown"),
            return_dtype=pl.Utf8
        ).alias("category")
    )

    print(f"   Products classified: {len(classifications):,}")

    print("\n2. Loading valid users...")
    users = get_valid_users(min_orders=MIN_ORDERS)
    print(f"   Users with {MIN_ORDERS}+ orders: {len(users):,}")

    # Process in batches
    print(f"\n3. Processing in batches of {BATCH_SIZE:,} users...")
    num_batches = (len(users) + BATCH_SIZE - 1) // BATCH_SIZE

    all_item_counts = {
        'familiar_product': 0,
        'familiar_ingredient': 0,
        'new_ingredient': 0,
        'total_items': 0,
    }

    all_customer_compositions = []

    for batch_num in range(num_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_users = users[batch_start:batch_start + BATCH_SIZE]

        print(f"   Batch {batch_num + 1}/{num_batches}: {len(batch_users):,} users", flush=True)

        batch_counts, batch_compositions = analyze_basket_composition(batch_users, classifications)

        # Accumulate
        for key in all_item_counts:
            all_item_counts[key] += batch_counts[key]

        if batch_compositions is not None:
            all_customer_compositions.append(batch_compositions)

    print("\n4. Computing statistics...")

    # Item-weighted (pooled)
    total = all_item_counts['total_items']
    print(f"\n   Item-weighted (pooled {total:,} items in orders 2+):")
    print(f"     Familiar product (exact repeat):          {all_item_counts['familiar_product']:,} ({all_item_counts['familiar_product']/total*100:.1f}%)")
    print(f"     Familiar ingredient, new product (switch): {all_item_counts['familiar_ingredient']:,} ({all_item_counts['familiar_ingredient']/total*100:.1f}%)")
    print(f"     New ingredient (novel food):               {all_item_counts['new_ingredient']:,} ({all_item_counts['new_ingredient']/total*100:.1f}%)")

    # Customer-weighted
    if all_customer_compositions:
        all_comps = np.vstack(all_customer_compositions)
        cust_means = all_comps.mean(axis=0)

        print(f"\n   Customer-weighted (mean across {len(all_comps):,} customers):")
        print(f"     Familiar product (exact repeat):          {cust_means[0]:.1f}%")
        print(f"     Familiar ingredient, new product (switch): {cust_means[1]:.1f}%")
        print(f"     New ingredient (novel food):               {cust_means[2]:.1f}%")

    print("\n5. Saving results...")

    # Save detailed report
    report = f"""# Basket Composition Analysis

Each item in orders 2+ is classified based on purchase history:

- **Familiar product**: Exact SKU purchased before (exact repeat)
- **Familiar ingredient, new product**: Same ingredient but different product (brand/variant switching)
- **New ingredient**: Never purchased this ingredient before (novel food)

## Item-weighted (pooled)

Total items analyzed: {total:,}

| Category | Count | Percentage |
|----------|-------|------------|
| Familiar product (exact repeat) | {all_item_counts['familiar_product']:,} | {all_item_counts['familiar_product']/total*100:.1f}% |
| Familiar ingredient, new product | {all_item_counts['familiar_ingredient']:,} | {all_item_counts['familiar_ingredient']/total*100:.1f}% |
| New ingredient (novel food) | {all_item_counts['new_ingredient']:,} | {all_item_counts['new_ingredient']/total*100:.1f}% |

**Interpretation:** Product repeats account for {all_item_counts['familiar_product']/total*100:.1f}% of purchases. Another {all_item_counts['familiar_ingredient']/total*100:.1f}% are brand/variant switches within familiar ingredients. Only {all_item_counts['new_ingredient']/total*100:.1f}% represent genuinely new ingredients.

## Customer-weighted

Customers analyzed: {len(all_comps):,}

| Category | Mean % |
|----------|--------|
| Familiar product (exact repeat) | {cust_means[0]:.1f}% |
| Familiar ingredient, new product | {cust_means[1]:.1f}% |
| New ingredient (novel food) | {cust_means[2]:.1f}% |

**Why two denominators:** Item-weighting reflects overall volume. Customer-weighting gives equal voice to each customer regardless of order size.

## Key Findings

1. **Most variety is brand switching, not dietary change:** {(all_item_counts['familiar_product'] + all_item_counts['familiar_ingredient'])/total*100:.1f}% of purchases are familiar ingredients (either exact repeats or switched products).

2. **True novelty is limited:** Only {all_item_counts['new_ingredient']/total*100:.1f}% of items represent genuinely new ingredients never purchased before.

3. **Meal subscription implications:** Customers may want variety in presentation (different recipes, preparations) while maintaining familiar core ingredients. "New" meals that combine familiar ingredients differently may be more appealing than meals with genuinely unfamiliar foods.
"""

    (SEQ_ANALYSIS_DIR / "BASKET_COMPOSITION.md").write_text(report)
    print(f"   Saved BASKET_COMPOSITION.md")

    # Save CSV summary
    summary_data = {
        'measure': ['Item-weighted', 'Customer-weighted'],
        'familiar_product_pct': [
            all_item_counts['familiar_product']/total*100,
            cust_means[0]
        ],
        'familiar_ingredient_pct': [
            all_item_counts['familiar_ingredient']/total*100,
            cust_means[1]
        ],
        'new_ingredient_pct': [
            all_item_counts['new_ingredient']/total*100,
            cust_means[2]
        ],
    }

    pl.DataFrame(summary_data).write_csv(SEQ_ANALYSIS_DIR / "basket_composition_summary.csv")
    print(f"   Saved basket_composition_summary.csv")

    print("\n" + "="*70)
    print("Basket composition analysis complete!")
    print("="*70)


if __name__ == "__main__":
    main()
