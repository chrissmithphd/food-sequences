# LLM-Assisted Classification — Pilot Results (v3.0)

**Status: pilot for review.** Not catalog-wide. Downstream recipe/novelty analysis is
blocked until the mapping is validated as reliable.

- Classifier: LLM, `model_id = us.anthropic.claude-opus-4-8`, `prompt_version = v3.0`
  (prompt in `prompt_v3.md`). Workflow: identify what the product IS → assign a
  recipe-equivalence group from `group_catalog_v3.json`. Regex is used only for
  supporting contradiction checks, never to assign a group.
- Cached outputs: `classifications_v3.jsonl` (one record per product, verbatim).
- Human-review sheet: `review_sheet_v3.csv` (top-10 by volume + random sample; the
  `human_correct` column is for a reviewer to fill). **Accuracy is reported from that
  column after review — not from the model's self-reported confidence.**

## Pilot scope
69 products across contrasting aisles chosen to contain known hard cases
(packaged/fresh produce, fresh pasta, specialty cheeses, crackers, condiments, oils,
milk, broth, instant foods, pet food, skin care). 60 resolved in-scope, 9 out-of-scope,
30 recipe groups, confidence high=57 / medium=3.

## The cited errors: regex-first (v2) vs LLM (v3)

| product | regex-first v2 (wrong) | LLM v3 | why v3 is right |
|---|---|---|---|
| Grape Tomatoes | `grape` | `tomato_fresh` | "grape" is the tomato variety |
| Spinach & Ricotta Ravioli | `cottage_or_ricotta` | `filled_pasta` | ricotta is the filling; product is pasta (and the aisle "specialty cheeses" misleads) |
| …Onion & Garlic Crackers | `onion` | `crackers` | onion/garlic are flavors; product is crackers |
| Mayonnaise with Olive Oil | `olive_oil` | `mayonnaise` | olive oil is an ingredient; product is mayonnaise |
| Organic Spaghetti Squash | `pasta` | `winter_squash` | it is a vegetable, not pasta |
| Chicken Corn Dog | `chicken` | `corn_dog` (in scope) | human prepared snack; "dog" is not pet food |
| Calendula Baby Diaper Care | unresolved | `OUT_OF_SCOPE_personal_care` | not a food |

Regex v2 "confidently resolved" every one of these incorrectly — which is exactly why
word-matching is insufficient and why self-reported confidence is not evidence.

## Coverage vs. accuracy
- **Coverage** (reported now): 69/69 products received a decision; 60 resolved in-scope.
- **Accuracy** (pending): to be computed from `review_sheet_v3.csv` human judgments,
  reported separately, for high-volume and random buckets.

## Next steps (gated)
1. Human review of `review_sheet_v3.csv`; record correctness; report accuracy by bucket.
2. If accuracy is sufficient, expand the catalog + classification across more aisles in
   batches, proposing new groups for review rather than inventing labels.
3. Only then re-run equivalence-level reorder and begin recurring-combination / novelty
   analysis. The regex v2 (`food_roles.py`) and v1 mappings are legacy/superseded.
