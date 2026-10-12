# Food Classification

Every product in the Instacart catalog is mapped to a **recipe-ingredient group** —
the thing a recipe's ingredient line would call it ("milk", "chicken broth", "cheese",
"onion") — so purchase sequences can be analyzed by food rather than by exact SKU.

- Code: [`src/food_sequences/food_classifier.py`](../src/food_sequences/food_classifier.py)
- Run: `python scripts/classify_products.py`
- Output: [`analysis/outputs/food_mapping.csv`](../analysis/outputs/food_mapping.csv)
  (one row per product) and a 40-row `food_mapping_review_sample.csv` for spot-checking.

## How it works

Each product is classified from its **name** (aisle/department are only used to decide
food vs. non-food), in one pass:

1. **Scope.** Products in non-food departments/aisles (pet food, personal care,
   household, supplements) are marked `out_of_scope`.
2. **Identify, then group.** The product is matched to one recipe-ingredient group
   from a fixed list of ~117 groups. The *name* decides, not a single keyword:
   compound overrides handle cases where a modifier would mislead (grape tomato →
   tomato; spaghetti squash → squash; corn dog → prepared snack), and product-type
   anchors are ordered ahead of flavor/variety words (garlic crackers → crackers;
   mayonnaise with olive oil → mayonnaise).
3. **Collapse minor variation.** Brand, package size, organic, and fat level are
   attributes, not groups — whole/2%/skim are all `milk`.
4. **Keep meaningful boundaries.** Dairy vs. plant milk, cheddar vs. the generic
   cheese group's role, broth vs. soup, plain pasta vs. boxed mac-and-cheese.
5. Products that match no group are left `unresolved` (not force-fit).

## Coverage

| | products | share of purchase volume |
|---|---|---|
| resolved | 30,530 | **87.5%** |
| out_of_scope (non-food) | 10,983 | 4.1% |
| unresolved | 8,175 | 8.4% |

49,688 products → **117 groups** across 27 role families.

## Interesting statistics

- **Grouping collapses enormous SKU variety.** A group holds a median of 171 distinct
  products (mean 261): 1,560 distinct cheese SKUs become one `cheese` group, 1,325
  breads become `bread`, 806 pastas become `pasta`. This is the whole point — reorder
  behavior is far clearer at the food level than the SKU level.
- **Volume leans to fresh and dairy.** Top groups by purchase volume: yogurt (4.3%),
  cheese (3.6%), bread (3.5%), leafy greens (3.3%), banana (2.9%), milk (2.9%), apple
  (2.3%), plant milk (1.9%), strawberries, avocado, tomato, onion.
- **Role-family mix of resolved products:** snacks 14%, dairy 13%, fruit 12%,
  beverages 9%, vegetables 9%, protein 8%, bread 4%, grains 4%, prepared dishes 3%.
- **Non-food is real and separated:** ~11k catalog items (4% of volume) are pet food,
  personal care, or household — correctly excluded from food analysis.

## Accuracy and limitations

This is a fast, reproducible recipe-ingredient classifier, not per-item human review.
On a hand-checked random sample of 40 products it is roughly **~75% correct**. The
systematic errors are:

- **Prepared dishes labeled by their main ingredient** — "Vegetable Lasagna" → pasta,
  "Chicken Quesadilla" → chicken (should be a prepared-dish group).
- **Occasional flavor/brand traps** — "Coffee Creamer, …Raspberry" → raspberries;
  "Caramel … Nut Bar" → candy.
- **Coverage gaps** — rare long-tail items (specialty/ethnic foods) left `unresolved`.

Accuracy is highest on the simple high-volume head (produce, dairy, plain pasta, broth)
and lowest on prepared/flavored/branded items. For analysis, prefer the resolved head;
treat prepared-dish and long-tail labels with caution. Higher accuracy would require
per-item LLM labeling of the ambiguous tail.

## Reproduce

```bash
python scripts/classify_products.py   # writes analysis/outputs/food_mapping.csv
```
The classifier is deterministic; the mapping is committed and diffable.
