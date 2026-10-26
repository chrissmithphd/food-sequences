# Food Classification

Every product in the Instacart catalog is mapped to a **recipe-ingredient label** —
the thing a recipe's ingredient line would call it ("milk", "chicken broth", "cheese",
"onion") — so purchase sequences can be analyzed by food rather than by exact SKU.

- Classification file: [`data/food_classification.csv`](../data/food_classification.csv)
  (one row per product: product_id, ingredient, is_food, is_prepared_dish, ...)
- Taxonomy: [`data/INGREDIENT_TAXONOMY.md`](../data/INGREDIENT_TAXONOMY.md)
- Method comparison: [`docs/classification/methods_compared/`](classification/methods_compared/)
- Ingredient-level findings: [`analysis/ingredients/`](../analysis/ingredients/)

## How it was built

Three classification methods were evaluated; the LLM-based classifier was selected:

1. **TF-IDF + regex** (`classify_tfidf.py`): fast, deterministic, ~75% accurate on a
   hand-checked sample. Systematic errors on prepared dishes and flavored products.
2. **Sentence embeddings** (`classify_embeddings.py`): nearest-neighbor against
   taxonomy anchors. Better on ambiguous products, slower.
3. **LLM classification** (`classify_fabric.py`): each product classified by Claude via
   the fabric CLI against a recipe-grounded taxonomy of ~446 defined ingredients
   (built from 1,000+ recipes across diverse cuisines). ~8 hours for all 49,688
   products. The LLM produced **633 distinct labels in all** — more than the ~446 the
   taxonomy defines, because it invented finer distinctions (`frozen_waffles`,
   `instant_noodles`, `marinara` vs. generic `pasta_sauce`). 5.6% of products were left
   unclassified — the LLM declining rather than guessing.

The committed `food_classification.csv` uses the LLM output with post-hoc corrections
applied by `apply_corrections.py` (e.g., condensed-soup reclassification). After
restricting to food and dropping labels with no purchases, **543 food ingredients**
(across 21 food categories) are analyzed downstream.

For reproducing on the same or overlapping products without an LLM,
`classify_lookup.py` provides an exact-match lookup table
([`product_ingredient_lookup.csv`](../data/product_ingredient_lookup.csv)) mapping each
product name to its ingredient and category. Products not in the table are flagged for
manual or LLM classification.

## Coverage

The 49,688 catalog products partition as:

| | Products |
|---|---:|
| Food — classified to an ingredient | 35,722 |
| Food — unclassified (LLM declined) | 2,807 |
| Non-food (out of scope) | 11,159 |
| **Total** | **49,688** |

The 2,807 unclassified products (5.6% of the catalog) are overwhelmingly long-tail,
low-volume items; they are excluded from ingredient-level analysis. Non-food covers pet
food, personal care, household, and supplements (`is_food = False`).

## How products map to ingredients

The taxonomy is grounded in how recipes actually list ingredients. A recipe says "1 cup
milk," not "1 cup Organic Horizon 2% Milk" — so the classifier asks, for each product,
**what would a recipe call this?** Four rules follow from that.

**1. Collapse variation recipes treat as interchangeable.** Brand, size, organic, fat
level, and shape are attributes, not different foods. Whole / 2% / skim → `milk`; penne
/ rigatoni → `pasta`; yellow / white onion → `onion`.

**2. Keep distinctions recipes make functionally.** When a recipe names something
specifically because it behaves differently, it stays separate: `buttermilk` ≠ `milk`
(acidity matters in baking), `canned_tomato` ≠ `tomato` (texture/moisture), dried herbs
→ `spices` vs. `fresh_herbs` (potency differs ~3:1).

**3. Flavor modifies; the noun defines.** Test: remove the flavor word — is it still the
same product? "Garlic Herb Crackers" → `crackers`; "Raspberry Vanilla Yogurt" →
`yogurt`; "Spinach Basil Linguini" → `pasta`.

**4. Complete dishes are not base ingredients.** If it's sold as a ready-to-eat or
heat-and-eat meal, it's a prepared dish, not an ingredient: boxed Kraft or a frozen
mac-and-cheese → `mac_and_cheese` (prepared); plain dry macaroni → `pasta`. Frozen pizza
→ `frozen_pizza` (prepared); pizza dough → `pizza_dough` (baking). Canned ready-to-eat
soup → `soup` (prepared); chicken broth → `chicken_broth` (cooking liquid).

A few worked examples:

| Product | Ingredient | Why |
|---|---|---|
| Organic Whole Milk | `milk` | organic + fat level are attributes |
| Barilla Penne Rigate | `pasta` | shape is preference, not a different food |
| Garden Herb Wheat Crackers | `crackers` | "garden herb" is flavor; still crackers |
| Kraft Macaroni & Cheese Dinner | `mac_and_cheese` (prepared) | complete boxed dish |
| Lean Cuisine Chicken Alfredo | `frozen_meal` (prepared) | complete entrée |
| Dove Body Wash | — (`is_food = False`) | non-food |

**Pitfalls the rules guard against:** reading a flavor as the food ("Raspberry Coffee
Creamer" is `coffee_creamer`, not a fruit); over-specifying (mild vs. sharp cheddar are
both `cheddar`); under-specifying (recipes do distinguish `chicken_breast` from
`chicken_thigh`); and missing the prepared-dish flag on complete meals.

## Prepared dishes

Products flagged `is_prepared_dish` include frozen meals, pizza, soup, deli-prepared
items, mac & cheese, and similar heat-and-eat or ready-to-eat items. The downstream
analysis uses a narrower definition: the 17 meal types under the taxonomy's "Prepared
Dishes & Meals" section (see [`INGREDIENT_TAXONOMY.md`](../data/INGREDIENT_TAXONOMY.md)).
The per-product flag is broader; the taxonomy section is the authoritative definition.

## Reproduce

```bash
# Full LLM classification (~8h, requires fabric CLI + Claude API)
python scripts/classification/classify_fabric.py
python scripts/classification/apply_corrections.py
```

## Limitations

- 2,807 products (5.6%) are unclassified — the LLM declined low-confidence guesses.
- The taxonomy has judgment calls: prepared dish vs. base ingredient, herb/spice
  granularity, where to draw the milk/protein-shake boundary.
- More labels emerged (633) than the taxonomy defined (~446) — the LLM invented finer
  distinctions (`frozen_waffles`, `instant_noodles`) not in the original taxonomy.
- "Fresh vs. packaged" is read per ingredient, not from a nutrition label.
