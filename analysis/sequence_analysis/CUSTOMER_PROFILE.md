# Customer Profile

## Research question

Who are the customers, descriptively? How long are they observed, how many orders
and items do they buy, how big is a trip, how often do they shop — and do they fall
into interpretable groups?

## Method

Order-level fields (orders, tenure, cadence) come from the lightweight orders table
over all prior+train customers; item counts stream the purchase table in user-id
bursts. "Tenure" sums `days_since_prior_order` (capped at 30/order, so it is a lower
bound). 206,209 customers.

## Distributions

![Customer profile distributions](figures/customer_profile_distributions.png)

| Measure | p10 | p25 | median | p75 | p90 |
|---------|----:|----:|-------:|----:|----:|
| Orders per customer | 4 | 6 | **10** | 20 | 37 |
| Observed tenure (days) | 49 | 81 | **145** | 248 | 332 |
| Food items (total) | 20 | 39 | **81** | 176 | 356 |
| Food items per order (basket) | 3 | 5 | **8** | 12 | 16 |
| Median days between orders (cadence) | 5 | 7 | **13** | 22 | 30 |

The median customer places 10 orders over ~5 observed months, buys 81 food items in
baskets of ~8, and shops about every 13 days. Every measure is strongly
right-skewed: a heavy tail of customers places 37+ orders and shops weekly.

## Segments

Splitting customers at the medians of two independent axes — **shopping frequency**
(cadence) and **basket size** — yields four well-populated groups:

![Customer segments](figures/customer_segments.png)

| Segment | Share | Mean orders | Mean basket | Mean cadence |
|---------|------:|------------:|------------:|-------------:|
| frequent / big-basket | 26.9% | 24 | 13 | 8 days |
| frequent / small-basket | 24.9% | 23 | 5 | 8 days |
| occasional / small-basket | 24.4% | 8 | 5 | 23 days |
| occasional / big-basket | 23.8% | 9 | 13 | 23 days |

Frequency and basket size are near-independent (the four cells are ~balanced), so
they are two genuinely different axes, not one. Frequency tracks order volume
strongly: frequent shoppers accumulate ~23–24 observed orders vs ~8–9 for occasional
shoppers — most of the "heavy customer" signal is cadence, not basket size.

## Limitations

- Tenure and order counts are **window-censored**: the dataset observes a slice of
  each customer's history, so these are observed, not lifetime, figures. The 30-day
  cap on inter-order gaps makes tenure a lower bound.
- Segments use median splits for interpretability, not a fitted clustering; the cut
  points are descriptive, not natural boundaries.
- Behavioral traits (repeat rate, variety, switching) are in the
  [customer-behavior report](CUSTOMER_BEHAVIOR.md); this report is the descriptive
  "who/how much" companion.
