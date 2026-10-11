# Food Ontology (recipe-ingredient clustering, v2)

The frozen labels are in [`analysis/outputs/food_roles_v2.csv`](../analysis/outputs/food_roles_v2.csv)
(one row per product). This document defines the ontology those labels follow.

## Clustering rule

A **cluster** is what a recipe's ingredient line names. Two products share a cluster
when a cook could swap one for the other **without changing what they'd write in the
recipe** — "1 cup milk", "1 onion", "2 cups chicken broth", "1 cup shredded cheddar".

- **Attributes, not cluster boundaries:** brand, organic, size, fat level, packaging.
  (Whole vs 2% milk is one cluster, `milk`, with `fat_level` as an attribute.)
- **Splits a cluster** only when the difference changes the recipe's flavor or role:
  dairy milk vs plant milk; cheddar vs mozzarella; broth vs soup; pasta vs mac & cheese;
  ingredient vs finished dish (eggs vs egg scramble; pizza dough vs pizza).
- **Aisle is a weak prior**, not evidence — a candidate net only; the product name decides.
- Unmatched names are left **`unresolved`**; nothing is force-fit.

## Hierarchy

`SKU (product_id)` → `cluster` (the equivalence unit) → `role_family` (broad grouping).
Each product also carries attributes (organic, fat_level, gluten_free, flavored).

## Cluster catalog

Share = percent of total purchase volume. Clusters within a family listed by volume.

### produce_fruit — 19.3%
banana, apple, berry_strawberry, berry_blueberry, berry_raspberry, berry_blackberry,
grape, citrus_lemon, citrus_lime, citrus_orange, avocado, melon, stone_fruit,
tropical_fruit, pear

### produce_veg — 17.4%
leafy_green, onion, garlic, ginger, tomato_fresh, potato, carrot, celery, pepper,
bell_pepper, cucumber, zucchini_squash, broccoli_cauliflower, mushroom, corn, peas,
asparagus, green_beans, cabbage, brussels_sprouts, beet, radish, eggplant, fresh_herb

### dairy — 14.6%
milk, cheese, yogurt, butter, cream_cheese, cottage_or_ricotta, sour_cream

### beverages — 5.5%
water, juice, coffee, soda, tea, wine, beer

### protein — 4.9%
chicken, ground_beef_or_beef, pork, turkey, bacon_sausage, deli_lunchmeat,
fish_seafood, tofu_meat_alt

### bread_and_baked — 4.3%
bread, tortilla_flatbread

### snacks — 3.3%
nuts_seeds, chips, crackers, cookies_sweets, granola_bar

### cooking_fats_creamers — 2.2%
half_and_half, heavy_cream

### grains — 2.0%
rice, oats, quinoa_other_grain

### milk_and_alternatives — 2.0%  (non-dairy; distinct flavor/role from dairy milk)
plant_milk, coconut_milk

### prepared_dish — 1.6%  (finished dishes / kits — NOT the base ingredient)
boxed_mac_and_cheese, frozen_pizza, frozen_or_prepared_meal

### condiments — 1.5%
olive_oil, cooking_oil, vinegar, soy_sauce, hot_sauce, ketchup, mustard, mayo,
salad_dressing

### eggs — 1.5%
eggs, egg_whites_or_substitute

### pasta_ingredient — 1.1%  (dry/fresh pasta you cook; shape = attribute)
pasta, filled_pasta

### Other families
cooking_liquids (stock_or_broth), soups (soup), tomato_bases (canned_tomatoes,
tomato_paste), sauces (pasta_sauce, salsa), legumes (beans_legumes), spreads
(nut_butter, jam_jelly, honey_syrup, hummus_dip), baking (flour, sugar), baking_acids
(buttermilk), seasonal_beverage (eggnog), breakfast (cereal), frozen (ice_cream).

## Boundary adjudications (reference)

| Product | cluster | role_family | why |
|---|---|---|---|
| Whole / 2% / fat-free milk | milk | dairy | fat is an attribute, not a boundary |
| Almond / oat / soy milk | plant_milk | milk_and_alternatives | distinct flavor/role from dairy |
| Coconut milk | coconut_milk | milk_and_alternatives | curry base, distinct flavor |
| Cultured buttermilk | buttermilk | baking_acids | recipe acid, not drinking milk |
| Eggnog | eggnog | seasonal_beverage | beverage, not a milk substitute |
| Chicken stock / beef broth / bouillon | stock_or_broth | cooking_liquids | interchangeable base |
| Chicken noodle soup | soup | soups | finished dish |
| "Mac & Cheese Dinner" (boxed) | boxed_mac_and_cheese | prepared_dish | cheese-pasta kit; "Dinner" is brand copy |
| Dry spaghetti (any brand) | pasta | pasta_ingredient | boil-and-serve ingredient |

## Coverage

v2 resolves **87.2% of purchase volume** (65.7% of distinct products; 108 clusters).
Volume is concentrated — the top ~4,600 products (9% of the catalog) are ~80% of
purchases — so the resolved head covers nearly all actual purchasing. The rare long
tail is left `unresolved` by design. A stratified validation sample is in
[`food_roles_validation.md`](../analysis/outputs/food_roles_validation.md).

---

### Footnote: history

v1 grouped by aisle + surface-string keywords and over-split by attribute (e.g. a
separate category per milk-fat level). It also mislabeled role (boxed mac & cheese
read as a "dinner"; broth not separated from soup). v2 replaces that with
recipe-ingredient clustering decided by culinary role, with attributes preserved.
Labels are frozen and versioned for reproducibility; re-labeling is an explicit
version bump. The superseded v1 code (`food_mapping.py`) is retained but not used.
