# Substitution vs. Coexistence

## Research question

When a customer uses more than one product for the same ingredient, are they
*replacing* one with another (serial commitment, a handoff), *alternating*
between them, or buying several in *coexistence*? And is any of this more
structured than random product choice?

## Method

Deduplicate to one (customer, order, ingredient, product). For each consecutive
pair of purchases of the same ingredient by a customer, record whether the product
**stayed the same**. Compare observed P(stay) to a null that shuffles product
labels across that ingredient's purchase slots (preserving each product's count):

```
expected P(stay) = Σ_p c_p(c_p − 1) / (n(n − 1))
```

`lift = observed / expected`: > 1 means products come in **runs** (serial
commitment); < 1 means **alternation** beyond chance; ≈ 1 means random.

## Results

| Scope | observed P(stay) | expected | lift |
|-------|-----------------:|---------:|-----:|
| All ingredients | 63.0% | 60.7% | 1.04 |
| Multi-product pairs only | 43.7% | 40.3% | 1.09 |
| Prepared dishes | 49.5% | 49.3% | 1.00 |
| Base ingredients | 63.6% | 61.2% | 1.04 |

By ingredient:

| Ingredient | observed | expected | lift | reading |
|-----------|---------:|---------:|-----:|---------|
| eggs | 84.8% | 79.8% | 1.06 | mild commitment |
| milk | 65.8% | 63.3% | 1.04 | mild commitment |
| coffee | 62.4% | 60.0% | 1.04 | mild commitment |
| banana | 91.5% | 88.2% | 1.04 | mild commitment |
| pasta | 42.4% | 41.0% | 1.04 | mild commitment |
| ice_cream | 31.7% | 30.6% | 1.04 | mild commitment |
| bread | 96.8% | 96.6% | 1.00 | random (one product dominates) |
| **yogurt** | **26.3%** | **27.4%** | **0.96** | **alternation — flavor variety-seeking** |

## Interpretation

**The "serial SKU commitment" tendency is real but weak.** Once you hold a
customer's product mix fixed, the temporal arrangement is only slightly more
run-like than random (lift 1.04–1.09 for most ingredients). This tempers the
[reorder reading](REORDER_PROBABILITY.md): the high product-level *lift* there is
partly a property of the baseline, not strong evidence that customers lock onto one SKU.

**The exception is the interesting part.** Yogurt is *anti*-persistent (lift 0.96):
customers alternate yogurt products more than random choice would — active flavor
variety-seeking within a familiar ingredient. ice_cream and pasta, also
"variety" categories, have the lowest absolute P(stay) (32%, 42%) even if their
lift is ~1. So the place to look for genuine rotation is discretionary/flavored
categories, not staples. Staples (banana 92%, bread 97%, eggs 85%) are bought as
the same product almost every time — but that is near their chance rate too,
because the customer simply has one product for them.

**When multiple products are used, replacement beats coexistence.** Among
multi-product (customer, ingredient) pairs, 72.4% are clean handoffs (one product's
run ends before another's begins) and only 27.6% show an earlier product persisting
past a later one's debut. So the typical multi-product story is "stopped buying A,
switched to B," not "buys both ongoing."

## Limitations

- "Clean handoff" is a loose temporal test; with few purchases per product many
  pairs trivially satisfy it. The 72% is directional, not a precise rate.
- The label-shuffle null removes *stable* product preference by construction, so
  lift isolates temporal clustering — a customer who always buys one milk shows
  lift ≈ 1, not because they lack preference but because there is nothing to
  arrange. Absolute P(stay) and lift should be read together.
- Order sequence, not calendar time (see the [calendar-time report](CALENDAR_TIME.md)).

## Follow-up

- Does a within-ingredient switch predict a later reversion to the original
  product, or is it permanent? (27.6% coexistence suggests some reversion.)
- Are yogurt/ice-cream alternation customers a distinct "variety-seeking" type?
  ([Customer-behavior report](CUSTOMER_BEHAVIOR.md).)
