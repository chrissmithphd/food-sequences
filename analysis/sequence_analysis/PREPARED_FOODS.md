# Prepared Dishes vs. Base Ingredients (Part 1.4 — corrected)

## Research question

Do customers treat prepared dishes (frozen meals, soups, pizzas) differently from
base ingredients (milk, eggs, rice) — more rotation, more "fatigue," faster
abandonment — or did the earlier comparison just mis-measure it?

## What was wrong before

The original comparison had two flaws:

1. **Wrong population.** It defined "prepared" from a hardcoded list of 18
   ingredient names, matching only **1,749** products. The classifier's
   authoritative `is_prepared_dish` flag marks **8,019** food products. The old
   analysis looked at ~22% of prepared dishes.
2. **Wrong metric and unfair grain.** It used the buggy "immediate reorder" rate
   and compared at the *ingredient* grain, where `frozen_meal` is a single giant
   bucket of thousands of distinct dishes while `milk` is one tight ingredient.
   Of course a mega-bucket looks different — that is an aggregation artifact, not
   behavior.

## Corrected approach

Use the `is_prepared_dish` flag (8,019 products) and the corrected next-order
**probability** plus shuffle-baseline **lift**, at the **exact-product grain** —
the only fair comparison, since it removes the "one bucket vs many dishes" problem.
Full dataset, no sampling.

## Results

| Group | grain | P(next order) | lift | P(within 5) | events |
|-------|-------|--------------:|-----:|------------:|-------:|
| Prepared dishes | **product** | 27.9% | **1.39×** | 55.4% | 3.2M |
| Base ingredients | **product** | 28.9% | **1.28×** | 58.7% | 25.1M |
| Prepared dishes | ingredient | 32.5% | 1.29× | 63.2% | 2.8M |
| Base ingredients | ingredient | 34.5% | 1.15× | 68.2% | 22.9M |

## Interpretation

**At the fair exact-product grain, prepared dishes and base ingredients reorder at
essentially the same rate** (27.9% vs 28.9% next order; 55% vs 59% within five
orders). The earlier "prepared foods rotate more / 31% vs 40%" gap was an artifact
of the broken metric and the mega-bucket ingredient grain — it does not survive.

If anything, the **lift runs the other way**: a specific prepared-dish product is
*more* temporally clustered above chance (1.39×) than a specific base-ingredient
product (1.28×). When a customer finds a frozen meal they like, they stick to that
exact SKU in runs at least as tightly as they stick to a brand of milk.

**There is no evidence here of distinctive "prepared-food fatigue."** We also do not
claim the opposite as a strong result — the point is that the earlier claim rested
on a mis-measurement, and once corrected the two groups behave alike on repurchase,
with prepared dishes showing marginally stronger single-SKU habit.

## Limitations

- `is_prepared_dish` is itself an LLM classification; edge cases (e.g. a rotisserie
  chicken, a salad kit) are judgment calls.
- Next-order probability does not capture *how many* distinct prepared dishes a
  customer cycles through overall — only whether a given one recurs. The high
  ingredient-grain breadth of `frozen_meal` is real; it just is not "rotation" in
  the reorder sense.
- Order sequence, not calendar time (see Part 10).

## Follow-up

- Within prepared dishes, does the commit-then-switch pattern (Part 1.2b / Part 6)
  look different from base ingredients — e.g., do customers churn through frozen
  meals via many short runs, vs. long runs on a staple milk?
