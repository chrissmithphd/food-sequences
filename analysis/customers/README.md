# Customers

How differently do people shop, which differences persist, and what can we learn
about distinct shopping behaviors?

- Sources: `analyze_customer_profile.py`, `analyze_customer_behavior.py`,
  `analyze_customer_extended.py`; `visualize_customers.py`
- Scope: 206k customers; behavioral metrics computed for 107k with ≥10 orders.

---

## Who the customers are

![Customer profile distributions](../figures/customer_profile_distributions.png)

| Measure | p10 | p25 | median | p75 | p90 |
|---------|----:|----:|-------:|----:|----:|
| Orders per customer | 4 | 6 | **10** | 20 | 37 |
| Observed tenure (days) | 49 | 81 | **145** | 248 | 332 |
| Food items per order | 3 | 5 | **8** | 12 | 16 |
| Days between orders | 5 | 7 | **13** | 22 | 30 |

The median customer places 10 orders over ~5 observed months, in baskets of ~8 items,
shopping about every 13 days. Every measure is strongly right-skewed — a heavy tail
shops weekly with 37+ orders. (Tenure and order counts are window-censored; the
30-day cap on inter-order gaps makes tenure a lower bound.)

## Frequency × basket size

![Customer segments](../figures/customer_segments.png)

Splitting at the medians of shopping frequency and basket size creates four
roughly equal groups. These are descriptive bins, not discovered clusters — the
underlying distributions are continuous:

| Segment | Share | Mean orders | Mean basket | Mean cadence |
|---------|------:|------------:|------------:|-------------:|
| frequent / big-basket | 26.9% | 24 | 13 | 8 days |
| frequent / small-basket | 24.9% | 23 | 5 | 8 days |
| occasional / small-basket | 24.4% | 8 | 5 | 23 days |
| occasional / big-basket | 23.8% | 9 | 13 | 23 days |

Frequency and basket size are genuinely different axes. **Frequency drives observed
order volume**: frequent shoppers accumulate ~24 orders vs ~9, regardless of basket
size.

## Which behaviors move together

![Behavior correlations](../figures/behavior_correlations.png)

The correlation matrix reveals three distinct groups:

**One big cluster (r > 0.9):** product_repeat, new_ing_rate, and diversity move
together almost perfectly. These are not three independent traits — they're one
dimension (how much of a customer's purchasing is familiar vs new), and it correlates
±0.5–0.6 with order count. "Repeater vs explorer" is largely "high-volume vs
low-volume."

**Low correlation with volume:** Two behaviors have near-zero Pearson correlation
with order count:
- **Product switching** (corrected, cross-order only): r = −0.04 with order count.
  Whether a customer sticks to one product per ingredient or rotates among several
  does not track purchasing volume. (Low linear correlation does not rule out other
  relationships, and it does not by itself establish a stable individual preference.)
- **Prepared-food share**: r = −0.08 with order count, +0.07 with basket size.
  How much a customer buys prepared food shows little linear relationship with how
  often or how much they shop overall.

**Effective ingredients** (inverse HHI) correlates +0.61 with basket size —
mechanically, bigger baskets spread across more ingredients. This is not a behavioral
trait; it's arithmetic.

## How much variation is within customers versus between them

![Within vs between](../figures/within_vs_between.png)

For both basket size and prepared-food share, the variation *within* a single
customer across their orders is almost as large as the variation *between*
customers:

| Measure | Between-customer SD | Within-customer mean SD | ICC |
|---------|--------------------:|------------------------:|----:|
| Basket size | 5.15 | 4.20 | 0.60 |
| Prepared-food share | 0.059 | 0.056 | 0.53 |

The intraclass correlation (ICC) measures what fraction of total variance is between
customers rather than within: 0.60 for basket size, 0.53 for prepared-food share.
Values near 0.5 mean between-customer and within-customer variation contribute roughly
equally. A customer who averages 8 items per basket might place orders ranging from
3 to 15. **Customer differences are real but modest** — order-to-order variation
within a customer accounts for nearly half of the total variation.

## Product switching

![Switch rate distribution](../figures/switch_rate_distribution.png)

The corrected switch rate (cross-order transitions only, excluding within-order
coexistence) has median 0.26: about 1 in 4 consecutive uses of the same ingredient
involves a different product. This varies widely across customers (p10 = 0.13,
p90 = 0.59) and has low linear correlation with shopping volume (r = −0.04).

Among the behavioral metrics examined, switch rate is the least confounded by
purchase volume. Whether that makes it a stable individual characteristic or simply
a measure that doesn't correlate with the most obvious confounder is a distinction
this data cannot fully resolve — it would require experimental or longitudinal
evidence beyond what purchase records provide.

## Behavioral metric distributions

| Measure | p10 | median | p90 |
|---------|----:|-------:|----:|
| Product repeat rate | 0.35 | 0.58 | 0.79 |
| New-ingredient rate | 0.14 | 0.30 | 0.51 |
| Diversity (ings ÷ items) | 0.13 | 0.28 | 0.48 |
| Switch rate (corrected) | 0.13 | 0.26 | 0.59 |
| Prepared-food share | 0.00 | 0.03 | 0.12 |

## Split-half stability

For customers with ≥20 orders, first-half vs second-half correlations.
**Caveat:** these correlations mix genuine stability with mechanical effects —
the second half has a longer accumulated repertoire, so novelty is mechanically
lower and repetition higher for every customer. The rank-order is meaningful (who
explores more stays exploring more), but the magnitude is inflated.

| Measure | r(first, second) |
|---------|------------------:|
| product_repeat | 0.81 |
| new_ing_rate | 0.81 |
| diversity | 0.82 |
| switch_rate | 0.73 |

Behavioral tendencies are moderately stable (r = 0.73–0.82). The repeat/novelty/
diversity cluster is the most stable; switch rate is somewhat less so. But recall
that within-customer variation is almost as large as between-customer — these
correlations reflect a real signal buried in substantial noise, not a clean partition
of customers into types.

## Limitations

Each item below names the problem and the direction of bias.

- **Censoring.** Order counts and tenure are observed, not lifetime. Everything is
  conditioned on a truncated window.

- **Repertoire metrics are mechanically tied to order count.** Repeat rate, novelty,
  and diversity are cumulative: more observed orders → higher repeat, lower novelty,
  by construction, independent of behavior. Their ±0.5–0.6 correlation with order
  count is mostly this artifact, so "high-volume vs low-volume" and
  "repeater vs explorer" are nearly the same axis. Treat these three as one
  observation-length-confounded measure, not three traits.

- **Split-half stability is inflated.** First vs second half differ in accumulated
  repertoire, so novelty is lower and repetition higher in the second half for
  *everyone*. A positive r (0.81 for new_ing_rate) therefore reflects a shared time
  trend plus genuine rank-order persistence; we cannot separate the two. Read it as
  an upper bound on true individual stability.

- **ICC is approximate here.** The design is badly unbalanced (order counts range from
  10 to 100+) and within-customer variance is not constant across customers, so the
  0.60 / 0.53 values are descriptive summaries, not a clean one-way random-effects
  decomposition. The qualitative point — within- and between-customer variation are
  the same order of magnitude — is robust; the exact numbers are not.

- **Switch rate uses one product per order.** When a customer buys several products of
  an ingredient in one order, only the most-purchased is kept, so simultaneous variety
  is not counted as switching. This is deliberate (the uncorrected version counted
  within-order coexistence as switches and ran ~10 points higher) but it discards
  information and the choice of representative is arbitrary.

- **Low Pearson r ≠ independence.** Switch rate and prepared-food share have r ≈ 0
  with order count. That rules out a linear volume relationship only. It does not
  establish statistical independence, nor that either is a stable individual trait —
  both would need longitudinal or experimental evidence this data can't provide.
