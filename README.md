# What Grocery Purchases Reveal About Food Choice

3.4 million Instacart orders from 206,000 customers, with 49,688 products classified
into 543 recipe-level ingredients. This project analyzes what people buy, what they
combine, what they repeat, and how their choices vary — at the level of *food*, not
brand.

Why ingredients instead of products? "Organic 2% Milk," "Whole Milk," and a
store-brand gallon all map to `milk`. "Chobani Blueberry" and "Fage Plain" both map
to `yogurt`. An ingredient collapses 18 products (banana) to 1,177 (yogurt), stripping
away brand, size, and flavor to reveal what customers actually eat.
([Classification methodology →](docs/FOOD_CLASSIFICATION.md))

---

## What customers buy vs. what stores stock

### [Ingredients →](analysis/ingredients/)

![What customers buy, by ingredient](analysis/figures/ingredients_by_volume.png)

![What stores stock, by ingredient](analysis/figures/stores_stock.png)

Fresh foods — produce, dairy, meat — are **57% of what customers buy but only 25% of
the products the catalog offers**. Packaged foods are the opposite: 45% of the catalog,
25% of purchases. The catalog is wide where branding differentiates (1,212 candy
products, 939 granola bars); the cart is deep where the food itself is the product
(18 banana SKUs account for 3% of all purchases).

Only **19% of products capture 80% of purchase volume.** Banana needs 2 products to
reach 80% of its sales; yogurt needs 190 of 1,177. One third of the Instacart food
catalog is labeled organic, accounting for 33.5% of food purchases — far above the
~6% US grocery average, reflecting this platform's customer base.

## What customers buy together

### [Basket contents →](analysis/basket/)

![Support vs lift](analysis/figures/cooccurrence_support_lift.png)

The median basket is 8 food items spanning 7 distinct ingredients. Two kinds of
ingredient associations emerge. **High-support pairs** — banana + yogurt (354k orders),
milk + yogurt (320k) — are staples that fill most carts, barely above chance. **High-
lift pairs** are ingredients that rarely appear alone but almost always appear together:
cake flour + powdered sugar (85×), bread flour + yeast (61×), lasagna noodles + ricotta
(51×). These are co-purchasing signatures — baking projects, spice blends, specific
dishes.

Lift measures how much more often two ingredients co-occur than their individual
popularity would predict. A lift of 85× means the pair appears 85 times more often
than independence. Three-ingredient combinations surface recognizable cooking contexts:
fresh herbs + garlic + onion (28k baskets, 12× lift), cucumber + lettuce + tomato
(salad), avocado + garlic + onion (guacamole). These are co-purchasing patterns, not
confirmed recipes.

## What customers buy again

### [Sequences →](analysis/sequences/)

![Purchase history heatmaps](analysis/figures/purchase_history_heatmap.png)

A specific product recurs in the next order **28% more often** than a
frequency-preserving shuffle of the same customer's baskets (lift 1.28×). The excess
shrinks as the grain broadens — at the category level it's 4%, mostly arithmetic.
Purchase runs are slightly longer than shuffled (5–10%), and repurchase timing is
**bursty, not periodic** — gap CV of 1.41 across ingredients, well above random.

When properly scored against both present and absent ingredients, **overall purchase
frequency is the best simple predictor** of the next order. Adding recency makes
predictions worse — the signal is in the long-run rate, not the recent sequence.
Most named "patterns" (staples, returns, rotation) match their random-baseline rates.
The exception is burst-then-absence: ingredients bought in an early cluster then
absent for the rest of the observed window (3.4% of ingredient histories vs 0.3%
random).

## How customers introduce variety

### [Novelty & exploration →](analysis/novelty/)

![Novelty by category](analysis/figures/novelty_by_category.png)

A new yogurt flavor and a first purchase of lentils are different kinds of novelty. The
blue bars are **new ingredients** (never before in this customer's observed history);
orange bars are **new products for a familiar ingredient** (a different brand or
flavor). Spices and baking have 75–81% novelty because they're bought rarely — each
purchase is likely the first observed. Dairy and fruit have 30–33% because staples
repeat almost every order.

The pooled new-ingredient rate (~22%) is inflated by truncation — the dataset starts
mid-history, so early orders are mechanically "new." By order 50+, the rate is ~6%
and still declining. Discoveries tilt toward the catalog's long tail: the top 20
ingredients are 37% of purchases but only 24% of first-time discoveries. Customer
exploration rates vary widely (p10 = 6%, p90 = 41%) even at comparable history
positions.

## Where prepared dishes fit

### [Prepared dishes →](analysis/prepared/)

![Prepared items per basket](analysis/figures/prepared_basket_distribution.png)

**79% of baskets contain zero prepared items.** 60% of customers buy a prepared dish
at some point, but it's typically 4% of their food items, in about 30% of their
orders. Frozen meals (54k customers), pizza (42k), and soup (41k) dominate. Chicken
nuggets have the most concentrated demand: 1,055 purchases per product from just 66
catalog items.

Baskets with prepared food are larger (median 12 vs 7 items), but the composition of
the rest of the basket is nearly identical — produce, dairy, and fruit shares within
±0.5%. Cross-sectional comparisons cannot establish whether prepared items replace or
supplement home cooking.

## How customers differ

### [Customers →](analysis/customers/)

![Behavior correlations](analysis/figures/behavior_correlations.png)

Most apparent behavioral "types" are really **volume differences**. Repeat rate,
novelty rate, and diversity correlate r > 0.9 with each other and ±0.5–0.6 with order
count. Two dimensions survive after volume is removed: **product switching** (whether
a customer rotates among products within an ingredient, r = −0.04 with volume) and
**prepared-food share** (r = −0.08).

Between-customer and within-customer variation are comparable: the intraclass
correlation is 0.60 for basket size and 0.53 for prepared-food share. A customer who
averages 8 items per basket routinely places orders ranging from 3 to 15. Customer
differences are real but modest — order-to-order variation accounts for nearly half of
the total.

---

## What this suggests about food selection

These are descriptive patterns from a grocery delivery platform, not demonstrated
results about meal subscriptions, cooking behavior, or dietary preferences.

1. **Read demand at the ingredient level.** Product data overstates variety — about a
   quarter of apparent product diversity is the same food in different packaging.
2. **Frequency is the dominant signal.** A customer's long-run purchase rate for each
   ingredient is a well-calibrated predictor. Sequence, recency, and named patterns
   add little beyond what frequency already explains.
3. **Prepared-meal demand is occasional and minority.** 60% of customers participate,
   but baskets are overwhelmingly raw ingredients and staples.

---

## Dataset and methodology

**Instacart Online Grocery Shopping Dataset 2017** — 206k customers, 3.4M orders,
49,688 products. Public on Kaggle:
[source](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis).
Anonymized integer IDs; no absolute dates; inter-order gaps capped at 30 days.

**Classification:** 49,688 products → 543 ingredients via LLM classification
(Claude, ~8h). A deterministic lookup table
([`product_ingredient_lookup.csv`](analysis/classification/product_ingredient_lookup.csv))
reproduces the mapping without an LLM.
[Taxonomy →](analysis/classification/INGREDIENT_TAXONOMY.md) ·
[Method →](docs/FOOD_CLASSIFICATION.md)

**Key limitations:** No absolute timestamps or seasonal patterns. 30-day cap on
inter-order gaps. Test-set orders lack item labels. The dataset begins mid-history
for each customer. Instacart's customer base skews urban and convenience-oriented;
organic penetration (33.5%) and plant-milk share (38% of milk purchases) are
platform-specific, not nationally representative.

## Repository structure

```
analysis/
  classification/   # ingredient classification + taxonomy + lookup table
  ingredients/      # demand vs assortment, concentration, organic penetration
  basket/           # basket composition, co-occurrence, triplets
  sequences/        # reorder, patterns, substitution, prediction
  novelty/          # novelty classification, repertoire growth, categories
  prepared/         # reach, dish types, basket composition
  customers/        # profiles, segments, behavioral correlations
  figures/          # all figures (PNG/SVG)
scripts/
  config.py         # shared paths and schemas
  data_pipeline/    # Kaggle → Parquet ingestion + audit
  classification/   # LLM classifier, lookup table, taxonomy corrections
  sequence_analysis/# one script per analysis; analyze_reorder.py is the shared core
```

## Reproducing

```bash
uv sync
python scripts/data_pipeline/ingest_data.py
python scripts/classification/classify_fabric.py     # ~8h; CSV already committed
python scripts/classification/apply_corrections.py
for s in analyze_reorder analyze_patterns analyze_substitution analyze_calendar_time \
         analyze_lift_decomposition analyze_novelty analyze_exploration \
         analyze_basket_contents analyze_prepared_foods \
         analyze_ingredient_lens analyze_customer_profile analyze_customer_behavior \
         analyze_sequences analyze_novelty_extended; do
  python scripts/sequence_analysis/$s.py
done
for v in visualize_ingredient_lens visualize_basket visualize_sequences \
         visualize_novelty visualize_prepared visualize_customers visualize_audit \
         generate_pattern_gallery; do
  python scripts/sequence_analysis/$v.py
done
```
