# Ingredients & Categories

Everything else in this project rests on one move: analyze purchases by **ingredient
(a recipe role)** rather than by **product (a specific SKU)**. This report explains
what an ingredient is, how it differs from a product, and what that difference buys
you analytically.

- Source: `analyze_ingredient_lens.py` → `top_ingredients_by_volume.csv`,
  `ingredient_lens_summary.csv`, `per_customer_repertoire.parquet`
- Classification: 38,529 food products → 632 ingredient labels (446 defined in the
  taxonomy; the LLM introduced finer distinctions). [Taxonomy](../classification/INGREDIENT_TAXONOMY.md)

## What is an ingredient?

An ingredient is the recipe-level role a product plays, with brand, size, and flavor
stripped away. "Organic 2% Milk," "Whole Milk," and a store-brand gallon all map to
`milk`; "Chobani Blueberry 5.3oz" and "Fage Plain" both map to `yogurt`.

How many products collapse into one ingredient, and which products customers actually
buy for it (top products by purchase volume):

| Ingredient | Catalog products | What people actually buy (top products) |
|-----------|-----------------:|------------------------------------------|
| milk | 277 | Organic Whole Milk · Reduced Fat 2% Milk · Whole Milk |
| yogurt | 1,177 | Total 2% Strawberry Greek · plain Greek · fruit-on-bottom cups |
| banana | 18 | Banana · Bag of Organic Bananas · Organic Banana |
| frozen_meal | 881 | Macaroni & Cheese · Pesto Tortellini Bowls · Pad Thai |

Two things to notice. First, the collapse ratio varies wildly: `banana` is 18
products, `yogurt` is 1,177. Second, the mapping isn't always clean — `milk` sweeps in
a few protein shakes, `yogurt` catches a tzatziki, `banana` catches banana chips. The
taxonomy is a recipe-grounded best effort, not ground truth; edge cases exist and are
a real limitation.

## What customers buy ≠ what the catalog stocks

Rank ingredients two ways — by **share of actual purchases** and by **share of
catalog products** — and the two orderings disagree sharply.

![What customers buy vs what the catalog stocks](../figures/catalog_vs_volume.png)

| Ingredient | % of purchases | % of catalog products | Catalog products |
|-----------|---------------:|----------------------:|-----------------:|
| banana | 3.0% | 0.1% | 18 |
| avocado | 1.8% | 0.05% | 17 |
| strawberry | 1.6% | 0.1% | 28 |
| spinach | 1.2% | 0.1% | 43 |
| milk | 3.0% | 0.8% | 277 |
| — | | | |
| candy | 1.0% | 3.4% | 1,212 |
| granola_bar | 1.5% | 2.6% | 939 |
| crackers | 1.5% | 2.3% | 835 |
| ice_cream | 1.3% | 2.3% | 830 |

Fresh whole foods are a **large share of purchases from a tiny number of products** —
bananas are 3% of all food purchases spread over 18 SKUs. Packaged goods are the
opposite: candy is 1% of purchases spread over 1,212 SKUs. The catalog is wide where
branding is the product (snacks); the cart is deep where the food is the product
(produce). Counting products tells you how sellers stock shelves; counting purchases
tells you what people eat. **16 of the top 20 ingredients by volume are fresh whole
foods.**

![Ingredients by purchase volume](../figures/ingredients_by_volume.png)

## A third of "variety" is packaging, not diet

![Brand multiplier distribution](../figures/brand_multiplier.png)

The median customer buys **45 distinct products but only 34 distinct ingredients** —
a **1.33× brand multiplier** (median of per-customer ratios). About a quarter of a
customer's apparent product variety dissolves at the ingredient level: four yogurt
brands and three milks read as variety in product data and as habit in ingredient
data. The ingredient lens is what separates genuine dietary variety from packaging
churn — see [novelty & exploration](../novelty/) for how this plays out over time.

## The grain also sharpens reorder analysis

Reorder behavior depends on the grain you measure at: the genuine order-to-order habit
sits at the **product** grain (a specific product is reordered ~29% above a
customer's own frequency baseline), while broader grains have higher raw reorder rates
that are mostly aggregation. Full treatment in [sequences](../sequences/).

## Limitations

- 2,807 products (5.6%) are unclassified — the LLM declined low-confidence guesses.
- The taxonomy has judgment calls (prepared dish vs. base ingredient, herb/spice
  granularity, the `milk`/protein-shake edge); 632 labels emerged from 446 defined.
- "Fresh vs packaged" is read per ingredient, not from a nutrition label.
