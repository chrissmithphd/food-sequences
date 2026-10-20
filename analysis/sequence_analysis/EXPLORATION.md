# Exploration Over a Customer's Lifetime

## Research question

As a customer accumulates orders, does their food exploration keep going, saturate,
or stop? And is "exploration" a stable trait or something every customer grows out of?

## Method

Deduplicate to one (customer, order, ingredient). For each customer, record the
order position at which each ingredient first appears, then track:

- **repertoire growth** — cumulative distinct ingredients by order position, averaged
  over customers who reach that position
- **within-order diversity** — distinct ingredients per order, by position
- **reactivation** — share of ingredient-repurchases that revive an ingredient
  dormant ≥5 / ≥10 orders
- **first vs. second half** — each customer's new-ingredient rate in the first vs.
  second half of their history (customers with ≥20 orders)

## Results

**Repertoire keeps growing — it does not saturate.**

| By order | Mean distinct ingredients | Customers reaching it |
|---------:|--------------------------:|----------------------:|
| 1 | 8.2 | 203,364 |
| 5 | 26.3 | 137,439 |
| 10 | 39.5 | 71,182 |
| 20 | 55.8 | 27,510 |
| 50 | 80.5 | 4,218 |
| 100 | 101.0 | 250 |

Even at 100 orders the curve is still climbing (~1 new ingredient every ~5 orders).
Customers do not converge on a fixed menu within the observed window.

**But the exploration *rate* collapses.** Within-order diversity is flat at ~8
distinct ingredients per order at every position (8.2 at order 1, 8.3 at order 50) —
baskets do not get more varied. The repertoire grows only because a small, shrinking
fraction of each basket is new:

| | first half | second half |
|---|---:|---:|
| New-ingredient rate (customers ≥20 orders) | 34.4% | 14.7% |

**97.7% of customers slow down** (second-half rate below first-half). The first→second
correlation is 0.66: a customer who explores more than average early still explores
more than average late, but almost everyone's absolute rate falls.

**Reactivation is modest.** 18.0% of ingredient-repurchases revive something dormant
≥5 orders; 6.5% revive something dormant ≥10 orders. Most repurchasing is of recently
bought ingredients, not long-dormant returns.

## Interpretation

Exploration is a declining rate over a still-growing repertoire. Customers steadily
add new foods, but the per-basket novelty share drops by more than half across their
history while basket diversity stays constant — the growth comes from accumulation,
not from increasingly adventurous baskets. Exploration tendency is a persistent
individual trait (r=0.66) layered on a universal slowdown.

## Limitations

- Repertoire growth is right-truncated: the oldest-observed order is not necessarily
  a customer's true first order, so early repertoire is an overcount of genuinely new
  foods and the first-half new-ingredient rate is inflated.
- Order position, not calendar time (see the [calendar-time report](CALENDAR_TIME.md)).
- "Distinct ingredients" counts the classification's 542 observed ingredients; finer
  or coarser taxonomy would shift absolute counts.
