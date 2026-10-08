# food-sequences

Study of food selection patterns in sequential purchases using the Instacart Online Grocery Shopping Dataset 2017.

## Project Overview

This portfolio project, motivated by CookUnity, investigates how customers repeat, rotate, stop selecting, and return to foods over successive purchases. The initial phase focuses on **data acquisition and validation**, not modeling.

## Research Questions

- How do customers repeat prepared food purchases across orders?
- When do familiar meals remain appealing vs. when do customers seek variety?
- What patterns exist in selection, rotation, and return behavior?

## Dataset

**Instacart Market Basket Analysis Dataset**

- **Primary Source**: Kaggle dataset (originally from 2017 competition)  
  https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis
- **Required Tables**:
  - `orders` - Order metadata with user IDs, order sequence, and timing
  - `products` - Product catalog with names and category assignments
  - `aisles` - Aisle taxonomy
  - `departments` - Department taxonomy
  - `order_products__prior` - Historical order contents
  - `order_products__train` - Training set order contents

**Note**: The original Kaggle competition page is no longer active, but the complete dataset (6 CSV files, 207 MB) is available as a Kaggle dataset. A partial archive exists at https://github.com/subwaymatch/instacart-dataset-2017 but lacks the critical historical order-item tables.

## Setup

### Prerequisites

- Python 3.12+
- Kaggle account with API credentials

### Installation

1. **Clone and navigate to the repository**:
   ```bash
   cd food-sequences
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up Kaggle credentials**:
   
   The Kaggle API requires authentication. You need to:
   
   a. Create a Kaggle account at https://www.kaggle.com
   
   b. Go to https://www.kaggle.com/settings/account
   
   c. Scroll to "API" section and follow instructions to generate a token (starts with `KGAT_`)
   
   d. **Choose one authentication method**:
   
   **Option 1: Environment variable** (recommended for single session):
   ```bash
   export KAGGLE_API_TOKEN=KGAT_your_token_here
   ```
   
   **Option 2: Save to file** (persists across sessions):
   ```bash
   mkdir -p ~/.kaggle
   echo 'KGAT_your_token_here' > ~/.kaggle/access_token
   chmod 600 ~/.kaggle/access_token
   ```
   
   Replace `KGAT_your_token_here` with your actual token from step (c).

### Download and Process Data

**One-command execution**:
```bash
python scripts/ingest_data.py
```

This script will:
1. Download the Instacart dataset from Kaggle (~200 MB compressed)
2. Extract CSV files to `data/raw/`
3. Convert to Parquet format in `data/processed/`
4. Record provenance metadata (source, date, checksums)

**Manual download fallback**:

If API download fails or you prefer manual download:

1. Visit: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis
2. Click "Download" button
3. Extract the ZIP to `data/raw/`
4. Run ingestion: `python scripts/ingest_data.py --skip-download`

## Data Validation

Run the audit to verify data quality and determine if the dataset supports the research questions:

```bash
python scripts/audit_data.py
```

This generates `docs/DATA_AUDIT.md` with:
- Table row counts and schema verification
- Join coverage between orders and products
- Duplicate detection
- Missing value analysis
- Per-user order count distributions
- Prepared food category coverage
- Recommendation on whether to proceed with analysis

## Project Structure

```
food-sequences/
├── data/
│   ├── raw/              # Downloaded CSV files (gitignored)
│   └── processed/        # Parquet files (gitignored)
├── docs/
│   └── DATA_AUDIT.md     # Data quality report
├── scripts/
│   ├── ingest_data.py    # Download and convert data
│   └── audit_data.py     # Validate and audit data
├── src/
│   └── food_sequences/   # Package code
├── pyproject.toml        # Dependencies and configuration
└── README.md             # This file
```

## Data Files

**Never commit**:
- Raw CSV files (`data/raw/`)
- Processed Parquet files (`data/processed/`)
- Kaggle credentials
- Any customer-level derived data

## Time Field Interpretation

The dataset has specific time semantics:

- **`order_number`**: Customer-relative sequence (1, 2, 3, ...)
- **`days_since_prior_order`**: Days between orders, **capped at 30**
- **No absolute dates**: Cannot reconstruct calendar dates
- **Elapsed time**: Can approximate but with 30-day ceiling artifacts

## Prepared Food Categories

Prepared food identification uses the actual product/aisle taxonomy in the dataset. Categories may include:

- Frozen prepared meals
- Frozen pizzas
- Deli prepared foods
- Refrigerated soups
- Ready-to-eat meal kits

**Note**: Inclusion rules are determined during data audit by inspecting actual taxonomy. Grocery products are not labeled as restaurant meals.

## Analysis Scope

- **Included**: Every observed order as an opportunity to select prepared foods
- **Preserved**: Orders with no prepared foods (zero-purchase opportunities)
- **Excluded**: Test set orders (no published item labels, not empty baskets)
- **Comparison**: Broader food cohort for baseline behavior

## Future Work

After data acquisition and validation:

1. Sequence analysis of prepared food selections
2. Repeat vs. rotation pattern identification
3. Prepared vs. fresh food substitution analysis
4. Report generation with visual sequence illustrations
5. GitHub Pages publication

## License

This is a portfolio project using the Instacart dataset under its published terms. Raw data files are not distributed with this repository.
