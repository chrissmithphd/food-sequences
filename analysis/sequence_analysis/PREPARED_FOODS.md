# Prepared Dishes vs. Base Ingredients

## Research question

Do customers treat prepared dishes (frozen meals, soups, pizzas) differently from
base ingredients (milk, eggs, rice) — more rotation, more "fatigue," faster
abandonment?

## Method

Split products by the classifier's authoritative `is_prepared_dish` flag (8,019
food products) and compare next-order **probability** plus shuffle-baseline
**lift** at the **exact-product grain**. The product grain is the fair comparison:
at the ingredient grain `frozen_meal` is a single giant bucket of thousands of
distinct dishes while `milk` is one tight ingredient, so any difference there is an
aggregation artifact rather than behavior. Full dataset, no sampling.

## Results

| Group | grain | P(next order) | lift | P(within 5) | events |
|-------|-------|--------------:|-----:|------------:|-------:|
| Prepared dishes | **product** | 27.9% | **1.39×** | 55.4% | 3.2M |
| Base ingredients | **product** | 28.9% | **1.28×** | 58.7% | 25.1M |
| Prepared dishes | ingredient | 32.5% | 1.29× | 63.2% | 2.8M |
| Base ingredients | ingredient | 34.5% | 1.15× | 68.2% | 22.9M |

## Interpretation

**At the exact-product grain, prepared dishes and base ingredients reorder at
essentially the same rate** (27.9% vs 28.9% next order; 55% vs 59% within five
orders).

If anything, the **lift runs the other way**: a specific prepared-dish product is
*more* temporally clustered above chance (1.39×) than a specific base-ingredient
product (1.28×). When a customer finds a frozen meal they like, they stick to that
exact SKU in runs at least as tightly as they stick to a brand of milk.

**There is no evidence here of distinctive "prepared-food fatigue."** The two groups
behave alike on repurchase, with prepared dishes showing marginally stronger
single-SKU habit; we do not claim the reverse as a strong result either.

## Limitations

- `is_prepared_dish` is itself an LLM classification; edge cases (e.g. a rotisserie
  chicken, a salad kit) are judgment calls.
- Next-order probability does not capture *how many* distinct prepared dishes a
  customer cycles through overall — only whether a given one recurs. The high
  ingredient-grain breadth of `frozen_meal` is real; it just is not "rotation" in
  the reorder sense.
- Order sequence, not calendar time (see the [calendar-time report](CALENDAR_TIME.md)).

## Follow-up

- Within prepared dishes, does the commit-then-switch pattern (see
  [reorder](REORDER_PROBABILITY.md) / [substitution](SUBSTITUTION.md))
  look different from base ingredients — e.g., do customers churn through frozen
  meals via many short runs, vs. long runs on a staple milk?
