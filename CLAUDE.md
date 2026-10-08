# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**food-sequences** is a data science portfolio project studying food selection patterns in sequential purchases using the Instacart Online Grocery Shopping Dataset 2017. The project investigates how customers repeat, rotate, stop selecting, and return to foods (especially prepared meals) over successive purchases.

The current phase focuses on **data acquisition and validation only**. Modeling is explicitly out of scope until data quality is confirmed.

## Core Commands

### Environment Setup
```bash
# Install all dependencies (including dev tools)
uv sync

# Install only production dependencies
uv sync --no-dev
```

### Data Pipeline (Primary Workflow)
```bash
# Full pipeline: download, extract, convert to Parquet, save provenance
python scripts/ingest_data.py

# Skip download if files already exist in data/raw/
python scripts/ingest_data.py --skip-download

# Audit data quality and generate report
python scripts/audit_data.py
```

### Development
```bash
# Run linting
uv run ruff check src/ scripts/

# Auto-fix linting issues
uv run ruff check --fix src/ scripts/

# Format code
uv run ruff format src/ scripts/

# Run tests (when test suite exists)
uv run pytest
```

## Architecture

### Data Flow
1. **Download** (`ingest_data.py`): Kaggle API → `data/raw/*.zip`
2. **Extract**: ZIP → `data/raw/*.csv`
3. **Convert**: CSV → `data/processed/*.parquet` (Parquet for speed/compression)
4. **Provenance**: Record source, date, checksums → `data/processed/provenance.json`
5. **Audit** (`audit_data.py`): Validate quality → `docs/DATA_AUDIT.md`

### Project Structure
```
src/food_sequences/
  ├── __init__.py        # Package initialization
  └── config.py          # Centralized configuration: paths, schemas, keywords

scripts/
  ├── ingest_data.py     # Download and convert dataset
  └── audit_data.py      # Validate data quality

data/
  ├── raw/               # Original CSV files (gitignored)
  └── processed/         # Parquet files + provenance.json (gitignored)

docs/
  └── DATA_AUDIT.md      # Generated quality report
```

### Configuration (`src/food_sequences/config.py`)

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
- Cannot reconstruct true elapsed time beyond ~30-day windows

**Order sets:**
- `prior`: Historical orders with item labels → `order_products__prior`
- `train`: Training set orders with item labels → `order_products__train`
- `test`: Competition test orders, **no published item labels** (NOT empty baskets)

**Prepared food identification:**
- Must inspect actual aisle/department taxonomy (see `audit_data.py`)
- Keywords in `config.PREPARED_FOOD_KEYWORDS` are initial search terms
- Audit refines categories based on real taxonomy structure
- Grocery products ≠ restaurant meals

## Data Quality Requirements

The audit validates:

1. **Schema completeness**: All expected columns present in each table
2. **ID uniqueness**: No duplicate primary keys
3. **Join coverage**: >95% of prior orders have item records
4. **Missing values**: Document nulls, especially `days_since_prior_order` (expected for first orders)
5. **User order counts**: Distribution must support repeat-purchase analysis
6. **Prepared food coverage**: Sufficient products and purchases for meaningful sequences

**Critical constraint**: Must preserve every observed order as an opportunity to select prepared foods, even if that order contains none (zero-purchase signal).

## Data Handling Rules

**NEVER commit to git:**
- Raw CSV files (`data/raw/**`)
- Processed Parquet files (`data/processed/**`)
- Kaggle credentials (`~/.kaggle/kaggle.json`)
- Customer-level derived data
- Any file with purchase sequences or user identifiers

**DO commit:**
- Data directory structure (`.gitkeep` files)
- Provenance metadata schema (documentation only, not files with actual checksums)
- Aggregated statistics in audit reports
- Code, documentation, visualizations

## Kaggle API Authentication

Kaggle uses token-based authentication (as of 2026). The user must:

1. Go to https://www.kaggle.com/settings/account
2. Scroll to "API" section and generate a token (format: `KGAT_...`)
3. Choose one authentication method:
   - **Environment variable**: `export KAGGLE_API_TOKEN=KGAT_...` (session-only)
   - **Token file**: Save token to `~/.kaggle/access_token` and `chmod 600` it (persists)
4. Accept competition rules at: https://www.kaggle.com/c/instacart-market-basket-analysis/rules

**Note**: Kaggle changed from `kaggle.json` (username/key) to token-based auth. Old accounts may still have `kaggle.json`, which also works.

**Scripts will detect missing credentials and provide exact manual steps.** Never request credentials in chat or commit them.

## Expected File Variations

The dataset may have filename variations:
- `order_products__prior.csv` OR `order_products_prior.csv`
- `order_products__train.csv` OR `order_products_train.csv`

Ingestion script searches for both patterns. All Parquet outputs use normalized names (underscores, no dunder).

## Analysis Goals (Future Phases)

After data validation succeeds:

1. Identify prepared food selection sequences per customer
2. Measure repeat purchase intervals and rotation patterns  
3. Detect "stop" events (prepared food drop-off) and "return" events
4. Compare prepared food behavior to broader grocery categories
5. Generate visual sequence diagrams for GitHub report

## Testing Strategy (When Implemented)

Tests should validate:
- Schema expectations in `config.py` match actual dataset structure
- Checksum verification for data integrity
- Join coverage calculations
- Category identification logic (prepared food keywords → actual products)
- Edge cases: single-order users, orders with no prior purchases, null `days_since_prior_order`

Use `pytest` with fixtures that load small subsets of real data (not synthetic).

## Dependencies

**Core:**
- `pandas`: Data manipulation and analysis
- `polars`: Alternative high-performance dataframe library (optional)
- `pyarrow`: Parquet file format support
- `kaggle`: Kaggle API client for dataset download

**Dev:**
- `jupyterlab`: Interactive exploration (not required for pipeline)
- `pytest`: Testing framework
- `ruff`: Fast Python linter and formatter
- `ipykernel`: Jupyter kernel for notebooks

**Why Parquet?**
- 5-10x smaller than CSV
- Column-oriented storage enables fast filtering/aggregation
- Preserves dtypes (no re-parsing strings as ints/floats)
- Standard in data science pipelines

## Known Limitations

1. **No absolute timestamps**: Cannot reconstruct calendar dates or seasonal patterns
2. **30-day cap on inter-purchase intervals**: Long gaps are censored
3. **Order continuity**: Some users have non-continuous `order_number` sequences (audit flags these)
4. **Test set opacity**: Test orders lack item labels, cannot be used for sequence analysis
5. **Category ambiguity**: "Prepared food" taxonomy requires human judgment on edge cases (e.g., frozen pizzas vs. meal kits)

## Vocabulary

- **Prepared foods**: Ready-to-eat meals requiring minimal cooking (frozen meals, deli items, etc.)
- **Order opportunity**: Any order where customer could have selected prepared food (includes zero-purchase orders)
- **Repeat**: Purchasing the same product in successive orders
- **Rotation**: Alternating between products in a category
- **Stop**: Ceasing to purchase prepared foods after a history of purchases
- **Return**: Resuming prepared food purchases after a gap

## Future Deliverable

GitHub Pages report with:
- Aggregate statistics on prepared food selection patterns
- Visual sequence diagrams (anonymized, no user IDs)
- Insights on repeat vs. rotation behavior
- Comparison to broader grocery categories
- Methodology and limitations documentation
