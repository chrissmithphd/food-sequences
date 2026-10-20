# Calendar Time vs. Order Sequence

## Research question

Analyses so far measure gaps in *orders* ("reappears 3 orders later"). But customers
shop at very different frequencies, so an order-gap is not a fixed amount of time. How
many days does an order-gap actually represent, and how much does it vary?

## Method

`orders.parquet` carries `days_since_prior_order` (capped at 30 days per order).
Cumulatively sum it per customer to get a day index for each order, then express each
ingredient repurchase gap in both orders and days (n = 18,965,913 repurchase gaps).

## Results

**Shopping cadence varies widely across customers:**

| Percentile | Median days between orders |
|-----------:|---------------------------:|
| p10 | 5 |
| p25 | 7 |
| p50 | 13 |
| p75 | 22 |
| p90 | 30 |

**An order-gap is not a clock.** Mapping ingredient repurchase order-gaps to days:

| Order gap | Median days | p25–p75 |
|----------:|------------:|--------:|
| 1 | 8 | 6–15 |
| 2 | 15 | 10–28 |
| 3 | 23 | 14–40 |
| 5 | 37 | 24–61 |
| 10 | 71 | 47–106 |

A single 5-order gap spans anywhere from **15 to 88 days (p10–p90)** depending on the
customer. The same order-distance means two weeks for a frequent shopper and three
months for an occasional one.

## Interpretation

Order-sequence gaps and calendar gaps are not interchangeable. Because cadence ranges
from weekly to monthly, any order-space pattern — "staples," "returns after a break" —
is partly a statement about a customer's shopping frequency, not purely about their
food behavior. A "5-order gap" is a stable unit of *shopping events* but a highly
variable unit of *time*. Order-space is the right frame for "how many shopping trips
until they buy it again"; day-space is required for anything about elapsed time, and
the two should not be conflated.

The 30-day cap on `days_since_prior_order` censors long gaps: any single inter-order
interval longer than 30 days is recorded as 30, so day-gaps spanning dormant periods
are lower bounds.

## Limitations

- `days_since_prior_order` is capped at 30 per order, so multi-order day-gaps that
  include long dormant stretches are underestimated.
- The dataset has no absolute calendar dates, so weekday/seasonality beyond
  `order_dow` / `order_hour_of_day` cannot be reconstructed.
- Day index assumes the observed first order is the start of counting; pre-window
  history is unknown.
