# Basket Composition (orders with a preceding order)

Each item in a basket (for orders 2..N) is classified as:
- **from immediately prior order** — also in order n-1
- **older, absent from prior** — bought earlier but not in order n-1 (a *delayed* reorder)
- **first observed** — never bought before by this customer

## Item-weighted (pool all items across all qualifying baskets)
Denominator = 31,573,455 basket items.

| Composition | Share |
|---|---|
| From immediately prior order | 27.7% |
| Older, absent from prior (delayed reorder) | 35.3% |
| First observed | 37.0% |

## Customer-weighted (each customer's mean, then averaged; n=197,523)

| Composition | Share |
|---|---|
| From immediately prior order | 26.9% |
| Older, absent from prior (delayed reorder) | 23.6% |
| First observed | 49.5% |

**Why two denominators:** item-weighting lets large baskets and heavy buyers
dominate; customer-weighting gives every customer equal say. The *older-absent*
share is the key quantity the earlier adjacent-overlap analysis missed entirely:
these are reorders of items skipped in the immediately preceding order.
