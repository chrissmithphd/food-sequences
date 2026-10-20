# Prepared Dishes

Prepared meals are the most meal-subscription-relevant slice of grocery behavior, so
they get their own study: who buys them, how much they rely on them, which dishes are
popular down to the individual product, and how they reorder.

- Source: `analyze_prepared_foods.py` → `prepared_food_audit.csv`,
  `prepared_topics.csv`, `prepared_products.csv`, `prepared_engagement*.csv`.

## What counts as a prepared dish

A prepared dish is a **pre-made meal that still needs warming or cooking** — a frozen
dinner, pizza, lasagna, pot pie, mac & cheese, deli-prepared meal. Not a snack, not a
drink, not a cooking ingredient. We define it as the 17 meal types in the taxonomy's
*Prepared Dishes & Meals* section, **not** the raw per-product `is_prepared_dish`
flag, which was too broad (it also marked snacks, soda, coffee, even produce).
Condensed / cream-of soups are a cooking base, so they were split into
`condensed_soup` and excluded; ready-to-eat soup remains a dish. [Taxonomy](../classification/INGREDIENT_TAXONOMY.md)

## Reach and reliance

**59.6% of customers (122,794 of 206,062) buy at least one prepared dish** — a
majority, but far below the ~90% you get if snacks count.

![How much prepared-dish buyers rely on them](../figures/prepared_engagement.png)

Among buyers:

| Measure | p10 | median | p90 |
|---------|----:|-------:|----:|
| Prepared dishes as % of food items | 1.0% | **4.4%** | 15.7% |
| Orders containing a prepared dish | 7.7% | **30%** | 78% |
| Distinct prepared dish types bought | 1 | **2** | 5 |

For the typical buyer, prepared meals are an occasional convenience — about one item
in twenty, under a third of orders — not a dietary base. A heavy-tail minority leans
on them (top decile: ~16% of items). Reliance does **not** rise with overall purchase
volume (correlation of prepared-item-share with order count = −0.21): heavy grocery
shoppers do not buy proportionally more prepared meals.

## Which dish types are popular

![Prepared dish types by reach](../figures/prepared_topics.png)

| Dish type | Customers | Items | Repeat-buyers\* |
|-----------|----------:|------:|---------------:|
| frozen_meal | 54,229 | 323,757 | 62% |
| frozen_pizza | 41,479 | 166,969 | 59% |
| soup (ready-to-eat) | 41,033 | 154,365 | 50% |
| mac_and_cheese | 35,777 | 118,454 | 54% |
| deli_prepared | 31,445 | 122,057 | 53% |
| frozen_appetizer | 25,452 | 71,095 | 47% |
| chicken_nuggets | 21,925 | 69,636 | 54% |
| frozen_burrito | 13,635 | 51,054 | 53% |
| instant_ramen | 9,284 | 21,592 | 39% |
| frozen_lasagna | 8,191 | 20,700 | 45% |
| instant_soup / canned_chili / pot_pie / meal_kit / hot_pocket | 2k–7k each | — | 32–43% |

\*share of a type's buyers who bought it in ≥2 separate orders. The category is
dominated by the **freezer** (meals, pizza, appetizers, burritos, lasagna); frozen_meal
and frozen_pizza are the stickiest (59–62% come back).

## Down to the individual dish

Because a dish type collapses hundreds of products, here are the specific products
customers actually buy within the three largest types:

![Most-bought products within big dish types](../figures/prepared_products.png)

- **frozen_meal:** Macaroni & Cheese, Pad Thai, Pesto Tortellini Bowls, Beans & Rice
  Cheddar Burrito, Broccoli & Cheddar Bake — comfort and single-serve ethnic bowls.
- **soup:** Organic Chicken Noodle, Organic Creamy Tomato, Organic Lentil (plain and
  vegetable), Traditional Chicken Noodle — classic ready-to-eat cans/boxes.
- **deli_prepared:** Classic Chicken Salad, Avocado Roll, Sesame Seaweed Salad,
  Tabouleh — the grab-and-go deli case (sushi, salads).

`prepared_products.csv` has the full ranking with per-product buyer counts.

## How prepared dishes reorder

| Group | P(next order) | Lift above chance |
|-------|--------------:|------------------:|
| Prepared dishes | 29.8% | **1.44×** |
| Base ingredients | 28.7% | 1.29× |

A specific prepared dish is reordered slightly *more* than a base-ingredient product,
and more above chance — when someone finds a frozen meal they like, they re-buy that
exact SKU in runs at least as tightly as a staple. But *across* products within a dish
type, buyers **rotate** rather than commit (within-type stay probability 49.5%, lift
1.00 — chance; vs 63.6% for base ingredients). So prepared-dish behavior is: lock onto
specific dishes you like, while rotating through the menu — both repetition and
variety at once ([substitution detail](../sequences/)).

## What it might mean for a meal service

- Prepared-meal demand is a **minority, occasional** grocery behavior (60% reach, ~4%
  of items for the median buyer). A prepared-only service is serving the heavy tail,
  not the median grocery shopper.
- Stickiness is at the **specific-dish** level (re-buy the exact meal), while customers
  **rotate across the menu** within a type — a menu needs both reliable favorites and
  rotation.
- Frozen dominates; deli-prepared is the main non-frozen channel.

## Limitations

- Even restricted to the meal list, grocery frozen dinners / canned chili are not a
  clean proxy for chef-prepared meal kits — treat generalizations as hypotheses.
- Reach counts anyone who bought ≥1 prepared dish in the observed window.
- The ready-to-eat / cooking-base soup split is drawn by product name and has edge
  cases.
