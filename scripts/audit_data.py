#!/usr/bin/env python3
"""
Audit the Instacart dataset for quality and completeness.

This script validates:
- Table schemas and row counts
- ID uniqueness and duplicate rows
- Join coverage between tables
- Missing values
- Per-user order statistics
- Prepared food category coverage

Generates: docs/DATA_AUDIT.md
"""

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from food_sequences.config import (
    DATA_PROCESSED,
    DOCS_DIR,
    EXPECTED_SCHEMAS,
    PREPARED_FOOD_KEYWORDS,
    REQUIRED_FILES,
)


def load_data() -> dict[str, pd.DataFrame]:
    """Load all Parquet files into memory."""
    data = {}

    print("Loading data files...")
    for table_name in REQUIRED_FILES.keys():
        parquet_path = DATA_PROCESSED / f"{table_name}.parquet"

        if not parquet_path.exists():
            print(f"  WARNING: {table_name}.parquet not found")
            continue

        try:
            df = pd.read_parquet(parquet_path)
            data[table_name] = df
            print(f"  Loaded {table_name}: {len(df):,} rows")
        except Exception as e:
            print(f"  ERROR loading {table_name}: {e}")

    return data


def audit_schemas(data: dict[str, pd.DataFrame]) -> list[str]:
    """Validate table schemas against expected structure."""
    findings = []
    findings.append("## Schema Validation\n")

    for table_name, df in data.items():
        findings.append(f"### {table_name}\n")
        findings.append(f"- **Rows**: {len(df):,}")
        findings.append(f"- **Columns**: {len(df.columns)}")

        expected = EXPECTED_SCHEMAS.get(table_name, {})
        if expected:
            missing_cols = set(expected.keys()) - set(df.columns)
            extra_cols = set(df.columns) - set(expected.keys())

            if missing_cols:
                findings.append(f"- ⚠️  **Missing columns**: {', '.join(missing_cols)}")
            if extra_cols:
                findings.append(f"- ℹ️  **Extra columns**: {', '.join(extra_cols)}")
            if not missing_cols and not extra_cols:
                findings.append("- ✓ Schema matches expected structure")
        else:
            findings.append(f"- Columns: {', '.join(df.columns)}")

        findings.append("")

    return findings


def audit_duplicates(data: dict[str, pd.DataFrame]) -> list[str]:
    """Check for duplicate rows and ID uniqueness."""
    findings = []
    findings.append("## Duplicate Detection\n")

    checks = {
        "orders": ("order_id", None),
        "products": ("product_id", None),
        "aisles": ("aisle_id", None),
        "departments": ("department_id", None),
        "order_products_prior": (None, ["order_id", "product_id"]),
        "order_products_train": (None, ["order_id", "product_id"]),
    }

    for table_name, (id_col, composite_key) in checks.items():
        if table_name not in data:
            continue

        df = data[table_name]
        findings.append(f"### {table_name}\n")

        # Check ID uniqueness
        if id_col and id_col in df.columns:
            n_unique = df[id_col].nunique()
            n_total = len(df)
            if n_unique == n_total:
                findings.append(f"- ✓ `{id_col}` is unique ({n_unique:,} values)")
            else:
                dup_count = n_total - n_unique
                findings.append(
                    f"- ⚠️  `{id_col}` has {dup_count:,} duplicates "
                    f"({n_unique:,} unique / {n_total:,} total)"
                )

        # Check composite key uniqueness
        if composite_key:
            n_unique = df[composite_key].drop_duplicates().shape[0]
            n_total = len(df)
            if n_unique == n_total:
                findings.append(
                    f"- ✓ Composite key {composite_key} is unique ({n_unique:,} combinations)"
                )
            else:
                dup_count = n_total - n_unique
                findings.append(
                    f"- ⚠️  Composite key {composite_key} has {dup_count:,} duplicate rows "
                    f"({n_unique:,} unique / {n_total:,} total)"
                )

        # Check full row duplicates
        n_dup_rows = df.duplicated().sum()
        if n_dup_rows > 0:
            findings.append(f"- ⚠️  {n_dup_rows:,} fully duplicate rows detected")
        else:
            findings.append("- ✓ No fully duplicate rows")

        findings.append("")

    return findings


def audit_joins(data: dict[str, pd.DataFrame]) -> list[str]:
    """Verify join coverage between tables."""
    findings = []
    findings.append("## Join Coverage\n")

    # Orders to order_products
    if "orders" in data and "order_products_prior" in data:
        orders = data["orders"]
        order_products = data["order_products_prior"]

        prior_orders = orders[orders["eval_set"] == "prior"]
        n_prior_orders = len(prior_orders)
        n_orders_with_items = order_products["order_id"].nunique()

        coverage_pct = (n_orders_with_items / n_prior_orders * 100) if n_prior_orders > 0 else 0

        findings.append("### Orders → Order Products (Prior)\n")
        findings.append(f"- Prior orders: {n_prior_orders:,}")
        findings.append(f"- Orders with items: {n_orders_with_items:,}")
        findings.append(f"- **Coverage**: {coverage_pct:.2f}%")

        if coverage_pct < 99:
            missing = n_prior_orders - n_orders_with_items
            findings.append(
                f"- ⚠️  {missing:,} prior orders have no items "
                "(may be test orders or data gap)"
            )
        else:
            findings.append("- ✓ High join coverage")

        findings.append("")

    # Products to aisles/departments
    if all(k in data for k in ["products", "aisles", "departments"]):
        products = data["products"]
        aisles = data["aisles"]
        departments = data["departments"]

        findings.append("### Products → Aisles/Departments\n")

        # Aisle coverage
        valid_aisles = products["aisle_id"].isin(aisles["aisle_id"])
        findings.append(f"- Products with valid aisle: {valid_aisles.sum():,} / {len(products):,}")
        if not valid_aisles.all():
            findings.append(f"  - ⚠️  {(~valid_aisles).sum():,} products have invalid aisle_id")

        # Department coverage
        valid_depts = products["department_id"].isin(departments["department_id"])
        findings.append(
            f"- Products with valid department: {valid_depts.sum():,} / {len(products):,}"
        )
        if not valid_depts.all():
            findings.append(
                f"  - ⚠️  {(~valid_depts).sum():,} products have invalid department_id"
            )

        findings.append("")

    return findings


def audit_missing_values(data: dict[str, pd.DataFrame]) -> list[str]:
    """Check for missing values in critical fields."""
    findings = []
    findings.append("## Missing Values\n")

    for table_name, df in data.items():
        null_counts = df.isnull().sum()
        null_cols = null_counts[null_counts > 0]

        if len(null_cols) > 0:
            findings.append(f"### {table_name}\n")
            for col, count in null_cols.items():
                pct = count / len(df) * 100
                findings.append(f"- `{col}`: {count:,} ({pct:.2f}%)")
            findings.append("")

    if len([f for f in findings if "###" in f]) == 0:
        findings.append("✓ No missing values detected in any table.\n")

    return findings


def audit_user_orders(data: dict[str, pd.DataFrame]) -> list[str]:
    """Analyze per-user order statistics."""
    findings = []
    findings.append("## User Order Statistics\n")

    if "orders" not in data:
        findings.append("⚠️  Orders table not available\n")
        return findings

    orders = data["orders"]

    # Orders per user
    orders_per_user = orders.groupby("user_id").size()

    findings.append(f"- **Total users**: {orders['user_id'].nunique():,}")
    findings.append(f"- **Total orders**: {len(orders):,}")
    findings.append(f"- **Mean orders per user**: {orders_per_user.mean():.1f}")
    findings.append(f"- **Median orders per user**: {orders_per_user.median():.0f}")
    findings.append(
        f"- **Min/Max orders per user**: {orders_per_user.min()} / {orders_per_user.max()}"
    )
    findings.append("\n**Distribution**:\n")

    # Bin the distribution
    bins = [0, 5, 10, 20, 50, 100, float("inf")]
    labels = ["1-5", "6-10", "11-20", "21-50", "51-100", "100+"]
    binned = pd.cut(orders_per_user, bins=bins, labels=labels)
    dist = binned.value_counts().sort_index()

    for label, count in dist.items():
        pct = count / len(orders_per_user) * 100
        findings.append(f"- {label} orders: {count:,} users ({pct:.1f}%)")

    findings.append("")

    # Order number continuity
    findings.append("### Order Number Continuity\n")
    discontinuities = 0
    for user_id, user_orders in orders.groupby("user_id"):
        order_nums = sorted(user_orders["order_number"].values)
        expected = list(range(1, len(order_nums) + 1))
        if order_nums != expected:
            discontinuities += 1

    if discontinuities > 0:
        findings.append(
            f"- ⚠️  {discontinuities:,} users have non-continuous order_number sequences"
        )
    else:
        findings.append("- ✓ All users have continuous order_number sequences (1, 2, 3, ...)")

    findings.append("")

    return findings


def audit_prepared_foods(data: dict[str, pd.DataFrame]) -> list[str]:
    """Identify and analyze prepared food categories."""
    findings = []
    findings.append("## Prepared Food Categories\n")

    if not all(k in data for k in ["products", "aisles", "departments"]):
        findings.append("⚠️  Required tables not available\n")
        return findings

    products = data["products"]
    aisles = data["aisles"]
    departments = data["departments"]

    # Join products with taxonomy
    products_full = products.merge(aisles, on="aisle_id", how="left").merge(
        departments, on="department_id", how="left"
    )

    # Search for prepared food aisles
    findings.append("### Aisles (Prepared Foods)\n")
    aisle_matches = []
    for keyword in PREPARED_FOOD_KEYWORDS["aisles"]:
        matches = aisles[aisles["aisle"].str.contains(keyword, case=False, na=False)]
        if len(matches) > 0:
            for _, row in matches.iterrows():
                n_products = (products_full["aisle_id"] == row["aisle_id"]).sum()
                aisle_matches.append(row["aisle_id"])
                findings.append(f"- `{row['aisle']}` (ID: {row['aisle_id']}, {n_products} products)")

    if not aisle_matches:
        findings.append("- ℹ️  No aisles matched keyword search")

    findings.append("")

    # Search for prepared food departments
    findings.append("### Departments (Prepared Foods)\n")
    dept_matches = []
    for keyword in PREPARED_FOOD_KEYWORDS["departments"]:
        matches = departments[departments["department"].str.contains(keyword, case=False, na=False)]
        if len(matches) > 0:
            for _, row in matches.iterrows():
                n_products = (products_full["department_id"] == row["department_id"]).sum()
                dept_matches.append(row["department_id"])
                findings.append(
                    f"- `{row['department']}` (ID: {row['department_id']}, {n_products} products)"
                )

    if not dept_matches:
        findings.append("- ℹ️  No departments matched keyword search")

    findings.append("")

    # Count products in prepared food categories
    prepared_products = products_full[
        products_full["aisle_id"].isin(aisle_matches)
        | products_full["department_id"].isin(dept_matches)
    ]

    findings.append("### Prepared Food Product Coverage\n")
    findings.append(f"- **Total products**: {len(products):,}")
    findings.append(f"- **Prepared food products**: {len(prepared_products):,}")
    findings.append(
        f"- **Coverage**: {len(prepared_products) / len(products) * 100:.2f}% of catalog"
    )

    # Sample products
    if len(prepared_products) > 0:
        findings.append("\n**Sample products** (first 10):\n")
        for _, row in prepared_products.head(10).iterrows():
            findings.append(f"- {row['product_name']} ({row['aisle']})")

    findings.append("")

    # Analyze purchase frequency
    if "order_products_prior" in data:
        order_products = data["order_products_prior"]

        # Join to get prepared food purchases
        purchases_full = order_products.merge(products_full, on="product_id", how="left")
        is_prepared = purchases_full["aisle_id"].isin(aisle_matches) | purchases_full[
            "department_id"
        ].isin(dept_matches)

        n_total_purchases = len(purchases_full)
        n_prepared_purchases = is_prepared.sum()

        findings.append("### Prepared Food Purchase Frequency\n")
        findings.append(f"- **Total purchases**: {n_total_purchases:,}")
        findings.append(f"- **Prepared food purchases**: {n_prepared_purchases:,}")
        findings.append(
            f"- **Purchase rate**: {n_prepared_purchases / n_total_purchases * 100:.2f}%"
        )

        # Orders with prepared foods
        orders_with_prepared = purchases_full[is_prepared]["order_id"].nunique()
        total_orders = purchases_full["order_id"].nunique()
        findings.append(f"- **Orders with prepared foods**: {orders_with_prepared:,} / {total_orders:,}")
        findings.append(
            f"- **Order penetration**: {orders_with_prepared / total_orders * 100:.2f}%"
        )

        findings.append("")

    return findings


def generate_recommendation(data: dict[str, pd.DataFrame]) -> list[str]:
    """Generate recommendation on whether to proceed with analysis."""
    findings = []
    findings.append("## Recommendation\n")

    # Check critical conditions
    issues = []
    warnings = []

    # All required tables present?
    missing_tables = set(REQUIRED_FILES.keys()) - set(data.keys())
    if missing_tables:
        issues.append(f"Missing required tables: {', '.join(missing_tables)}")

    # Sufficient data volume?
    if "orders" in data and len(data["orders"]) < 10000:
        warnings.append("Order count seems low (< 10,000)")

    # Join coverage?
    if "orders" in data and "order_products_prior" in data:
        orders = data["orders"]
        order_products = data["order_products_prior"]
        prior_orders = orders[orders["eval_set"] == "prior"]
        coverage = order_products["order_id"].nunique() / len(prior_orders)
        if coverage < 0.95:
            warnings.append(f"Join coverage is low ({coverage * 100:.1f}%)")

    # Prepared food coverage?
    if all(k in data for k in ["products", "aisles"]):
        products = data["products"]
        aisles = data["aisles"]
        products_full = products.merge(aisles, on="aisle_id", how="left")

        aisle_matches = []
        for keyword in PREPARED_FOOD_KEYWORDS["aisles"]:
            matches = aisles[aisles["aisle"].str.contains(keyword, case=False, na=False)]
            aisle_matches.extend(matches["aisle_id"].tolist())

        prepared_products = products_full[products_full["aisle_id"].isin(aisle_matches)]
        if len(prepared_products) < 100:
            warnings.append(f"Few prepared food products identified ({len(prepared_products)})")

    # Generate recommendation
    if issues:
        findings.append("### ⚠️  NOT RECOMMENDED TO PROCEED\n")
        findings.append("**Critical issues:**\n")
        for issue in issues:
            findings.append(f"- {issue}")
        findings.append("\nResolve these issues before proceeding with analysis.")
    elif warnings:
        findings.append("### ⚠️  PROCEED WITH CAUTION\n")
        findings.append("**Warnings:**\n")
        for warning in warnings:
            findings.append(f"- {warning}")
        findings.append(
            "\nData quality is acceptable but may limit analysis scope. "
            "Consider refining category definitions or validating join coverage."
        )
    else:
        findings.append("### ✓ RECOMMENDED TO PROCEED\n")
        findings.append(
            "Data quality is good. All required tables are present, join coverage is high, "
            "and prepared food categories have sufficient coverage for analysis."
        )

    findings.append("")

    return findings


def main():
    print("=" * 70)
    print("Instacart Dataset Audit")
    print("=" * 70)
    print()

    # Load data
    data = load_data()

    if not data:
        print("\nERROR: No data files found")
        print("Run: python scripts/ingest_data.py")
        return 1

    print()

    # Run audits
    all_findings = []

    all_findings.append("# Data Audit Report\n")
    all_findings.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    all_findings.append(
        "This report validates the Instacart dataset for quality and completeness.\n"
    )
    all_findings.append("---\n")

    print("Running schema validation...")
    all_findings.extend(audit_schemas(data))

    print("Checking for duplicates...")
    all_findings.extend(audit_duplicates(data))

    print("Verifying join coverage...")
    all_findings.extend(audit_joins(data))

    print("Checking missing values...")
    all_findings.extend(audit_missing_values(data))

    print("Analyzing user order statistics...")
    all_findings.extend(audit_user_orders(data))

    print("Identifying prepared food categories...")
    all_findings.extend(audit_prepared_foods(data))

    print("Generating recommendation...")
    all_findings.extend(generate_recommendation(data))

    # Write report
    DOCS_DIR.mkdir(exist_ok=True)
    report_path = DOCS_DIR / "DATA_AUDIT.md"

    with open(report_path, "w") as f:
        f.write("\n".join(all_findings))

    print()
    print("=" * 70)
    print(f"Audit complete: {report_path}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
