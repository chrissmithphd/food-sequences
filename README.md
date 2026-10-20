# Understanding Meal Selection, Variety, and Retention

**How do customers choose foods over time — and what do repetition, variety, and novelty reveal about how they eat?**

This project studies grocery purchasing as a proxy for meal selection: Do customers repeat, rotate, or explore? What is genuine dietary variety versus brand churn? How do prepared meals fit in? The work is framed around questions a meal-subscription service would ask (menu variety, retention, familiarity vs. novelty) — grocery data can't answer those directly, but it reveals the underlying selection patterns.

**The approach:** classify 49,688 Instacart products into recipe ingredients, then analyze purchasing at four grains — exact product, recipe ingredient, ingredient category, retail aisle — and across order sequences.

---

## Dataset

**Instacart Online Grocery Shopping Dataset 2017** — 206,000 customers, 3.4M orders, 49,688 products, sequential purchase history per customer. No absolute dates; inter-order gaps are capped at 30 days.

**Classification:** all 49,688 products mapped to a 446-ingredient recipe taxonomy (632 labels emerged) using an LLM (recipe-grounded reasoning), chosen over TF-IDF and embedding baselines. [Classification analysis →](analysis/classification/CLASSIFICATION_ANALYSIS.md) · [method comparison →](analysis/classification/methods_compared/README.md)

- 38,529 food items (77.5%); 2,807 unclassified (5.6%, the LLM declined low-confidence guesses)
- Prepared *dishes* are defined by the taxonomy's "Prepared Dishes & Meals" section (17 meal types), **not** the raw per-product `is_prepared_dish` flag, which proved noisy (it also marked snacks, drinks, and condiments). See [prepared dishes](analysis/sequence_analysis/PREPARED_FOODS.md).

> Memory note: the full purchase table is ~30M rows; every analysis streams it in customer-id bursts to stay within memory. See [docs/PROCESSING.md](docs/PROCESSING.md).

---

## Results

Each result below is a standalone analysis with its own report; the README carries the headline and a figure.

### 1. Ingredients & Categories — the lens that changes the picture

A product ID says "Chobani Blueberry Greek 5.3oz"; an ingredient says "yogurt." Analyzing at the ingredient level surfaces two findings invisible at the product grain.

![Ingredients by purchase volume](analysis/sequence_analysis/figures/ingredients_by_volume.png)

- **The cart is deep on fresh; the catalog is wide on packaged.** Ranked by purchase volume, **16 of the top 20 ingredients are fresh whole foods** (yogurt, bananas, milk, apples, avocados). Ranked by catalog product count, snacks and packaged goods dominate. A meal service reading product-level data would misread demand.
- **A third of "variety" is packaging.** The median customer buys **45 distinct products but only 34 ingredients** (1.33×). Product churn overstates real dietary variety.
- **"Category loyalty" is mostly arithmetic.** A category recurs in the next order 59% of the time vs. 29% for an exact product — but against a chance baseline the *lift* inverts: product **1.29×** (real habit) vs. category **1.04×** (barely above chance; broad buckets refill because they hold many products).

[Ingredients & categories report →](analysis/sequence_analysis/INGREDIENTS.md)

### 2. Basket Contents — small, fresh, occasionally prepared

![Basket composition by department](analysis/sequence_analysis/figures/basket_composition.png)

- **A basket is small and fresh:** median **8 food items**, **7 distinct ingredients**. Produce alone is 31% of items; fresh departments (produce, dairy, meat, deli) are over half.
- **Prepared meals ride along, they don't dominate:** 3.9% of items, and **one basket in five (20.8%)** contains a prepared dish.
- **What goes together is recipe signatures.** The highest-*lift* co-purchases are intact recipes — cake flour + powdered sugar (85×), bread flour + yeast (61×), lasagna noodles + ricotta (51×), a cumin/chili/paprika spice cluster. The highest-*volume* pairs are just staples (banana + yogurt, 354k baskets).

[Basket contents report →](analysis/sequence_analysis/BASKET_CONTENTS.md) · [co-occurrence report →](analysis/sequence_analysis/COOCCURRENCE.md)

### 3. Sequences — how choices repeat over orders

![Reorder lift by level](analysis/sequence_analysis/figures/reorder_lift_by_level.png)

- **Real loyalty is to specific products.** Exact-product repurchase is 29% above chance; the habit lives at the SKU, not the category ([reorder probability →](analysis/sequence_analysis/REORDER_PROBABILITY.md)).
- **Within an ingredient, commitment is mild and variety-seeking is category-specific.** Holding one product for a run before switching is only slightly above chance (lift 1.04–1.09); yogurt actively *alternates* (0.96), and discretionary categories (ice cream, pasta) have the lowest stay rates ([substitution →](analysis/sequence_analysis/SUBSTITUTION.md)).
- **Most "patterns" are frequency in disguise.** Against a frequency-preserving null, staples, rotation, and "returns" occur at or *below* chance; the one real signal is **early abandonment** — an ingredient tried a few times then dropped (5× above chance) ([patterns →](analysis/sequence_analysis/PATTERN_ANALYSIS.md)).

| Pattern | Observed | Random baseline | Verdict |
|---------|---------:|----------------:|---------|
| Persistent staple | 9.2% | 9.2% | at chance |
| Regular rotation | 4.6% | 5.5% | below chance |
| Return after break | 58% | 69% | below chance |
| Burst then absence | 1.6% | 0.3% | **5× above chance** |

- **An order-gap is not a clock.** Cadence ranges from weekly to monthly (median 13 days), so a 5-order gap spans 15–88 days depending on the customer; sequence patterns must not be read as calendar behavior ([calendar time →](analysis/sequence_analysis/CALENDAR_TIME.md)).

![Pattern Gallery](analysis/figures/pattern_gallery.png)

Each row is one product for one customer. ■ = purchased, · = not. Staples, rotation, bursts, returns, and replacements are all visible.

### 4. Novelty & Exploration — a falling rate over a growing repertoire

![Novelty decay](analysis/sequence_analysis/figures/novelty_decay.png)

- **Steady-state exploration is ~6%, not the ~22% raw figure** — the pooled number is inflated by short observed histories (a first observed order is 100% "new" by construction). Once a repertoire is established, about one item in fifteen is a genuinely new ingredient.
- **The repertoire never saturates but baskets don't get more varied:** the average customer has bought 40 distinct ingredients by order 10, 101 by order 100 (of 542 in the catalog), yet basket diversity stays flat at ~8. Growth is accumulation, and **97.7% of customers explore less later than earlier.**

[Novelty report →](analysis/sequence_analysis/NOVELTY.md) · [exploration report →](analysis/sequence_analysis/EXPLORATION.md)

### 5. Prepared Dishes — a minority, occasional convenience

![Prepared dish types by reach](analysis/sequence_analysis/figures/prepared_topics.png)

- **59.6% of customers buy a prepared meal** (frozen dinners, pizza, mac & cheese, deli-prepared) — a majority, but far from the inflated 90% you get if snacks count. For the typical buyer they're **~4% of items and ~30% of orders**: a convenience, not a dietary base. Reliance does *not* rise with purchase volume.
- **Frozen dominates** (frozen_meal reaches 54k customers, then pizza, soup, mac & cheese). A specific prepared dish is reordered slightly *more* than a staple (1.44× vs 1.29× lift), but buyers **rotate across** prepared SKUs within a type more than they rotate staples.

[Prepared dishes report →](analysis/sequence_analysis/PREPARED_FOODS.md)

### 6. Customers — who they are, and whether "type" is real

![Customer segments](analysis/sequence_analysis/figures/customer_segments.png)

- **Descriptively:** the median customer places 10 orders over ~5 observed months, in baskets of ~8 items, shopping every ~13 days. Splitting on frequency × basket size gives four balanced segments; frequency, not basket size, drives order volume ([customer profile →](analysis/sequence_analysis/CUSTOMER_PROFILE.md)).
- **Behaviorally:** traits are stable across a customer's history (first-half predicts second-half, r 0.73–0.82), but most axes (repeat rate, novelty, diversity) are **mostly purchase volume** (|r| 0.5–0.6). The one volume-independent trait is within-ingredient product-switching — the cleanest axis for segmentation ([customer behavior →](analysis/sequence_analysis/CUSTOMER_BEHAVIOR.md)).

---

## What This Might Mean for Meal Subscriptions

These are grocery patterns; whether they generalize is an open question. They suggest:

1. **Read demand at the ingredient level** — product-level data overweights packaged variety; fresh staples are what customers actually buy.
2. **Loyalty attaches to specific items,** not food families — the only grain that reorders well above chance is the exact product.
3. **A third of apparent variety is packaging,** not diet.
4. **Within-ingredient commitment is mild; variety-seeking is category-specific** (flavored/discretionary categories rotate; staples don't).
5. **Exploration is low and falling** (~6% steady state), while the repertoire slowly accumulates — expect established subscribers to explore sparingly.
6. **Customer "type" is mostly volume,** except product-switching — the trait worth segmenting on.
7. **"Returns" and "rotation" track frequency, not behavior;** the real signal is early abandonment — a possible churn cue.
8. **Order-gaps are not time** — cadence varies weekly-to-monthly; don't read sequence gaps as a calendar.
9. **Prepared-meal demand is a minority, occasional behavior** (60% reach, ~4% of items) — a prepared-only service targets the heavy tail, not the median grocery shopper.

---

## Repository Structure

```
analysis/
  classification/
    food_classification.csv         # 49,688 products → ingredients (+ is_food, is_prepared_dish)
    INGREDIENT_TAXONOMY.md          # 446-ingredient recipe taxonomy
    CLASSIFICATION_ANALYSIS.md      # Classification statistics ← start here
    methods_compared/               # TF-IDF vs. embeddings vs. LLM
  sequence_analysis/                # All results below live here
    *.md                            # One report per result (reorder, novelty, patterns,
                                    #   prepared, substitution, co-occurrence, exploration,
                                    #   customer profile/behavior, calendar, ingredients, basket)
    *.csv                           # Aggregate summaries (no customer IDs)
    figures/                        # Result figures (png/svg)
  figures/                          # Pattern gallery
docs/
  PROCESSING.md                     # How the full dataset is processed within memory
  DATA_AUDIT.md                     # Data quality validation
scripts/
  data_pipeline/                    # Kaggle → Parquet ingestion + audit
  classification/                   # TF-IDF, embeddings, LLM classifiers + corrections
  sequence_analysis/                # One script per result; analyze_reorder.py is the shared core
```

---

## Reproducing the Analysis

```bash
uv sync                                                   # dependencies

# 1. Data (requires Kaggle credentials) → data/processed/*.parquet
python scripts/data_pipeline/ingest_data.py

# 2. Classification (LLM pass is ~8h; CSV is already committed)
python scripts/classification/classify_fabric.py         # LLM classification
python scripts/classification/apply_corrections.py        # taxonomy-driven fixes (e.g. condensed_soup)
python scripts/classification/analyze_classification.py   # stats + figures

# 3. Sequence analysis — each writes its report's CSVs/figures (memory-safe, full dataset)
python scripts/sequence_analysis/analyze_reorder.py           # reorder probability + lift (shared core)
python scripts/sequence_analysis/analyze_patterns.py          # pattern classification + null baseline
python scripts/sequence_analysis/analyze_novelty.py           # novelty / repertoire
python scripts/sequence_analysis/analyze_exploration.py       # repertoire growth over lifetime
python scripts/sequence_analysis/analyze_substitution.py      # within-ingredient commit vs. rotate
python scripts/sequence_analysis/analyze_cooccurrence.py      # within-order co-occurrence
python scripts/sequence_analysis/analyze_prepared_foods.py    # prepared dishes: reach, topics, reorder
python scripts/sequence_analysis/analyze_basket_contents.py   # basket size + composition
python scripts/sequence_analysis/analyze_customer_profile.py  # tenure, orders, basket, segments
python scripts/sequence_analysis/analyze_customer_behavior.py # behavioral traits + stability
python scripts/sequence_analysis/analyze_calendar_time.py     # order-gap vs. day-gap
python scripts/sequence_analysis/analyze_lift_decomposition.py

# figures
python scripts/sequence_analysis/visualize_ingredient_lens.py
python scripts/sequence_analysis/visualize_audit.py
python scripts/sequence_analysis/generate_pattern_gallery.py
```

---

## References

**Dataset:** [Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (2017)
**Classification grounding:** 1,000+ recipes across diverse cuisines (knowledge-based).
**Methodological note:** descriptive patterns are separated from prediction; when sequence features don't beat a baseline, that is reported rather than overfit.
