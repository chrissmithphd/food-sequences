# Novelty & Exploration

How much of each order is genuinely new food, how that changes over a customer's
lifetime, and whether anyone keeps exploring.

- Sources: `analyze_novelty.py` (`novelty_weighting.csv`,
  `novelty_by_order_position.csv`), `analyze_exploration.py` (`repertoire_growth.csv`,
  `order_diversity.csv`).

## Three kinds of "new"

Deduplicate to one item per (customer, order, product). For orders n ≥ 2, classify
each item by the customer's *prior observed* history:

- **familiar product** — this exact product appeared earlier
- **familiar ingredient, new product** — the product is new, the ingredient isn't
- **new ingredient** — never seen before for this customer

| Weighting | familiar product | familiar ingredient, new product | new ingredient |
|-----------|-----------------:|---------------------------------:|---------------:|
| Item-weighted | 63.9% | 11.7% | 24.4% |
| Order-weighted | 69.4% | 21.6% | 38.8% |
| Customer-weighted | 51.2% | 12.3% | 38.7% |

Item-weighting lets heavy, repetitive buyers dominate (so its novelty is lowest).
But **none of these pooled numbers is a stable exploration rate** — because they
average over early orders where novelty is inflated by truncation.

## The truncation artifact (the key correction)

The dataset starts mid-history, so a customer's first *observed* order is 100% "new"
by construction — we can't see what came before. Apparent novelty therefore starts at
100% and decays as the observed window lengthens:

![Novelty decay](../figures/novelty_decay.png)

| Order position | new-ingredient share | familiar-product share |
|---------------:|---------------------:|-----------------------:|
| 1 | 100.0% | 0.0% |
| 2 | 63.4% | 28.1% |
| 5 | 35.6% | 51.5% |
| 10 | 22.5% | 64.5% |
| 20 | 13.7% | 74.5% |
| 50 | 7.6% | 82.7% |
| 100 | 5.3% | 86.8% |

**Steady-state exploration is ~5–7%, not ~22%.** Once a repertoire is established
(order 50+), about one item in fifteen is a genuinely new ingredient. Any statement
about exploration must condition on order position or restrict to established
customers; the pooled average is a truncation artifact, not a behavior.

## The repertoire grows, but baskets don't get more varied

Cumulative distinct ingredients a customer has ever bought, by order position:

| By order | Mean distinct ingredients | Customers reaching it |
|---------:|--------------------------:|----------------------:|
| 1 | 8.2 | 203,364 |
| 5 | 26.3 | 137,439 |
| 10 | 39.5 | 71,182 |
| 20 | 55.8 | 27,510 |
| 50 | 80.5 | 4,218 |
| 100 | 101.0 | 250 |

The curve is still climbing at order 100 — **the repertoire never saturates** (out of
542 ingredients in the catalog). Yet within-order diversity is flat at ~8 distinct
ingredients at every position. The repertoire grows by slow accumulation — a trickle
of new items into otherwise familiar baskets — not by baskets becoming more
adventurous.

## Exploration is a stable trait on top of a universal slowdown

For customers with ≥20 orders, the new-ingredient rate falls from **34.4% in the first
half of their history to 14.7% in the second**, and **97.7% slow down**. But the
first-half/second-half correlation is 0.66: a customer who explores more than average
early still does so late. Exploration is a persistent individual trait layered on a
near-universal decline.

Reactivation is modest: 18% of ingredient-repurchases revive something dormant ≥5
orders, only 6.5% dormant ≥10 orders — most repurchasing is of recently bought items,
not long-dormant returns.

## Brand multiplier

The median customer buys 45 distinct products but only 34 distinct ingredients
(1.33×) — a quarter of apparent product variety is the same ingredient in different
packaging (detail in [ingredients](../ingredients/)).

## Limitations

- Truncation can be conditioned around but not removed; the ~5–7% floor is a lower
  bound if customers also explored before the observed window.
- "Familiar ingredient, new product" mixes brand / size / flavor switches — the data
  carries only product names, not structured attributes.
- Order position, not calendar time ([sequences](../sequences/) §4).
