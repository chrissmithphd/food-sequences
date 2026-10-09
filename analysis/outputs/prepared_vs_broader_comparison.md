# Prepared Food vs. Broader Grocery: Comparison

Generated from 13.7M user-product sequences (197,523 users, 49,683 products).

## Sequence-Level Metrics (per user-product pair)

| Feature | Prepared (n=1.63M) | Other (n=12.03M) | Diff |
|---|---|---|---|
| Selection frequency | 0.143 | 0.145 | -1.3% |
| Max consecutive purchases | 1.43 | 1.46 | -2.5% |
| Mean gap (orders between repeats) | 1.41 | 1.58 | -10.7% |
| Recent frequency (last 5 orders) | 0.144 | 0.149 | -3.6% |
| Long-term frequency | 0.113 | 0.114 | -1.0% |
| Recency (orders since last purchase) | 9.83 | 9.65 | +1.8% |
| Total purchases | 2.30 | 2.48 | -7.1% |

**Takeaway:** At the individual product level, prepared foods are repurchased at nearly the same
rate as other groceries. The slightly shorter mean gap (-10.7%) hints at tighter repeat cycles,
but the overall pattern is remarkably similar.

## Basket-Level Metrics

| Metric | Orders with prepared food | Orders without |
|---|---|---|
| Count | 1,729,283 (52.1%) | 1,590,742 (47.9%) |
| Mean basket size | 13.2 products | 6.8 products |
| Mean aisles represented | 9.5 | 4.9 |
| Basket-to-basket Jaccard overlap | 0.175 | 0.178 |
| % of previous basket retained | 30.2% | 26.8% |

**Takeaway:** Orders containing prepared foods are ~2x larger and span ~2x as many aisles.
This is largely a selection effect — bigger baskets have more chances to include prepared items.
Basket overlap is similar regardless of prepared-food presence, suggesting prepared foods don't
make baskets more or less "sticky."

## Caveats

- "Prepared food" is defined by aisle/department keyword matching (5,839 of 49,688 products).
  Edge cases (e.g., frozen pizza vs. pizza dough) are included based on aisle taxonomy, not
  human judgment of every product.
- Sequence metrics compare user-product pairs. A user who buys 5 different frozen meals
  generates 5 low-frequency sequences, not 1 high-frequency "prepared food" sequence.
  Category-level analysis (aisle/department sequences) addresses this.
