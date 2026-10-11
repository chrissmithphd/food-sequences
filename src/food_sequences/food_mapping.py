"""
Reviewable food-equivalence hierarchy (v1).

Three levels, kept explicitly separate:
  - SKU            : product_id (exact product)
  - equivalent food: brand- and minor-form-agnostic food (the `subgroup` column),
                     e.g. "spaghetti", "2% milk", "large eggs"
  - food family    : broader grouping with meaningful variation retained as
                     attributes (the `family` column), e.g. "pasta", "milk", "eggs"

Design rules (from the task spec):
  - Names + taxonomy are evidence; aisle membership ALONE is insufficient.
  - Ingredients and finished dishes stay separate (plain pasta != pasta dinner;
    eggs != prepared egg scramble; pizza dough != finished pizza).
  - Preserve attributes that affect equivalence: prepared-vs-ingredient, shape,
    flavor, protein, dietary restriction, physical form, organic.
  - Leave ambiguous items UNRESOLVED (status="ambiguous"); never force a match.

v1 covers three families only. This is deliberately narrow and well-supported;
expansion is future work and must be re-reviewed.
"""

import json
import re

FOOD_MAPPING_VERSION = "v1"

# Families covered in v1 and the aisles whose products are *candidates* for them.
# Candidacy is a starting pool only — names decide final mapping and may exclude
# items (e.g. prepared dishes) or leave them unresolved.
FAMILY_CANDIDATE_AISLES = {
    "pasta": ["dry pasta", "fresh pasta"],
    "milk": ["milk"],
    "eggs": ["eggs"],
}

# Pasta shapes -> canonical equivalent-food subgroup. Ordered: first match wins,
# longer/more-specific patterns first.
PASTA_SHAPES = [
    ("angel_hair", r"angel hair|capellini|cappellini"),
    ("spaghetti", r"spaghett|spaghettini"),
    ("penne", r"\bpenne"),
    ("rigatoni", r"rigatoni"),
    ("macaroni", r"macaroni|elbow"),
    ("fettuccine", r"fettuccin|fettucin"),
    ("linguine", r"linguin"),
    ("rotini", r"rotini|fusilli|spiral"),
    ("shells", r"\bshell|conchigli"),
    ("ziti", r"\bziti"),
    ("lasagna_sheet", r"lasagn"),
    ("farfalle", r"farfalle|bow ?tie"),
    ("orzo", r"\borzo"),
    ("vermicelli", r"vermicelli"),
    ("gnocchi", r"gnocchi"),
    ("pappardelle", r"pappardelle"),
    ("soba", r"\bsoba|udon|ramen"),
    ("rigate", r"rigate"),  # generic ridged tube, after specific shapes
    # egg_noodle and noodle_other are LAST: only when no named shape above matched
    ("egg_noodle", r"egg noodle|egg pasta|enriched egg"),
    ("noodle_other", r"\bnoodle|kluski|dumpling"),
]

FILLED_PASTA = r"ravioli|tortellini|tortelloni|stuffed|filled|triangles|agnolotti|mezzaluna"
PREPARED_DISH = (
    r"\bdinner\b|\bmeal\b|\bentree\b|lasagna with|with meat sauce|with vodka|"
    r"scramble|bites|wrap|bowl\b|frozen entree|microwav"
)


def _attr_flags(name_lower):
    """Attributes that may be preserved across all families."""
    return {
        "organic": bool(re.search(r"organic", name_lower)),
        "gluten_free": bool(re.search(r"gluten[ -]?free", name_lower)),
        "whole_grain": bool(re.search(r"whole wheat|whole grain|whole[ -]grain", name_lower)),
    }


def map_pasta(name):
    low = name.lower()
    attrs = _attr_flags(low)
    attrs["flavor"] = bool(re.search(r"spinach|tomato|veggie|vegetable|basil|garlic|lemon|squid ink|beet", low))
    attrs["egg"] = bool(re.search(r"\begg\b|enriched egg", low))

    # Finished-dish guard: a prepared pasta dish is NOT plain pasta.
    if re.search(PREPARED_DISH, low):
        return dict(family="pasta", subgroup=None, attributes=attrs,
                    confidence="n/a", status="excluded_prepared", is_prepared=True,
                    reason="name indicates a prepared dish, not an ingredient pasta")

    filled = bool(re.search(FILLED_PASTA, low))
    shape = None
    for canon, pat in PASTA_SHAPES:
        if re.search(pat, low):
            shape = canon
            break

    if filled:
        attrs["filled"] = True
        return dict(family="pasta", subgroup="filled_pasta", attributes=attrs,
                    confidence="medium", status="resolved", is_prepared=False,
                    reason="filled pasta (ravioli/tortellini) — distinct subgroup, flagged for review")
    if shape:
        return dict(family="pasta", subgroup=shape, attributes=attrs,
                    confidence="high", status="resolved", is_prepared=False,
                    reason=f"shape keyword matched -> {shape}")
    return dict(family="pasta", subgroup=None, attributes=attrs,
                confidence="low", status="ambiguous", is_prepared=False,
                reason="pasta aisle but no recognized shape keyword — left unresolved")


def map_milk(name):
    low = name.lower()
    attrs = _attr_flags(low)
    attrs["lactose_free"] = bool(re.search(r"lactose[ -]?free", low))
    attrs["flavored"] = bool(re.search(r"chocolate|strawberry|vanilla", low))
    attrs["grassfed"] = bool(re.search(r"grass ?fed|grassmilk", low))

    # Non-cow / specialty products that share the dairy "milk" aisle but are a
    # different food. Out of v1 cow-milk scope (NOT conflated into fat subgroups).
    if re.search(r"almond|coconut|\bsoy|\boat ?milk|cashew|macadamia|hemp|flax|"
                 r"rice milk|\bgoat|egg ?nog|buttermilk|half and half|half & half|"
                 r"\bshake|beverage|nutritional|supershake", low):
        return dict(family="milk", subgroup=None, attributes=attrs,
                    confidence="n/a", status="out_of_scope", is_prepared=False,
                    reason="non-cow or specialty milk product — outside v1 cow-milk scope")

    if re.search(r"\bskim\b|non[ -]?fat|fat[ -]?free|\b0 ?%|zero fat", low):
        sub = "skim"
    elif re.search(r"\b1 ?%|one percent|1 percent|lowfat|low[ -]fat", low):
        sub = "1pct"
    elif re.search(r"\b2 ?%|two percent|2 percent|reduced[ -]?fat", low):
        sub = "2pct"
    elif re.search(r"whole", low) and not attrs["whole_grain"]:
        sub = "whole"
    else:
        return dict(family="milk", subgroup=None, attributes=attrs,
                    confidence="low", status="ambiguous", is_prepared=False,
                    reason="cow milk but no explicit fat level in name — left unresolved")
    return dict(family="milk", subgroup=sub, attributes=attrs,
                confidence="high", status="resolved", is_prepared=False,
                reason=f"fat level matched -> {sub}")


def map_eggs(name):
    low = name.lower()
    attrs = _attr_flags(low)
    attrs["pasture_free_range"] = bool(re.search(r"pastur|free[ -]?range|cage[ -]?free", low))
    attrs["brown"] = bool(re.search(r"brown", low))

    # Prepared egg dishes sitting in the eggs aisle are NOT the egg ingredient.
    if re.search(r"scramble|bites|omelet|frittata|patty|sandwich|bowl\b", low):
        return dict(family="eggs", subgroup=None, attributes=attrs,
                    confidence="n/a", status="excluded_prepared", is_prepared=True,
                    reason="prepared egg dish, not the egg ingredient")

    if re.search(r"egg white", low):
        sub = "egg_whites"
    elif re.search(r"substitute|beaters|liquid egg", low):
        sub = "egg_substitute"
    elif re.search(r"jumbo", low):
        sub = "jumbo"
    elif re.search(r"extra large|x-?large|xl\b", low):
        sub = "xlarge"
    elif re.search(r"\blarge\b", low):
        sub = "large"
    elif re.search(r"medium", low):
        sub = "medium"
    else:
        return dict(family="eggs", subgroup=None, attributes=attrs,
                    confidence="low", status="ambiguous", is_prepared=False,
                    reason="eggs aisle but no size/type keyword — left unresolved")
    conf = "medium" if sub in ("egg_whites", "egg_substitute") else "high"
    return dict(family="eggs", subgroup=sub, attributes=attrs,
                confidence=conf, status="resolved", is_prepared=False,
                reason=f"egg size/type matched -> {sub}")


FAMILY_MAPPERS = {"pasta": map_pasta, "milk": map_milk, "eggs": map_eggs}


def build_mapping(products, aisles):
    """
    products: DataFrame[product_id, product_name, aisle_id, department_id]
    aisles:   DataFrame[aisle_id, aisle]
    Returns a long DataFrame, one row per candidate product, with the versioned
    mapping schema. Products not in any covered family's candidate aisles are
    omitted entirely (they are simply out of v1 scope — not "unresolved").
    """
    import pandas as pd

    aisle_name = dict(zip(aisles["aisle_id"], aisles["aisle"]))
    rows = []
    for family, cand_aisles in FAMILY_CANDIDATE_AISLES.items():
        aisle_ids = {aid for aid, nm in aisle_name.items() if nm in cand_aisles}
        pool = products[products["aisle_id"].isin(aisle_ids)]
        mapper = FAMILY_MAPPERS[family]
        for _, prod in pool.iterrows():
            m = mapper(prod["product_name"])
            rows.append({
                "product_id": prod["product_id"],
                "original_name": prod["product_name"],
                "aisle": aisle_name[prod["aisle_id"]],
                "family": m["family"],
                "subgroup": m["subgroup"],
                "attributes": json.dumps(m["attributes"]),
                "is_prepared": m["is_prepared"],
                "mapping_method": f"name_rule_{FOOD_MAPPING_VERSION}",
                "confidence": m["confidence"],
                "status": m["status"],
                "reason": m["reason"],
                "mapping_version": FOOD_MAPPING_VERSION,
            })
    return pd.DataFrame(rows)
