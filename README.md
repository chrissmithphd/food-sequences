# Food Selection Sequences: How Customers Repeat, Rotate, and Return to Foods

Study of food selection patterns in sequential grocery purchases using the Instacart Online Grocery Shopping Dataset 2017.

## Question

How do customers repeat and rotate foods, and can their past selections predict when a previously purchased food will disappear from — or return to — their subsequent orders?

This project uses real purchase data from 206,000 customers across 3.4 million orders to study the structure of repeat purchasing behavior. It examines exact products, food categories, and prepared foods specifically. The analysis separates descriptive patterns from predictive modeling, and reports honestly when sequence features do not outperform simple baselines.

## Key Findings

> **⚠️ Under revision (2026-10).** This analysis is being corrected after a methodological review. Two issues affect the findings below: (1) reordering was mis-measured using adjacent-basket overlap instead of Instacart's `reordered` field and full-history reorder intervals — **now corrected, see below**; (2) the pattern classifier used mutually-exclusive labels, evaluated only the single largest gap, and an absolute `max_gap ≤ 10` cap that wrongly excluded long regular cycles — **rewrite pending; the staple/rotation/return percentages below are provisional**. A reconciliation table at the bottom tracks what changed.

### Delayed reordering is common — and it was the headline the old analysis got wrong

Using Instacart's `reordered` field and full-history repeat intervals (not adjacent-basket overlap), reordering is frequent, but mostly **delayed**:

- Only **27.8%** of product reorders happen in the *immediately next* order; **66.3%** happen within 10 subsequent orders (event-weighted, censoring-aware).
- At the item level, **delayed reorders (35.3%) outnumber immediate repeats (27.7%)** of basket contents. An earlier draft read low adjacent-basket overlap (Jaccard 0.18) as "little reordering" — that inference was wrong, because overlap cannot see a product skipped for a few orders and bought again.
- The median gap between consecutive purchases of the same product is **2 orders**.

![When do customers reorder](analysis/figures/reorder_curve_product_vs_aisle.png)

The **green line (aisle) sits well above the blue line (exact product)**: customers return to the same *kind* of food (85% within 10 orders) more than to the same exact SKU (66%). That gap is brand/variant switching — the same aisle, a different product — held separate here and kept for future recipe analysis.

![Repeat interval distribution](analysis/figures/repeat_interval_distribution.png)

**Weighting changes the story**, so all three are reported: event-weighted (66.3% within 10) lets frequent repeat-buyers dominate; customer-weighted (62.3%) gives each customer equal say; customer-product-weighted (32.0%) gives each (customer, product) pair equal say and is far lower — because 8.1M of 13.7M pairs are single-purchase, so most *pairs* are never repeated even though most *purchase events* are.

### Food classification: every product mapped to a recipe-ingredient group

To analyze purchasing by *food* rather than exact SKU, all 49,688 products are classified
into **117 recipe-ingredient groups** (what a recipe would call them — "milk", "chicken
broth", "cheese", "onion"). The name decides the group; brand, size, organic, and fat
level are collapsed; non-food (pet, personal care, household) is excluded. This resolves
**87.5% of purchase volume**, and collapses huge SKU variety (e.g. 1,560 cheese SKUs → one
`cheese` group). It's a fast, reproducible classifier at ~75% accuracy on a hand-checked
random sample, most reliable on the high-volume head and weakest on prepared/branded items.

See the full write-up — approach, coverage, statistics, and honest accuracy — in
**[docs/FOOD_CLASSIFICATION.md](docs/FOOD_CLASSIFICATION.md)**. Mapping:
[`analysis/outputs/food_mapping.csv`](analysis/outputs/food_mapping.csv).

---

### Most grocery items are not staples — they come and go
*(⚠️ LEGACY / PROVISIONAL — from the pre-review classifier; depends on the classifier rewrite noted in the banner. Do not cite without that caveat.)*

Of 4.5 million classifiable user-product sequences (users with 10+ orders who bought a product at least twice), only **6% are persistent staples** — products bought in more than half of orders with runs of 3+ consecutive purchases. The most common classified pattern is **return after a break** (21%): customers stop buying something for 5+ orders, then resume. Another 15% show **replacement by another product** in the same aisle. Nearly half (45%) of sequences don't fit any clean pattern.

![Pattern Prevalence](analysis/figures/pattern_prevalence.png)

### What the patterns look like

Each row below shows one customer's purchase history for one product. Colored squares mark orders where the product was purchased; gray dots mark orders where it was not.

![Pattern Gallery](analysis/figures/pattern_gallery.png)

- **Persistent Staple**: Bag of Organic Bananas bought in 88% of orders, with only occasional gaps. These are the minority.
- **Regular Rotation**: Sliced Black Olives appearing every few orders with consistent spacing — the customer returns to it periodically.
- **Burst then Absence**: Mediterranean Crusted Salmon bought 3 times in quick succession, then never again.
- **Return after Break**: Naturals Chicken Nuggets purchased regularly, then absent for 10+ orders, then bought again.
- **Replacement by Another**: Garlic bought twice early on, then stops — another product in the same aisle starts around the same time.

### Prepared foods behave like everything else

One of the more striking findings: prepared foods (frozen meals, deli items, frozen pizza — 5,839 products) show almost identical sequence patterns to other groceries. Selection frequency, consecutive purchase runs, and gap lengths differ by less than 3%.

![Prepared vs Other](analysis/figures/prepared_vs_other_patterns.png)

The one difference is at the basket level: orders containing prepared foods are nearly 2× larger (13.2 vs 6.8 products). This is a selection effect — bigger baskets are more likely to include at least one prepared item — not evidence that prepared food buyers behave differently.

### Patterns have distinct feature signatures

The classification rules produce patterns with separated feature distributions. Note this is **descriptive, not validation**: patterns necessarily separate on the features used to define them, so this plot illustrates the rules rather than confirming them.

![Features by Pattern](analysis/figures/features_by_pattern.png)

- Staples have high frequency (median 0.62) and long consecutive runs (median 5)
- Rotations have moderate frequency with consistent, short gaps
- Burst-then-absence shows low recency (recently active) but concentrated early
- Returns have the largest mean gaps (median 5 orders between purchases)
- Replacements have high recency (long since last purchase) — the product has not been bought for a while (terminal absence in the observed window; this does not establish abandonment, since follow-up is censored and off-platform purchases are unobserved)

### Classification rules are transparent, with documented threshold sensitivity

All pattern thresholds were defined before examining examples. Sensitivity analysis shows gradual prevalence changes when thresholds are varied — no cliff edges or unstable boundaries:

![Threshold Sensitivity](analysis/figures/threshold_sensitivity.png)

The most sensitive parameter is `return_min_gap`: lowering it from 5 to 3 orders increases return-after-break from 21% to 25%, while raising it to 15 drops it to 7%. The `staple_min_frequency` threshold also matters — relaxing from 0.5 to 0.3 doubles the staple category from 6% to 13%. All other parameters shift prevalence by less than 5 percentage points across their full range.

## Data

**Source**: [Instacart Market Basket Analysis Dataset](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (2017)

| Table | Rows | Description |
|---|---|---|
| orders | 3,421,083 | Order metadata with user, sequence, timing |
| order_products_prior | 32,434,489 | Historical order contents |
| order_products_train | 1,384,617 | Training set order contents |
| products | 49,688 | Product catalog |
| aisles | 134 | Aisle taxonomy |
| departments | 21 | Department taxonomy |

Data validation confirmed 100% join coverage between orders and purchase records, no duplicate primary keys, and `days_since_prior_order` null only for first orders (expected). See [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md) for the full quality report.

### Key data constraints

- **No absolute dates**: Only customer-relative order numbers and inter-order days (capped at 30)
- **Test orders excluded**: 75,000 test-set orders have no published item labels and cannot be used
- **30-day ceiling**: Inter-purchase intervals longer than 30 days are censored
- **"Prepared food" is taxonomy-based**: Defined by aisle/department keywords (frozen meals, deli, etc.), not human review of every product

## Sequence Measurement (Phase 1)

### Product-level sequences

For each (customer, product) pair, we extract:

| Feature | Description | Full Dataset Mean |
|---|---|---|
| selection_frequency | Purchases ÷ total orders | 0.145 |
| max_consecutive | Longest run of consecutive orders with this product | 1.46 |
| mean_gap | Average orders between purchases | 1.55 |
| recent_frequency | Purchase rate in last 5 orders | 0.148 |
| longterm_frequency | Purchase rate in all earlier orders | 0.114 |
| recency | Orders since last purchase | 9.67 |

**13.7 million** user-product sequences across 197,523 users and 49,683 products.

### Reorder measurement (corrected)

**Reconciliation against Instacart's `reordered` field.** A history-based indicator (product seen in any earlier order by this customer) reproduces the `reordered` field on **100.000%** of 33,567,840 purchase rows (19,903,887 reorders; 13,663,953 first-time). The two measure the same thing; the full-history indicator is used throughout so it can also quantify *delayed* reorders, which the flag marks but does not measure.

**Basket composition** (items in orders that have a predecessor):

| Composition | Item-weighted | Customer-weighted |
|---|---|---|
| From immediately prior order | 27.7% | 26.9% |
| Older, absent from prior (**delayed reorder**) | **35.3%** | 23.6% |
| First observed | 37.0% | 49.5% |

Item-weighting pools all items (large baskets/heavy buyers dominate); customer-weighting gives each of 197,523 customers equal say. The *older-absent* share — items skipped in the immediately preceding order then rebought — is exactly what the old adjacent-overlap analysis missed.

**Censoring-aware cumulative reorder probability** (Kaplan-Meier; terminal purchases with incomplete follow-up are right-censored):

| Within n orders | 1 | 2 | 3 | 5 | 10 |
|---|---|---|---|---|---|
| Exact product, event-weighted | 27.8% | 40.7% | 48.2% | 56.8% | 66.3% |
| Exact product, customer-weighted | 27.0% | 38.6% | 45.3% | 53.1% | 62.3% |
| Exact product, customer-product-weighted | 10.8% | 16.6% | 20.4% | 25.4% | 32.0% |
| Same aisle (brand/variant allowed), event-weighted | 42.4% | 58.5% | 67.0% | 76.0% | 85.1% |

#### Adjacent-basket overlap (what the old analysis used — kept for transparency)

Consecutive baskets share **17.7%** of products (Jaccard); 28.6% of the previous order's items reappear in the *immediately following* order. This describes neighbor-to-neighbor churn only. It does **not** measure reordering — a product skipped for several orders and rebought is invisible to it — which is why the earlier "repeat purchasing is the exception" conclusion was wrong.

### Category-level sequences

Aisle-level (134 categories) and department-level (21 categories) sequences are also extracted. At the aisle level, repeat rates are much higher than at the product level — customers return to the same *aisles* even when they pick different *products*.

### Prepared food comparison

> **Cohort note.** The table below uses the **broad** frozen+deli definition (5,329 products — sweeps in ice cream, frozen produce, lunch meat). The primary **meal-like** cohort is now the 3,245 products in documented meal aisles (`config.MEAL_LIKE_AISLES`). On the corrected reorder measure, both cohorts track all-products closely: within 10 orders, meal-like 63.6% vs broad 64.0% vs all 66.3% (event-weighted) — prepared/meal items reorder slightly *less* than groceries overall, not more. The sequence-feature table below is from the broad cohort and will be regenerated against the meal-like cohort during the classifier rewrite.

| Metric | Prepared Foods (broad) | Other Groceries | Difference |
|---|---|---|---|
| Selection frequency | 0.143 | 0.145 | -1.3% |
| Max consecutive | 1.43 | 1.46 | -2.5% |
| Mean gap | 1.41 | 1.58 | -10.7% |
| Basket size (when present) | 13.2 products | 6.8 products | +94% |
| Basket-to-basket Jaccard | 0.175 | 0.178 | -1.7% |

At the individual product level, prepared foods are repurchased at nearly the same rate as other groceries. The slightly shorter mean gap (-10.7%) hints at tighter repeat cycles, but the difference is small.

## Pattern Classification (Phase 2)

### Rules (defined before examining examples)

| Pattern | Rule | Prevalence |
|---|---|---|
| **Persistent Staple** | Frequency ≥ 50%, consecutive run ≥ 3 | 6.0% (272K) |
| **Regular Rotation** | 3+ purchases, frequency < 50%, spread ≥ 50% of history, gap CV < 1.5, no single gap > 10 orders or > 3× mean | 10.0% (452K) |
| **Burst then Absence** | 3+ purchases, dense in first half, sparse in second half, ≥ 3 orders since last purchase | 3.2% (142K) |
| **Return after Break** | Gap of ≥ 5 orders with ≥ 2 purchases before and ≥ 1 after | 20.7% (933K) |
| **Replacement by Another** | Burst/unclassified + same-aisle product starts within 3 orders of this one stopping | 14.8% (667K) |
| **Unclassified** | No pattern matched | 45.2% (2.04M) |

Patterns are mutually exclusive (first match wins in priority order: staple > rotation > burst > return). Replacement is detected via a cross-product merge after initial classification. Sequences with fewer than 2 purchases or from users with fewer than 10 orders are excluded from classification.

## Methodology

### Memory-efficient processing

The Instacart dataset's `order_products_prior` table (32.4M rows, ~1 GB in memory) makes naive joins crash on machines with limited RAM. All processing uses a **batched approach**: users are split into groups of 10,000, each batch processes independently, and results are concatenated. This keeps peak memory under 2 GB.

### Pattern classification algorithm

Rather than row-by-row Python iteration (which would take hours on 4.5M sequences), the classifier uses a **two-phase approach**:

1. **Precompute**: Extract scalar features from the `order_numbers` list column in a single batched pass (~2.5 minutes). This produces `gap_cv`, `max_gap`, `early_density`, `late_density`, etc.
2. **Classify**: Apply vectorized boolean masks using the precomputed scalars (~0.25 seconds for all 4.5M rows). Threshold sensitivity re-runs are subsecond.

Replacement detection uses a merge-join on `(user_id, aisle)` rather than nested per-user loops, completing in ~2.5 seconds.

## Reproducibility

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Kaggle account with API credentials

### Commands

```bash
# Install dependencies
uv sync

# Download, extract, convert data to Parquet
python scripts/ingest_data.py

# Validate data quality
python scripts/audit_data.py

# Build product sequences (batched, ~5 min)
python scripts/build_sequences_batched.py

# Build basket overlap and category sequences (~10 min)
python scripts/build_phase1_remaining.py

# Delayed-reorder analysis: reconciliation, repeat events, censored KM curves (~15 min)
python scripts/analyze_reorder.py

# Classify patterns and run sensitivity analysis (~3 min) [classifier rewrite pending]
python scripts/analyze_patterns.py

# Food classification: map every product to a recipe-ingredient group
python scripts/classify_products.py

# Generate figures
python scripts/generate_reorder_figures.py
python scripts/generate_phase2_figures.py
```

### Kaggle authentication

The Kaggle API requires token-based authentication:

1. Go to https://www.kaggle.com/settings/account
2. Generate a token (format: `KGAT_...`)
3. Either:
   - `export KAGGLE_API_TOKEN=KGAT_your_token_here`, or
   - Save to `~/.kaggle/access_token` and `chmod 600` it

### Project structure

```
food-sequences/
├── analysis/
│   ├── outputs/           # Parquet files with computed features and classifications
│   └── figures/           # PNG + SVG figures
├── data/
│   ├── raw/               # Downloaded CSV files (gitignored)
│   └── processed/         # Parquet files (gitignored)
├── docs/
│   └── DATA_AUDIT.md      # Data quality report
├── scripts/
│   ├── ingest_data.py     # Download and convert data
│   ├── audit_data.py      # Validate data quality
│   ├── build_sequences_batched.py    # Extract product sequences
│   ├── build_phase1_remaining.py     # Basket overlap + category sequences
│   ├── analyze_patterns.py           # Pattern classification (rewrite pending)
│   ├── analyze_reorder.py            # Delayed-reorder measurement + reconciliation
│   ├── classify_products.py          # Map every product to a recipe-ingredient group
│   ├── generate_reorder_figures.py   # Reorder curve figures
│   └── generate_phase2_figures.py    # Pattern figure generation
├── src/food_sequences/
│   ├── config.py            # Centralized paths and configuration
│   ├── food_classifier.py   # Recipe-ingredient classifier (see docs/FOOD_CLASSIFICATION.md)
│   ├── patterns.py          # Pattern classification rules
│   ├── reorder.py           # Delayed-reorder measurement
│   └── sequences.py         # Sequence extraction functions
└── README.md
```

## What Changed in the 2026-10 Revision

Reconciliation of corrected results against the earlier version:

| Claim / metric | Earlier version | Corrected | Why it changed |
|---|---|---|---|
| How reordering was measured | Adjacent-basket Jaccard (0.18) | Full-history indicator + `reordered` field + censored KM | Overlap can't see delayed reorders; it was the wrong instrument |
| "Repeat purchasing is the exception" | Stated as a finding | **Removed — false** | 66.3% of products are reordered within 10 orders; delayed reorders (35.3%) outnumber immediate repeats (27.7%) |
| "Reordering is at category level, not products" | Stated | Reframed as product-vs-aisle gap | Both are substantial; the gap (66%→85% within 10) is specifically brand/variant switching |
| Reorder reconciliation vs `reordered` | Field never used | 100.000% agreement on 33.6M rows | New check confirms the indicator is correct |
| Single-purchase repeat interval | Implicitly 0 (mean_gap=0) | **MISSING** (8.1M pairs) + censored observation | A product bought once has no interval, not a zero interval |
| Prepared-food cohort | Broad frozen+deli (5,329 products) | Meal-like aisles primary (3,245); broad kept as comparison | "Deli/frozen" swept in ice cream, lunch meat, frozen produce |
| "Rules capture real structure" (boxplots) | Stated as validation | **Removed** — relabeled descriptive | Patterns separate on the features that define them (circular) |
| Replacement = "abandoned" | Stated | Softened to "terminal absence in window" | Follow-up is censored; off-platform purchases unobserved |
| Pattern classifier | Final result | **Flagged provisional** | Mutually-exclusive labels, largest-gap-only, max_gap≤10 cap all pending rewrite |

### Still pending (not yet corrected)
- Classifier rewrite to **overlapping descriptive flags**, evaluating **all** eligible breaks (not just the largest), with the absolute `max_gap ≤ 10` cap removed so **long regular cycles stay eligible**, and explicit handling so an **every-other-order** sequence registers as periodic.
- Explicit unit tests on hand-built sequences (consecutive, alternating, slow rotation, break-and-return).
- Gallery rebuild: complete histories or marked cropping, marked observation endpoints, alternating/slow-cycle examples, both products shown for replacements.
- Per-(customer, product) usual-cycle estimation using only preceding purchases at cutoffs; sensitivity re-run including replacement detection.

## Limitations and Caveats

- **Non-selection is not boredom.** A customer who stops buying frozen pizza may have found it at a different store, changed their diet, or simply not needed it that week. Availability, price, household needs, and off-platform purchases are unobserved.
- **An alternative is not a proven substitution.** When product A stops and product B starts in the same aisle, we flag it as a *potential* replacement. It could be coincidence, a new household member's preference, or a seasonal shift.
- **This analysis does not establish subscriber longevity.** The Instacart dataset has no subscription model. Patterns observed here may not transfer to subscription meal services.
- **Order-number time is not calendar time.** Customer-relative order sequences have no global alignment. "Order 10" for one customer may be 3 months of history; for another, 3 years.
- **Category boundaries are approximate.** "Prepared food" is defined by aisle/department keyword matching, not human review of all 49,688 products. Edge cases (frozen pizza dough vs. frozen pizza) follow the taxonomy's classification.

## Source Attribution

**Dataset**: "The Instacart Online Grocery Shopping Dataset 2017", accessed via [Kaggle](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis). This project uses the data under Kaggle's published terms. Raw purchase histories and customer identifiers are not redistributed.

## License

This is a portfolio project. Code is available for review. Raw data files are not distributed with this repository.
