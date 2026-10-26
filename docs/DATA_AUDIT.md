# Data Audit Report

**Generated**: 2026-10-08 15:37:25

This report validates the Instacart dataset for quality and completeness.

---

## Schema Validation

### orders

- **Rows**: 3,421,083
- **Columns**: 7
- ✓ Schema matches expected structure

### products

- **Rows**: 49,688
- **Columns**: 4
- ✓ Schema matches expected structure

### aisles

- **Rows**: 134
- **Columns**: 2
- ✓ Schema matches expected structure

### departments

- **Rows**: 21
- **Columns**: 2
- ✓ Schema matches expected structure

### order_products_prior

- **Rows**: 32,434,489
- **Columns**: 4
- ✓ Schema matches expected structure

### order_products_train

- **Rows**: 1,384,617
- **Columns**: 4
- ✓ Schema matches expected structure

## Duplicate Detection

### orders

- ✓ `order_id` is unique (3,421,083 values)
- ✓ No fully duplicate rows

### products

- ✓ `product_id` is unique (49,688 values)
- ✓ No fully duplicate rows

### aisles

- ✓ `aisle_id` is unique (134 values)
- ✓ No fully duplicate rows

### departments

- ✓ `department_id` is unique (21 values)
- ✓ No fully duplicate rows

### order_products_prior

- ✓ Composite key ['order_id', 'product_id'] is unique (32,434,489 combinations)
- ✓ No fully duplicate rows

### order_products_train

- ✓ Composite key ['order_id', 'product_id'] is unique (1,384,617 combinations)
- ✓ No fully duplicate rows

## Join Coverage

### Orders → Order Products (Prior)

- Prior orders: 3,214,874
- Orders with items: 3,214,874
- **Coverage**: 100.00%
- ✓ High join coverage

### Products → Aisles/Departments

- Products with valid aisle: 49,688 / 49,688
- Products with valid department: 49,688 / 49,688

## Missing Values

### orders

- `days_since_prior_order`: 206,209 (6.03%)

## User Order Statistics

- **Total users**: 206,209
- **Total orders**: 3,421,083
- **Mean orders per user**: 16.6
- **Median orders per user**: 10
- **Min/Max orders per user**: 4 / 100

**Distribution**:

- 1-5 orders: 43,576 users (21.1%)
- 6-10 orders: 60,937 users (29.6%)
- 11-20 orders: 50,965 users (24.7%)
- 21-50 orders: 39,821 users (19.3%)
- 51-100 orders: 10,910 users (5.3%)
- 100+ orders: 0 users (0.0%)

### Order Number Continuity

- ✓ All users have continuous order_number sequences (1, 2, 3, ...)

## Prepared Food Categories (keyword-based pre-classification estimate)

> **Note:** This section uses a keyword-based aisle/department filter to estimate
> prepared food coverage before the LLM classification was run. The subsequent
> classification identified 8,278 prepared dishes using a recipe-grounded taxonomy
> (see `docs/FOOD_CLASSIFICATION.md` and `data/food_classification.csv`). The numbers below are the pre-classification
> estimate; the 8,278 figure is the authoritative count.



### Aisles (Prepared Foods)

- `frozen pizza` (ID: 79, 335 products)
- `frozen meals` (ID: 38, 880 products)
- `prepared meals` (ID: 13, 317 products)
- `prepared soups salads` (ID: 1, 146 products)
- `fresh pasta` (ID: 12, 123 products)
- `hot dogs bacon sausage` (ID: 106, 387 products)

### Departments (Prepared Foods)

- `frozen` (ID: 1, 4007 products)
- `deli` (ID: 20, 1322 products)

### Prepared Food Product Coverage

- **Total products**: 49,688
- **Prepared food products**: 5,839
- **Coverage**: 11.75% of catalog

**Sample products** (first 10):

- Smart Ones Classic Favorites Mini Rigatoni With Vodka Cream Sauce (frozen meals)
- Cut Russet Potatoes Steam N' Mash (frozen produce)
- Chocolate Fudge Layer Cake (frozen dessert)
- Pizza for One Suprema  Frozen Pizza (frozen pizza)
- Three Cheese Ziti, Marinara with Meatballs (frozen meals)
- Italian Herb Porcini Mushrooms Chicken Sausage (hot dogs bacon sausage)
- Traditional Lasagna with Meat Sauce Savory Italian Recipes (frozen meals)
- Beef Hot Links Beef Smoked Sausage With Chile Peppers (hot dogs bacon sausage)
- Raisin Cinnamon Bagels 5 count (frozen breads doughs)
- Vegetarian Grain Meat Sausages Italian - 4 CT (tofu meat alternatives)

### Prepared Food Purchase Frequency

- **Total purchases**: 32,434,489
- **Prepared food purchases**: 3,630,063
- **Purchase rate**: 11.19%
- **Orders with prepared foods**: 1,672,463 / 3,214,874
- **Order penetration**: 52.02%

## Recommendation

### ✓ RECOMMENDED TO PROCEED

Data quality is good. All required tables are present, join coverage is high, and prepared food categories have sufficient coverage for analysis.
