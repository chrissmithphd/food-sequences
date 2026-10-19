# Basket Composition Analysis

Each item in orders 2+ is classified based on purchase history:

- **Familiar product**: Exact SKU purchased before (exact repeat)
- **Familiar ingredient, new product**: Same ingredient but different product (brand/variant switching)
- **New ingredient**: Never purchased this ingredient before (novel food)

## Item-weighted (pooled)

Total items analyzed: 30,198,323

| Category | Count | Percentage |
|----------|-------|------------|
| Familiar product (exact repeat) | 19,301,985 | 63.9% |
| Familiar ingredient, new product | 4,353,579 | 14.4% |
| New ingredient (novel food) | 6,542,759 | 21.7% |

**Interpretation:** Product repeats account for 63.9% of purchases. Another 14.4% are brand/variant switches within familiar ingredients. Only 21.7% represent genuinely new ingredients.

## Customer-weighted

Customers analyzed: 197,435

| Category | Mean % |
|----------|--------|
| Familiar product (exact repeat) | 51.3% |
| Familiar ingredient, new product | 14.7% |
| New ingredient (novel food) | 34.0% |

**Why two denominators:** Item-weighting reflects overall volume. Customer-weighting gives equal voice to each customer regardless of order size.

## Key Findings

1. **Most variety is brand switching, not dietary change:** 78.3% of purchases are familiar ingredients (either exact repeats or switched products).

2. **True novelty is limited:** Only 21.7% of items represent genuinely new ingredients never purchased before.

3. **Meal subscription implications:** Customers may want variety in presentation (different recipes, preparations) while maintaining familiar core ingredients. "New" meals that combine familiar ingredients differently may be more appealing than meals with genuinely unfamiliar foods.
