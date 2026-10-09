"""
Customer-product sequence extraction and feature calculation.

This module builds per-customer purchase sequences and calculates features
like selection frequency, consecutive selections, gaps between repeats,
and basket variety.
"""

import numpy as np
import pandas as pd
import polars as pl
from pathlib import Path
from typing import Literal

from food_sequences.config import DATA_PROCESSED


def load_data() -> dict[str, pd.DataFrame]:
    """Load all processed Parquet files."""
    data = {}

    files = {
        "orders": "orders.parquet",
        "products": "products.parquet",
        "aisles": "aisles.parquet",
        "departments": "departments.parquet",
        "order_products_prior": "order_products_prior.parquet",
        "order_products_train": "order_products_train.parquet",
    }

    for name, filename in files.items():
        path = DATA_PROCESSED / filename
        data[name] = pd.read_parquet(path)

    return data


def build_full_order_product_table(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build complete order-product table with all metadata.

    Joins orders, products, aisles, departments, and purchase records.
    Returns one row per (order_id, product_id) with full context.
    """
    # Combine prior and train purchases
    purchases = pd.concat([
        data["order_products_prior"],
        data["order_products_train"]
    ], ignore_index=True)

    # Join with orders
    full = purchases.merge(data["orders"], on="order_id", how="left")

    # Join with products
    full = full.merge(data["products"], on="product_id", how="left")

    # Join with aisles and departments
    full = full.merge(data["aisles"], on="aisle_id", how="left")
    full = full.merge(data["departments"], on="department_id", how="left")

    # Sort by user and order sequence
    full = full.sort_values(["user_id", "order_number", "add_to_cart_order"])

    return full


def identify_prepared_food_products(data: dict[str, pd.DataFrame]) -> set[int]:
    """
    Identify prepared food product IDs based on aisle/department taxonomy.

    Uses the same keywords as the audit script for consistency.
    """
    products = data["products"]
    aisles = data["aisles"]
    departments = data["departments"]

    prepared_aisle_keywords = [
        "frozen pizza",
        "frozen meals",
        "prepared meals",
        "prepared soups salads",
        "fresh pasta",
        "hot dogs bacon sausage",
    ]

    prepared_dept_keywords = ["frozen", "deli"]

    # Find prepared food aisles
    prepared_aisles = set()
    for keyword in prepared_aisle_keywords:
        matches = aisles[aisles["aisle"].str.contains(keyword, case=False, na=False)]
        prepared_aisles.update(matches["aisle_id"].values)

    # Find prepared food departments
    prepared_depts = set()
    for keyword in prepared_dept_keywords:
        matches = departments[departments["department"].str.contains(keyword, case=False, na=False)]
        prepared_depts.update(matches["department_id"].values)

    # Get products in these categories
    prepared_products = products[
        products["aisle_id"].isin(prepared_aisles) |
        products["department_id"].isin(prepared_depts)
    ]

    return set(prepared_products["product_id"].values)


def build_user_order_sequences(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build per-user order sequences with metadata.

    Returns one row per (user_id, order_number) with order characteristics.
    """
    orders = data["orders"].copy()

    # Only keep prior and train orders (not test)
    orders = orders[orders["eval_set"].isin(["prior", "train"])].copy()

    # Sort by user and order
    orders = orders.sort_values(["user_id", "order_number"])

    # Calculate cumulative days (with 30-day cap awareness)
    orders["cumulative_days"] = orders.groupby("user_id")["days_since_prior_order"].cumsum()

    # Count orders per user
    orders["user_total_orders"] = orders.groupby("user_id")["order_id"].transform("count")

    return orders


def build_product_sequences(
    full_data: pd.DataFrame,
    min_orders: int = 4
) -> pd.DataFrame:
    """
    Build customer-product purchase sequences.

    For each (user_id, product_id) pair, create a sequence showing
    which orders contained that product.

    Args:
        full_data: Full order-product table from build_full_order_product_table
        min_orders: Minimum orders a user must have to be included

    Returns:
        DataFrame with columns:
        - user_id
        - product_id
        - product_name
        - aisle
        - department
        - first_order_num: First order this product appeared
        - last_order_num: Last order this product appeared
        - total_purchases: Total times purchased
        - order_numbers: List of order numbers when purchased
        - user_total_orders: Total orders for this user
    """
    # Filter to users with sufficient history
    user_order_counts = full_data.groupby("user_id")["order_number"].max()
    valid_users = user_order_counts[user_order_counts >= min_orders].index

    df = full_data[full_data["user_id"].isin(valid_users)].copy()

    # Group by user and product
    sequences = df.groupby(["user_id", "product_id"]).agg({
        "order_number": ["min", "max", "count", list],
        "product_name": "first",
        "aisle": "first",
        "department": "first",
    }).reset_index()

    # Flatten column names
    sequences.columns = [
        "user_id", "product_id",
        "first_order_num", "last_order_num", "total_purchases", "order_numbers",
        "product_name", "aisle", "department"
    ]

    # Add user total orders
    user_totals = df.groupby("user_id")["order_number"].max().to_dict()
    sequences["user_total_orders"] = sequences["user_id"].map(user_totals)

    return sequences


def calculate_sequence_features(sequences: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate features from purchase sequences.

    Features include:
    - Selection frequency (purchases / total orders)
    - Maximum consecutive purchases
    - Mean gap between purchases
    - Recency (orders since last purchase)
    - Recent frequency (last 5 orders)
    - Long-term frequency (all but last 5)
    """
    features = sequences.copy()

    def calc_features(row):
        order_nums = sorted(row["order_numbers"])
        total_orders = row["user_total_orders"]

        # Basic frequency
        freq = len(order_nums) / total_orders

        # Consecutive purchases
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(order_nums)):
            if order_nums[i] == order_nums[i-1] + 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1

        # Gaps between purchases
        gaps = [order_nums[i] - order_nums[i-1] - 1
                for i in range(1, len(order_nums))]
        mean_gap = np.mean(gaps) if gaps else 0.0

        # Recency
        recency = total_orders - row["last_order_num"]

        # Recent vs long-term frequency
        recent_threshold = total_orders - 5
        recent_purchases = sum(1 for o in order_nums if o > recent_threshold)
        longterm_purchases = len(order_nums) - recent_purchases

        recent_freq = recent_purchases / 5 if total_orders >= 5 else freq
        longterm_freq = longterm_purchases / (total_orders - 5) if total_orders > 5 else 0.0

        return pd.Series({
            "selection_frequency": freq,
            "max_consecutive": max_consecutive,
            "mean_gap": mean_gap,
            "recency": recency,
            "recent_frequency": recent_freq,
            "longterm_frequency": longterm_freq,
        })

    feature_cols = features.apply(calc_features, axis=1)
    features = pd.concat([features, feature_cols], axis=1)

    return features


def calculate_basket_variety(full_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate basket variety metrics per order.

    Metrics:
    - unique_products: Number of unique products in order
    - unique_aisles: Number of unique aisles represented
    - unique_departments: Number of unique departments
    - prepared_food_count: Number of prepared food items
    - prepared_food_ratio: Ratio of prepared foods to total items
    """
    prepared_foods = identify_prepared_food_products({
        "products": full_data[["product_id", "aisle_id", "department_id"]].drop_duplicates(),
        "aisles": full_data[["aisle_id", "aisle"]].drop_duplicates(),
        "departments": full_data[["department_id", "department"]].drop_duplicates(),
    })

    full_data = full_data.copy()
    full_data["is_prepared_food"] = full_data["product_id"].isin(prepared_foods)

    variety = full_data.groupby(["user_id", "order_id", "order_number"]).agg({
        "product_id": "nunique",
        "aisle_id": "nunique",
        "department_id": "nunique",
        "is_prepared_food": ["sum", "mean"],
    }).reset_index()

    variety.columns = [
        "user_id", "order_id", "order_number",
        "unique_products", "unique_aisles", "unique_departments",
        "prepared_food_count", "prepared_food_ratio"
    ]

    return variety


def build_category_sequences(
    full_data: pd.DataFrame,
    category: Literal["aisle", "department"],
    min_orders: int = 4
) -> pd.DataFrame:
    """
    Build purchase sequences at category level (aisle or department).

    Similar to build_product_sequences but aggregates by category.
    """
    # Filter to users with sufficient history
    user_order_counts = full_data.groupby("user_id")["order_number"].max()
    valid_users = user_order_counts[user_order_counts >= min_orders].index

    df = full_data[full_data["user_id"].isin(valid_users)].copy()

    category_col = category if category == "aisle" else "department"
    category_id = f"{category}_id"

    # Group by user and category
    sequences = df.groupby(["user_id", category_id]).agg({
        "order_number": ["min", "max", "count", list],
        category_col: "first",
    }).reset_index()

    # Flatten column names
    sequences.columns = [
        "user_id", f"{category}_id",
        "first_order_num", "last_order_num", "total_purchases", "order_numbers",
        category_col
    ]

    # Add user total orders
    user_totals = df.groupby("user_id")["order_number"].max().to_dict()
    sequences["user_total_orders"] = sequences["user_id"].map(user_totals)

    return sequences
