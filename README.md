# Understanding Meal Selection, Variety, and Retention

**How do customers choose meals over time? What patterns of repetition, rotation, and novelty explain satisfaction and longevity?**

This project grew out of an effort to understand meal subscriptions — specifically, how services might better understand customer preferences, fatigue, novelty-seeking, and retention. Before we can analyze meal sequences or predict satisfaction, we need to represent what meals contain in a way that supports comparison and similarity analysis.

The work here uses grocery purchase data to build that foundation: classifying products into recipe-oriented ingredients, analyzing how people select and repeat foods, and preparing to study meal composition and variety.

---

## The Meal Subscription Challenge

Meal delivery services face a common challenge: **keeping customers engaged over time**.

Customers subscribe for convenience, variety, and quality. But after weeks or months, they may experience:
- **Meal fatigue:** ordering the same types of meals repeatedly
- **Lack of novelty:** not discovering new favorites
- **Insufficient variety:** menu doesn't match their preference for rotation vs. repetition

Understanding which customers prefer **repetition** (ordering the same few meals reliably) vs. **exploration** (trying new meals frequently) vs. **rotation** (cycling through a stable set) could inform menu curation, recommendations, and retention strategies.

But to study meal sequences, we need:
1. A way to represent what meals contain (ingredients, flavors, cuisines)
2. A taxonomy that preserves distinctions that matter to customers
3. Methods for measuring meal similarity, variety, and novelty

This project tackles the first two using grocery purchase data as a proxy for meal selection behavior.

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

## Understanding Food Selection Patterns

Using the Instacart dataset with LLM-based ingredient classifications, we analyzed how customers select and reorder foods at multiple levels: exact products, recipe ingredients, ingredient categories, and retail aisles.

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

### Most Variety is Brand Switching, Not Novel Foods

When we track what's actually *new* in each order:

![Basket Composition](analysis/sequence_analysis/figures/basket_composition.png)

- **64% Familiar products** (exact repeats)
- **14% Familiar ingredients, new products** (brand switching)
- **22% New ingredients** (genuinely novel foods)

**Key insight:** 78% of purchases are familiar ingredients. Customers want variety in *presentation*, not dietary overhaul. Different brands, sizes, and preparations of the same ingredient feel varied.

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

Real customer purchasing patterns showing product repetition vs brand switching:

![Product Repetition](analysis/sequence_analysis/figures/product_repetition_examples.png)

![Brand Switching](analysis/sequence_analysis/figures/brand_switching_examples.png)

[Detailed sequence analysis with methodology, statistics, and meal subscription implications →](analysis/sequence_analysis/SEQUENCE_ANALYSIS.md)

---

## Implications for Meal Subscriptions

### Key Insights

**1. Variety doesn't require novelty:** Customers are loyal to ingredient categories but flexible on products. Rotating presentations of familiar ingredients (chicken parmesan → chicken marsala) feels varied without dietary risk.

**2. Brand switching is "safe variety":** 14% of purchases are familiar ingredients in different products. Customers want the same food prepared differently.

**3. Temporary absences aren't churn:** 31% of ingredient patterns show long gaps followed by returns. Don't over-react to pauses in ordering.

**4. Staples are rare:** Only 10% of ingredients are persistent staples. Most customers explore, rotate, and return rather than settling into fixed routines.

**5. Prepared foods need more rotation:** Prepared dishes show lower immediate reordering (31% vs 40%) than base ingredients. Menu variety matters more for complete meals than pantry staples.

### For Menu Design

- **Emphasize familiar ingredients in new combinations** over genuinely exotic foods
- **Plan for rotation:** Bring back popular dishes after gaps, don't force immediate repeats
- **Maintain category consistency:** Always offer options in core categories customers prefer
- **Accommodate irregular patterns:** Don't force fixed schedules or predictable ordering

### Current Foundation

✓ **49,688 products classified** into recipe-oriented ingredients  
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
