# Reorder Probability Audit (Part 1.1 + 1.2)

## Research question

Do customers show *loyalty* to broad food categories and *flexibility* at the
product level — or was that earlier conclusion an artifact of how the statistic
was defined and how broad categories aggregate many products?

## What was wrong before

The original `analyze_ingredient_sequences.py` reported an "immediate_pct":

```
immediate_pct = (# repeat intervals of length 1) / (# all repeat intervals)
```

Two defects:

1. **It is not a next-order probability.** It conditions on a repeat *existing*
   — it answers "given this item was repurchased at all, how often was the gap
   one order?" It cannot answer "if a customer buys X in order N, how likely is
   X in order N+1?" because items never repurchased are excluded from the
   denominator entirely.

2. **No within-order deduplication at coarse levels.** `item_counts` and the
   repeat loop incremented once per *row*. A customer buying three dairy
   products in one order generated three separate `category=DAIRY` repeat
   events (all with the same gap). This inflated category/ingredient/aisle
   counts — exactly the levels where the "loyalty" story was strongest.

## Corrected definitions

Deduplicate to **one event per (customer, order, level-value)**. Orders are
numbered 1..N consecutively per customer, so an event at order *n* has an
observable next order iff *n* < the customer's max order.

- **P(next order)** — P(same value in order *n+1* | observable next order)
- **P(within k)** — P(value reappears in *n+1..n+k* | ≥ k observable future orders)
- **P(eventual | observable)** — ever reappears later (right-censored by window)
- **old interval metric** — reproduced for contrast (P(gap=1 | repeated at all))

## Popularity baseline (does loyalty survive?)

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

| Level | P(next) | within 2 | within 3 | within 5 | within 10 | eventual\* | old metric | expected | **Lift** |
|-------|--------:|---------:|---------:|---------:|----------:|-----------:|-----------:|---------:|---------:|
| **Product** | 28.7% | 41.8% | 49.5% | 58.3% | 68.2% | 64.1% | 44.7% | 22.2% | **1.29×** |
| **Ingredient** | 34.8% | 50.2% | 58.9% | 68.6% | 78.9% | 74.7% | 46.6% | 30.2% | **1.15×** |
| **Aisle** | 43.3% | 59.6% | 68.1% | 77.1% | 86.1% | 81.6% | 53.0% | 39.6% | **1.09×** |
| **Category** | 58.8% | 74.6% | 81.7% | 88.3% | 93.9% | 90.2% | 65.2% | 56.4% | **1.04×** |

\*eventual return is right-censored by the observation window; treat as a lower bound.

## What changed, and what it means

**The old "immediate" numbers were inflated at every level** (e.g., category
65.2% → corrected 58.8% next-order; product 44.7% → 28.7%). The interval metric
systematically overstated next-order behavior because it dropped never-repeated
items from the denominator.

**The headline reverses once you account for chance.** Raw persistence *does*
rise with aggregation — a category (58.8%) recurs far more than an exact product
(28.7%). The earlier report read that as "category loyalty, product flexibility."
But the **lift** tells the opposite story:

- **Product lift 1.29×** — exact-SKU repurchase is 29% above what basket
  composition alone predicts. This is the strongest genuine signal.
- **Category lift 1.04×** — category recurrence is barely 4% above chance. Almost
  all of it is a mathematical consequence of broad buckets refilling, not a
  behavioral preference for the family.

So the real finding is: **the behavioral habit lives at the product level, not
the category level.** Customers return to specific SKUs more than chance; their
apparent "category loyalty" is mostly aggregation. Ingredient (1.15×) sits in
between — some genuine ingredient-level habit, much of it still aggregation.

This is the opposite emphasis from the original README, and it is the more
defensible reading: the coarser the bucket, the more "loyalty" is just arithmetic.

## Limitations

- **Censoring.** `P(within k)` restricts to events with ≥ k observable future
  orders (a clean conditional estimator); eventual-return is a censored lower
  bound. A Kaplan–Meier curve would smooth the tail but does not change the
  next-order conclusions.
- **Baseline scope.** The shuffle baseline preserves each customer's basket set
  and frequencies but not cross-customer structure; it isolates *temporal*
  persistence, which is the quantity of interest here.
- **Order number ≠ calendar time.** Addressed separately (Part 10).

## Follow-up questions

- Which *specific* ingredients/products carry the high lift (true habits) versus
  near-1 lift (bought by everyone, persist by chance)? (Part 1.2 extension.)
- Does product-level lift concentrate in staples (milk, bananas) or also appear
  in discretionary items? Ties into the substitution analysis (Part 6).
