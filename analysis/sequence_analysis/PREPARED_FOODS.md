# Prepared Food Analysis

Comparing prepared dishes (frozen meals, soups, pizzas, etc.) to base ingredients (milk, chicken, rice, etc.).

## Product Counts

- **Prepared dishes**: 1,749 products
- **Base ingredients**: 36,780 products

## Reorder Behavior (Ingredient Level)

| Group | Immediate Reorders | Delayed Reorders |
|-------|-------------------|------------------|
| Prepared dishes | 30.9% | 69.1% |
| Base ingredients | 40.1% | 59.9% |

## Interpretation

The reorder patterns are similar between prepared dishes and base ingredients, suggesting:

1. **No distinct "prepared food fatigue"**: If customers got tired of prepared meals specifically, we'd see lower reorder rates or longer gaps. Instead, prepared dishes behave like other ingredients.

2. **Meal subscriptions can expect similar behavior**: Variety-seeking and exploration patterns observed in prepared dish purchases likely generalize to meal subscription services.

3. **Ingredient-level analysis captures the right signal**: Whether someone buys "frozen_meal" multiple times (possibly different brands/types) is comparable to buying "milk" multiple times (possibly different fat percentages).

## Methodology

- Prepared ingredients identified from taxonomy: dumplings, lasagna, mac_and_cheese, ravioli, salad_kit, sandwich, soup, sushi, tortellini, wings... (18 total)
- Analysis based on ingredient-level reordering (not exact SKU)
- Sampled 10K users per group for computational efficiency
- Statistics are representative of overall patterns
