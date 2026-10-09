# Example Data Files

This directory contains small example CSV files showing the schema of the Instacart dataset. These are **not real customer data** — they're synthetic examples to illustrate the structure.

## Files

| File | Rows | Description |
|---|---|---|
| `orders_example.csv` | 20 | Order metadata: user, sequence, day-of-week, hour, days since prior order |
| `products_example.csv` | 16 | Product catalog: product ID, name, aisle, department |
| `aisles_example.csv` | 8 | Aisle taxonomy |
| `departments_example.csv` | 4 | Department taxonomy |
| `order_products__prior_example.csv` | 16 | Historical purchase records |
| `order_products__train_example.csv` | 12 | Training set purchase records |

## Schema Documentation

### orders.csv

| Column | Type | Description |
|---|---|---|
| `order_id` | int | Unique order identifier |
| `user_id` | int | Customer identifier |
| `eval_set` | str | prior / train / test |
| `order_number` | int | Customer-relative order sequence (1, 2, 3, ...) |
| `order_dow` | int | Day of week (0-6) |
| `order_hour_of_day` | int | Hour of day (0-23) |
| `days_since_prior_order` | float | Days since previous order (null for first order, capped at 30) |

### products.csv

| Column | Type | Description |
|---|---|---|
| `product_id` | int | Unique product identifier |
| `product_name` | str | Product name |
| `aisle_id` | int | Aisle identifier (foreign key) |
| `department_id` | int | Department identifier (foreign key) |

### aisles.csv

| Column | Type | Description |
|---|---|---|
| `aisle_id` | int | Unique aisle identifier |
| `aisle` | str | Aisle name |

### departments.csv

| Column | Type | Description |
|---|---|---|
| `department_id` | int | Unique department identifier |
| `department` | str | Department name |

### order_products__prior.csv & order_products__train.csv

| Column | Type | Description |
|---|---|---|
| `order_id` | int | Order identifier (foreign key) |
| `product_id` | int | Product identifier (foreign key) |
| `add_to_cart_order` | int | Sequence in which product was added to cart |
| `reordered` | int | 1 if customer has ordered this product before, 0 otherwise |

## Notes

- **No absolute dates**: The dataset only has customer-relative order sequences, not calendar dates
- **days_since_prior_order is capped at 30**: Longer gaps are censored
- **test set orders have no published item labels**: The `order_products__test.csv` file does not exist
- **eval_set values**: `prior` (historical orders), `train` (training set), `test` (competition test set, no items)

## Getting the Real Data

The full dataset is available from Kaggle:

1. Go to: https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis
2. Download the dataset (207 MB)
3. Or use `scripts/ingest_data.py` to download via Kaggle API

See the main [README.md](../../README.md) for detailed setup instructions.
