# Classification Method Comparison

Three NLP approaches were compared on the 49,688 Instacart products:

## 1. TF-IDF + Rule Refinement (`tfidf_refined.csv`)

**Method:** sklearn TfidfVectorizer with cosine similarity to 446 ingredient descriptions, followed by product-identity rule corrections.

**Strengths:**
- Better on product-type identity (cookies, yogurt, pasta shapes, filled pasta)
- Rule-based corrections handle systematic misclassifications

**Weaknesses:**
- Sparse vocabulary misses short/unusual product names
- Defaults to wrong ingredient when no match (score=0)

**Results:**
- 38,987 food items (78.5%)
- 1,537 prepared dishes
- Mean match score: 0.430

**Scripts:** `scripts/classification/classify_tfidf.py`, `scripts/classification/refine_tfidf.py`

## 2. Sentence Embeddings (`embeddings.csv`)

**Method:** all-MiniLM-L6-v2 encodes both products and ingredient descriptions, cosine similarity in embedding space.

**Strengths:**
- Better semantic understanding (frozen meals, salad dressings, ramen)
- Higher confidence scores overall

**Weaknesses:**
- Confused by flavor words (chocolate cookies → baking_chocolate; yogurt → ice_cream)
- Over-semantic on some simple product-identity cases

**Results:**
- 40,598 food items (81.7%)
- 3,259 prepared dishes
- Mean match score: 0.548

**Scripts:** `scripts/classification/classify_embeddings.py`

## 3. Fabric/LLM ✓ (Final) (`fabric_llm.csv`)

**Method:** Pipe product batches through Claude via fabric CLI with 446-ingredient taxonomy as system prompt. LLM applies recipe-grounded reasoning.

**Strengths:**
- Correct on ALL spot checks including hard cases (steak→steak, soda→soda)
- Appropriately cautious: marks uncertain cases as "unclassified" rather than guessing wrong
- Best semantic + product-identity understanding

**Weaknesses:**
- Slowest: ~5 min per 500-product batch (100 batches total)
- Occasional timeouts on large batches

**Results:**
- 38,529 food items (77.5%)
- 8,278 prepared dishes  
- 2,807 unclassified (5.6%) — LLM declining rather than guessing

**Scripts:** `scripts/classification/classify_fabric.py`, `scripts/classification/taxonomy.md`

## Spot Check Comparison (21 products)

| Method | Correct Only | Wrong |
|---|---|---|
| TF-IDF + refinement | 7 | — |
| Embeddings | 4 | — |
| Both right | 5 | — |
| Both wrong | — | 5 |

Neither TF-IDF nor embeddings alone is sufficient. Methods have **complementary strengths**: TF-IDF anchors on product-type words, embeddings capture semantic context. Both struggle with the same edge cases.

**Fabric/LLM succeeds on all spot checks** including the 5 cases where both TF-IDF and embeddings failed.

## Final Decision

**`fabric_llm.csv` is the authoritative classification** and is copied (with post-hoc
corrections) to `data/food_classification.csv`.
