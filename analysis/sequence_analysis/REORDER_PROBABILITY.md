# Reorder Probability

## Research question

Do customers show *loyalty* to broad food categories and *flexibility* at the
product level? A broad category recurs in the next order far more often than an
exact product — but a broad bucket recurs often simply because it holds many
products. The question is how much more a value recurs than its popularity alone
would produce.

## Definitions

Deduplicate to **one event per (customer, order, level-value)**. Orders are
numbered 1..N consecutively per customer, so an event at order *n* has an
observable next order iff *n* < the customer's max order.

- **P(next order)** — P(same value in order *n+1* | observable next order)
- **P(within k)** — P(value reappears in *n+1..n+k* | ≥ k observable future orders)
- **P(eventual | observable)** — ever reappears later (right-censored by window)

## Popularity baseline

A broad category recurs often *simply because it holds many products*. To separate
real temporal persistence from aggregation, compare observed P(next) to the
expectation under a **random re-ordering of each customer's baskets** that
preserves their basket contents and frequencies but destroys order. For a value
present in *b* of a customer's *B* baskets, that expectation is analytic:
P(next basket has it | current has it) = (b−1)/(B−1). Aggregated:

```
expected P(next) = Σ b(b−1)/B  /  Σ (B−1)b/B        Lift = observed / expected
```

Lift ≈ 1 ⇒ "persistence" is just popularity. Lift > 1 ⇒ genuine habit.

## Results (full dataset, 30.4M deduplicated food events)

| Level | P(next) | within 2 | within 3 | within 5 | within 10 | eventual\* | expected | **Lift** |
|-------|--------:|---------:|---------:|---------:|----------:|-----------:|---------:|---------:|
| **Product** | 28.7% | 41.8% | 49.5% | 58.3% | 68.2% | 64.1% | 22.2% | **1.29×** |
| **Ingredient** | 34.8% | 50.2% | 58.9% | 68.6% | 78.9% | 74.7% | 30.2% | **1.15×** |
| **Aisle** | 43.3% | 59.6% | 68.1% | 77.1% | 86.1% | 81.6% | 39.6% | **1.09×** |
| **Category** | 58.8% | 74.6% | 81.7% | 88.3% | 93.9% | 90.2% | 56.4% | **1.04×** |

\*eventual return is right-censored by the observation window; treat as a lower bound.

## What it means

Raw persistence rises with aggregation — a category (58.8%) recurs far more than an
exact product (28.7%). But the **lift** runs the opposite way:

- **Product lift 1.29×** — exact-SKU repurchase is 29% above what basket
  composition alone predicts. This is the strongest genuine signal.
- **Category lift 1.04×** — category recurrence is barely 4% above chance. Almost
  all of it is a mathematical consequence of broad buckets refilling, not a
  behavioral preference for the family.

**The behavioral habit lives at the product level, not the category level.**
Customers return to specific SKUs more than chance; apparent "category loyalty" is
mostly aggregation. Ingredient (1.15×) sits in between — some genuine
ingredient-level habit, much of it still aggregation. The coarser the bucket, the
more "loyalty" is just arithmetic.

## Why does product-level lift exceed ingredient-level lift?

Product lift (1.29×) > ingredient lift (1.15×) is counter-intuitive — a finer grain
showing a *stronger* signal. It is not evidence that customers prefer exact products
over ingredients. Decomposing by whether a customer buys one or several products for
a given ingredient:

| Subset (share of events) | grain | P(next) | expected | lift |
|---|---|--:|--:|--:|
| **Single-product** (customer,ingredient) — 44.5% | product ≡ ingredient | 28.1% | 23.2% | **1.21×** |
| **Multi-product** (customer,ingredient) — 55.5% | product | 29.2% | 21.5% | **1.36×** |
| **Multi-product** — 55.5% | ingredient | 41.4% | 37.1% | **1.12×** |

When a customer buys only one product for an ingredient (44.5% of events), the two
grains are identical by construction and lift matches exactly (1.21× / 1.21×) — a
clean sanity check.

The entire product>ingredient gap lives in **multi-product** pairs. There, specific
SKUs cluster in time far more than the ingredient does (1.36× vs 1.12×). The
mechanism: customers **commit to one product for a run of orders, then switch to a
different product of the same ingredient**. The ingredient stays present (so its
persistence is only mildly above chance), while each individual product arrives in
temporal bursts (high product lift).

So the grain difference is a signature of *serial SKU commitment within a stable
ingredient* — the substitution behavior examined in the
[substitution report](SUBSTITUTION.md).

## Limitations

- **Censoring.** `P(within k)` restricts to events with ≥ k observable future
  orders (a clean conditional estimator); eventual-return is a censored lower
  bound. A Kaplan–Meier curve would smooth the tail but does not change the
  next-order conclusions.
- **Baseline scope.** The shuffle baseline preserves each customer's basket set
  and frequencies but not cross-customer structure; it isolates *temporal*
  persistence, which is the quantity of interest here.
- **Order number ≠ calendar time.** Addressed in the [calendar-time report](CALENDAR_TIME.md).

## Follow-up questions

- Which *specific* ingredients/products carry the high lift (true habits) versus
  near-1 lift (bought by everyone, persist by chance)?
- How often does the within-ingredient switch stick vs. revert to the original
  product? ([Substitution report](SUBSTITUTION.md).)
