#!/usr/bin/env python3
"""
Refine TF-IDF classifications using product-identity rules.
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import ANALYSIS_OUTPUTS


def refine_classification(df):
    """Apply product-identity rules to fix misclassifications."""
    refined = df.copy()
    refined['notes'] = refined['notes'].astype(str)
    corrections = 0

    for idx, row in df.iterrows():
        name = row['product_name'].lower()
        aisle = row['aisle'].lower()
        dept = row['department'].lower()
        original = row['ingredient']

        new_ing = None
        new_cat = None
        new_prepared = False

        # PASTA - product identity override
        if any(x in name for x in ['spaghetti', 'penne', 'rigatoni', 'fettuccine', 'linguini', 'macaroni', 'pasta']):
            if 'squash' not in name and 'sauce' not in name:
                new_ing = 'pasta'
                new_cat = 'grains_pasta'

        # YOGURT - product identity override
        elif 'yogurt' in name and 'frozen' not in name and 'ice' not in name:
            new_ing = 'yogurt'
            new_cat = 'dairy'

        # COOKIES - product identity override
        elif 'cookie' in name and 'sheet' not in name:
            new_ing = 'cookies'
            new_cat = 'snacks'

        # CITRUS - specific fruits
        elif any(x in name for x in ['clementine', 'mandarin', 'tangerine']):
            new_ing = 'orange'
            new_cat = 'produce_fruit'
        elif 'nectarine' in name:
            new_ing = 'nectarine'
            new_cat = 'produce_fruit'
        elif 'grapefruit' in name:
            new_ing = 'grapefruit'
            new_cat = 'produce_fruit'

        # HOUSEHOLD - specific products
        elif 'foil' in name or ('wrap' in name and dept != 'bakery') or ('bag' in name and 'garbage' in name):
            new_ing = 'food_storage'
            new_cat = 'household'

        # HOUSEHOLD by department
        elif dept == 'household' or aisle in ['cleaning products', 'laundry', 'paper goods', 'trash bags liners', 'food storage', 'kitchen supplies']:
            if 'foil' in name or 'wrap' in name or 'bag' in name:
                new_ing = 'food_storage'
                new_cat = 'household'
            elif any(x in name for x in ['cleaner', 'detergent', 'soap', 'bleach']):
                new_ing = 'cleaning_supplies'
                new_cat = 'household'
            elif any(x in name for x in ['paper towel', 'toilet paper', 'tissue', 'napkin']):
                new_ing = 'paper_goods'
                new_cat = 'household'

        # PERSONAL CARE by department
        elif dept == 'personal care' or aisle in ['vitamins supplements', 'skin care', 'hair care', 'oral hygiene', 'deodorants']:
            if 'vitamin' in name or 'supplement' in name:
                new_ing = 'vitamins'
                new_cat = 'personal_care'
            elif 'shampoo' in name or 'conditioner' in name:
                new_ing = 'hair_care'
                new_cat = 'personal_care'
            elif 'toothpaste' in name or 'toothbrush' in name or 'floss' in name:
                new_ing = 'oral_care'
                new_cat = 'personal_care'
            elif 'lotion' in name or 'sunscreen' in name:
                new_ing = 'body_lotion'
                new_cat = 'personal_care'
            else:
                new_ing = 'personal_care_other'
                new_cat = 'personal_care'

        # PET FOOD
        elif dept == 'pets' or 'pet' in aisle or 'dog food' in aisle or 'cat food' in aisle:
            if 'dog' in name:
                new_ing = 'dog_food'
                new_cat = 'pet_food'
            elif 'cat' in name:
                new_ing = 'cat_food'
                new_cat = 'pet_food'
            else:
                new_ing = 'pet_food'
                new_cat = 'pet_food'

        # Apply correction
        if new_ing and new_ing != original:
            refined.at[idx, 'ingredient'] = new_ing
            refined.at[idx, 'category'] = new_cat
            refined.at[idx, 'is_prepared_dish'] = new_prepared
            refined.at[idx, 'is_food'] = new_cat not in ['household', 'personal_care', 'pet_food']
            refined.at[idx, 'notes'] = f'refined from {original}'
            corrections += 1

    return refined, corrections


def main():
    print("Loading classification...")
    df = pd.read_csv(ANALYSIS_OUTPUTS / "food_classification_final.csv")
    print(f"Total products: {len(df):,}")

    print("\nApplying refinements...")
    refined, corrections = refine_classification(df)
    print(f"Corrections made: {corrections:,}")

    # Save
    output_path = ANALYSIS_OUTPUTS / "food_classification_refined.csv"
    refined.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

    # Re-check spot checks
    print("\n" + "="*70)
    print("Spot checks (after refinement):")
    print("="*70)
    for pid in [1, 9, 33, 43, 76, 148, 160]:
        row = refined[refined['product_id'] == pid].iloc[0]
        orig = df[df['product_id'] == pid].iloc[0]
        status = "✓" if row['ingredient'] != orig['ingredient'] else " "
        print(f"{status} {pid:3d}: {row['product_name'][:40]:40s} → {row['ingredient']:20s}")

    print(f"\nTop 30 ingredients (refined):")
    for ing, cnt in refined['ingredient'].value_counts().head(30).items():
        print(f"  {ing:30s} {cnt:>6,}")


if __name__ == "__main__":
    main()
