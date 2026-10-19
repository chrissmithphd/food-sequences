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

**Why two denominators:** 
- **Item-weighted**: Counts every item purchase (heavy buyers with large orders dominate)
- **Customer-weighted**: Average each customer's percentages first, then average those (every customer has equal voice regardless of order size)

The difference reveals that heavy buyers stick to familiar products more (64% vs 51% familiar) while lighter buyers explore more (34% vs 22% new ingredients).

## Key Findings

1. **Novelty drives variety more than brand switching:** New ingredients (21.7%) are more common than brand switches (14.4%). Customers try genuinely new foods more often than they just change brands of familiar ingredients.

2. **But most purchases are still familiar:** 78.3% of purchases are known ingredients (63.9% exact repeats + 14.4% brand switches). Exploration happens, but repetition dominates volume.

3. **Individual customers explore more than volume suggests:** Customer-weighted shows 34% new ingredients vs 22% item-weighted. This means people who buy less explore more, while heavy buyers stick to routines.
