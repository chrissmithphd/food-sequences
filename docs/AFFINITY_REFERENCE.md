# Food Profiles — Reference Dataset & Methodology

> This is the detailed methodology behind the [Food Profiles analysis](../analysis/food_profiles/).
> "Food profile" is the public-facing name for what the data schema calls an *affinity*
> (the stable key `affinity_id` and the `data/affinity/` paths are kept to avoid breaking
> compatibility). The two terms mean the same thing.

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
lift within a profile exceeds that of their component ingredients (e.g.,
`curry_paste + turmeric` at ~80× within curries). A pair reaching higher lift is a
stronger *association*; whether adding pairs improves *classification* over single
ingredients is untested here — the held-out evaluation (§6a) uses single ingredients
only, and rarer pairs reach higher lift partly through smaller support.

Code: [`scripts/affinity/build_associations.py`](../scripts/affinity/build_associations.py).
Outputs: `ingredient_associations.csv` (6,107 rows), `ingredient_combinations.csv`
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

**Coverage: ~87% of ingredient mentions map** in both corpora. The unmapped remainder is
deliberate: genuinely ambiguous generics ("beef", "cheese" — which span several existing
slugs and are left unmapped rather than force-assigned) and recipe ingredients our
*grocery* taxonomy has no slug for. The override table records these **gaps** — they are
findings in their own right (§8).

## 5. Dataset coverage and quality

| Measure | Value |
|---|---|
| 543 taxonomy slugs with ≥1 ingredient association | 355 (65%) |
| …with distinctive (lift ≥ 2) evidence | 349 |
| Grocery **purchase volume** covered by associated slugs | **90.0%** |
| Profiles graded by **reference support** (strong / moderate / weak / unmeasured) | 33 / 8 / 2 / 5 |

**Two different properties — don't conflate them.** *Reference support* (this section) is
how much labeled recipe evidence underlies a profile: recipe count and number of
distinctive ingredients. *Predictive detectability* (§6) is how reliably those ingredients
identify the profile on held-out recipes. A profile can have ample reference support and
still be hard to detect — grilling has thousands of recipes but few distinctive
ingredients, so it is well *supported* but poorly *detectable*. Below, "support grade"
means the first; the held-out evaluation measures the second.

The 36% of slugs with no association are overwhelmingly **snack and convenience items
absent from recipe corpora** — granola_bar, deli_meat, kombucha, string_cheese,
mac_and_cheese, chicken_nuggets, fruit_snacks. This is informative, not a defect: those
purchases carry no cooking signal, and a detector should treat them as profile-neutral
rather than expect the reference to explain them. Cooking-relevant ingredients — which
dominate purchase *volume* — are well covered.

Support grade is `strong` when a profile has ≥1,000 recipes and ≥5 distinctive
ingredients, `moderate` at ≥500 and ≥3, else `weak`. Per-profile detail is in
[`coverage_report.csv`](../data/affinity/coverage_report.csv). It describes evidence
quantity only, **not** whether the profile is detectable.

## 6. Signatures, and support vs. detectability

**All 14 meal-style and all 8 composition profiles have strong reference support** — the
reframe toward meal style was the right call. Representative measured signatures:

| Profile | Recipes | Top distinctive ingredients (lift) |
|---|--:|---|
| curries | 1,439 | curry_paste (48×), garam_masala (41×), plant_milk/coconut (26×), turmeric (25×), ghee (21×) |
| stir-fries | 1,690 | oyster_sauce (25×), peanut_oil (19×), fish_sauce (13×), rice_noodles (13×), hoisin_sauce (13×) |
| legume-heavy | 9,533 | lentils (16×), tempeh (15×), white/pinto/black beans, tofu (13×), chickpeas (12×) |
| sweet baking | 25,022 | cake_flour, chocolate_chips, cocoa_powder, powdered_sugar, condensed_milk |
| salads | 14,687 | cucumber, lettuce, radish, wine vinegars, melons |
| c_indian | 3,003 | garam_masala (12×, P(profile\|ingredient)=93% within this corpus), ghee, naan, cardamom, turmeric |
| c_mexican | 6,438 | refried_beans, taco_seasoning, guacamole, tortilla_chips, salsa |

Support, though, does not guarantee detectability. The held-out evaluation (§6a) shows
profiles like **grilling and roasting have substantial reference support but weak
predictive detectability** (average precision 0.17 and 0.03) — they are cooking *methods*
whose ingredients aren't distinctive. Conversely, rare profiles like chili and curries
have modest recipe counts yet detect far above their base rate. Cuisine support is uneven
(10 strong, 8 moderate, 2 weak — `c_russian`, `c_brazilian` have too few recipes), as
expected: regional cuisine is well-supported for only some traditions, while meal style is
broad.

## 6a. Held-out detectability

Signatures are learned on a training split and used to classify held-out recipes
(`scripts/affinity/evaluate.py`), so these are measured, not asserted.

- **Cuisine** (20-way, single-label): the ingredient classifier reaches **57.7% accuracy**
  (macro-F1 0.48), about 2.9× the **19.7% majority-class baseline** (always predicting
  Italian, the most common label — not random chance, which over 20 classes would be far
  lower). Confusions cluster on cuisines with overlapping ingredients (§7).
- **Meal style & composition** (multi-label, one-vs-rest **average precision** — a ranking
  metric, not classification accuracy): detected well for seafood (0.72), meat (0.72),
  sweet baking (0.70), salads (0.66), pasta (0.63); detected far above base rate though at
  modest absolute precision for rare, distinctive profiles (chili 0.53 on a 0.9% base
  rate); and **weak** for roasts (0.03), the `spicy` tag (0.16), stir-fries (0.16), and
  grilling (0.17). Average precision near a profile's prevalence means no better than a
  random ranking.

These numbers are on **complete recipe ingredient lists**. Grocery baskets are partial and
mix several meals, so treat them as an upper reference, not demonstrated basket
performance.

## 7. Overlapping profiles: shared evidence, not interchangeable categories

Profile overlap is measured by Jaccard similarity of distinctive-ingredient sets
([`affinity_overlap.csv`](../data/affinity/affinity_overlap.csv)). High overlap means two
profiles draw on mostly the same distinctive ingredients, so a detector built on this
taxonomy will **struggle to tell them apart** — it does *not* establish that the
distinction is unimportant to customers or should be permanently discarded. The strongest
overlaps:

| Pair | Jaccard | Reading |
|---|--:|---|
| stir_fries ~ c_chinese | 0.53 | a food style and a cuisine describing the same dishes — complementary dimensions, expect correlation |
| vegetarian ~ plant_forward | 0.50 | near-identical ingredient evidence; hard to separate with this taxonomy |
| curries ~ c_indian | 0.44 | curry ingredients and Indian ingredients coincide heavily (see note below) |
| c_thai ~ c_vietnamese | 0.43 | shared Southeast-Asian ingredient base; hard to separate |
| c_british ~ c_irish | 0.34 | shared ingredient base |
| c_chinese ~ c_korean ~ c_vietnamese | ~0.32 | an East/SE-Asian cluster sharing soy/ginger/chili bases |

The defensible conclusions: where two profiles share most distinctive ingredients, the
evidence can't separate them, so a **broader grouping may be the honest reporting unit
when evidence is thin** — while **finer distinctions should be preserved wherever the
ingredients support them**, not merged away permanently. Grouping is a response to
insufficient evidence, not a claim that the categories are the same.

`curries ~ c_indian` needs a specific caveat: it is **not** evidence that Indian and Thai
cuisines should collapse. Curry is a **food style that spans cuisines**; cuisine and food
style are complementary dimensions, and a dish can score on both. The overlap reflects
that curry ingredients and Indian ingredients coincide — not that regional cuisines are
interchangeable.

## 8. Limitations and missing information

- **Recipes are not groceries.** Associations describe how ingredients co-occur in
  *recipes*. A grocery basket mixes several meals and restocking, so the reference tells
  the detector what a combination *could* indicate, never that a basket is one dish.
- **Grocery-taxonomy gaps.** Several ingredients that are strong culinary discriminators
  have no slug in our (grocery-built) taxonomy and are therefore invisible to detection:
  **olives** (Mediterranean/Greek), **capers**, **lemongrass** (SE Asian), **mirin/sake**
  (Japanese), **tomatillo** (Mexican), **fennel**, **shredded coconut**, **sumac/za'atar**
  (Middle Eastern). Recorded in `ingredient_overrides.csv`. These are *not* patched —
  the existing abstraction is kept intact — but they bound which profiles are reachable
  (notably Mediterranean/Greek and Japanese).
- **Deliberate lumping.** `fresh_herbs` collapses cilantro/basil/mint/parsley/dill;
  `hot_pepper` collapses chipotle/poblano/Thai chile; scallions/leeks/shallots fold into
  `onion`; cooking coconut milk sits under `plant_milk`. This erases some herb- and
  chile-based cuisine discriminators — though coconut milk still surfaces for
  curries/Thai *through* `plant_milk` (lift 26×), so the lumping degrades rather than
  destroys. It is a measured detectability limit, not a bug.
- **Corpus artifacts.** Cuisine `P(profile|ingredient)` runs 90–100% because *every*
  What's Cooking recipe has exactly one cuisine — those conditionals are relative to a
  cuisine-balanced competition set, not grocery reality, and overstate real-world
  distinctiveness; use **lift** for cuisine. Lift magnitudes are **not comparable across
  the two corpora** — they have different background populations: What's Cooking's 20
  balanced cuisines cap Italian's lift near 5× (it is 20% of that corpus), while Food.com's
  rarer dish tags allow 40–80×. Food.com tags are user-supplied and noisy.
- **Combinations are the lower-confidence layer.** Many high-lift pairs rest on
  15–50 recipes; treat `ingredient_combinations.csv` as a candidate pool to be filtered
  by support, not as settled. Single-ingredient associations are the robust core.
- **Mapping residue.** Generic "cheese" strings map to `american_cheese` (no generic
  cheese slug), mildly inflating it; ~10% of mentions stay unmapped (long tail + the gaps
  above).

## 9. Recommendations for the detector phase

- **Lead with meal-style and composition profiles.** They have uniformly strong reference
  support and detect well; treat cuisine as corroborating evidence, and only for the
  traditions the held-out evaluation actually separates.
- **Score with lift and support, not prevalence.** Require a minimum support and weight
  by distinctiveness (lift or P(profile|ingredient)); discount ingredients common
  everywhere. Remember lift is an association statistic, not a calibrated probability that
  a basket contains the food style.
- **Group only where the evidence forces it.** Where profiles share most distinctive
  ingredients (vegetarian/plant-forward; Thai/Vietnamese; British/Irish), report a broader
  grouping when the finer split can't be supported — but keep the finer labels available
  and use them wherever ingredients do separate them. Grouping is a fallback for thin
  evidence, not a permanent taxonomy decision. Keep cuisine and food style as separate
  dimensions (a basket can be both "curry" and "Indian").
- **Separate preference strength, stability, and evolution.** A customer's consistent
  purchasing of a profile's distinctive ingredients is itself evidence of a preference —
  no temporal test required. Use a **frequency-preserving baseline** specifically for the
  *evolution* question (does the mix of food styles change over time beyond stable habits
  and sampling variation?), where the sequence work showed such baselines deflate stories
  that are really just stable habits. And throughout, purchases are evidence of food
  *choices*, not direct proof of what a customer enjoys.
- **Expect profile-neutral purchases.** A third of ingredients (snacks/convenience) carry
  no cooking signal; the detector should abstain on them rather than infer from noise.
- **Optional, separate from production:** a small targeted taxonomy extension (olives,
  lemongrass, capers, tomatillo, a cooking-coconut-milk split) would unlock
  Mediterranean/Greek and Japanese detection. Proposed only — not applied here.

---

*Reproduce:* download the two corpora into `data/external/` (git-ignored; see the §1
links — `kaggle datasets download -d kaggle/recipe-ingredients-dataset` and
`-d shuyangli94/food-com-recipes-and-user-interactions`), then run, in order:
`build_associations.py` (associations + combinations), `validate.py` (coverage +
overlap), `evaluate.py` (held-out detectability + confusion), and `visualize_profiles.py`
(figures) — all under `scripts/affinity/` via `uv run python -I`. Raw corpora are not
redistributed; only the derived CSVs in `data/affinity/` are committed.
