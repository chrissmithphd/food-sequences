# Food Profiles

Can you tell what *kind* of food someone is cooking from the ingredients alone — not the
exact recipe, but the style: a curry, a salad, a baking project, something seafood-based?
This analysis builds a reference that maps our 543 ingredients to recognizable **food
profiles**, then tests how reliably those profiles can actually be identified from
ingredient evidence.

A food profile is a food *style* (curry, salad, pasta, stir-fry, baking), a *composition*
pattern (legume-heavy, seafood-oriented, vegetable-forward), or — more weakly — a
*cuisine* (Italian, Indian, Thai). They overlap by design: one dish can be a curry, Indian,
and legume-heavy at once. These are associations between ingredients and food types —
**not** a claim about what any customer enjoys eating. That comes later, and only with
care.

- Sources: `scripts/affinity/` (`ingredient_map.py`, `build_associations.py`,
  `evaluate.py`, `visualize_profiles.py`); reference data in `data/affinity/`.
- Evidence: two public recipe corpora — **Food.com** (231,637 recipes, dish/composition
  tags) for food styles, **What's Cooking / Yummly** (39,774 recipes, 20 cuisines) for
  cuisine. Full methodology: [Food Profiles reference →](../../docs/AFFINITY_REFERENCE.md).

---

## How it works, briefly

Each profile is a label that already exists in a recipe corpus, so its ingredient
associations are **measured, not assigned**. Recipe ingredients (free text like "ground
cumin", "parmigiano reggiano") are normalized onto our 543 slugs, and for each
(profile, ingredient) we compute how common the ingredient is *within* the profile
(prevalence), how common it is overall (base rate), and the ratio — **lift**, how many
times more likely than chance. Lift is what separates a *characteristic* ingredient from
a merely *common* one.

Two numbers frame everything: the reference covers ingredients making up **90% of
Instacart food purchase volume**, but only **64% of the 543 ingredients** appear in any
profile — the missing third is snacks and convenience items (granola bars, deli meat,
chips) that simply aren't recipe ingredients and carry no cooking signal.

## What distinguishes each food style

![Signature ingredients by food style](../figures/profiles_signatures.png)

Ranked by lift, the signatures are sharp and sensible. Curries are defined by
`curry_paste` (48×), `garam_masala` (41×), and coconut milk (which lives under
`plant_milk`, 26×). Chili by `kidney_beans` (39×) and `pinto_beans` (28×). Legume-heavy
meals by `lentils`, `tofu`, and a wall of beans. Seafood splits into specific fish
(`tilapia`, `halibut`, `trout`). Sweet baking by `cake_flour`, `cocoa_powder`, and
`chocolate_chips`. None of these required hand-tuning — they fall out of the recipe
statistics.

## Common is not the same as characteristic

![Common vs. distinctive ingredients in Italian cuisine](../figures/profiles_common_vs_distinct.png)

The single most important methodological point. In Italian recipes, **garlic, onion, and
tomato are everywhere** — but they're everywhere in *most* cuisines too, so their lift is
near 1: common, not distinctive. The real Italian signatures are the lower-prevalence,
high-lift ingredients: `marinara`, `ricotta`, `filled_pasta`, `pesto`. Ranking by raw
frequency would surface garlic and miss ricotta; ranking by lift does the opposite. Any
detector built on this reference must weight by distinctiveness, not popularity.

## Do ingredient pairs beat single ingredients?

![Best pair lift vs. best single-ingredient lift](../figures/profiles_combos_vs_singles.png)

Yes — combinations carry more signal than individual ingredients, echoing the published
cuisine-network result. The best *pair* lift exceeds the best *single* lift for every
flagship style (curry_paste + turmeric reaches ~85× within curries vs ~48× for the best
single). The catch: pair evidence is thinner — many high-lift pairs rest on only 15–40
recipes (coffee + kidney_beans hits 110× in chili on just 16 recipes, a real but niche
trick). Pairs are a candidate pool to be filtered by support, not taken at face value.

## Which profiles are actually recognizable?

![Held-out detectability by profile](../figures/profiles_detectability.png)

A list of associated ingredients proves nothing until you test it. Recipes were split
train/test, signatures learned from the training half only, and held-out recipes
classified. The bars are average precision; the dots are the prevalence a blind guess
would hit — the gap is real detectability.

**Reliable:** seafood (0.72), meat (0.72), sweet baking (0.70), salads (0.66), pasta
(0.63). **Rare but highly distinctive:** chili, pizza, and curries sit lower in absolute
precision but tower over their chance baseline (chili 0.53 vs a 0.9% prevalence). **Weak
— the honest negatives:** roasts (0.03), spicy (0.16), stir-fries (0.16), grilling
(0.17). Roasting and grilling are *methods* with few distinctive ingredients, and "spicy"
is a sensory flavor ingredients can't pin down — exactly the limit we expected, now
measured.

## Where cuisine identification confuses — and where to stop splitting

![Cuisine confusion matrix](../figures/profiles_cuisine_confusion.png)

On a 20-way cuisine task, the ingredient classifier reaches **57.7% accuracy** (macro-F1
0.48) against a 19.7% majority baseline — nearly 3× chance, from ingredients alone. The
mistakes are not random: Southern US ↔ Cajun/Creole, Italian ↔ Greek/Spanish, Japanese ↔
Chinese, French ↔ British. Those confusions are the data telling us where cuisine-level
detail stops paying off.

The same message comes from measured signature overlap (Jaccard of distinctive
ingredients): `vegetarian ≈ plant_forward` (0.52), `curries ≈ Indian` (0.49),
`Thai ≈ Vietnamese` (0.46), `British ≈ Irish` (0.38). The practical reading: keep a
single broad **curry** profile rather than splitting Thai from Indian, merge
vegetarian/vegan and the East/Southeast-Asian cuisines, and treat cuisine as supporting
evidence beneath the more robust food-style and composition profiles.

## What this means for grocery baskets

The reference is built on recipes, and **a grocery basket is not a recipe.** A single
order mixes several meals and a week of restocking, so the honest target is "this basket
shows *evidence consistent with* curries and salads," never "this basket is a curry."
Three cautions carry forward:

- **Staples dominate and don't discriminate.** Most of a basket is milk, bananas, and
  onions. A detector has to lean on the sparse, distinctive ingredients, which may appear
  in only a few items.
- **Normalizing to ingredients loses cuisine-fine detail** (cilantro, basil, and mint all
  become `fresh_herbs`; chipotle and poblano become `hot_pepper`), and the grocery
  taxonomy has no slug for some signatures at all (olives, lemongrass, capers). That caps
  Mediterranean/Greek and some Asian detection regardless of method.
- **Any profile claim must clear a frequency baseline.** As the sequence analysis showed,
  plausible food stories often evaporate against a proper null: a customer only has an
  affinity for curries if curry ingredients recur *beyond* what their overall ingredient
  mix already predicts.

## Limitations

- Associations are measured from recipe corpora with their own biases (Food.com is
  US-home-cook-skewed; What's Cooking is a cuisine-balanced competition set, so its
  `P(profile|ingredient)` overstates real-world distinctiveness — use lift). Lift
  magnitudes are **not comparable across the two corpora**.
- Sensory-flavor profiles (savory, creamy, herbal, citrusy, smoky) are carried as
  definitions only — ingredients can't establish how a dish tastes — and are not scored.
- Combination evidence is lower-confidence than single-ingredient evidence.
- This phase measures ingredient→profile associations and their detectability on recipes.
  It does **not** profile customers or infer taste; that is the next layer, and it will
  need the frequency baseline above.
