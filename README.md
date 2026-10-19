# Understanding Meal Selection, Variety, and Retention

**How do customers choose meals over time? What patterns of repetition, rotation, and novelty explain satisfaction and longevity?**

This project explores questions relevant to meal subscriptions: How do customers choose foods over time? Do they prefer repetition, rotation, or exploration? What drives variety-seeking versus loyalty? When do they return to familiar foods after trying something new?

To study these questions at the *ingredient* level (not just product brands), we need to classify products into recipe-oriented categories. That classification enables analysis of whether customers are changing brands, substituting ingredients, or genuinely shifting food preferences.

**The approach:** Use grocery purchase data (Instacart) as a proxy for meal selection patterns. Classify 49,688 products into recipe ingredients using LLM-based taxonomy. Analyze purchasing sequences at multiple levels: exact products, recipe ingredients, ingredient categories, and retail aisles.

**The motivation:** Meal subscription services likely face questions about menu variety, customer retention, and balancing familiarity with novelty. Grocery data won't answer those questions directly, but it can reveal patterns in how people select and repeat foods over time.

---

## Dataset and Approach

**Instacart Online Grocery Shopping Dataset 2017:**
- 206,000 customers
- 3.4 million orders
- 49,688 unique products
- Sequential purchase history per customer

**Why grocery data?** While not identical to meal subscriptions, grocery purchases reveal selection patterns: repeat staples, rotated items, one-time experiments, and long gaps before returns. These patterns mirror meal subscription behavior.

**The classification challenge:** To analyze food at the *ingredient* level rather than the *product* level, we need to map products to recipe-oriented categories. "Organic 2% Milk" and "Whole Milk" should both be "milk" — brand and fat percentage don't matter for recipe comparisons. But "Yogurt" and "Ice Cream" should be distinct — recipes don't substitute one for the other.

---

## Classification: Products → Recipe Ingredients

We classified all 49,688 products into a **446-ingredient recipe taxonomy** grounded in how recipes actually use ingredients.

### Taxonomy Principles

**Recipe equivalence:** If recipes treat variations interchangeably, they're the same ingredient.
- All milk types (whole, 2%, skim, organic) → `milk`
- All pasta shapes (spaghetti, penne, rigatoni) → `pasta`

**Meaningful distinctions:** If recipes distinguish them, so do we.
- Pasta vs. filled pasta (ravioli) → different ingredients
- Fresh herbs vs. dried herbs → different ingredients
- Yogurt vs. ice cream → different ingredients

**Prepared dishes separate from base ingredients:**
- "Frozen Mac and Cheese" → `mac_and_cheese` (complete dish), not `pasta` or `cheese`
- "Canned Chicken Noodle Soup" → `soup`, not `chicken` or `noodles`

### Classification Methods

We compared three approaches:

| Method | How It Works | Strengths | Weaknesses |
|--------|--------------|-----------|------------|
| **TF-IDF + rules** | Cosine similarity to ingredient descriptions, then product-identity corrections | Good on product-type words (cookies, yogurt, pasta) | Misses short/unusual names |
| **Sentence embeddings** | all-MiniLM-L6-v2 semantic matching | Better semantic understanding (frozen meals, dressings) | Confused by flavor words |
| **LLM (Claude)** ✓ | Recipe-grounded reasoning via fabric CLI | **100% on spot checks**, combines semantic + product-identity | Slow (~8 hours for full dataset) |

**Final result:** 49,688 products classified using the LLM approach. [See detailed method comparison →](analysis/classification/methods_compared/README.md)

### Classification Results

- **38,529 food items** (77.5%)
- **8,278 prepared dishes** (frozen meals, meal kits, canned soups)
- **2,807 unclassified** (5.6%) — LLM declined to guess rather than forcing low-confidence assignments
- **Top 25 ingredients** represent 41% of all products
- **632 unique ingredients** used (vs. 446 defined — LLM introduced additional distinctions)

**Example classifications:**
- "Chocolate Sandwich Cookies" → `cookies` ✓
- "Light Strawberry Blueberry Yogurt" → `yogurt` ✓ (not `strawberry`)
- "Smart Ones Mini Rigatoni" → `frozen_meal` ✓ (not `pasta`)
- "Organic Spaghetti" → `pasta` ✓
- "T Bone Steak" → `steak` ✓

[Full classification analysis with statistics, distribution, and examples →](analysis/classification/CLASSIFICATION_ANALYSIS.md)

---

## The Ingredient Lens

The whole point of this project is to stop analyzing *products* and start analyzing *ingredients*. A product ID tells you someone bought "Chobani Blueberry Greek 5.3oz." An ingredient tells you they bought yogurt. Recipes, meals, and preferences live at the ingredient level — so that is where we look. Two findings only become visible once you apply this lens.

### What Customers Buy ≠ What the Catalog Stocks

Counting *products*, the catalog is dominated by packaged goods — thousands of candy, vitamin, and cracker SKUs. That tells you how sellers stock shelves, not what people eat. Re-rank by **actual purchase volume at the ingredient level** and the picture inverts:

![What customers buy by ingredient](analysis/sequence_analysis/figures/ingredients_by_volume.png)

Sixteen of the top twenty ingredients by volume are fresh, whole foods — yogurt, bananas, milk, apples, avocados, onions, tomatoes, spinach. Only granola bars, crackers, ice cream, and cereal represent packaged goods. The catalog is wide on packaged variety; the cart is deep on fresh staples. **You cannot see this without collapsing brands into ingredients** — at the product level, no single banana SKU outranks the sea of snack brands.

### A Third of "Variety" Is Just the Same Ingredient in a Different Package

The median customer buys **45 distinct products but only 34 distinct ingredients** — a 1.33× brand multiplier. A quarter of their apparent product variety dissolves the moment you look at ingredients:

![Brand multiplier distribution](analysis/sequence_analysis/figures/brand_multiplier.png)

Someone cycling through four yogurt brands and three kinds of milk looks like an explorer in product data and a creature of habit in ingredient data. The ingredient lens separates genuine dietary variety from packaging churn — a distinction product IDs physically cannot express.

---

## Understanding Food Selection Patterns

With that lens in place, we analyzed how customers select and reorder foods at multiple levels: exact products, recipe ingredients, ingredient categories, and retail aisles.

### Loyalty at the Category Level, Variety at the Product Level

Customers are remarkably consistent about food *categories* but highly variable about specific *products*:

| Level | Immediate Reorders | Delayed Reorders | Median Gap |
|-------|-------------------|------------------|------------|
| **Category** (e.g., DAIRY) | 73% | 27% | 1 order |
| **Ingredient** (e.g., milk) | 49% | 51% | 2 orders |
| **Product** (e.g., Organic 2% Milk) | 45% | 55% | 2 orders |

![Reorder Comparison](analysis/sequence_analysis/figures/reorder_comparison.png)

**What this reveals:** Customers stick to food families (if they buy dairy, they keep buying dairy) but rotate within categories (milk → yogurt → cheese) and switch brands frequently.

The gap between ingredient-level (49%) and product-level (45%) immediate reorders represents pure brand/variant switching while maintaining ingredient loyalty.

### Variety Comes More from New Ingredients Than Brand Switching

When we track what's actually *new* in each order (item-weighted across 30M purchases):

![Basket Composition](analysis/sequence_analysis/figures/basket_composition.png)

- **64% Familiar products** (exact repeats)
- **22% New ingredients** (genuinely novel foods - never purchased this ingredient before)
- **14% Familiar ingredients, new products** (brand switching within known ingredients)

**Key insight:** Novel ingredients (22%) drive more variety than brand switching (14%). Customers are trying genuinely new foods more often than they're just changing brands of familiar foods.

**Item-weighted vs customer-weighted:** These percentages reflect total volume (item-weighted). If we weight each customer equally instead (customer-weighted), novel ingredients rise to 34% - individual customers explore more than heavy buyers do, but heavy buyers stick to familiar products and dominate the volume.

### Patterns: Returns Are More Common Than Staples

Analyzing 3.4M user-ingredient pairs with 2+ purchases:

![Pattern Prevalence](analysis/sequence_analysis/figures/pattern_prevalence.png)

| Pattern | Percentage |
|---------|------------|
| Irregular/Mixed | 50% |
| **Return after Break** (gap 5+ orders, then resume) | **31%** |
| Persistent Staple (bought in >50% of orders) | 10% |
| Regular Rotation (consistent 2-5 order gaps) | 7% |
| Burst then Absence | 2% |

**Key insight:** True staples are rare (10%). Returns after breaks (31%) are 3× more common. Customers don't settle into fixed routines — they explore, pause, and return.

### Prepared Foods Show Higher Rotation

![Prepared vs Base](analysis/sequence_analysis/figures/prepared_vs_base.png)

| Group | Immediate Reorders | Delayed Reorders |
|-------|-------------------|------------------|
| **Prepared dishes** | 31% | 69% |
| **Base ingredients** | 40% | 60% |

Prepared dishes have lower immediate reorder rates than staples like milk or eggs. Customers want more variety in "what's for dinner" than in pantry staples.

### Example Sequences

Real customer purchasing patterns across order histories:

![Pattern Gallery](analysis/figures/pattern_gallery.png)

Each row is one product for one customer. ■ = purchased, · = not purchased. Patterns reveal staples (frequent consecutive purchases), rotation (consistent gaps), bursts (early clustering), returns (long gaps then resumption), and replacements (switching to different products).

[Detailed sequence analysis with methodology, statistics, and meal subscription implications →](analysis/sequence_analysis/SEQUENCE_ANALYSIS.md)

---

## What This Might Mean for Meal Subscriptions

These are patterns in grocery purchasing. Whether they generalize to meal subscriptions is an open question, but they suggest some possibilities:

**1. The ingredient lens changes the headline:** Ranked by catalog product count, snacks and packaged goods dominate; ranked by what customers actually buy, fresh produce and dairy dominate. A meal service reading product-level data would badly misread demand. Ingredient-level volume is the signal that matters.

**2. Repetition dominates, but exploration beats brand-switching:** 64% of purchases are exact product repeats. Within the remaining 36%, genuinely new ingredients (22%) outnumber brand switches within a known ingredient (14%). When customers reach past their staples, they tend to try new foods rather than new brands of familiar foods.

**3. A third of "variety" is packaging, not diet:** The median customer touches 45 products but only 34 ingredients (1.33×). Product-level churn overstates real dietary variety — a correction only the ingredient lens can make.

**4. Returns after breaks are common:** 31% of ingredient patterns show long gaps (5+ orders) followed by returns. Only 10% are persistent staples. If meal subscriptions see similar patterns, temporary pauses might not signal churn.

**5. Prepared foods show higher rotation:** Prepared dishes have lower immediate reordering (31% vs 40%) than base ingredients like milk. This could mean customers want more variety in "what's for dinner" than in pantry staples.

**6. Most patterns are irregular:** 50% don't fit clean categories (staples, rotation, bursts). Customers explore, pause, and return unpredictably rather than following simple routines.

### Current Foundation

✓ **49,688 products classified** into recipe-oriented ingredients  
✓ **Ingredient-lens views** (purchase volume vs catalog count, brand multiplier)  
✓ **Multi-level sequence analysis** (product, ingredient, category, aisle)  
✓ **Basket composition** (familiar vs novel breakdown)  
✓ **Pattern classification** (staples, rotation, returns, irregular)  
✓ **Prepared food comparison** (prepared dishes vs base ingredients)

### Future Work

- Ingredient co-occurrence analysis (which ingredients appear together?)
- Recipe decomposition for prepared foods (what's actually *in* a frozen meal?)
- Customer segmentation (repeaters vs rotators vs explorers)
- Temporal patterns (weekly cycles, seasonality)
- Integration with actual meal subscription data and retention outcomes

---

## Repository Structure

```
analysis/
  classification/
    food_classification.csv              # Final ingredient classification (49,688 products)
    INGREDIENT_TAXONOMY.md               # 446-ingredient taxonomy
    CLASSIFICATION_ANALYSIS.md           # Detailed statistical analysis ← Start here
    methods_compared/                    # TF-IDF vs. embeddings vs. LLM
    archived/                            # Historical work
  
  figures/                               # Reorder analysis visualizations
  outputs/                               # Other analysis outputs

scripts/
  data_pipeline/                         # Kaggle → Parquet ingestion
  classification/                        # TF-IDF, embeddings, LLM classifiers
  sequence_analysis/                     # Reorder and pattern analysis

docs/
  CLASSIFICATION_METHODOLOGY.md          # Recipe-to-ingredient reasoning
  DATA_AUDIT.md                         # Data quality validation
```

---

## Reproducing the Analysis

**Install dependencies:**
```bash
uv sync
```

**Download Instacart dataset:**
```bash
# Requires Kaggle API credentials
python scripts/data_pipeline/ingest_data.py
```

**Run classification analysis:**
```bash
# Generate statistics and figures
python scripts/classification/analyze_classification.py
```

**Reproduce classifications** (requires ~8 hours):
```bash
# TF-IDF approach
python scripts/classification/classify_tfidf.py
python scripts/classification/refine_tfidf.py

# Embeddings approach
python scripts/classification/classify_embeddings.py

# LLM approach (requires fabric CLI)
python scripts/classification/classify_fabric.py
```

---

## References and Context

**Original research question:** How customers repeat, rotate, and return to foods in grocery purchases.

**Extension for meal subscriptions:** Understanding meal composition and variety patterns that may inform retention strategies.

**Dataset:** [Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (2017)

**Classification grounding:** 1,000+ recipes across diverse cuisines (knowledge-based, not extracted from a specific recipe corpus).

**Methodological note:** This analysis separates descriptive patterns from predictive modeling. When sequence features don't outperform baselines, we report that honestly rather than overfitting.

---

*For detailed classification statistics, taxonomy analysis, and method comparisons, see [CLASSIFICATION_ANALYSIS.md](analysis/classification/CLASSIFICATION_ANALYSIS.md).*
