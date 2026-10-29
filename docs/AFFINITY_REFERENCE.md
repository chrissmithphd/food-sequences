# Food-Affinity Reference Dataset

A reusable, evidence-backed reference describing how the project's 543 recipe
ingredients — and their combinations — relate to **food/meal styles, composition
patterns, flavors, and cuisines**. It is built to answer one question before any
customer modeling happens:

> What recognizable types of food and flavor preferences can be inferred from
> combinations of common recipe ingredients, and how reliably can our existing
> ingredient vocabulary carry that signal?

This document is the methodology and findings for the reference data in
[`data/affinity/`](../data/affinity/). It contains **no customer analysis** — no basket
classification, segmentation, or recipe inference. Those are the next phase. Throughout,
these are **food affinities** (evidence of what someone buys or cooks), not proven taste
preferences.

## 1. Reference sources

Associations are **measured from labeled recipe corpora**, not hand-assigned, so every
number traces to data. Two public corpora, chosen to match the reframed priority
(meal/food style primary, composition complementary, cuisine supporting):

| Corpus | Role | Size | Labels used |
|---|---|---|---|
| [Food.com recipes](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions) | meal style + composition (primary) | 231,637 recipes | `tags` (dish type, course, main-ingredient, dietary) |
| [What's Cooking / Yummly](https://www.kaggle.com/datasets/kaggle/recipe-ingredients-dataset) | cuisine (supporting) | 39,774 recipes | `cuisine` (20 world cuisines) |

Both carry redistribution-unfriendly provenance (scraped Food.com; Yummly competition
data), so the raw corpora live in **git-ignored `data/external/`** and only derived
statistics are committed. The choice was deliberate: Food.com's tag vocabulary names
dish types directly (salads, curries, stir-fry, baking…), which is where the strongest
and most broadly applicable signal turned out to be. What's Cooking supplies clean,
balanced cuisine labels for the supporting layer and corroborates the
combination-over-frequency idea from the literature.

Two papers motivated the combination emphasis: Caprioli et al. 2025 (*npj Science of
Food*) — ingredient *relationships* distinguish cuisines better than ingredient
frequency alone — and Ahn et al. 2011 (*Scientific Reports*) — Western cuisines pair
flavor-compound-sharing ingredients while East Asian cuisines avoid it. The second needs
a flavor-compound database we don't have, so it informs only how we treat the flavor
dimension (below), not the measured statistics. (Recipe1M and FoodOn were considered;
neither adds labeled cuisine/dish signal beyond the two corpora above for this purpose.)

## 2. The affinity taxonomy

48 candidate affinities across three overlapping levels (a customer or basket can score
on many at once — Indian, curry, legume-heavy, and vegetarian are not mutually
exclusive):

| Dimension | Count | Examples |
|---|---|---|
| Meal / dish style (primary) | 14 | salads, soups & stews, curries, stir-fries, pasta, pizza, sandwiches, chili, casseroles, grilling/BBQ, roasts, breakfast, sweet baking, bread baking |
| Composition (complementary) | 8 | legume-heavy, seafood-oriented, poultry, meat-centered, vegetable-forward, grain-based, vegetarian, plant-forward |
| Flavor — measurable by presence | 1 | spicy |
| Flavor — sensory (catalog only, **unmeasured**) | 5 | savory/umami, creamy, herbal, citrusy, smoky |
| Cuisine (supporting) | 20 | italian, mexican, indian, thai, chinese, japanese, greek, … |

Each measured affinity **is** a recipe label, so its statistics are grounded. Sensory
flavors are carried as definitions only: ingredients cannot establish how a finished
dish *tastes* (buying chilies is not proof of a taste for heat), so we do not fabricate
measurements for them. `spicy` is kept as measurable-*by-presence* only — it detects
chili/heat ingredients, not perceived spiciness.

The taxonomy favors **useful distinctions over maximum granularity**. "Curries" is one
affinity, not Thai-vs-Indian — and §7 shows that choice is supported by the data, not
just convenient.

## 3. How associations were derived

For every (affinity, ingredient) pair we report, from the recipes carrying that label:

- **prevalence** = P(ingredient | affinity) — how common it is *within* the affinity;
- **base_rate** = P(ingredient) in the same corpus — how common it is overall;
- **lift** = prevalence / base_rate — how much the affinity concentrates it (1.0 = chance);
- **P(affinity | ingredient)** — how strongly the ingredient points *to* the affinity;
- **support** — raw recipe count (so weak evidence can be filtered out).

Garlic is common in Italian recipes but appears everywhere, so its lift and
P(affinity|ingredient) are low — prevalence alone would mislead. Lift plus support is
the core signal. We also report **distinctive combinations**: ingredient pairs whose
lift within an affinity is high, capturing the relational structure single-ingredient
frequency misses (e.g., `curry_paste + turmeric` at 80× within curries).

Code: [`scripts/affinity/build_associations.py`](../scripts/affinity/build_associations.py).
Outputs: `ingredient_associations.csv` (6,098 rows), `ingredient_combinations.csv`
(1,720 rows), `affinities.csv` (the 48 definitions).

## 4. Mapping external ingredients to our taxonomy

Recipe corpora list ingredients as free text ("ground cumin", "extra-virgin olive oil",
"garlic cloves"). [`scripts/affinity/ingredient_map.py`](../scripts/affinity/ingredient_map.py)
normalizes each string to an existing slug, reusing the taxonomy's own synonym lists
(the text after each `- slug:` line) plus a curated override table
([`ingredient_overrides.csv`](../data/affinity/ingredient_overrides.csv)) for terms the
synonyms miss. Matching order: curated override → exact synonym → specifier-before-
generic-head ("parmesan cheese" → `parmesan`, "lemon juice" → `lemon`) → contained
multi-word phrase → unambiguous head noun. Nothing is force-matched.

**Coverage: ~89% (What's Cooking) and ~90% (Food.com) of ingredient mentions map.** The
override table also records deliberate **gaps** — recipe ingredients our *grocery*
taxonomy has no slug for — because those are findings in their own right (§8).

## 5. Dataset coverage and quality

| Measure | Value |
|---|---|
| 543 taxonomy slugs with ≥1 affinity association | 348 (64%) |
| …with distinctive (lift ≥ 2) evidence | 342 |
| Grocery **purchase volume** covered by associated slugs | **90.3%** |
| Affinities graded strong / moderate / weak / unmeasured | 33 / 8 / 2 / 5 |

The 36% of slugs with no association are overwhelmingly **snack and convenience items
absent from recipe corpora** — granola_bar, deli_meat, kombucha, string_cheese,
mac_and_cheese, chicken_nuggets, fruit_snacks. This is informative, not a defect: those
purchases carry no cooking-affinity signal, and the detector should treat them as
affinity-neutral rather than expect the reference to explain them. Cooking-relevant
ingredients — which dominate purchase *volume* — are well covered.

Evidence grade is `strong` when an affinity has ≥1,000 recipes and ≥5 distinctive
ingredients, `moderate` at ≥500 and ≥3, else `weak`. Per-affinity detail (with each
affinity's top distinctive ingredients) is in
[`coverage_report.csv`](../data/affinity/coverage_report.csv).

## 6. Strong and weak signatures

**All 14 meal-style and all 8 composition affinities grade strong** — the reframe toward
meal style was the right call. Representative measured signatures:

| Affinity | Recipes | Top distinctive ingredients (lift) |
|---|--:|---|
| curries | 1,439 | curry_paste (48×), garam_masala (41×), plant_milk/coconut (26×), turmeric (25×), ghee (21×) |
| stir-fries | 1,690 | oyster_sauce (25×), peanut_oil (19×), fish_sauce (13×), rice_noodles (13×), hoisin_sauce (13×) |
| legume-heavy | 9,533 | lentils (16×), tempeh (15×), white/pinto/black beans, tofu (13×), chickpeas (12×) |
| sweet baking | 25,022 | cake_flour, chocolate_chips, cocoa_powder, powdered_sugar, condensed_milk |
| salads | 14,687 | cucumber, lettuce, radish, wine vinegars, melons |
| c_indian | 3,003 | garam_masala (12×, P(aff\|ing)=93%), ghee, naan, cardamom, turmeric |
| c_mexican | 6,438 | refried_beans, taco_seasoning, guacamole, tortilla_chips, salsa |

Cuisine is weaker and uneven: **10 strong, 8 moderate, 2 weak** (`c_russian`,
`c_brazilian` — too few recipes and too few ingredients distinctive after our taxonomy's
abstraction). This matches the plan's expectation that regional cuisine is detectable
only for a subset of traditions, while meal style is broad.

## 7. Overlapping categories and grouping

Affinity overlap is measured by Jaccard similarity of distinctive-ingredient sets
([`affinity_overlap.csv`](../data/affinity/affinity_overlap.csv)), so grouping decisions
rest on evidence, not taste. The strongest overlaps:

| Pair | Jaccard | Reading |
|---|--:|---|
| stir_fries ~ c_chinese | 0.53 | meal style and cuisine describe the same dishes — keep both dimensions, expect correlation |
| vegetarian ~ plant_forward | 0.50 | **merge candidate** (near-duplicate composition labels) |
| curries ~ c_indian | 0.44 | supports a single cross-cuisine "curry" affinity over splitting by region |
| c_thai ~ c_vietnamese | 0.43 | **merge candidate** → "Southeast Asian" |
| c_british ~ c_irish | 0.34 | **merge candidate** → "British Isles" |
| c_chinese ~ c_korean ~ c_vietnamese | ~0.32 | an East/SE-Asian cluster sharing soy/ginger/chili bases |

These confirm the decision to keep "curries" unified and point to concrete cuisine
merges for the detector phase. They also show the three dimensions are *correlated, not
redundant*: a dish-style and a cuisine can describe the same recipes while a customer's
value lies in scoring on both.

## 8. Limitations and missing information

- **Recipes are not groceries.** Associations describe how ingredients co-occur in
  *recipes*. A grocery basket mixes several meals and restocking, so the reference tells
  the detector what a combination *could* indicate, never that a basket is one dish.
- **Grocery-taxonomy gaps.** Several ingredients that are strong culinary discriminators
  have no slug in our (grocery-built) taxonomy and are therefore invisible to detection:
  **olives** (Mediterranean/Greek), **capers**, **lemongrass** (SE Asian), **mirin/sake**
  (Japanese), **tomatillo** (Mexican), **fennel**, **shredded coconut**, **sumac/za'atar**
  (Middle Eastern). Recorded in `ingredient_overrides.csv`. These are *not* patched —
  the existing abstraction is kept intact — but they bound which affinities are reachable
  (notably Mediterranean/Greek and Japanese).
- **Deliberate lumping.** `fresh_herbs` collapses cilantro/basil/mint/parsley/dill;
  `hot_pepper` collapses chipotle/poblano/Thai chile; scallions/leeks/shallots fold into
  `onion`; cooking coconut milk sits under `plant_milk`. This erases some herb- and
  chile-based cuisine discriminators — though coconut milk still surfaces for
  curries/Thai *through* `plant_milk` (lift 26×), so the lumping degrades rather than
  destroys. It is a measured detectability limit, not a bug.
- **Corpus artifacts.** Cuisine `P(affinity|ingredient)` runs 90–100% because *every*
  What's Cooking recipe has exactly one cuisine — those conditionals are relative to a
  cuisine-balanced competition set, not grocery reality, and overstate real-world
  distinctiveness; use **lift** for cuisine. Lift magnitudes are **not comparable across
  corpora**: What's Cooking's 20 balanced cuisines cap Italian's lift near 5× (it's 20%
  of the corpus), while Food.com's rarer dish tags allow 40–80×. Food.com tags are
  user-supplied and noisy.
- **Combinations are the lower-confidence layer.** Many high-lift pairs rest on
  15–50 recipes; treat `ingredient_combinations.csv` as a candidate pool to be filtered
  by support, not as settled. Single-ingredient associations are the robust core.
- **Mapping residue.** Generic "cheese" strings map to `american_cheese` (no generic
  cheese slug), mildly inflating it; ~10% of mentions stay unmapped (long tail + the gaps
  above).

## 9. Recommendations for the detector phase

- **Lead with meal-style and composition affinities.** They grade uniformly strong and
  cover the broad population; treat cuisine as corroborating evidence, and only for the
  strong/moderate traditions.
- **Score with lift and support, not prevalence.** Require a minimum support and weight
  by distinctiveness (lift or P(affinity|ingredient)); discount ingredients that are
  common everywhere.
- **Apply the measured merges** before modeling: vegetarian+plant-forward; Thai+Vietnamese
  (and the broader East/SE-Asian cluster); British+Irish. Keep "curries" unified.
- **Hold affinities to a frequency-preserving baseline**, exactly as the sequence work
  did — an affinity is only real for a customer if its ingredient evidence recurs beyond
  what that customer's overall ingredient mix predicts. Plausible food stories should be
  made to clear that bar before they are believed.
- **Expect affinity-neutral purchases.** A third of ingredients (snacks/convenience) carry
  no signal; the detector should abstain on them rather than infer from noise.
- **Optional, separate from production:** a small targeted taxonomy extension (olives,
  lemongrass, capers, tomatillo, a cooking-coconut-milk split) would unlock
  Mediterranean/Greek and Japanese detection. Proposed only — not applied here.

---

*Reproduce:* place the two corpora under `data/external/` (see §1 links), then
`uv run python -I scripts/affinity/build_associations.py` and
`uv run python -I scripts/affinity/validate.py`. Raw corpora are not redistributed;
only the derived CSVs in `data/affinity/` are committed.
