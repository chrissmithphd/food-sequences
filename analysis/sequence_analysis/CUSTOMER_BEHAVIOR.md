# Customer-Level Behavior (Part 9)

## Research question

Do customers have consistent behavioral tendencies — some repeaters, some explorers —
or is apparent "type" just a side effect of how much they buy? And are those
tendencies stable across a customer's history?

## Method

For each customer with ≥10 orders (107,257 customers), compute per-customer measures
on deduplicated (customer, order, product, ingredient) events:

- **product_repeat / ingredient_repeat** — share of non-first item-events repeating an
  earlier product / ingredient
- **new_ing_rate** — share of items that are a new ingredient
- **repertoire** — distinct ingredients; **diversity** — distinct ingredients ÷ items
- **switch_rate** — within an ingredient, share of consecutive purchases that change product
- **n_orders**, **avg_basket**

Then test (a) distribution shape, (b) correlation of each measure with volume
(n_orders, avg_basket), and (c) split-half stability: correlate first-half vs.
second-half values for customers with ≥20 orders.

## Results

**Wide spread across customers (medians with p10–p90):**

| Measure | p10 | p50 | p90 |
|---------|----:|----:|----:|
| product_repeat | 0.35 | 0.58 | 0.79 |
| ingredient_repeat | 0.49 | 0.70 | 0.86 |
| new_ing_rate | 0.14 | 0.30 | 0.51 |
| repertoire (distinct ingredients) | 17 | 49 | 93 |
| diversity | 0.13 | 0.28 | 0.48 |
| switch_rate | 0.13 | 0.35 | 0.59 |
| avg_basket | 3.4 | 8.3 | 15.9 |

**Most "types" are largely volume.** Repeat, novelty, and diversity measures correlate
±0.5–0.6 with how much a customer buys:

| Measure | corr(n_orders) | corr(avg_basket) |
|---------|---------------:|-----------------:|
| product_repeat | +0.52 | +0.16 |
| ingredient_repeat | +0.58 | +0.28 |
| new_ing_rate | −0.58 | −0.28 |
| repertoire | +0.46 | +0.65 |
| diversity | −0.58 | −0.29 |
| **switch_rate** | **−0.06** | **+0.19** |

Heavier buyers repeat more and explore less — so "repeater vs. explorer" is to a large
degree "high-volume vs. low-volume." The exception is **switch_rate**: how often a
customer swaps products within an ingredient is essentially independent of volume
(−0.06 with order count). It is a genuine preference dimension, not a volume artifact.

**Tendencies are stable across a customer's history.** First-half vs. second-half
correlations:

| Measure | r |
|---------|---:|
| product_repeat | 0.81 |
| new_ing_rate | 0.81 |
| diversity | 0.82 |
| switch_rate | 0.73 |

A customer's behavior in the first half of their orders strongly predicts the second
half — these are durable individual traits, not transient phases.

## Interpretation

Customers do differ consistently, but most of the obvious axes (repeat rate, novelty,
diversity) are entangled with purchase volume. The one trait that stands on its own is
product-switching within an ingredient — some customers lock onto one product per
ingredient, others rotate among several, and this holds regardless of how much they
buy or how long they stay. If customer segmentation is the goal, switch_rate is the
dimension that carries information beyond volume.

## Limitations

- Right-truncation inflates early-history novelty, so first-half new_ing_rate is an
  overcount; split-half correlations are less affected because truncation hits both
  halves' baselines similarly.
- Measures are correlational; no causal claim about why volume and repetition move together.
- Per-customer metrics contain user_ids and are not committed; only this aggregate report is.
