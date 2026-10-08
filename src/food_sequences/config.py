"""Configuration and schema definitions for the Instacart dataset."""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"

# Kaggle dataset configuration
KAGGLE_DATASET = "psparks/instacart-market-basket-analysis"
DATASET_NAME = "Instacart Market Basket Analysis Dataset"
KAGGLE_URL = f"https://www.kaggle.com/datasets/{KAGGLE_DATASET}"

# Required data files (with possible filename variations)
REQUIRED_FILES = {
    "orders": ["orders.csv"],
    "products": ["products.csv"],
    "aisles": ["aisles.csv"],
    "departments": ["departments.csv"],
    "order_products_prior": ["order_products__prior.csv", "order_products_prior.csv"],
    "order_products_train": ["order_products__train.csv", "order_products_train.csv"],
}

# Expected schemas (for validation)
EXPECTED_SCHEMAS = {
    "orders": {
        "order_id": "int",
        "user_id": "int",
        "eval_set": "str",
        "order_number": "int",
        "order_dow": "int",
        "order_hour_of_day": "int",
        "days_since_prior_order": "float",  # Float because it can be NaN for first order
    },
    "products": {
        "product_id": "int",
        "product_name": "str",
        "aisle_id": "int",
        "department_id": "int",
    },
    "aisles": {
        "aisle_id": "int",
        "aisle": "str",
    },
    "departments": {
        "department_id": "int",
        "department": "str",
    },
    "order_products_prior": {
        "order_id": "int",
        "product_id": "int",
        "add_to_cart_order": "int",
        "reordered": "int",
    },
    "order_products_train": {
        "order_id": "int",
        "product_id": "int",
        "add_to_cart_order": "int",
        "reordered": "int",
    },
}

# Prepared food category keywords to search for
# These will be refined during audit based on actual taxonomy
PREPARED_FOOD_KEYWORDS = {
    "aisles": [
        "frozen pizza",
        "frozen meals",
        "prepared meals",
        "prepared soups salads",
        "fresh pasta",
        "refrigerated meals",
        "hot dogs bacon sausage",
        "packaged meals",
    ],
    "departments": [
        "frozen",
        "prepared foods",
        "deli",
    ],
}
