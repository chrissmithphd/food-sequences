#!/usr/bin/env python3
"""
Complete TF-IDF classification using full ingredient taxonomy.
"""

import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED, ANALYSIS_OUTPUTS


def load_taxonomy():
    """Parse full taxonomy from markdown file."""
    taxonomy_path = Path(__file__).parent.parent / "analysis" / "INGREDIENT_TAXONOMY.md"

    with open(taxonomy_path) as f:
        content = f.read()

    ingredients = {}
    current_category = None

    # Map section headers to categories
    category_map = {
        "PRODUCE - FRUIT": ("produce_fruit", False),
        "PRODUCE - VEGETABLES": ("produce_vegetables", False),
        "DAIRY": ("dairy", False),
        "PROTEIN - MEAT": ("protein_meat", False),
        "PROTEIN - SEAFOOD": ("protein_seafood", False),
        "PROTEIN - PLANT-BASED": ("protein_plant", False),
        "GRAINS, PASTA & RICE": ("grains_pasta", False),
        "BREAD & BAKERY": ("bread_bakery", False),
        "OILS, FATS & VINEGARS": ("oils_fats", False),
        "CONDIMENTS & SAUCES": ("condiments", False),
        "SPICES & SEASONINGS": ("spices", False),
        "BAKING": ("baking", False),
        "COOKING LIQUIDS": ("cooking_liquids", False),
        "SPREADS & JAMS": ("spreads", False),
        "BEVERAGES": ("beverages", False),
        "NUTS & SEEDS": ("nuts_seeds", False),
        "SNACKS": ("snacks", False),
        "BREAKFAST": ("breakfast", False),
        "FROZEN FOODS": ("frozen_simple", False),
        "PREPARED DISHES & MEALS": ("prepared_dishes", True),
        "BABY PRODUCTS": ("baby", False),
        "PET PRODUCTS": ("pet_food", False),
        "HOUSEHOLD (NON-FOOD)": ("household", False),
        "PERSONAL CARE (NON-FOOD)": ("personal_care", False),
    }

    for line in content.split('\n'):
        # Detect category headers
        if line.startswith('### '):
            header = line.replace('###', '').strip()
            if header in category_map:
                current_category = category_map[header]

        # Extract ingredient definitions
        elif match := re.match(r'^- `([a-z_]+)`: (.+)$', line):
            ing_name = match.group(1)
            description = match.group(2).lower()

            if current_category:
                category, is_prepared = current_category
                ingredients[ing_name] = (category, is_prepared, description)

    return ingredients


def main():
    print("Loading taxonomy...")
    taxonomy = load_taxonomy()
    print(f"Loaded {len(taxonomy)} ingredients")

    print("\nLoading products...")
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    departments = pd.read_parquet(DATA_PROCESSED / "departments.parquet")

    products = products.merge(aisles, on="aisle_id", how="left")
    products = products.merge(departments, on="department_id", how="left")
    products["aisle"] = products["aisle"].fillna("unknown")
    products["department"] = products["department"].fillna("unknown")
    print(f"Total products: {len(products):,}")

    # Build taxonomy corpus
    ingredient_names = list(taxonomy.keys())
    ingredient_texts = [taxonomy[ing][2] for ing in ingredient_names]

    # Build product corpus
    product_texts = [
        f"{row['product_name']} {row['aisle']} {row['department']}".lower()
        for _, row in products.iterrows()
    ]

    print("\nComputing TF-IDF vectors...")
    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2), min_df=1)

    all_texts = ingredient_texts + product_texts
    vectorizer.fit(all_texts)

    ingredient_vectors = vectorizer.transform(ingredient_texts)
    product_vectors = vectorizer.transform(product_texts)

    print("Computing similarities...")
    similarities = cosine_similarity(product_vectors, ingredient_vectors)

    print("Assigning ingredients...")
    results = []
    for i, row in products.iterrows():
        best_idx = similarities[i].argmax()
        best_score = similarities[i][best_idx]
        best_ingredient = ingredient_names[best_idx]
        category, is_prepared, _ = taxonomy[best_ingredient]

        is_food = category not in ["household", "personal_care", "pet_food"]

        results.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "aisle": row["aisle"],
            "department": row["department"],
            "ingredient": best_ingredient,
            "category": category,
            "is_food": is_food,
            "is_prepared_dish": is_prepared,
            "match_score": best_score,
            "notes": ""
        })

        if (i + 1) % 5000 == 0:
            print(f"  {i+1:,} / {len(products):,}")

    results_df = pd.DataFrame(results)

    # Save
    output_path = ANALYSIS_OUTPUTS / "food_classification_final.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")

    # Stats
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"Total: {len(results_df):,}")
    print(f"Food: {results_df['is_food'].sum():,} ({results_df['is_food'].mean()*100:.1f}%)")
    print(f"Prepared: {results_df['is_prepared_dish'].sum():,}")
    print(f"\nMatch scores:")
    print(f"  Mean: {results_df['match_score'].mean():.3f}")
    print(f"  Median: {results_df['match_score'].median():.3f}")
    print(f"  Low (<0.15): {(results_df['match_score'] < 0.15).sum():,}")

    print(f"\nTop 30 ingredients:")
    for ing, cnt in results_df['ingredient'].value_counts().head(30).items():
        print(f"  {ing:30s} {cnt:>6,}")

    print(f"\nTop 20 categories:")
    for cat, cnt in results_df['category'].value_counts().head(20).items():
        print(f"  {cat:30s} {cnt:>6,}")

    # Spot checks
    print("\n" + "="*70)
    print("Spot checks:")
    print("="*70)
    for pid in [1, 9, 33, 43, 76, 148, 160]:
        row = results_df[results_df['product_id'] == pid].iloc[0]
        print(f"{pid:3d}: {row['product_name'][:45]:45s} → {row['ingredient']:20s} ({row['match_score']:.3f})")

    # Review low confidence
    print("\n" + "="*70)
    print("Low confidence (<0.15) - sample 30:")
    print("="*70)
    low_conf = results_df[results_df['match_score'] < 0.15].sample(min(30, len(results_df[results_df['match_score'] < 0.15])), random_state=42)
    for _, row in low_conf.iterrows():
        print(f"{row['product_id']:5d} | {row['product_name'][:40]:40s} → {row['ingredient']:20s} ({row['match_score']:.3f})")


if __name__ == "__main__":
    main()
