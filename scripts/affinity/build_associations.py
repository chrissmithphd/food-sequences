#!/usr/bin/env python3
"""Compute measured ingredient→affinity associations from labeled recipe corpora.

Each *affinity* is defined by a label that already exists in a recipe corpus, so the
association statistics are measured, not assigned:

  - meal styles & composition  -> Food.com `tags`   (salads, curries, baking, vegan, ...)
  - cuisines (supporting)       -> What's Cooking `cuisine` (italian, indian, thai, ...)

For every (affinity, ingredient) we report how common the ingredient is *within* the
affinity (prevalence = P(ingredient | affinity)), how common it is overall (base rate =
P(ingredient)), their ratio (lift), how distinctive the affinity is given the ingredient
(P(affinity | ingredient)), and the raw support. Garlic is common in Italian food but
not distinctive of it — lift and P(affinity|ingredient) separate the two; prevalence
alone does not.

We also report distinctive *combinations*: ingredient pairs whose lift within an
affinity is high (the structure the 2025 cuisine-network paper found carries more signal
than single-ingredient frequency).

Ingredients are normalized to the project's 543-slug taxonomy via ingredient_map, so the
output speaks the same vocabulary as the grocery pipeline. Sensory-flavor affinities
(smoky, savory, creamy, herbal, citrusy) are NOT measured here — ingredients can't
establish how a finished dish tastes — and are carried as catalog-only rows in
affinities.csv.

Outputs (data/affinity/):
  affinities.csv              affinity definitions (all dimensions, incl. unmeasured)
  ingredient_associations.csv measured single-ingredient associations
  ingredient_combinations.csv measured distinctive pairs

Usage:
  uv run python -I scripts/affinity/build_associations.py
"""
from __future__ import annotations

import ast
import csv
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingredient_map import IngredientMapper  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
EXT = ROOT / "data" / "external"
OUT = ROOT / "data" / "affinity"
WC = EXT / "whats_cooking" / "train.json"
FC = EXT / "food_com" / "RAW_recipes.csv"

MIN_SLUG_DOCS = 40        # ignore ultra-rare slugs when forming pairs
MIN_ASSOC_SUPPORT = 20    # minimum recipes for a reported single-ingredient association
MIN_PAIR_SUPPORT = 15     # minimum recipes for a reported pair
TOP_PAIRS_PER_AFFINITY = 40

# --------------------------------------------------------------------------- #
# Affinity taxonomy. source: "foodcom" (tag selector) or "whatscooking" (cuisine).
# Flavor/sensory affinities with source None are catalog-only (not measured).
# --------------------------------------------------------------------------- #
AFFINITIES = [
    # ---- meal / dish styles (PRIMARY) : Food.com tags ----
    ("salads", "Salads", "meal_style", None, {"salads"}, "foodcom"),
    ("soups_stews", "Soups & stews", "meal_style", None, {"soups-stews", "stews"}, "foodcom"),
    ("curries", "Curries", "meal_style", None, {"curries"}, "foodcom"),
    ("stir_fries", "Stir-fries", "meal_style", None, {"stir-fry"}, "foodcom"),
    ("pasta_dishes", "Pasta dishes", "meal_style", None, {"pasta"}, "foodcom"),
    ("pizza", "Pizza", "meal_style", None, {"pizza"}, "foodcom"),
    ("sandwiches", "Sandwiches", "meal_style", None, {"sandwiches"}, "foodcom"),
    ("chili", "Chili", "meal_style", None, {"chili"}, "foodcom"),
    ("casseroles", "Casseroles & bakes", "meal_style", None, {"casseroles"}, "foodcom"),
    ("grilling_bbq", "Grilling & BBQ", "meal_style", None, {"barbecue", "grilling"}, "foodcom"),
    ("roasts", "Roasts", "meal_style", None, {"roast"}, "foodcom"),
    ("breakfast", "Breakfast", "meal_style", None, {"breakfast"}, "foodcom"),
    ("sweet_baking", "Sweet baking", "meal_style", None,
     {"cakes", "cookies-and-brownies", "pies"}, "foodcom"),
    ("bread_baking", "Bread baking", "meal_style", None, {"breads"}, "foodcom"),
    # ---- composition (COMPLEMENTARY, measurable) ----
    ("legume_heavy", "Legume-heavy", "composition", None, {"beans"}, "foodcom"),
    ("seafood_oriented", "Seafood-oriented", "composition", None, {"seafood", "fish"}, "foodcom"),
    ("poultry", "Poultry-centered", "composition", None, {"poultry", "chicken"}, "foodcom"),
    ("meat_centered", "Meat-centered", "composition", None, {"meat"}, "foodcom"),
    ("vegetable_forward", "Vegetable-forward", "composition", None, {"vegetables"}, "foodcom"),
    ("grain_based", "Grain-based", "composition", None, {"grains", "rice"}, "foodcom"),
    ("vegetarian", "Vegetarian", "composition", None, {"vegetarian"}, "foodcom"),
    ("plant_forward", "Plant-forward (vegan)", "composition", None, {"vegan"}, "foodcom"),
    # ---- flavor: measurable-by-presence ----
    ("spicy", "Spicy (chili/heat present)", "flavor", None, {"spicy"}, "foodcom"),
    # ---- flavor: sensory, NOT measurable from ingredients (catalog only) ----
    ("f_savory", "Savory / umami", "flavor_sensory", None, set(), None),
    ("f_creamy", "Creamy / rich", "flavor_sensory", None, set(), None),
    ("f_herbal", "Herbal", "flavor_sensory", None, set(), None),
    ("f_citrusy", "Citrusy / acidic", "flavor_sensory", None, set(), None),
    ("f_smoky", "Smoky", "flavor_sensory", None, set(), None),
    # ---- cuisine (SUPPORTING) : What's Cooking labels ----
    ("c_italian", "Italian", "cuisine", None, {"italian"}, "whatscooking"),
    ("c_mexican", "Mexican", "cuisine", None, {"mexican"}, "whatscooking"),
    ("c_southern_us", "Southern US", "cuisine", None, {"southern_us"}, "whatscooking"),
    ("c_indian", "Indian", "cuisine", None, {"indian"}, "whatscooking"),
    ("c_chinese", "Chinese", "cuisine", None, {"chinese"}, "whatscooking"),
    ("c_french", "French", "cuisine", None, {"french"}, "whatscooking"),
    ("c_cajun_creole", "Cajun / Creole", "cuisine", None, {"cajun_creole"}, "whatscooking"),
    ("c_thai", "Thai", "cuisine", None, {"thai"}, "whatscooking"),
    ("c_japanese", "Japanese", "cuisine", None, {"japanese"}, "whatscooking"),
    ("c_greek", "Greek", "cuisine", None, {"greek"}, "whatscooking"),
    ("c_spanish", "Spanish", "cuisine", None, {"spanish"}, "whatscooking"),
    ("c_korean", "Korean", "cuisine", None, {"korean"}, "whatscooking"),
    ("c_vietnamese", "Vietnamese", "cuisine", None, {"vietnamese"}, "whatscooking"),
    ("c_moroccan", "Moroccan", "cuisine", None, {"moroccan"}, "whatscooking"),
    ("c_british", "British", "cuisine", None, {"british"}, "whatscooking"),
    ("c_filipino", "Filipino", "cuisine", None, {"filipino"}, "whatscooking"),
    ("c_irish", "Irish", "cuisine", None, {"irish"}, "whatscooking"),
    ("c_jamaican", "Jamaican", "cuisine", None, {"jamaican"}, "whatscooking"),
    ("c_russian", "Russian", "cuisine", None, {"russian"}, "whatscooking"),
    ("c_brazilian", "Brazilian", "cuisine", None, {"brazilian"}, "whatscooking"),
]

DESCRIPTIONS = {
    "spicy": "Recipes tagged spicy; measured by presence of chili/heat ingredients, "
             "not by how hot the finished dish is.",
    "vegetable_forward": "Broad main-ingredient tag; high recipe volume, low specificity.",
}


def recipe_affinities_foodcom(tags: set[str]) -> list[str]:
    out = []
    for aid, _, _, _, sel, src in AFFINITIES:
        if src == "foodcom" and sel & tags:
            out.append(aid)
    return out


def load_recipes():
    """Yield (affinity_ids, slug_set) per recipe from both corpora."""
    mapper = IngredientMapper()
    cache: dict[str, str | None] = {}

    def to_slugs(strings):
        s = set()
        for raw in strings:
            if raw not in cache:
                slug, _ = mapper.map(raw)
                cache[raw] = slug
            slug = cache[raw]
            if slug:
                s.add(slug)
        return s

    # Food.com (meal style + composition + spicy)
    csv.field_size_limit(10**7)
    with open(FC) as f:
        for row in csv.DictReader(f):
            try:
                tags = set(ast.literal_eval(row["tags"]))
                ings = ast.literal_eval(row["ingredients"])
            except (ValueError, SyntaxError):
                continue
            aff = recipe_affinities_foodcom(tags)
            if aff:
                yield aff, to_slugs(ings)
    # What's Cooking (cuisine)
    cu2aff = {next(iter(sel)): aid for aid, _, _, _, sel, src in AFFINITIES
              if src == "whatscooking"}
    for r in json.load(open(WC)):
        aid = cu2aff.get(r["cuisine"])
        if aid:
            yield [aid], to_slugs(r["ingredients"])


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # per-source background totals and slug doc-counts (background = that corpus)
    src_of = {aid: src for aid, _, _, _, _, src in AFFINITIES}
    bg_recipes = Counter()                     # source -> n recipes seen
    bg_slug = defaultdict(Counter)             # source -> slug -> doc count
    aff_recipes = Counter()                    # affinity -> n recipes
    aff_slug = defaultdict(Counter)            # affinity -> slug -> doc count
    bg_pairs = defaultdict(Counter)            # source -> pair -> doc count
    aff_pairs = defaultdict(Counter)           # affinity -> pair -> doc count

    # two-pass not needed: track which corpus a recipe is in via its affinities' source
    for affs, slugs in load_recipes():
        src = src_of[affs[0]]
        bg_recipes[src] += 1
        for sl in slugs:
            bg_slug[src][sl] += 1
        for a in affs:
            aff_recipes[a] += 1
            for sl in slugs:
                aff_slug[a][sl] += 1

    # frequent slugs per source (for pair formation)
    freq_slugs = {src: {s for s, c in bg_slug[src].items() if c >= MIN_SLUG_DOCS}
                  for src in bg_slug}

    # second pass for pairs (restricted to frequent slugs to bound memory)
    for affs, slugs in load_recipes():
        src = src_of[affs[0]]
        fs = sorted(s for s in slugs if s in freq_slugs[src])
        for pair in combinations(fs, 2):
            bg_pairs[src][pair] += 1
            for a in affs:
                aff_pairs[a][pair] += 1

    # ---- write affinities.csv ----
    with open(OUT / "affinities.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["affinity_id", "name", "dimension", "parent", "source",
                    "n_recipes", "selector", "description"])
        for aid, name, dim, parent, sel, src in AFFINITIES:
            w.writerow([aid, name, dim, parent or "", src or "",
                        aff_recipes.get(aid, 0), "|".join(sorted(sel)),
                        DESCRIPTIONS.get(aid, "")])

    # ---- write ingredient_associations.csv ----
    assoc_rows = []
    for aid, _, dim, _, _, src in AFFINITIES:
        if src is None:
            continue
        N = aff_recipes.get(aid, 0)
        Nbg = bg_recipes[src]
        if N == 0:
            continue
        for slug, n in aff_slug[aid].items():
            if n < MIN_ASSOC_SUPPORT:
                continue
            prevalence = n / N
            base = bg_slug[src][slug] / Nbg
            lift = prevalence / base if base else 0.0
            p_aff_given_ing = n / bg_slug[src][slug]
            assoc_rows.append([aid, slug, src, n, round(prevalence, 4),
                               round(base, 4), round(lift, 2),
                               round(p_aff_given_ing, 4)])
    assoc_rows.sort(key=lambda r: (r[0], -r[6]))
    with open(OUT / "ingredient_associations.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["affinity_id", "slug", "source", "support", "prevalence",
                    "base_rate", "lift", "p_affinity_given_ingredient"])
        w.writerows(assoc_rows)

    # ---- write ingredient_combinations.csv ----
    comb_rows = []
    for aid, _, _, _, _, src in AFFINITIES:
        if src is None:
            continue
        N = aff_recipes.get(aid, 0)
        Nbg = bg_recipes[src]
        if N == 0:
            continue
        scored = []
        for pair, n in aff_pairs[aid].items():
            if n < MIN_PAIR_SUPPORT:
                continue
            prevalence = n / N
            base = bg_pairs[src][pair] / Nbg
            lift = prevalence / base if base else 0.0
            scored.append((lift, n, pair, prevalence, base))
        scored.sort(key=lambda t: -t[0])
        for lift, n, pair, prevalence, base in scored[:TOP_PAIRS_PER_AFFINITY]:
            comb_rows.append([aid, pair[0], pair[1], src, n, round(prevalence, 4),
                              round(base, 5), round(lift, 2)])
    with open(OUT / "ingredient_combinations.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["affinity_id", "slug_a", "slug_b", "source", "support",
                    "prevalence", "base_rate", "lift"])
        w.writerows(comb_rows)

    # ---- console summary ----
    print("background recipes:", dict(bg_recipes))
    print(f"affinities measured: {sum(1 for a in AFFINITIES if a[5])}")
    print(f"association rows: {len(assoc_rows)} | combination rows: {len(comb_rows)}")
    print("\nrecipes per affinity:")
    for aid, name, dim, _, _, src in AFFINITIES:
        if src:
            print(f"  {dim:14s} {aid:16s} {aff_recipes.get(aid,0):7d}  {name}")


if __name__ == "__main__":
    main()
