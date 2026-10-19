# Purchase Pattern Classification — Audit (Part 1.3)

## Research question

The original analysis sorted 3.4M customer-ingredient pairs into staples, rotation,
bursts, returns, and irregular. Are those patterns distinctive behaviors, or do they
mostly re-describe purchase frequency and the length of the observed history?

## Definitions audited

For users with ≥10 orders, each (customer, ingredient) pair with ≥2 purchases is
labelled by precedence: **persistent staple** (bought in >50% of orders with a run
of 3+ consecutive) → **return after break** (a gap ≥5 orders) → **burst then
absence** (≥70% of purchases in the first 30% of history) → **regular rotation**
(≥3 purchases, gap CV < 0.5, mean gap 2–5) → **irregular** otherwise.

## Findings

### 1. 40% of pairs are silently excluded
Among ≥10-order users, **2.26M (40%) of (customer, ingredient) pairs are bought only
once** and are dropped before classification. Reporting pattern shares among the
remaining repeat pairs overstates how "patterned" behavior is. As a share of *all*
pairs, even the largest pattern (returns) is ~35%, not ~58%.

### 2. The headline figures are threshold-fragile
"Return after break" prevalence among repeat pairs, by gap threshold:

| gap ≥ | 3 | 4 | 5 | 6 | 8 | 10 |
|-------|--:|--:|--:|--:|--:|---:|
| share | 75.0% | 66.5% | 58.1% | 50.5% | 38.1% | 29.1% |

A defensible change in one threshold moves the headline from 29% to 75%. (The
earlier report's 31% used an additional "gap not first" restriction; a slightly more
inclusive and equally defensible rule gives 58% at the same threshold.) These labels
are not robust descriptions.

### 3. Prevalence is dominated by history length, not behavior
By customer history length B:

| B (orders) | staple | return | burst | irregular |
|-----------|-------:|-------:|------:|----------:|
| 10–14 | 14.5% | 26.7% | 1.0% | 49.5% |
| 15–24 | 10.9% | 48.5% | 1.7% | 32.6% |
| 25–49 | 7.4% | 70.1% | 2.1% | 17.6% |
| 50+ | 4.4% | 84.9% | 1.3% | 8.3% |

"Return after break" rises from 27% to 85% simply because longer histories contain
more opportunities for a ≥5-order gap. "Irregular" collapses symmetrically. The
taxonomy largely tracks how long we observed the customer.

### 4. Against a frequency-preserving random baseline, most patterns are not distinctive
Scatter each pair's *b* purchases at random over the customer's *B* orders
(preserving frequency, destroying order) and re-classify:

| Pattern | observed | random | verdict |
|---------|---------:|-------:|---------|
| persistent staple | 9.2% | 9.2% | **at chance** |
| regular rotation | 4.6% | 5.5% | **below chance** |
| return after break | 58.1% | 68.6% | **below chance** |
| burst then absence | 1.6% | 0.3% | **5× above chance** |
| irregular | 26.5% | 16.5% | above chance |

Staples, rotation, and returns occur at or **below** their random rates — they are
mostly consequences of frequency and history length, not distinctive temporal
behavior. Random purchasing actually produces *more* "returns" than customers do.

### 5. The one real signal: burst-then-absence
Burst-then-absence is the only named pattern meaningfully above chance (1.6% vs
0.3%). It is not a window-cutoff artifact: **99.3% of burst pairs have their last
purchase ≥5 orders before the customer's final observed order** — the customer kept
shopping, they just stopped buying that ingredient. This is genuine early
abandonment: an ingredient tried a few times, then dropped.

### 6. Rule overlap is modest
Before precedence, 6.2% of pairs match two rules and 0.1% match three; 26.5% match
none (→ irregular). Precedence order affects ~6% of labels.

## Interpretation

The pattern taxonomy mostly re-describes two nuisance variables — purchase frequency
and observation-window length — rather than distinctive behavior. The earlier
conclusions "returns after breaks are common" and "most behavior is irregular" do
**not** survive as behavioral claims: a frequency+history null reproduces or exceeds
them. The durable, distinctive finding is **early abandonment** (burst-then-absence),
which exceeds chance and is not a censoring artifact.

## Reporting correction

Pattern prevalence should be reported **by (customer, ingredient) pair**, not as a
percentage of customers. By customer, 97.5% exhibit at least one "irregular" pair and
96.5% at least one "return" pair — because customers have many pairs, almost everyone
shows every pattern at least once. That is not "96% of customers are returners."

## Limitations

- Thresholds are inherently arbitrary; the sensitivity analysis is the honest summary.
- The random baseline preserves per-customer frequency but not cross-ingredient
  correlations; it isolates temporal structure, which is the quantity of interest.
- Order sequence, not calendar time (Part 10).

## Follow-up

- Characterize burst-then-absence ingredients: are they discretionary/novel items
  (tried and dropped) vs. staples? Ties to novelty (Part 1.5) and substitution (Part 6).
