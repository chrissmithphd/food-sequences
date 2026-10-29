# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**food-sequences** is a data science portfolio project studying food selection
patterns in sequential purchases using the Instacart Online Grocery Shopping Dataset
2017. The project classifies 49,688 products into 543 recipe-level ingredients, then
analyzes purchasing behavior at the ingredient level across each customer's order
history.

The dataset is public (Kaggle), with anonymized integer user IDs. There is no
sensitive or proprietary data.

## Core Commands

### Environment Setup
```bash
uv sync                    # Install all dependencies (including dev tools)
```

### Data Pipeline
```bash
python scripts/data_pipeline/ingest_data.py          # Kaggle → data/processed/
python scripts/data_pipeline/audit_data.py           # Validate quality → docs/DATA_AUDIT.md
```

### Classification
```bash
python scripts/classification/classify_fabric.py     # LLM classification (~8h; CSV committed)
python scripts/classification/apply_corrections.py   # Taxonomy fixes
python scripts/classification/classify_lookup.py build  # Build exact-match lookup table
```

### Analysis (each writes to its analysis/<topic>/ directory)
```bash
for s in analyze_reorder analyze_patterns analyze_substitution analyze_calendar_time \
         analyze_lift_decomposition analyze_novelty analyze_exploration \
         analyze_cooccurrence analyze_basket_contents analyze_prepared_foods \
         analyze_ingredient_lens analyze_customer_profile analyze_customer_behavior; do
  python scripts/sequence_analysis/$s.py
done
python scripts/sequence_analysis/visualize_ingredient_lens.py
python scripts/sequence_analysis/visualize_audit.py
python scripts/sequence_analysis/generate_pattern_gallery.py
```

### Development
```bash
uv run ruff check scripts/
uv run ruff check --fix scripts/
uv run ruff format scripts/
uv run pytest
```

## Architecture

### Sequence Analysis Pipeline (`scripts/sequence_analysis/`)
One production pipeline — no `audit_*` / `*_v2` / duplicate variants (fix the
production script in place; git holds history). `analyze_reorder.py` is the shared
core: `load_events()` (full purchase table as one frame) and `iter_events()`
(user-id bursts), plus `analyze_level(level, keep=...)` for next-order probability +
shuffle-baseline lift. Every heavy analysis consumes `iter_events()` and accumulates
per-customer partials across bursts — exact results at ~1.2GB peak. See
`docs/PROCESSING.md`. **Never subsample input to save memory; chunk it.**

### Project Structure
```
scripts/
  ├── config.py          # Shared configuration: paths, schemas, keywords
  ├── data_pipeline/     # Kaggle → Parquet ingestion + audit
  ├── classification/    # LLM classifier, lookup-table classifier, taxonomy corrections
  └── sequence_analysis/ # One script per result; analyze_reorder.py is the shared core

analysis/                # Analysis findings only (one dir per topic)
  ├── ingredients/       # Demand vs assortment, concentration, organic penetration
  ├── basket/            # Basket size, composition, co-occurrence
  ├── sequences/         # Reorder, patterns, substitution, calendar
  ├── novelty/           # Novelty, repertoire growth
  ├── prepared/          # Reach, dish types, products, reorder
  ├── customers/         # Profile, segments, behavior
  ├── food_profiles/     # Food-style/cuisine signatures from ingredients + validation
  └── figures/           # All figures (png/svg)

data/                    # Inputs + derived data (not analysis findings)
  ├── INGREDIENT_TAXONOMY.md          # Recipe-ingredient taxonomy (parsed by the pipeline)
  ├── food_classification.csv         # Product → ingredient map
  ├── product_ingredient_lookup.csv   # Deterministic lookup table
  ├── affinity/          # Food Profiles reference (associations, combinations, overrides)
  ├── raw/               # Original CSV files
  └── processed/         # Parquet files + provenance.json

scripts/
  └── affinity/          # Food Profiles: recipe→ingredient mapping, associations, evaluation, figures

docs/                    # PROCESSING.md, DATA_AUDIT.md, FOOD_CLASSIFICATION.md
  ├── AFFINITY_REFERENCE.md   # Food Profiles reference methodology
  └── classification/    # Method comparison, figures, archived classification attempts
```

**Food Profiles layer** (`scripts/affinity/` → `data/affinity/` → `analysis/food_profiles/`):
a reference mapping the 543 ingredients to food styles / composition / cuisine via measured
recipe-corpus statistics (lift, support), validated on held-out recipes. Public name is
"food profile"; the data schema key is `affinity_id` (kept for compatibility). Raw recipe
corpora live in git-ignored `data/external/`; only derived stats are committed.

### Configuration (`scripts/config.py`)

Centralized definitions for:
- **Paths**: Project root, data directories, docs
- **Dataset metadata**: Kaggle competition ID, required files, schema expectations
- **Prepared food keywords**: Aisle/department search terms for category identification

All scripts import from `config.py` to ensure consistency.

### Data Semantics (Instacart Dataset)

**Time fields have specific interpretations:**
- `order_number`: Customer-relative sequence (1, 2, 3, ...), NOT a timestamp
- `days_since_prior_order`: Inter-purchase interval, **capped at 30 days**
- **No absolute calendar dates** in the dataset

**Order sets:**
- `prior`: Historical orders with item labels → `order_products__prior`
- `train`: Training set orders with item labels → `order_products__train`
- `test`: Competition test orders, **no published item labels** (NOT empty baskets)

**Prepared food identification:**
Defined by the taxonomy's "Prepared Dishes & Meals" section (17 meal types), not a
hardcoded ingredient list. The per-product `is_prepared_dish` flag is broader; the
taxonomy section is the authoritative definition.

## Data Handling Rules

**NEVER commit to git:**
- Kaggle credentials (`~/.kaggle/kaggle.json`)
- The original data files from Kaggle (too large for GitHub)

**DO commit:**
- Data directory structure (`.gitkeep` files)
- Processed Parquet files (`data/processed/`)
- Classification data (`data/food_classification.csv`, `data/product_ingredient_lookup.csv`, `data/INGREDIENT_TAXONOMY.md`)
- Aggregate analysis results (CSVs under `analysis/<topic>/`)
- Figures (PNG/SVG under `analysis/figures/`)
- Code, documentation, derived data that other researchers could use

## Kaggle API Authentication

Kaggle uses token-based authentication (as of 2026). The user must:

1. Go to https://www.kaggle.com/settings/account
2. Scroll to "API" section and generate a token (format: `KGAT_...`)
3. Choose one authentication method:
   - **Environment variable**: `export KAGGLE_API_TOKEN=KGAT_...` (session-only)
   - **Token file**: Save token to `~/.kaggle/access_token` and `chmod 600` it (persists)

**Dataset source**: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis

## Known Limitations

1. **No absolute timestamps**: Cannot reconstruct calendar dates or seasonal patterns
2. **30-day cap on inter-purchase intervals**: Long gaps are censored
3. **Test set opacity**: Test orders lack item labels, cannot be used for sequence analysis
4. **Category ambiguity**: "Prepared food" taxonomy requires human judgment on edge cases
5. **Instacart-specific**: Customer base skews urban and convenience-oriented; organic penetration and plant-milk shares are platform-specific, not nationally representative
6. **2,807 unclassified products** (5.6%): The LLM declined low-confidence guesses

## Vocabulary

- **Ingredient**: The recipe-level role a product plays (milk, yogurt, banana) — brand, size, and flavor stripped away
- **Category**: Taxonomy grouping of ingredients (PRODUCE - VEGETABLES, DAIRY, SNACKS, etc.)
- **Prepared foods**: Ready-to-eat meals requiring minimal cooking (frozen meals, deli items, etc.)
- **Brand multiplier**: Distinct products ÷ distinct ingredients per customer (median 1.33×)
- **Repeat**: Purchasing the same product in successive orders
- **Rotation**: Alternating between products in a category
- **Stop**: Ceasing to purchase prepared foods after a history of purchases
- **Return**: Resuming prepared food purchases after a gap
