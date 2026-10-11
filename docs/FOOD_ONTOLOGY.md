# Role-Based Food Ontology (design spec, v2)

**Status:** design for review. Supersedes the v1 regex/aisle mapping
(`food_mapping.py`), which is retained but marked legacy/provisional.

## Why this exists

Earlier mappings grouped products by aisle + surface-string keywords. That failed
on *role*: it called a boxed "Mac & Cheese **Dinner**" a prepared dinner, matched
"g‑**oat milk**" as oat milk, and could not separate cooking **broth** from **soup**
(same aisle) or **buttermilk** (a baking acid) from drinking milk. Evidence from
this dataset:

- Almond milk appears across **six** aisles (soy-lactosefree, coffee, ice cream,
  yogurt, milk, "missing") — aisle does **not** cleanly separate plant from dairy milk.
- "Buttermilk" spans cultured buttermilk (milk aisle), buttermilk **pancake mix**,
  and buttermilk **ranch** — three roles, one string.
- Broth (106) and stock (59) sit in the **same aisle as soup**.

Grounding references: stock/broth/bouillon are "largely interchangeable" cooking
bases and distinct from soup, a finished dish (Wikipedia, *Stock (food)*; James
Beard). Plant milks are a category distinct from dairy; almond/oat/soy fill a
similar role while coconut milk is a distinct culinary category, and flavor
profiles make them "not interchangeable substitutes" (Wikipedia, *Plant milk*).

## Principles

1. **Equivalence = culinary role.** Two products are equivalent if they can play
   the same role in a recipe with a compatible flavor profile — i.e. a cook could
   substitute one for the other. Role is the decision.
2. **Flavor profile is the secondary splitter.** Same nominal role but a flavor
   that changes the dish stays separate (coconut milk vs. oat milk; tomato vs.
   alfredo sauce).
3. **Ingredient ≠ finished dish.** Dry pasta ≠ boxed mac & cheese ≠ frozen pasta
   dinner. Eggs ≠ egg scramble. Pizza dough ≠ finished pizza. Broth ≠ soup.
4. **Aisle is a weak prior, not evidence.** Start the candidate pool from aisles,
   but override when the name signals a different role.
5. **Ignore brand copy.** Words like "Dinner," "Deluxe," "Classic," "Homestyle"
   are marketing, not role signals.
6. **Preserve attributes, don't collapse them:** dairy-vs-plant, flavor profile,
   fat level, dietary restriction (gluten-free, vegan), prepared-vs-ingredient,
   physical form. Dietary distinctions must remain queryable.
7. **Leave ambiguous items `unresolved`.** Never force a match. Report confidence
   and a reason for every assignment.
8. **Labels are frozen + versioned.** The LLM/culinary judgment runs once and is
   committed as a reviewable CSV; downstream analysis reproduces from the frozen
   file. Re-labeling is a deliberate version bump with a diff.

## Hierarchy

- **SKU** — the product.
- **role_category** — substitutable within a recipe (the equivalence unit):
  e.g. `cooking_stock_broth`, `dairy_milk_2pct`, `plant_milk_neutral`,
  `boxed_mac_and_cheese`, `pasta_dry_spaghetti`, `tomato_pasta_sauce`.
- **role_family** — broader grouping that keeps meaningful variants as attributes:
  e.g. `cooking_liquids`, `milk_and_alternatives`, `pasta_ingredient`,
  `prepared_pasta_dish`, `sauces`.

## Role families (broad target set)

Marked ⬤ = priority for first labeling batch (highest purchase volume + the hard
cases we discussed); ○ = subsequent batches.

### ⬤ milk_and_alternatives
- `dairy_milk_{skim,1pct,2pct,whole}` — cow milk by fat (flavor: neutral dairy)
- `plant_milk_neutral` — almond, oat, soy, cashew, rice, pea (dairy-milk substitute role)
- `coconut_milk` — separate (curry/cooking base, distinct flavor)
- `buttermilk_cultured` → actually role_family `baking_leavening_acids` (NOT milk)
- `eggnog` → role_family `seasonal_beverages` (NOT milk)
- `cream_half_and_half` → role_family `cooking_fats_creamers`
- Attributes: dairy|plant, flavored, fat_level, lactose_free, organic

### ⬤ cooking_liquids
- `cooking_stock_broth` — stock + broth + bouillon (interchangeable base)
  - Attribute protein: chicken|beef|vegetable|bone|seafood
- (soups are a *different* family, below)

### ⬤ soups (finished dish — NOT a base)
- `canned_soup`, `dry_soup_mix`, `fresh_refrigerated_soup`

### ⬤ pasta_ingredient (dry/fresh pasta you cook)
- `pasta_dry_{spaghetti,penne,macaroni,…}` by shape; attributes: egg, whole_grain,
  gluten_free, flavor, fresh|dry, filled (ravioli/tortellini = `filled_pasta`)

### ⬤ prepared_pasta_dish (finished/kit — NOT pasta ingredient)
- `boxed_mac_and_cheese` (pantry kit), `frozen_pasta_meal`, `deli_pasta_meal`

### ○ sauces
- `tomato_pasta_sauce`, `cream_alfredo_sauce`, `pesto`, `salsa`, `asian_sauce`,
  `gravy`, `marinade` — flavor profile is the splitter; sauce ≠ the dish it tops

### ○ cheese
- `shredded_cooking_cheese`, `sliced_sandwich_cheese`, `block_cheese`,
  `cream_cheese_spread`, `cottage_ricotta`, `specialty_cheese`, `grated_hard_cheese`

### ○ eggs_ingredient
- `eggs_{large,xlarge,jumbo,medium}`, `egg_whites`, `egg_substitute`; prepared egg
  dishes (scramble/bites) → `prepared_breakfast` family

### ○ bread_and_baked
- `sandwich_bread`, `buns_rolls`, `tortilla_flatbread`, `bagels`, `bakery_dessert`

### ○ yogurt
- `plain_yogurt` (cooking/base), `flavored_yogurt_snack`, `greek_yogurt`,
  `drinkable_yogurt`, `non_dairy_yogurt`

### ○ further families (later batches)
breakfast_cereal, hot_cereal, nut_butters_spreads, jams_honey, baking_ingredients
(flour/sugar/leavening), oils_vinegars, fresh_fruit, fresh_vegetables,
raw_proteins (meat/poultry/seafood), deli_lunchmeat, frozen_prepared_meals,
beverages (soda/juice/water/coffee/tea), snacks (chips/crackers/candy), condiments.

## Hard-case adjudications (reference)

| Product pattern | role_category | role_family | Rationale |
|---|---|---|---|
| "Mac & Cheese Dinner" (boxed) | boxed_mac_and_cheese | prepared_pasta_dish | cheese-pasta kit; "Dinner" is brand copy |
| Frozen lasagna / ziti dinner | frozen_pasta_meal | prepared_pasta_dish | finished meal, not an ingredient |
| Dry spaghetti (any brand) | pasta_dry_spaghetti | pasta_ingredient | boil-and-serve ingredient |
| Chicken stock / beef broth / bouillon | cooking_stock_broth | cooking_liquids | interchangeable base |
| Chicken noodle soup | canned_soup | soups | finished dish |
| Almond/oat/soy milk | plant_milk_neutral | milk_and_alternatives | dairy-milk substitute role |
| Coconut milk (can) | coconut_milk | milk_and_alternatives | curry base, distinct flavor |
| Cultured buttermilk | buttermilk_cultured | baking_leavening_acids | recipe acid, not drinking milk |
| Buttermilk pancake mix | pancake_waffle_mix | baking_mixes | a mix, not buttermilk |
| Eggnog | eggnog | seasonal_beverages | beverage, not a milk substitute |
| 2% milk | dairy_milk_2pct | milk_and_alternatives | distinct flavor/role from plant milk |

## Labeling plan (frozen, versioned, volume-prioritized)

1. Rank products by total purchase count so labeling effort covers the most of
   actual purchases first; the rare long tail may remain `unresolved`.
2. Assign `role_category`/`role_family`/attributes per the adjudications above,
   family by family, starting with the ⬤ set.
3. Emit `food_roles_v2.csv` (product_id, name, aisle, role_family, role_category,
   attributes, confidence, status, reason, version) + an examples doc + a
   stratified manual-validation sample.
4. Human review of the validation sample before any downstream (combinations,
   novelty) is run on these labels.

## Reproducibility note

`food_roles_v2.csv` is the frozen artifact of a judgment-based labeling step.
It is committed and diffable; downstream code reads it deterministically. The
labeling step is documented here, not re-run automatically, so results do not
drift when the model changes. A version bump (v3) is an explicit, reviewed event.
