#!/usr/bin/env python3
"""
Sentence-embedding classification using full ingredient taxonomy.

Uses all-MiniLM-L6-v2 (sentence-transformers) to encode both products and
ingredient descriptions, then assigns each product to its nearest ingredient
by cosine similarity.

Requires: sentence-transformers, scikit-learn (both in pyproject.toml).

Reproduce:
    uv run python scripts/classify_embeddings.py

Output: analysis/outputs/food_classification_embeddings.csv
"""

import sys
import re
from pathlib import Path
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_PROCESSED, ANALYSIS_OUTPUTS


def load_taxonomy():
    """Parse full taxonomy from INGREDIENT_TAXONOMY.md.

    Shared logic with classify_complete.py (TF-IDF variant).
    """
    taxonomy_path = Path(__file__).parent.parent.parent / "data" / "INGREDIENT_TAXONOMY.md"

    with open(taxonomy_path) as f:
        content = f.read()

    ingredients = {}
    current_category = None

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
        if line.startswith('### '):
            header = line.replace('###', '').strip()
            if header in category_map:
                current_category = category_map[header]
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

    print("\nLoading sentence transformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Encode ingredient descriptions
    print("Encoding ingredient taxonomy...")
    ingredient_names = list(taxonomy.keys())
    ingredient_texts = [
        f"{ing.replace('_', ' ')} {taxonomy[ing][2]}"
        for ing in ingredient_names
    ]
    ingredient_embeddings = model.encode(ingredient_texts, show_progress_bar=True)

    # Encode products (name + aisle + department for context)
    print("\nEncoding products...")
    product_texts = [
        f"{row['product_name']} {row['aisle']} {row['department']}"
        for _, row in products.iterrows()
    ]

    batch_size = 1000
    product_embeddings = []
    for i in range(0, len(product_texts), batch_size):
        batch = product_texts[i:i + batch_size]
        batch_emb = model.encode(batch, show_progress_bar=False)
        product_embeddings.append(batch_emb)
        if (i // batch_size + 1) % 10 == 0:
            print(f"  Encoded {i + len(batch):,} / {len(product_texts):,}")
    product_embeddings = np.vstack(product_embeddings)

    print("\nComputing cosine similarities...")
    similarities = cosine_similarity(product_embeddings, ingredient_embeddings)

    print("Assigning ingredients...")
    results = []
    for i, row in products.iterrows():
        best_idx = similarities[i].argmax()
        best_score = float(similarities[i][best_idx])
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
            "notes": f"similarity={best_score:.3f}"
        })

        if (i + 1) % 5000 == 0:
            print(f"  {i + 1:,} / {len(products):,}")

    results_df = pd.DataFrame(results)

    output_path = ANALYSIS_OUTPUTS / "food_classification_embeddings.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total: {len(results_df):,}")
    print(f"Food: {results_df['is_food'].sum():,} ({results_df['is_food'].mean() * 100:.1f}%)")
    print(f"Prepared: {results_df['is_prepared_dish'].sum():,}")
    print(f"\nMatch scores:")
    print(f"  Mean: {results_df['match_score'].mean():.3f}")
    print(f"  Median: {results_df['match_score'].median():.3f}")
    print(f"  Low (<0.3): {(results_df['match_score'] < 0.3).sum():,}")

    print(f"\nTop 20 ingredients:")
    for ing, cnt in results_df['ingredient'].value_counts().head(20).items():
        print(f"  {ing:30s} {cnt:>6,}")

    # Spot checks
    print("\nSpot checks:")
    for pid in [1, 9, 33, 43, 76, 148, 160]:
        row = results_df[results_df['product_id'] == pid].iloc[0]
        print(f"  {pid:3d}: {row['product_name'][:45]:45s} -> {row['ingredient']:20s} ({row['match_score']:.3f})")


if __name__ == "__main__":
    main()
