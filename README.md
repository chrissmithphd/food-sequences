# Meal Selection, Variety, and Retention in Grocery Purchasing

How do customers choose foods over time — what they repeat, rotate, and try once —
and what does that suggest for a meal-subscription service? Grocery data can't answer
subscription questions directly, but it shows the underlying selection patterns.

The project classifies 49,688 Instacart products into recipe ingredients, then
analyzes purchasing at the ingredient level across a customer's order history.

---

## Dataset

**Instacart Online Grocery Shopping Dataset 2017** — 206,000 customers, 3.4M orders,
49,688 products, sequential purchase history per customer. No absolute dates;
inter-order gaps are capped at 30 days.

**Classification.** All 49,688 products mapped to a 446-ingredient recipe taxonomy
(632 labels emerged) with an LLM, chosen over TF-IDF and embedding baselines.
38,529 are food (77.5%); 2,807 unclassified (the model declined low-confidence
guesses). Prepared *dishes* are defined by the taxonomy's "Prepared Dishes & Meals"
section (17 meal types), not the per-product `is_prepared_dish` flag, which was too
broad. [Classification analysis →](analysis/classification/CLASSIFICATION_ANALYSIS.md)

The full purchase table is ~30M rows; every analysis streams it in customer-id
bursts to stay within memory ([docs/PROCESSING.md](docs/PROCESSING.md)).

---

## Results

Each result is a standalone analysis with its own report; the summaries below give
the headline and a figure.

### Ingredients

Analyzing at the ingredient level (not the product SKU) surfaces two things.

![Ingredients by purchase volume](analysis/sequence_analysis/figures/ingredients_by_volume.png)

- **What customers buy differs from what the catalog stocks.** By purchase volume,
  16 of the top 20 ingredients are fresh whole foods (yogurt, bananas, milk, apples,
  avocados). By catalog product count, packaged goods dominate — thousands of candy
  and snack SKUs.
- **A third of apparent "variety" is packaging.** The median customer buys 45
  distinct products but only 34 distinct ingredients (1.33×) — several brands of the
  same ingredient read as variety at the product grain but not the ingredient grain.

[Ingredients report →](analysis/sequence_analysis/INGREDIENTS.md)

### Basket contents

![Basket composition by department](analysis/sequence_analysis/figures/basket_composition.png)

- A basket is small and fresh: median 8 food items, 7 distinct ingredients. Produce
  is 31% of items; fresh departments (produce, dairy, meat, deli) are over half.
- The strongest co-purchases are recipe signatures — cake flour + powdered sugar
  (85× over chance), bread flour + yeast (61×), lasagna noodles + ricotta (51×), a
  cumin/chili/paprika spice cluster — while the highest-volume pairs are just staples
  (banana + yogurt).

[Basket contents report →](analysis/sequence_analysis/BASKET_CONTENTS.md) ·
[co-occurrence report →](analysis/sequence_analysis/COOCCURRENCE.md)

### Sequences

How purchases repeat and rotate from one order to the next.

![Reorder lift by grain](analysis/sequence_analysis/figures/reorder_lift_by_level.png)

- **Reordering is a real habit at the specific-product level:** a product a customer
  bought is reordered ~29% more often than their own basket mix would produce by
  chance ([reorder probability →](analysis/sequence_analysis/REORDER_PROBABILITY.md)).
- **Within an ingredient, commitment is mild and variety-seeking is category-specific:**
  holding one product for a run before switching is only slightly above chance; yogurt
  actively alternates, and discretionary categories (ice cream, pasta) rotate most
  ([substitution →](analysis/sequence_analysis/SUBSTITUTION.md)).
- **Most named "patterns" are frequency in disguise.** Against a frequency-preserving
  null, staples, rotation, and "returns" land at or below chance; the one real signal
  is early abandonment — an ingredient tried a few times then dropped
  ([patterns →](analysis/sequence_analysis/PATTERN_ANALYSIS.md)).

| Pattern | Observed | Random baseline |
|---------|---------:|----------------:|
| Persistent staple | 9.2% | 9.2% |
| Regular rotation | 4.6% | 5.5% |
| Return after break | 58% | 69% |
| Burst then absence | 1.6% | 0.3% (5× above chance) |

- **An order-gap is not a clock:** cadence ranges from weekly to monthly (median 13
  days), so a 5-order gap spans 15–88 days depending on the customer
  ([calendar time →](analysis/sequence_analysis/CALENDAR_TIME.md)).

![Pattern gallery](analysis/figures/pattern_gallery.png)

Each row is one product for one customer (■ = purchased). Staples, rotation, bursts,
returns, and replacements are visible.

### Novelty and exploration

![Novelty decay](analysis/sequence_analysis/figures/novelty_decay.png)

- **Steady-state exploration is ~6%, not the ~22% pooled figure** — the pooled number
  is inflated by short observed histories (a first observed order is "new" by
  construction). Once a repertoire is established, about one item in fifteen is a new
  ingredient.
- The repertoire keeps growing (40 distinct ingredients by order 10, 101 by order
  100, of 542 in the catalog) but baskets don't get more varied (~8 throughout), and
  97.7% of customers explore less later than earlier.

[Novelty report →](analysis/sequence_analysis/NOVELTY.md) ·
[exploration report →](analysis/sequence_analysis/EXPLORATION.md)

### Prepared dishes

![Prepared dish types by reach](analysis/sequence_analysis/figures/prepared_topics.png)

- **60% of customers buy a prepared meal** (frozen dinners, pizza, mac & cheese,
  deli-prepared). For the typical buyer they are ~4% of items and ~30% of orders — a
  convenience, not a dietary base — and reliance does not rise with purchase volume.
- Frozen dominates (frozen_meal reaches 54k customers, then pizza, soup, mac &
  cheese). A specific prepared dish is reordered slightly more than a staple, but
  buyers rotate across prepared SKUs within a type more than they rotate staples.

[Prepared dishes report →](analysis/sequence_analysis/PREPARED_FOODS.md)

### Customers

![Customer segments](analysis/sequence_analysis/figures/customer_segments.png)

- **Descriptively:** the median customer places 10 orders over ~5 observed months, in
  baskets of ~8 items, shopping every ~13 days — every measure strongly right-skewed.
  Splitting on frequency × basket size gives four balanced segments; frequency, not
  basket size, drives order volume
  ([customer profile →](analysis/sequence_analysis/CUSTOMER_PROFILE.md)).
- **Behaviorally:** traits are stable across a customer's history (first half predicts
  second, r 0.73–0.82), but most axes (repeat rate, novelty, diversity) are largely a
  function of purchase volume. The one volume-independent trait is within-ingredient
  product-switching
  ([customer behavior →](analysis/sequence_analysis/CUSTOMER_BEHAVIOR.md)).

---

## What it might mean for meal subscriptions

Grocery patterns, offered as hypotheses rather than demonstrated subscription results:

1. Read demand at the ingredient level — product data overweights packaged variety.
2. Reordering is a real habit at the specific-product level (~29% above a frequency baseline).
3. A third of apparent variety is packaging, not diet.
4. Within-ingredient commitment is mild; variety-seeking concentrates in flavored/discretionary categories.
5. Exploration is low (~6%) and falling; the repertoire grows slowly.
6. Customer "type" is mostly purchase volume — product-switching is the exception worth segmenting on.
7. "Returns" and "rotation" track frequency; the real signal is early abandonment, a possible churn cue.
8. Order-gaps are not calendar time.
9. Prepared-meal demand is a minority, occasional behavior (60% reach, ~4% of items).

---

## Repository Structure

```
analysis/
  classification/
    food_classification.csv         # 49,688 products → ingredients (+ is_food, is_prepared_dish)
    INGREDIENT_TAXONOMY.md          # 446-ingredient recipe taxonomy
    CLASSIFICATION_ANALYSIS.md      # classification statistics
    methods_compared/               # TF-IDF vs. embeddings vs. LLM
  sequence_analysis/
    *.md                            # one report per result
    *.csv                           # aggregate summaries (no customer IDs)
    figures/                        # result figures (png/svg)
  figures/                          # pattern gallery
docs/
  PROCESSING.md                     # how the full dataset is processed within memory
  DATA_AUDIT.md                     # data quality validation
scripts/
  data_pipeline/                    # Kaggle → Parquet ingestion + audit
  classification/                   # classifiers + taxonomy corrections
  sequence_analysis/                # one script per result; analyze_reorder.py is the shared core
```

---

## Reproducing the Analysis

```bash
uv sync                                                    # dependencies
python scripts/data_pipeline/ingest_data.py                # Kaggle → data/processed/*.parquet

# classification (LLM pass ~8h; CSV already committed)
python scripts/classification/classify_fabric.py
python scripts/classification/apply_corrections.py         # taxonomy fixes (e.g. condensed_soup)
python scripts/classification/analyze_classification.py

# results — each writes its report's CSVs/figures (memory-safe, full dataset)
python scripts/sequence_analysis/analyze_reorder.py            # shared core: reorder probability + lift
python scripts/sequence_analysis/analyze_patterns.py
python scripts/sequence_analysis/analyze_novelty.py
python scripts/sequence_analysis/analyze_exploration.py
python scripts/sequence_analysis/analyze_substitution.py
python scripts/sequence_analysis/analyze_cooccurrence.py
python scripts/sequence_analysis/analyze_prepared_foods.py
python scripts/sequence_analysis/analyze_basket_contents.py
python scripts/sequence_analysis/analyze_customer_profile.py
python scripts/sequence_analysis/analyze_customer_behavior.py
python scripts/sequence_analysis/analyze_calendar_time.py
python scripts/sequence_analysis/analyze_lift_decomposition.py

# figures
python scripts/sequence_analysis/visualize_ingredient_lens.py
python scripts/sequence_analysis/visualize_audit.py
python scripts/sequence_analysis/generate_pattern_gallery.py
```

---

## References

**Dataset:** [Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (2017).
**Classification grounding:** 1,000+ recipes across diverse cuisines (knowledge-based).
**Method:** descriptive patterns are kept separate from prediction; when sequence features don't beat a baseline, that is reported rather than overfit.
