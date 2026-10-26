# Data

This project's inputs are the **public Instacart Online Grocery Shopping Dataset
2017**, hosted on Kaggle:
https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis

The raw/processed tables are **not committed** here — they are the public source
(regenerable in minutes) and the largest file exceeds GitHub's 100MB limit. Recreate
them with:

```bash
python scripts/data_pipeline/ingest_data.py     # Kaggle → data/processed/*.parquet
```

That produces (under `data/processed/`, gitignored):

| File | Rows | Contents |
|------|-----:|----------|
| `orders.parquet` | 3.4M | order_id, user_id, order_number, dow, hour, days_since_prior_order |
| `order_products_prior.parquet` | ~30M | order_id, product_id, add_to_cart_order, reordered |
| `order_products_train.parquet` | ~1.4M | same, for train orders |
| `products.parquet`, `aisles.parquet`, `departments.parquet` | — | catalog reference |

## What we created (and publish)

The project's own contributions live in the repo and are what another researcher
would reuse:

- **`food_classification.csv`** — all 49,688 products mapped to their recipe
  ingredient, with `is_food` and `is_prepared_dish`. This is the key derived dataset
  (543 food ingredients analyzed downstream).
- **`product_ingredient_lookup.csv`** — deterministic product→ingredient+category
  lookup table; reproduces the mapping without re-running the LLM.
- **`INGREDIENT_TAXONOMY.md`** — the recipe-ingredient taxonomy (24 categories,
  21 of them food) the classification targets. Parsed at runtime by the analysis
  pipeline, so it lives here as reference data rather than under `analysis/`.
- **`analysis/<topic>/*.csv`** — every aggregate result table (no user IDs).

Per-customer derived tables (`*.parquet` under `analysis/`) are intermediate and
gitignored; regenerate them by running the analysis scripts.
