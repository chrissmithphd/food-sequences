# Product classification prompt (v3.0)

Model is given, per product: `product_name`, `aisle`, `department`.
Aisle/department are weak hints — the product name decides. Matching a word in the
name is insufficient; identify what the product IS first, then its recipe role.

## Step 1 — identify the product
- **product_type**: the kind of thing it is (e.g. crackers, mayonnaise, filled pasta,
  fresh vegetable, pet food, skin-care). This is a noun for the object, not an ingredient.
- **base_food**: the principal food it is made of / the ingredient a recipe would call it.
- **prep_state**: raw / cooked / prepared-dish / shelf-stable / kit / non-food.
- **named_ingredient_role**: for each notable ingredient word in the name, is it the
  **product** itself, a **filling**, or a **flavor**? (e.g. "grape" in grape tomato =
  variety/flavor descriptor; "ricotta" in spinach-ricotta ravioli = filling;
  "olive oil" in mayonnaise-with-olive-oil = minor ingredient, product is mayonnaise.)

## Step 2 — assign a recipe-equivalence group
Pick the group from the shared catalog whose members are usually interchangeable in the
same recipe role. Ignore brand, package size, organic status, and minor variation
(whole vs 2% milk). If no catalog group fits, output `status=proposed_group` with a
suggested name and definition for review — do not invent an inconsistent label.

## Step 3 — preserve meaningful boundaries
Plain pasta ≠ mac and cheese; raw chicken ≠ chicken dinner; cheddar ≠ parmesan. A broad
`role_family` may connect related groups without declaring them equivalent.

## Step 4 — status and confidence (not everything is high-confidence)
- **status**: resolved | ambiguous | insufficient_info | out_of_scope | proposed_group
- **out_of_scope**: not a human food ingredient/dish (pet food, personal care, supplies).
- **confidence**: high | medium | low. Self-reported confidence is a hint, not proof;
  all labels are subject to human validation.

## Output fields
`product_type, base_food, prep_state, named_ingredient_role, recipe_group, role_family,
status, confidence, reason`. Cached with `model_id` and `prompt_version=v3.0`.
