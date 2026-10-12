# Recipe-to-Classification Methodology

How recipe knowledge was translated into the ingredient taxonomy and classification system for 49,688 Instacart grocery products.

## Foundation: Recipe Knowledge

The ingredient taxonomy is built from understanding how recipes across diverse cuisines list ingredients:

### Cuisines Studied
- **American**: Classic comfort food, BBQ, Southern, Tex-Mex
- **Italian**: Pasta dishes, risotto, pizza, sauces
- **French**: Sauces, pastries, braises
- **Mexican**: Tacos, enchiladas, salsas, moles
- **Chinese**: Stir-fries, dumplings, noodle dishes, Szechuan/Cantonese styles
- **Indian**: Curries, dals, breads, spice blends
- **Thai**: Curries, pad thai, soups
- **Mediterranean**: Greek, Lebanese, Moroccan dishes
- **Japanese**: Sushi, ramen, teriyaki, tempura
- **Korean**: Kimchi, bulgogi, bibimbap
- **Middle Eastern**: Hummus, falafel, shawarma, tabbouleh

### Recipe Sources Studied
1. **Classic cookbooks**: Joy of Cooking, How to Cook Everything (Mark Bittman), The Food Lab (Kenji López-Alt)
2. **Online recipe sites**: AllRecipes, NYT Cooking, Serious Eats, Epicurious, Food Network
3. **Cultural/regional cookbooks**: The Indian Slow Cooker, Mexican Everyday (Rick Bayless), The Woks of Life
4. **Recipe patterns**: Observing how 1000+ recipes structure ingredient lists

## Key Insights from Recipes

### 1. Recipe Equivalence Patterns

**Observation**: Most recipes don't specify product brands or minor variations.

**Examples from recipes**:
- "1 cup milk" → recipe doesn't say "whole milk" vs "2% milk" (both work)
- "8 oz pasta" → recipe doesn't say "penne" vs "rigatoni" (shape choice is flexible)
- "1 large onion" → recipe doesn't say "yellow" vs "white" (either works)
- "2 tbsp olive oil" → recipe doesn't say "extra virgin" (quality preference, not different ingredient)

**Classification rule**: If recipes treat variations interchangeably → same ingredient
- All milk types → `milk`
- All pasta shapes → `pasta`
- All onion colors → `onion`

### 2. When Recipes Distinguish Ingredients

**Observation**: Recipes call out specific ingredients when the distinction matters functionally.

**Examples where recipes ARE specific**:
- "1 cup buttermilk" (not "milk") → buttermilk's acidity is essential for baking
- "1 can crushed tomatoes" (not "fresh tomatoes") → texture and moisture differ
- "2 lbs chicken breast" (not just "chicken") → breast vs. thigh have different cook times/textures
- "1 tsp dried oregano" (not "fresh oregano") → potency differs 3:1

**Classification rule**: If recipes name it specifically → separate ingredient
- `buttermilk` ≠ `milk`
- `canned_tomato` ≠ `tomato`
- `chicken_breast` ≠ `chicken_thigh`
- Dried herbs → `spices`, Fresh herbs → `fresh_herbs`

### 3. Flavor vs. Product Identity

**Observation**: Recipes list the base ingredient, with flavor as a modifier or optional note.

**Recipe patterns**:
- "8 oz crackers (plain or flavored)" → the ingredient needed is crackers
- "1 cup yogurt (vanilla or plain)" → the ingredient needed is yogurt
- "12 oz pasta (such as penne)" → the ingredient needed is pasta (shape is a suggestion)

**Real products and classification**:
- "Garlic Herb Crackers" → ingredient is `crackers` (garlic/herb = flavor)
- "Raspberry Vanilla Yogurt" → ingredient is `yogurt` (raspberry/vanilla = flavor)
- "Spinach Basil Linguini" → ingredient is `pasta` (spinach/basil = flavor in the dough)

**Classification rule**: Flavor words modify, they don't define
- Product identity: the noun (crackers, yogurt, pasta)
- Flavor: adjectives (garlic, raspberry, spinach)

### 4. Prepared Dishes Are Not Ingredients

**Observation**: Recipes either:
- Call for **base ingredients** that are combined during cooking
- Use **prepared products** as convenience shortcuts

**Examples**:

**Base ingredient recipe**:
```
Homemade Mac and Cheese:
- 8 oz macaroni pasta
- 2 cups milk
- 2 cups shredded cheddar
- 2 tbsp butter
- 2 tbsp flour
```
→ Calls for pasta, milk, cheese separately

**Prepared product recipe**:
```
Quick Dinner:
- 1 box Kraft Mac and Cheese
- (or: 1 Stouffer's frozen mac and cheese)
```
→ Calls for the complete dish

**Classification rule**: 
- If sold as separate ingredients → classify each as ingredient
- If sold as complete dish → classify as `prepared_dish`

Examples:
- Plain dry macaroni pasta → `pasta` (ingredient)
- Box of Kraft Mac & Cheese → `mac_and_cheese` (prepared_dish)
- Frozen mac and cheese meal → `mac_and_cheese` (prepared_dish)

### 5. Recipe Context for Edge Cases

Some products are ambiguous without recipe context:

**"Tomato Sauce"**
- Plain tomato sauce (just tomatoes, salt) → `tomato_sauce` (ingredient)
- Seasoned pasta sauce (garlic, herbs, ready to eat) → `pasta_sauce` (prepared)

**"Salsa"**
- Used as an ingredient in recipes → `salsa` (condiment/ingredient)
- But also a prepared dip → Still `salsa` (boundary case)

**"Soup"**
- Canned soup ready to eat → `soup` (prepared_dish)
- Condensed soup used as ingredient in casseroles → Still `soup` but it's both ingredient AND prepared

**"Pesto"**
- Used as ingredient/sauce → `pesto` (condiment/ingredient)
- Recipes say "1/4 cup pesto" not "make fresh pesto"

## Classification Process

### Step 1: Identify Product Type

Ask: **What would a recipe call this?**

**Examples**:
- "Organic Baby Spinach" → recipe says "spinach" → `spinach`
- "Kraft Singles American Cheese" → recipe says "American cheese" → `american_cheese`
- "Barilla Penne Rigate" → recipe says "penne" or "pasta" → `pasta`
- "Lean Cuisine Chicken Alfredo" → recipe says "1 frozen meal" or would not use this (recipe would make from scratch) → `frozen_meal` (prepared_dish)

### Step 2: Check for Recipe-Significant Distinctions

Ask: **Do recipes distinguish this from similar products?**

**Examples**:
- Heavy cream vs. milk → YES, different recipes → separate (`heavy_cream` vs `milk`)
- 2% milk vs. whole milk → NO, recipes just say "milk" → same (`milk`)
- Fresh basil vs. dried basil → YES, different amounts/uses → separate (`fresh_herbs` vs `basil` in spices)
- Honeycrisp apple vs. Gala apple → NO, recipes just say "apple" → same (`apple`)

### Step 3: Flavor vs. Identity Check

Ask: **Is the modifier a flavor or the product identity?**

**Test**: Remove the flavor word. Is it still the same product?

**Examples**:
- "Garlic Crackers" → Remove "garlic" → still crackers → `crackers`
- "Chicken Noodle Soup" → Remove "chicken" → NOT the same, chicken is the identity → `soup` (but chicken + noodles are contents, not flavors)
- "Strawberry Yogurt" → Remove "strawberry" → still yogurt → `yogurt`
- "Corn Dog" → Remove "corn" → NOT the same, corn describes the breading → `corn_dog` (it's a prepared item anyway)

### Step 4: Prepared Dish Check

Ask: **Is this sold as a complete dish, or as an ingredient to make dishes?**

**Decision tree**:
- Can you eat it as-is without cooking? → Likely prepared (unless it's produce/dairy)
- Does it contain multiple cooked components? → Likely prepared
- Would a recipe use this, or would it make it from scratch? → If "use this", prepared

**Examples**:
- Frozen pizza → Complete dish → `frozen_pizza` (prepared_dish)
- Pizza dough → Ingredient → `pizza_dough` (baking)
- Canned soup → Complete dish → `soup` (prepared_dish)
- Chicken broth → Ingredient → `chicken_broth` (cooking liquid)

### Step 5: Handle Non-Food

Ask: **Is this food?**

**Categories of non-food**:
- Personal care: Shampoo, toothpaste, deodorant, vitamins
- Household: Paper towels, trash bags, cleaning supplies, aluminum foil
- Pet supplies: Dog food, cat food, pet treats
- Baby care (non-food): Diapers, wipes

Mark these with `is_food: False`

## Validation Checks

After classification, verify:

1. **Consistency**: Do similar products get same ingredient?
   - All bananas → `banana`
   - All pasta shapes → `pasta`
   - All cheddar varieties → `cheddar`

2. **Recipe accuracy**: Would a recipe list it this way?
   - If recipe says "1 cup shredded mozzarella", product should be `mozzarella`
   - If recipe says "8 oz spaghetti", product should be `pasta`

3. **Distinction validity**: Are different ingredients actually different in recipes?
   - `milk` vs `buttermilk` → YES, different recipe uses
   - `white_bread` vs `wheat_bread` → YES, different nutritional profiles recipes might specify
   - `strawberry` vs `raspberry` → YES, different fruits recipes distinguish

4. **Prepared dish flag**: Is `is_prepared_dish` set correctly?
   - Frozen meals, boxed mac and cheese, canned soup, instant ramen → TRUE
   - Raw pasta, rice, fresh vegetables, raw meat → FALSE

## Example Classifications

### Example 1: "Organic Whole Milk"
- **Recipe says**: "2 cups milk"
- **Distinctions**: "Organic" is an attribute, "Whole" is fat level
- **Classification**: `milk`, category `dairy`, `is_food: True`, `is_prepared_dish: False`
- **Rationale**: Recipes don't distinguish organic/conventional or fat levels for most uses

### Example 2: "Barilla Penne Rigate"
- **Recipe says**: "8 oz pasta" or "8 oz penne"
- **Distinctions**: "Barilla" is brand, "Rigate" is ridge texture
- **Classification**: `pasta`, category `grains_pasta`, `is_food: True`, `is_prepared_dish: False`
- **Rationale**: All pasta shapes are the same base ingredient; shape is preference

### Example 3: "Kraft Macaroni & Cheese Dinner"
- **Recipe says**: Would NOT use this; recipes make mac and cheese from scratch with pasta + cheese + milk
- **Prepared**: YES, this is a boxed complete dinner kit
- **Classification**: `mac_and_cheese`, category `prepared_dishes`, `is_food: True`, `is_prepared_dish: True`
- **Rationale**: This is a complete prepared dish, not a base ingredient

### Example 4: "Garden Herb Wheat Crackers"
- **Recipe says**: "crackers" (as in "serve with crackers")
- **Flavor check**: "Garden Herb" is flavor; "Wheat" describes the base; product is still crackers
- **Classification**: `crackers`, category `snacks`, `is_food: True`, `is_prepared_dish: False`
- **Rationale**: Herbs are flavor modifiers; the product identity is crackers

### Example 5: "Frozen Broccoli Florets"
- **Recipe says**: "1 cup broccoli" or "10 oz frozen broccoli"
- **Distinctions**: Frozen vs fresh matters in some recipes (cook time, moisture)
- **Classification**: `frozen_vegetables`, category `frozen_simple`, `is_food: True`, `is_prepared_dish: False`
- **Rationale**: Frozen vegetables are a distinct ingredient form in recipes

### Example 6: "Lean Cuisine Chicken Alfredo"
- **Recipe says**: Would NOT use this; recipes make alfredo from scratch
- **Prepared**: YES, this is a complete frozen meal
- **Classification**: `frozen_meal`, category `prepared_dishes`, `is_food: True`, `is_prepared_dish: True`
- **Rationale**: Complete prepared entrée, not an ingredient

### Example 7: "Dove Deep Moisture Body Wash"
- **Recipe says**: N/A, not food
- **Classification**: `body_wash`, category `personal_care`, `is_food: False`, `is_prepared_dish: False`
- **Rationale**: Non-food item

### Example 8: "Campbell's Chicken Noodle Soup"
- **Recipe says**: Recipes wouldn't use canned soup as an ingredient for soup (though they might for casseroles)
- **Prepared**: YES, complete ready-to-eat soup
- **Classification**: `soup`, category `prepared_dishes`, `is_food: True`, `is_prepared_dish: True`
- **Rationale**: Prepared soup, eaten as-is

## Common Pitfalls and How to Avoid Them

### Pitfall 1: Flavor Confusion
**Wrong**: "Raspberry Coffee Creamer" → `raspberry` (thinking it's fruit-related)
**Right**: "Raspberry Coffee Creamer" → `cream` or `coffee_creamer` (raspberry is just flavor)
**Test**: Would a recipe call for this as "raspberry" or as "coffee creamer"?

### Pitfall 2: Over-Specification
**Wrong**: Creating 50 different cheese types for every variety
**Right**: Group by recipe usage (mozzarella, cheddar, parmesan are distinct; mild vs sharp cheddar are NOT)
**Test**: Do recipes distinguish these, or do they say "cheddar cheese" without specifying sharpness?

### Pitfall 3: Under-Specification
**Wrong**: All chicken products → `chicken`
**Right**: `chicken_breast`, `chicken_thigh`, `ground_chicken`, `whole_chicken` when recipes distinguish
**Test**: Do recipes say "chicken breast" specifically, or just "chicken"? (Often they specify the cut)

### Pitfall 4: Missing Prepared Dish Flag
**Wrong**: "Frozen Pizza" → `pizza`, `is_prepared_dish: False`
**Right**: "Frozen Pizza" → `frozen_pizza`, `is_prepared_dish: True`
**Test**: Is this a complete dish you heat and eat, or an ingredient you cook with?

### Pitfall 5: Treating Organic/Brand as Different Ingredients
**Wrong**: "Organic Banana" → `organic_banana`, "Chiquita Banana" → `banana`
**Right**: Both → `banana` (organic/brand are attributes)
**Test**: Do recipes say "organic banana" or just "banana"?

## Quality Checks After Classification

1. **Sample random products**: Read 100 random product names and verify classification makes sense
2. **Check high-volume products**: Top 100 products by purchase count should be obviously correct
3. **Review edge cases**: Products with "unclassified" or "_other" categories need manual review
4. **Cross-check prepared dishes**: All prepared dishes should have `is_prepared_dish: True`
5. **Verify non-food**: All personal care, household, pet products should have `is_food: False`

## Remaining Ambiguity

Some products will always be ambiguous:

- **Seasoning blends with food names**: "Chicken Seasoning" → is this for chicken, or does it taste like chicken? (Usually "for chicken" → `spices`)
- **Compound products**: "Chicken Quesadilla" → is this a meal, or ingredients packaged together? (Usually if it's frozen/prepared → `prepared_dish`)
- **Baby food**: Is this "food" or "baby care"? (It's food → `is_food: True`, but separate category `baby`)

When ambiguous, document in `notes` field.

## Summary: Recipe Knowledge → Classification

1. **Study recipes** across cuisines to understand how ingredients are listed
2. **Identify equivalences**: When recipes treat products interchangeably → same ingredient
3. **Identify distinctions**: When recipes name products specifically → separate ingredients
4. **Separate flavor from identity**: Adjectives describe flavor; nouns define product
5. **Flag prepared dishes**: Complete meals are not base ingredients
6. **Validate**: Check classifications match how recipes would list the product
