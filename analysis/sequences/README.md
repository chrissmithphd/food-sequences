# Sequences

How a customer's choices repeat, rotate, and space out across successive orders. Four
questions: do they reorder the same thing? do they commit to a product or rotate
within an ingredient? are the named "patterns" (staples, returns, bursts) real? and
does an order-gap mean a fixed amount of time?

- Sources: `analyze_reorder.py` (`reorder_probability_audit.csv`,
  `lift_decomposition.csv`), `analyze_patterns.py` (`pattern_distribution.csv`),
  `analyze_substitution.py` (`substitution_*.csv`), `analyze_calendar_time.py`
  (`calendar_gap_summary.csv`).

## 1. Reordering: a real habit at the product level

Deduplicate to one event per (customer, order, value) at each grain, then ask: given
an event with an observable next order, does the same value reappear in order *n+1*?
Compare the observed rate to a **frequency baseline** — a random re-ordering of each
customer's baskets that keeps what/how-much they buy but destroys *when*. For a value
in *b* of *B* baskets the expectation is (b−1)/(B−1); `lift = observed / expected`.

![Reorder lift by grain](../figures/reorder_lift_by_level.png)

| Grain | P(next) | within 5 | eventual | expected | Lift |
|-------|--------:|---------:|---------:|---------:|-----:|
| Product | 28.7% | 58.3% | 64.1% | 22.2% | 1.29× |
| Ingredient | 34.8% | 68.6% | 74.7% | 30.2% | 1.15× |
| Aisle | 43.3% | 77.1% | 81.6% | 39.6% | 1.09× |
| Category | 58.8% | 88.3% | 90.2% | 56.4% | 1.04× |

The headline: **a specific product is reordered ~29% more often than a customer's own
basket mix would produce by chance** — a genuine order-to-order habit at the exact
SKU. Raw reorder rates rise as the grain broadens (product 29% → category 59%), but
that is mostly aggregation (a broad bucket refills because it holds more products);
lift, which removes frequency, is the comparable quantity and is highest at the
product grain.

**Why lift is highest at the finest grain.** It is *not* that products are reordered
more than ingredients — they cannot be, since every product reorder is also an
ingredient reorder (ingredient P(next) 34.8% > product 28.7%). Splitting by how many
products a customer uses per ingredient shows the mechanism:

| Subset (share of events) | grain | P(next) | lift |
|---|---|--:|--:|
| Single-product (customer,ingredient) — 44.5% | product ≡ ingredient | 28.1% | 1.21× |
| Multi-product — 55.5% | product | 29.2% | 1.36× |
| Multi-product — 55.5% | ingredient | 41.4% | 1.12× |

Where a customer uses one product per ingredient the grains coincide (1.21× / 1.21× —
a clean sanity check). The whole product-vs-ingredient gap lives in multi-product
pairs, where customers **hold one product for a run of orders then switch to another
of the same ingredient** — the ingredient stays present (mild lift) while each product
arrives in bursts (higher lift). That substitution behavior is section 2.

## 2. Substitution: mild commitment, category-specific variety

When a customer buys an ingredient again, do they keep the same product (commitment)
or switch (rotation)? Compare observed P(stay the same product) to a null that
shuffles each ingredient's product labels (counts preserved).

| Scope | P(stay) | expected | lift |
|-------|--------:|---------:|-----:|
| All ingredients | 63.0% | 60.7% | 1.04 |
| Multi-product pairs only | 43.7% | 40.3% | 1.09 |
| Base ingredients | 63.6% | 61.2% | 1.04 |
| Prepared dishes | 49.5% | 49.3% | 1.00 |

Commitment is **real but mild** (lift 1.04–1.09): product runs are only slightly more
run-like than chance. The interesting variation is by ingredient:

| Ingredient | P(stay) | lift | reading |
|-----------|--------:|-----:|---------|
| eggs | 84.8% | 1.06 | mild commitment |
| banana | 91.5% | 1.04 | one product, bought repeatedly |
| milk | 65.8% | 1.04 | mild commitment |
| bread | 96.8% | 1.00 | random (one product dominates) |
| ice_cream | 31.7% | 1.04 | low stay rate — variety category |
| **yogurt** | **26.3%** | **0.96** | **alternates below chance — active variety-seeking** |

Staples (banana, bread, eggs) stay high simply because the customer has one product
for them. Variety-seeking is concentrated in **discretionary, flavored categories** —
yogurt actively alternates (stays *less* than chance), and ice cream / pasta have the
lowest stay rates. Prepared dishes behave like a variety category: within a dish type,
buyers rotate across SKUs at chance (49.5%, lift 1.00) rather than committing. Among
multi-product (customer, ingredient) pairs, 72% are clean handoffs (A-run then B-run)
rather than ongoing coexistence.

## 3. "Patterns" mostly re-describe frequency and history length

Sorting (customer, ingredient) pairs into staples / rotation / returns / bursts, then
re-classifying a frequency-preserving random null, shows most of the taxonomy is not
distinctive behavior.

| Pattern | Observed | Random baseline | Verdict |
|---------|---------:|----------------:|---------|
| Persistent staple | 9.2% | 9.2% | at chance |
| Regular rotation | 4.6% | 5.5% | below chance |
| Return after break | 58.1% | 68.6% | below chance |
| Burst then absence | 1.6% | 0.3% | **5× above chance** |
| Irregular | 26.5% | 16.5% | above chance |

"Return after break" is also threshold-fragile — its share runs 75% → 29% as the gap
threshold moves from 3 to 10 orders — and rises from 27% to 85% purely with history
length (longer histories contain more opportunities for a gap). Random shopping
produces *more* "returns" than real customers. The one pattern that survives is
**burst-then-absence**: an ingredient bought a few times early then dropped, 5× above
chance and not a censoring artifact (99.3% of bursts end ≥5 orders before the
customer's last observed order). That is genuine **early abandonment** — a candidate
churn signal.

![Pattern gallery](../figures/pattern_gallery.png)

Each row is one product for one customer (■ = purchased). Staples, rotation, bursts,
returns, and replacements are visible.

## 4. An order-gap is not a clock

All the above measures gaps in *orders*. But cadence varies enormously, so an
order-gap is not a fixed amount of time:

| Order gap | Median days | p10–p90 |
|----------:|------------:|--------:|
| 1 | 8 | 3–30 |
| 2 | 15 | 6–42 |
| 3 | 23 | 9–59 |
| 5 | 37 | 15–88 |
| 10 | 71 | 32–147 |

Shopping cadence ranges from a median of 5 days between orders (p10 of customers) to
30 (p90), median 13. A single 5-order gap spans **15 to 88 days** depending on the
customer. Order-space is the right frame for "how many shopping trips until they buy
it again"; calendar-space needs the day index; the two must not be conflated. (The
30-day cap on `days_since_prior_order` makes long day-gaps lower bounds.)

## Limitations

- `P(within k)` conditions on ≥k observable future orders; eventual-return is a
  right-censored lower bound. The shuffle/random nulls preserve each customer's
  frequencies but not cross-customer structure — they isolate temporal structure,
  which is the quantity of interest.
- Pattern thresholds are arbitrary; the sensitivity analysis is the summary that
  matters. No absolute calendar dates exist in the data.
