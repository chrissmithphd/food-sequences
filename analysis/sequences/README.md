# Sequences

How a customer's choices repeat, rotate, and space out across successive orders.
Observations are stated first; possible explanations are flagged as such. The shuffle
and random baselines here test **temporal concentration** — whether a value clusters
in time beyond what a customer's purchase frequency alone implies. That is not the
same as loyalty, preference, or predictability, and we do not read it as such.

- Sources: `analyze_reorder.py` (`reorder_probability_audit.csv`,
  `lift_decomposition.csv`), `analyze_patterns.py` (`pattern_distribution.csv`,
  `pattern_independent_rules.csv`), `analyze_substitution.py`,
  `analyze_calendar_time.py`, `visualize_behavior.py`.
- The reorder baseline is validated by a brute-force permutation check built into
  `analyze_reorder._validate()` (run as an assert).

## 1. Next-order reordering

For an occurrence of a value at order *n* (observable iff *n* < the customer's true
final order *N*), does the same value appear in order *n+1*? The baseline is a random
re-ordering of that customer's *N* baskets; for a value in *b* of them the exact
expectation is (b−1)/(N−1). Observed and expected are summed over the **same**
observable occurrences, so the ratio (lift) is a like-for-like comparison.

| Grain | P(next) | within 5 | expected | Lift |
|-------|--------:|---------:|---------:|-----:|
| Product | 28.6% | 58.3% | 22.3% | 1.28× |
| Ingredient | 34.8% | 68.6% | 30.3% | 1.15× |
| Aisle | 43.3% | 77.1% | 39.7% | 1.09× |
| Category | 58.8% | 88.2% | 56.4% | 1.04× |

**Observation:** a specific product recurs in the next order ~29% more often than a
reshuffle of the same customer's baskets would produce; the excess shrinks toward
zero as the grain broadens. **Reading:** purchases of a specific product are somewhat
*concentrated in time* rather than spread evenly across a customer's orders. Broader
grains have higher raw reorder rates but near-1 lift — a wide bucket refills often
simply because it holds more products, which is arithmetic, not behavior. We do not
interpret the cross-grain ordering as evidence about whether customers "prefer"
products over ingredients.

**Where the product/ingredient lift gap comes from** (`lift_decomposition.csv`): for
(customer, ingredient) pairs using a single product it is zero by construction (both
grains 1.20×). It lives entirely in multi-product pairs (product 1.35× vs ingredient
1.11×): the ingredient stays present while individual products arrive in temporal
bunches. That is a description of timing, examined next.

## 2. Within an ingredient: coexistence vs. transitions

Two behaviors must be separated. A customer can buy several products of one ingredient
**in the same order** (coexistence) or use different products **across orders**
(transition). Counting simultaneous purchases as switches is a mistake that earlier
inflated apparent alternation.

**Coexistence (simultaneous):** 8.5% of ingredient-orders contain ≥2 products of that
ingredient at once — but it is highly concentrated in flavored/discretionary
categories: **yogurt 37%, ice cream 26%, pasta 13%, milk 12%**, versus staples
(banana, bread, eggs ~0.5%). Buying several yogurts in one trip is common; buying two
loaves of different bread is not.

**Transitions (across orders), clean single-product subset:** stay-with-same-product
probability vs a label-shuffle baseline.

| Ingredient | P(stay) | expected | lift | coexistence |
|-----------|--------:|---------:|-----:|------------:|
| banana | 92.8% | 89.5% | 1.04 | 0.5% |
| bread | 98.2% | 97.9% | 1.00 | 0.5% |
| eggs | 86.5% | 81.5% | 1.06 | 0.7% |
| milk | 86.1% | 80.2% | 1.08 | 12% |
| yogurt | 77.1% | 71.2% | 1.08 | 37% |
| ice_cream | 64.4% | 59.5% | 1.08 | 26% |
| pasta | 60.8% | 56.7% | 1.07 | 13% |

**Observation:** across orders, the same product recurs slightly more than a label
reshuffle predicts everywhere (lift 1.0–1.08) — mild temporal concentration, not
alternation. (An earlier version reported yogurt *alternating below chance*; that was
an artifact of treating same-order multi-yogurt purchases as switches.) Staples have
high stay rates because the customer uses one product; discretionary categories have
lower stay rates and much of their variety is **simultaneous**, not sequential.

## 3. Pattern labels

Sorting (customer, ingredient) pairs (≥2 purchases, ≥10-order customers) into
staple / return / burst / rotation requires precedence, which forces one label and
hides overlap. The honest view is each rule evaluated **independently** (they overlap,
so they do not sum to 100), next to a frequency-preserving random null:

| Rule (independent) | Observed | Random null |
|--------------------|---------:|------------:|
| return after break (gap ≥5) | 59.8% | 68.6% |
| rotation (regular gaps) | 7.4% | 5.5% |
| persistent staple | 9.2% | 9.2% |
| burst then absence | 3.4% | 0.3% |

**Observations:** "returns" and "staples" occur at or below their random rates — a
reshuffle of the same purchases produces as many, so these labels mostly re-describe
how often a thing is bought and how long the customer was observed (the "return" rate
also runs 75%→29% as the gap threshold moves 3→10, and rises with history length).
**Burst-then-absence** — bought a few times early, then not again within the observed
window — is the one rule clearly above its random rate (3.4% vs 0.3% independently;
1.6% vs 0.3% after precedence). 99% of these end well before the customer's last
observed order.

**What this does and does not establish:** it establishes that a few ingredients are
bought in an early cluster and then absent *for the rest of the observed window*. It
does **not** establish abandonment or churn — we observe only a slice of each
customer's history, have no post-window data, and cannot tell a dropped ingredient
from one that returns after our window ends.

## 4. Which ingredients follow which (transition matrix)

![Ingredient transition matrix](../figures/ingredient_transition_matrix.png)

P(ingredient in column appears in order *n+1* | row ingredient in order *n*), top
ingredients, full dataset (`ingredient_transitions.csv`). The diagonal is next-order
self-recurrence (banana 60%, milk 57%, yogurt 56%, water 56% — ~2–3× each
ingredient's overall next-order rate). Off the diagonal, the strongest associations
above base rate are recognizable kitchen clusters: onion ↔ fresh_herbs (~2.0×),
lettuce ↔ tomato (~1.6×, salad), crackers ↔ granola_bar (snacking). These are
population-level conditional rates normalized by each column's base rate; they
describe co-timing, not causation.

## 5. Purchase histories (examples)

![Purchase history heatmaps](../figures/purchase_history_heatmap.png)

Real customers, ingredient (row) × order (column). The grids make the raw behavior
visible: dense rows are frequently-rebought ingredients, broken rows are gaps, rows
that start partway are later discoveries, and rows that stop are items not seen again
in the window. These are illustrations, not a sample the quantitative results depend
on.

## 6. An order-gap is not a clock

Cadence varies widely, so order-gaps don't map to fixed time:

| Order gap | Median days | p10–p90 |
|----------:|------------:|--------:|
| 1 | 8 | 3–30 |
| 5 | 37 | 15–88 |
| 10 | 71 | 32–147 |

Median cadence is 13 days (p10–p90 of customers: 5–30). A 5-order gap spans 15–88 days
depending on the customer, so any order-space pattern is partly a statement about
shopping frequency. (The 30-day cap on `days_since_prior_order` makes long day-gaps
lower bounds.)

## Limitations

- The shuffle/random nulls preserve each customer's purchase frequencies but not
  cross-customer structure; they isolate temporal concentration only.
- `P(within k)` conditions on ≥k observable future orders; eventual return is a
  right-censored lower bound. There is no post-window observation, so nothing here
  speaks to churn.
- The transition matrix uses a population base-rate normalization, not a per-customer
  one; strong associations are co-timing at the population level.
