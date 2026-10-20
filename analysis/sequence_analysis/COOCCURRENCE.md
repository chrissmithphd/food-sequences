# Ingredient Co-occurrence Within Orders (Part 8)

## Research question

Which ingredients get bought together in the same order, and which pairings are
*distinctive* (they go together more than their individual popularity would predict)
versus just two common staples landing in the same big basket?

## Method

Deduplicate to one (order, ingredient). For the 200 most order-frequent ingredients,
count orders containing each pair (support) and compare to independence:

```
lift(a,b) = P(a and b in an order) / (P(a) · P(b))
```

High **support** = common pairing. High **lift** = the two appear together far more
than chance — a signature of a shared recipe or use. Computed over the whole dataset:
all 3,309,682 orders and all 542 observed ingredients, every pair evaluated. Pairs are
reported down to a support floor of 500 orders — the floor governs only which pairs are
frequent enough for a stable lift estimate, not which data is counted.

## Results

**Distinctive pairings (highest lift) are recipe signatures:**

| Pair | lift | support |
|------|-----:|--------:|
| cake_flour + powdered_sugar | 85.5 | 862 |
| bread_flour + yeast | 60.8 | 650 |
| garlic_powder + onion_powder | 55.3 | 1,783 |
| lasagna_noodles + ricotta | 50.7 | 740 |
| red_wine + wine | 45.2 | 6,491 |
| almond_flour + coconut_flour | 38.4 | 639 |
| baking_powder + baking_soda | 31.6 | 1,045 |
| champagne + red_wine | 30.6 | 1,051 |
| beef_broth + beef_roast | 28.1 | 812 |
| cayenne + cumin | 27.9 | 530 |
| chili_powder + kidney_beans | 27.9 | 1,079 |
| cumin + paprika | 26.9 | 878 |
| chili_powder + cumin | 26.2 | 855 |
| cumin + turmeric | 25.9 | 690 |

These resolve into recognizable cooking contexts:

- **Baking**: cake_flour + powdered_sugar, bread_flour + yeast, almond_flour +
  coconut_flour, baking_powder + baking_soda
- **Spice blends**: garlic_powder + onion_powder, the cumin cluster (paprika, chili
  powder, cayenne, turmeric) — the makings of chili and curry
- **Specific dishes**: lasagna_noodles + ricotta (lasagna), chili_powder + kidney_beans
  (chili), beef_broth + beef_roast (pot roast)
- **Alcohol stock-ups**: red_wine + wine, champagne + red_wine, champagne + wine

The very highest lifts come from specialty ingredients that are individually rare but
almost never bought except together for a recipe — which is exactly why evaluating
*all* ingredients, not just the most frequent, surfaces them.

**Popular pairings (highest support) are staples, with lift near 1:**

| Pair | support | lift |
|------|--------:|-----:|
| banana + yogurt | 354,386 | 1.44 |
| milk + yogurt | 320,475 | 1.47 |
| banana + milk | 308,371 | 1.37 |
| apple + banana | 290,063 | 1.70 |
| avocado + banana | 238,192 | 1.56 |
| apple + yogurt | 234,998 | 1.42 |

Banana, yogurt, milk, and apple co-occur constantly simply because each is in a huge
share of baskets. Their lift (1.3–1.7) is modestly above chance but nothing like the
recipe pairs.

## Interpretation

Support and lift answer different questions. Support tells you what fills carts: fresh
produce and dairy staples, together, constantly. Lift tells you what *goes together for
a purpose* — and the strongest signals are intact recipes: a baker's basket, a chili
spice set, lasagna ingredients. A bundling or recommendation strategy should use lift,
not support: high-support pairs are already in nearly every basket and need no
prompting, while high-lift pairs identify a recipe the customer is assembling and the
partner ingredient they might still need.

## Limitations

- Co-occurrence is within an order, not within a recipe or a meal; a single order can
  mix several meals and household needs.
- The support floor (500 orders) means pairings rarer than that are not ranked, though
  they are still counted toward each ingredient's totals.
- Lift is symmetric and pairwise; it does not capture directional or three-way combinations.
