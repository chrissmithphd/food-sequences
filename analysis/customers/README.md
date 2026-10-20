# Customers

Who the customers are descriptively (how long, how often, how much), and whether they
have consistent behavioral tendencies or just differ by volume.

- Sources: `analyze_customer_profile.py` (`customer_profile_summary.csv`,
  `customer_segments.csv`), `analyze_customer_behavior.py` (behavioral metrics).

## Who they are

![Customer profile distributions](../figures/customer_profile_distributions.png)

Across all 206,209 customers:

| Measure | p10 | p25 | median | p75 | p90 |
|---------|----:|----:|-------:|----:|----:|
| Orders per customer | 4 | 6 | **10** | 20 | 37 |
| Observed tenure (days) | 49 | 81 | **145** | 248 | 332 |
| Food items (total) | 20 | 39 | **81** | 176 | 356 |
| Food items per order | 3 | 5 | **8** | 12 | 16 |
| Days between orders (cadence) | 5 | 7 | **13** | 22 | 30 |

The median customer places 10 orders over ~5 observed months, in baskets of ~8 items,
shopping about every 13 days. Every measure is strongly right-skewed — a heavy tail
shops weekly and places 37+ orders. (Tenure and order counts are window-censored —
observed, not lifetime — and the 30-day cap on inter-order gaps makes tenure a lower
bound.)

## Segments

Splitting at the medians of two near-independent axes — **shopping frequency** and
**basket size** — gives four well-balanced groups:

![Customer segments](../figures/customer_segments.png)

| Segment | Share | Mean orders | Mean basket | Mean cadence |
|---------|------:|------------:|------------:|-------------:|
| frequent / big-basket | 26.9% | 24 | 13 | 8 days |
| frequent / small-basket | 24.9% | 23 | 5 | 8 days |
| occasional / small-basket | 24.4% | 8 | 5 | 23 days |
| occasional / big-basket | 23.8% | 9 | 13 | 23 days |

The four cells are roughly equal, so frequency and basket size are genuinely
different axes, not one. **Frequency, not basket size, drives order volume**: frequent
shoppers accumulate ~23–24 observed orders versus ~8–9 for occasional ones, at similar
basket sizes.

## Do customers have consistent "types"?

For customers with ≥10 orders (107,257), per-customer behavioral measures:

| Measure | p10 | median | p90 |
|---------|----:|-------:|----:|
| product repeat rate | 0.35 | 0.58 | 0.79 |
| ingredient repeat rate | 0.49 | 0.70 | 0.86 |
| new-ingredient rate | 0.14 | 0.30 | 0.51 |
| distinct ingredients (repertoire) | 17 | 49 | 93 |
| diversity (ingredients ÷ items) | 0.13 | 0.28 | 0.48 |
| within-ingredient switch rate | 0.13 | 0.35 | 0.59 |

**Tendencies are stable across a customer's history** — first-half values predict
second-half with correlation 0.73–0.82 (product_repeat 0.81, new_ing_rate 0.81,
diversity 0.82, switch_rate 0.73). These are durable individual traits, not phases.

**But most "types" are largely volume.** Repeat, novelty, and diversity correlate
±0.5–0.6 with purchase volume — heavier buyers repeat more and explore less, so
"repeater vs explorer" is to a large degree "high-volume vs low-volume":

| Measure | corr(n_orders) | corr(avg_basket) |
|---------|---------------:|-----------------:|
| product_repeat | +0.52 | +0.16 |
| new_ing_rate | −0.58 | −0.28 |
| diversity | −0.58 | −0.29 |
| **switch_rate** | **−0.06** | +0.19 |

The exception is **within-ingredient product-switching** — essentially independent of
volume (−0.06 with order count). Whether a customer locks onto one product per
ingredient or rotates among several is a genuine preference dimension that survives
after volume is accounted for. If you segment on one behavioral trait, switch_rate is
the one that carries information beyond "how much do they buy."

## Limitations

- Tenure / order counts are window-censored (observed, not lifetime); segments use
  median splits for interpretability, not a fitted clustering.
- Behavioral correlations are descriptive; no causal claim about why volume and
  repetition move together.
- Per-customer tables contain user IDs and are not committed; only aggregate
  summaries are.
