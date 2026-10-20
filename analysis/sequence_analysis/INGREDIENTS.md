# Ingredients & Categories

## The ingredient lens

A product ID says a customer bought "Chobani Blueberry Greek 5.3oz." An ingredient
says they bought yogurt. Recipes, meals, and preferences live at the ingredient
level, so we collapse 49,688 products into a recipe-ingredient taxonomy and analyze
there. Two things only become visible through this lens.

## What customers buy ≠ what the catalog stocks

![Ingredients by purchase volume](figures/ingredients_by_volume.png)

Counted as *products*, the catalog is dominated by packaged goods — thousands of
candy, vitamin, and cracker SKUs. Re-ranked by **actual purchase volume at the
ingredient level**, the picture inverts: **16 of the top 20 ingredients are fresh,
whole foods** — yogurt, bananas, milk, apples, avocados, onions, tomatoes, spinach.
Only granola bars, crackers, ice cream, and cereal represent packaged goods in the
top 20. The catalog is wide on packaged variety; the cart is deep on fresh staples —
a distinction invisible at the product grain, where no single banana SKU outranks the
sea of snack brands.

## A third of "variety" is the same ingredient, different package

![Brand multiplier distribution](figures/brand_multiplier.png)

The median customer buys **45 distinct products but only 34 distinct ingredients** —
a **1.33× brand multiplier** (median of per-customer ratios). A quarter of apparent
product variety is packaging churn, not dietary variety: someone cycling four yogurt
brands and three milks looks like an explorer in product data and a creature of habit
in ingredient data.

## Category loyalty is mostly arithmetic

The grain you measure at changes the story. A broad category (DAIRY) recurs in the
next order 59% of the time; an exact product only 29%. But against a chance baseline
that preserves each customer's basket mix, the **lift** inverts:

| Grain | P(next order) | Lift above chance |
|-------|--------------:|------------------:|
| Product | 28.7% | **1.29×** |
| Ingredient | 34.8% | 1.15× |
| Aisle | 43.3% | 1.09× |
| Category | 58.8% | 1.04× |

![Reorder lift by level](figures/reorder_lift_by_level.png)

Category recurrence is only 4% above chance — a broad bucket refills often simply
because it holds hundreds of products, not because customers are loyal to the family.
The genuine habit is at the **product** grain (29% above chance). The coarser the
bucket, the more "loyalty" is just aggregation. Full treatment, including why the
finer product grain carries the stronger signal, in the
[reorder-probability report](REORDER_PROBABILITY.md).

## Limitations

- The taxonomy is recipe-grounded but has judgment calls (prepared dishes vs. base
  ingredients, herb/spice granularity); 632 ingredient labels emerged from 446
  defined, as the classifier introduced distinctions.
- "Fresh vs packaged" in the volume view is a per-ingredient reading, not a
  nutritional classification.
