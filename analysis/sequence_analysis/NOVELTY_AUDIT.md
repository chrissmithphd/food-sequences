# Novelty & Repertoire Audit (Part 1.5)

## Research question

How much of each order is genuinely new food versus familiar? And is the headline
"22% new ingredients" a real exploration rate, or an artifact of only observing a
slice of each customer's history?

## Definitions

Deduplicate to one item per (customer, order, product). For orders n ≥ 2, classify
each item by the customer's *prior observed* history:

- **familiar product** — this exact product appeared in an earlier order
- **familiar ingredient, new product** — product is new, but its ingredient is not
- **new ingredient** — the ingredient has never appeared before for this customer

## Weighting matters

| Weighting | familiar product | familiar ingredient, new product | new ingredient |
|-----------|-----------------:|---------------------------------:|---------------:|
| Item-weighted | 63.9% | 11.7% | 24.4% |
| Order-weighted | 69.4% | 21.6% | 38.8% |
| Customer-weighted | 51.2% | 12.3% | 38.7% |

Item-weighting lets heavy, large-basket buyers dominate; they are more repetitive,
so item-weighted novelty (24.4%) is lower than customer-weighted (38.7%). The
earlier README reported the item-weighted 22–24% and customer-weighted ~34% — both
roughly reproduced. But **neither number is a stable "exploration rate"**, because
both pool early orders where novelty is inflated by truncation (below).

## The truncation artifact (the important finding)

Because the dataset starts mid-history, a customer's first observed order contains
only "new" ingredients by construction — we simply have not seen their past. Apparent
novelty therefore starts at 100% and decays as the observed window lengthens:

| Order position | new-ingredient share | familiar-product share |
|---------------:|---------------------:|-----------------------:|
| 1 | 100.0% | 0.0% |
| 2 | 63.4% | 28.1% |
| 3 | 49.1% | 39.7% |
| 5 | 35.6% | 51.5% |
| 10 | 22.5% | 64.5% |
| 20 | 13.7% | 74.5% |
| 50 | 7.6% | 82.7% |
| 100 | 5.3% | 86.8% |

**The steady-state exploration rate is ~5–7%, not 22%.** Once a customer's repertoire
is established (order 50+), only about one item in fifteen is a genuinely new
ingredient. The large "novelty" figures are dominated by early orders where we
cannot see prior purchases. Any statement about exploration must condition on order
position or restrict to established customers — the pooled average is a truncation
average, not a behavior.

This also reframes exploration-over-lifetime (Part 7): exploration does not merely
"decline," it decays steeply toward a low, stable floor.

## Repertoire multiplier (robust)

Median distinct products per customer = 45; median distinct ingredients = 34.

- ratio of medians = 1.324×
- **median of per-customer ratios = 1.333×** ← the correct statistic
- mean of per-customer ratios = 1.401× (right-skewed)

Here the median-of-ratios (1.333×) essentially matches the ratio-of-medians, so the
earlier "1.33×" was not misleading. About a quarter of a customer's product variety
collapses when viewed as ingredients.

## Limitations

- **"Brand switching" is not decomposed** into brand vs. size vs. flavor. The data
  carries only product names; a reliable split would need structured attributes.
  The 12–22% "familiar ingredient, new product" bucket mixes all three.
- Truncation cannot be fully removed, only conditioned around. The ~5–7% floor is a
  lower bound on true novelty if customers also had pre-window exploration.

## Follow-up

- Do new ingredients arrive independently or in clusters (several new ingredients in
  one order)? (Part 7 / Part 8.)
- Is the novelty floor the same for all customers, or do some remain explorers? (Part 9.)
