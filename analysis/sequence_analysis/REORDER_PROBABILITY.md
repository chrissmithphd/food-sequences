# Reorder Probability

## Research question

When a customer buys something, how likely are they to buy it again in their next
order — and is that more than their own basket mix would produce by chance?

## Definitions

Deduplicate to **one event per (customer, order, level-value)** at each grain
(product, ingredient, category, aisle). Orders are numbered 1..N consecutively per
customer, so an event at order *n* has an observable next order iff *n* < the
customer's max order.

- **P(next order)** — P(same value in order *n+1* | observable next order)
- **P(within k)** — P(value reappears in *n+1..n+k* | ≥ k observable future orders)
- **P(eventual | observable)** — ever reappears later (right-censored by window)

## Baseline

A value recurs partly just because the customer buys it often. To separate real
temporal persistence from frequency, compare observed P(next) to the expectation
under a **random re-ordering of each customer's baskets** — contents and frequencies
preserved, order destroyed. For a value present in *b* of a customer's *B* baskets:
P(next basket has it | current has it) = (b−1)/(B−1). Aggregated:

```
expected P(next) = Σ b(b−1)/B  /  Σ (B−1)b/B        Lift = observed / expected
```

Lift ≈ 1 ⇒ recurrence is just frequency. Lift > 1 ⇒ a genuine order-to-order habit.

## Results (full dataset, 30.4M deduplicated food events)

| Grain | P(next) | within 2 | within 3 | within 5 | within 10 | eventual\* | expected | Lift |
|-------|--------:|---------:|---------:|---------:|----------:|-----------:|---------:|-----:|
| Product | 28.7% | 41.8% | 49.5% | 58.3% | 68.2% | 64.1% | 22.2% | 1.29× |
| Ingredient | 34.8% | 50.2% | 58.9% | 68.6% | 78.9% | 74.7% | 30.2% | 1.15× |
| Aisle | 43.3% | 59.6% | 68.1% | 77.1% | 86.1% | 81.6% | 39.6% | 1.09× |
| Category | 58.8% | 74.6% | 81.7% | 88.3% | 93.9% | 90.2% | 56.4% | 1.04× |

\*eventual return is right-censored by the observation window; treat as a lower bound.

## What it means

**Customers reorder specific products about 29% more often than their own basket mix
would produce by chance** (product lift 1.29×). That is a real order-to-order habit
at the exact-SKU level: when someone buys a product, they are meaningfully more
likely to buy that same product next time than a frequency-only model predicts.

The raw next-order rate rises as the grain broadens (product 29% → category 59%),
which is expected — a broader bucket refills more often simply because it holds more
products. Lift, which removes that, is the comparable quantity and it is highest at
the product grain.

## Lift is highest at the product grain — why

Product lift (1.29×) exceeds ingredient lift (1.15×). This is **not** that products
are reordered more than ingredients — they can't be, since every product reorder is
also an ingredient reorder (ingredient P(next) 34.8% > product 28.7%). The higher
*lift* reflects a lower baseline for a rarer value, and it points to within-ingredient
substitution. Splitting by how many products a customer uses per ingredient:

| Subset (share of events) | grain | P(next) | expected | lift |
|---|---|--:|--:|--:|
| Single-product (customer,ingredient) — 44.5% | product ≡ ingredient | 28.1% | 23.2% | 1.21× |
| Multi-product (customer,ingredient) — 55.5% | product | 29.2% | 21.5% | 1.36× |
| Multi-product — 55.5% | ingredient | 41.4% | 37.1% | 1.12× |

When a customer uses one product for an ingredient, the two grains coincide (1.21× /
1.21× — a sanity check). The product-vs-ingredient lift gap lives entirely in
multi-product pairs, where a customer **holds one product for a run of orders, then
switches to another product of the same ingredient**: the ingredient stays present
(mild lift) while each product arrives in temporal bursts (higher lift). That is a
substitution signature, covered in the [substitution report](SUBSTITUTION.md).

## Limitations

- **Censoring.** `P(within k)` restricts to events with ≥ k observable future orders;
  eventual-return is a censored lower bound.
- **Baseline scope.** The shuffle baseline preserves each customer's basket set and
  frequencies but not cross-customer structure; it isolates temporal persistence.
- **Order number ≠ calendar time** — see the [calendar-time report](CALENDAR_TIME.md).
