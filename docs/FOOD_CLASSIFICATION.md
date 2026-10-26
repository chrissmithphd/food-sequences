# Food Classification

Every product in the Instacart catalog is mapped to a **recipe-ingredient label** —
the thing a recipe's ingredient line would call it ("milk", "chicken broth", "cheese",
"onion") — so purchase sequences can be analyzed by food rather than by exact SKU.

- Classification file: [`data/food_classification.csv`](../data/food_classification.csv)
  (one row per product: product_id, ingredient, is_food, is_prepared_dish, ...)
- Taxonomy: [`data/INGREDIENT_TAXONOMY.md`](../data/INGREDIENT_TAXONOMY.md)
- Method comparison: [`analysis/classification/methods_compared/`](../analysis/classification/methods_compared/)
- Detailed analysis: [`analysis/classification/CLASSIFICATION_ANALYSIS.md`](../analysis/classification/CLASSIFICATION_ANALYSIS.md)

## How it was built

Three classification methods were evaluated; the LLM-based classifier was selected:

1. **TF-IDF + regex** (`classify_tfidf.py`, `refine_tfidf.py`): Fast, deterministic,
   ~75% accurate on a hand-checked sample. Systematic errors on prepared dishes and
   flavored products.
2. **Sentence embeddings** (`classify_embeddings.py`): Nearest-neighbor against
   taxonomy anchors. Better on ambiguous products, slower.
3. **LLM classification** (`classify_fabric.py`): Each product classified by Claude
   via the fabric CLI against a 446-ingredient taxonomy grounded in 1,000+ recipes.
   ~8 hours to process all 49,688 products. The LLM introduced 194 additional
   ingredient distinctions beyond the 446 defined (e.g., `frozen_waffles`,
   `instant_noodles`), producing 632 total ingredient labels. 5.6% of products were
   left unclassified — the LLM declining rather than guessing.

The committed `food_classification.csv` uses the LLM output with post-hoc corrections
applied by `apply_corrections.py` (e.g., condensed soup reclassification).

For reproducing on the same or overlapping products without an LLM,
`classify_lookup.py` provides an exact-match lookup table
([`product_ingredient_lookup.csv`](../data/product_ingredient_lookup.csv))
mapping each product name to its ingredient and category. Products not in the table
are flagged for manual or LLM classification.

## Coverage

| | Products | Share of purchase volume |
|---|---|---|
| Food (resolved ingredient) | 38,529 | ~91% |
| Non-food (out of scope) | 11,159 | ~4% |
| Unclassified | 2,807 | ~5% |

49,688 products → **632 ingredients** across ~30 role families.

## What the classification does

1. **Scope.** Products in non-food departments/aisles (pet food, personal care,
   household, supplements) are marked `out_of_scope`.
2. **Identify, then group.** Each product is mapped to one recipe-ingredient label.
   Compound overrides handle cases where a modifier would mislead (grape tomato →
   tomato; spaghetti squash → squash; corn dog → corn_dog), and product-type anchors
   are ordered before flavor/variety words (garlic crackers → crackers).
3. **Collapse minor variation.** Brand, package size, organic, and fat level are
   attributes, not groups — whole/2%/skim are all `milk`.
4. **Keep meaningful boundaries.** Dairy vs. plant milk, broth vs. soup, plain
   pasta vs. boxed mac-and-cheese, fresh herbs vs. dried spices.
5. Products that match no group are left `unclassified` (not force-fit).

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
- 632 labels emerged from 446 defined — the LLM invented finer distinctions that
  aren't in the original taxonomy (documented in CLASSIFICATION_ANALYSIS.md §1).
- "Fresh vs. packaged" is read per ingredient, not from a nutrition label.
