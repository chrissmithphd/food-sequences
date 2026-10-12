"""
Recipe-role food classifier (v4) — a code reproduction of the LLM pilot judgment.

This is NOT per-item LLM labeling; it encodes the identify-then-group reasoning the
v3 LLM pilot established, so results can be replicated (approximately — the LLM pilot
is the gold reference; see scripts/build_food_mapping_full.py for the agreement check).

Order of decision (first match wins):
  1. SCOPE — non-food by department/aisle -> out_of_scope (pet food, personal care, household)
  2. COMPOUND OVERRIDES — multiword names where a modifier would otherwise win
     (grape tomato -> tomato, spaghetti squash -> squash, corn dog -> corn dog)
  3. PRODUCT-TYPE ANCHORS — the head product noun beats flavor/variety words
     (garlic crackers -> crackers, mayonnaise with olive oil -> mayonnaise)
  4. unmatched -> unresolved (never force-fit)

Groups align with analysis/food_classification/group_catalog_v3.json so output can be
compared directly to the LLM pilot labels.
"""

import json
import re

CLASSIFIER_VERSION = "v4"

NONFOOD_DEPARTMENTS = {"personal care", "household", "pets"}
NONFOOD_AISLES = {
    "dog food care", "cat food care", "baby accessories", "baby bath body care",
    "diapers wipes", "skin care", "body lotions soap", "soap", "hair care",
    "deodorants", "oral hygiene", "feminine care", "facial care", "eye ear care",
    "shave needs", "first aid", "cold flu allergy", "digestion",
    "muscles joints pain relief", "vitamins supplements", "paper goods",
    "trash bags liners", "cleaning products", "dish detergents", "laundry",
    "air fresheners candles", "food storage", "kitchen supplies", "more household",
    "plates bowls cups flatware",
}

# (group, regex) — specific multiword overrides that must beat generic anchors.
COMPOUND_OVERRIDES = [
    ("winter_squash", r"spaghetti squash|butternut squash|acorn squash|winter squash|kabocha|delicata"),
    ("tomato_fresh", r"(grape|cherry|roma|plum|vine[- ]ripen|heirloom|campari) tomato|tomato(es)? on the vine"),
    ("corn_dog", r"corn dog"),
    ("pancake_waffle_mix", r"(pancake|waffle).{0,10}mix|mix.{0,10}(pancake|waffle)"),
    ("buttermilk", r"cultured buttermilk|\bbuttermilk\b(?!.*(pancake|waffle|biscuit|bread|ranch|dressing|mix))"),
]

# Ordered product-type anchors. EARLIER = wins. Finished-product / head nouns first,
# so flavor and variety modifiers (garlic, grape, spinach) don't hijack the label.
ANCHORS = [
    # prepared dishes / kits (beat their base ingredients)
    ("boxed_mac_and_cheese", r"mac.{0,6}chee|macaroni.*(chee|chedd)|shells?.*(chee|chedd)|mac & chee|mac and chee"),
    ("frozen_or_prepared_meal", r"\bdinner\b|\bentree\b|lasagna with|with meat sauce|pot pie|burrito|lean cuisine|smart ones|hot pocket|\bbowl\b.*rice|tv dinner"),
    ("frozen_pizza", r"\bpizza\b(?!.*(dough|crust mix|sauce|seasoning))"),
    ("soup", r"\bsoup\b|chowder|bisque"),
    # stuffed pasta beats cheese/greens words
    ("filled_pasta", r"ravioli|tortellini|tortelloni|agnolotti|stuffed shells|stuffed pasta"),
    # snack products beat flavor words (garlic/cheddar crackers)
    ("crackers", r"\bcrackers?\b|nut thins|rice crackers|wheat thins|triscuit|saltine"),
    ("rice_cakes", r"rice cakes?"),
    ("baking_chips", r"chocolate chips|baking chips|butterscotch chips|white chocolate chips|carob chips|cacao chips"),
    ("candy_chocolate", r"chips ahoy|\bcandy\b|chocolate bar|milk chocolate|dark chocolate(?! chips)|\btoffee\b|gummy|licorice|\bcaramels?\b|\btruffles?\b"),
    ("chips", r"\bchips\b|tortilla chips|potato chips|\bpretzels?\b|snap pea crisps|veggie straws|pita chips"),
    # condiments/sauces beat their ingredient words (mayo-with-olive-oil)
    ("mayonnaise", r"mayonnaise|\bmayo\b|aioli"),
    ("ketchup", r"ketchup|catsup"),
    ("mustard", r"\bmustard\b(?!.*(greens|seed))"),
    ("hot_sauce", r"hot sauce|sriracha|tabasco|buffalo sauce|chili sauce"),
    ("salad_dressing", r"salad dressing|ranch dressing|vinaigrette|italian dressing|caesar dressing"),
    ("pasta_sauce", r"pasta sauce|marinara|spaghetti sauce|alfredo sauce|\balfredo\b|pizza sauce|arrabbiata|vodka sauce"),
    ("salsa", r"\bsalsa\b|pico de gallo"),
    ("soy_sauce", r"soy sauce|tamari"),
    ("tomato_paste", r"tomato paste"),
    ("canned_tomatoes", r"(diced|crushed|whole peeled|stewed|fire roasted).{0,12}tomato|canned tomato|tomato sauce"),
    # oils / vinegars
    ("olive_oil", r"olive oil"),
    ("cooking_oil", r"\b(vegetable|canola|avocado|coconut|grapeseed|sunflower) oil\b|cooking oil"),
    ("vinegar", r"vinegar"),
    # produce: squash (beats pasta for 'spaghetti squash' already handled; zucchini separate)
    ("zucchini", r"zucchini|courgette"),
    ("winter_squash", r"\bsquash\b(?!.*(blossom))"),
    # tomato (fresh) beats grape only because grape-tomato is an override above;
    # plain fresh tomato here
    ("tomato_fresh", r"\btomato(es)?\b(?!.*(paste|sauce|soup|canned|dried|sun[- ]))"),
    # pasta / grains
    ("filled_pasta_check", r""),  # placeholder (filled handled above)
    ("pasta", r"spaghetti|penne|rigatoni|macaroni|fettuccin|fettucin|linguin|rotini|fusilli|lasagn|farfalle|\bziti\b|\borzo\b|vermicelli|gnocchi|pappardelle|\bpasta\b|egg noodle|\bnoodle"),
    ("couscous", r"couscous"),
    ("rice", r"\brice\b(?!.*(cake|milk|vinegar|paper|krispies|a roni|cracker|bread))"),
    ("oats", r"\boats?\b|oatmeal|rolled oats|steel cut"),
    ("quinoa_other_grain", r"quinoa|barley|farro|bulgur|polenta|millet"),
    ("bread", r"\bbread\b|baguette|sourdough|ciabatta|\bbuns?\b|\brolls?\b|bagel|english muffin|\bpita\b|naan|tortilla|flatbread"),
    ("flour", r"\bflour\b"),
    ("sugar", r"\bsugar\b(?!.*(snap|free gum|cookie))"),
    ("pesto", r"\bpesto\b"),
    ("guacamole", r"guacamole"),
    ("applesauce", r"apple ?sauce"),
    ("kombucha", r"kombucha"),
    # dairy & alternatives (plant/coconut/buttermilk already partly handled)
    ("plant_milk", r"almond ?milk|\bsoy ?milk|oat ?milk|cashew ?milk|rice milk|hemp ?milk|flax ?milk|macadamia ?milk|almondmilk|soymilk|oatmilk|coconut ?milk"),
    ("half_and_half", r"half (and|&) half|half-and-half"),
    ("heavy_cream", r"heavy cream|whipping cream"),
    ("sour_cream", r"sour cream"),
    ("cream_cheese", r"cream chee"),
    ("cottage_or_ricotta", r"cottage cheese|ricotta"),
    ("cheese", r"\bchee(se|z)\b|cheddar|mozzarella|parmesan|parmigian|provolone|swiss chee|monterey|colby|\bfeta\b|gouda|\bbrie\b|gruyere|pepper jack|string cheese"),
    ("yogurt", r"yogurt|yoghurt|\bkefir\b|skyr"),
    ("butter", r"\bbutter\b(?!.*(nut|peanut|almond|cashew|cocoa|apple|body))"),
    ("eggnog", r"egg ?nog"),
    ("milk", r"\bmilk\b|whole milk|reduced fat milk|skim milk"),
    ("eggs", r"\beggs?\b(?!.*(nog|plant|beater|substitute|roll))"),
    ("egg_whites_or_substitute", r"egg white|egg substitute|egg beater"),
    # cooking liquids
    ("cooking_stock_broth", r"\bbroth\b|\bstock\b(?! up)|bouillon|bone broth"),
    # proteins
    ("bacon_sausage", r"\bbacon\b|sausage|hot dog|frankfurter|bratwurst|chorizo"),
    ("deli_lunchmeat", r"lunch ?meat|deli (meat|slices)|sliced (turkey|ham|chicken|roast beef)|pepperoni|salami|prosciutto"),
    ("chicken", r"\bchicken\b(?!.*(broth|stock|soup|bouillon|flavored|dog|cat))"),
    ("ground_beef_or_beef", r"ground beef|\bbeef\b(?!.*(broth|stock|jerky|flavored|dog|cat))"),
    ("pork", r"\bpork\b|\bham\b(?!burger)"),
    ("turkey", r"\bturkey\b(?!.*(broth|stock))"),
    ("fish_seafood", r"salmon|\btuna\b|tilapia|\bcod\b|shrimp|\bcrab\b|\bfish\b|haddock|mahi|halibut|scallop"),
    ("tofu_meat_alt", r"\btofu\b|tempeh|seitan|meatless|plant.?based.*(burger|chicken|meat)|beyond meat|impossible"),
    # legumes / spreads
    ("beans_legumes", r"black beans|garbanzo|chickpea|kidney beans|pinto beans|cannellini|navy beans|refried beans|\blentils?\b|\bbeans\b(?!.*(green|coffee|vanilla|jelly))"),
    ("hummus_dip", r"\bhummus\b"),
    ("nut_butter", r"peanut butter|almond butter|cashew butter|\bnut butter"),
    ("jam_jelly", r"\bjam\b|jelly|preserves|fruit spread|marmalade"),
    ("honey_syrup", r"\bhoney\b|maple syrup|\bsyrup\b|agave"),
    # desserts / snack products must beat fruit-FLAVOR words (raspberry gelato -> ice cream)
    ("ice_cream", r"ice cream|gelato|frozen yogurt|\bsorbet\b|popsicle|\bgelato pop\b"),
    ("cookies_sweets", r"\bcookies?\b|chips ahoy|oreo|\bbrownie|candy bar"),
    ("granola_bar", r"granola bar|energy bar|protein bar|cereal bar|\bnut bar\b|snack bar"),
    ("jam_jelly", r"\bjam\b|jelly|preserves|marmalade|(strawberr|raspberr|blueberr|blackberr|grape|apricot|peach|cherry|fruit)[a-z]* spread"),
    # produce: fruit
    ("banana", r"\bbanana"),
    ("apple", r"\bapple\b(?!.*(sauce|juice|cider|vinegar))|honeycrisp|fuji apple|gala apple|granny smith"),
    ("strawberries", r"strawberr"), ("blueberries", r"blueberr"),
    ("raspberries", r"raspberr"), ("blackberries", r"blackberr"),
    ("grapes", r"\bgrapes?\b(?!fruit)"),
    ("citrus_lemon", r"\blemon\b(?!ade)"), ("citrus_lime", r"\blimes?\b"),
    ("citrus_orange", r"\borange\b(?!.*juice)|clementine|mandarin|tangerine"),
    ("citrus_grapefruit", r"grapefruit"),
    ("mixed_berries", r"berry medley|mixed berr|triple berr"),
    ("avocado", r"avocado|hass"),
    ("melon", r"watermelon|cantaloupe|honeydew|\bmelon\b"),
    ("stone_fruit", r"peach|nectarine|\bplum\b|apricot|\bcherr"),
    ("tropical_fruit", r"mango|pineapple|papaya|\bkiwi\b|pomegranate|\bdates?\b"),
    ("pear", r"\bpears?\b"),
    # produce: vegetables & aromatics
    ("onion", r"\bonions?\b|shallot|scallion|green onion|\bleek"),
    ("garlic", r"\bgarlic\b(?!.*(bread|powder|salt))"),
    ("ginger", r"\bginger\b(?!.*(ale|bread|snap))"),
    ("potato", r"\bpotato(es)?\b(?!.*(chip|fries|tots))|\byams?\b|sweet potato"),
    ("carrot", r"\bcarrots?\b"),
    ("celery", r"\bcelery\b"),
    ("leafy_green", r"spinach|\bkale\b|arugula|romaine|lettuce|spring mix|salad greens|super greens|mixed greens|baby greens|chard|collard"),
    ("pepper", r"bell pepper|sweet pepper|jalape|poblano|serrano|red peppers?\b|green peppers?\b"),
    ("cucumber", r"cucumber"),
    ("broccoli_cauliflower", r"broccoli|cauliflower"),
    ("mushroom", r"mushroom|cremini|portobello|shiitake"),
    ("asparagus", r"asparagus"),
    ("green_beans", r"green beans|string beans"),
    ("brussels_sprouts", r"brussels? sprout"),
    ("cabbage", r"cabbage|bok choy"),
    ("corn", r"\bcorn\b(?!.*(flake|starch|bread|meal|syrup|chip|tortilla|dog))"),
    ("peas", r"\bpeas\b(?!.*(nut|crisp))|snap peas?\b(?!.*crisp)|snow peas?"),
    ("radish", r"radish"), ("beet", r"\bbeets?\b"), ("eggplant", r"eggplant|aubergine"),
    ("fresh_herb", r"\bcilantro\b|\bparsley\b|\bbasil\b(?!.*(sauce|pesto))|\bmint\b(?!.*gum)|\bthyme\b|\brosemary\b|\bdill\b"),
    # beverages / snacks / frozen
    ("water", r"\bwater\b(?!.*(melon|chestnut|cress))|seltzer|sparkling water|club soda"),
    ("soda", r"\bsoda\b|\bcola\b|soft drink|root beer|ginger ale"),
    ("juice", r"\bjuice\b|lemonade|apple cider\b"),
    ("coffee", r"\bcoffee\b|espresso|\blatte\b|cold brew"),
    ("tea", r"\btea\b(?!spoon)|matcha|\bchai\b"),
    ("beer", r"\bbeer\b|\bale\b(?!rgy)|lager|\bipa\b"),
    ("wine", r"\bwine\b|chardonnay|cabernet|merlot|pinot|\brose\b|champagne|prosecco"),
    ("cookies_sweets", r"\bcookies?\b|\bcandy\b|chocolate bar|\bbrownie"),
    ("granola_bar", r"granola bar|energy bar|protein bar|cereal bar"),
    ("nuts_seeds", r"\balmonds?\b|\bcashews?\b|\bwalnuts?\b|pistachio|\bpecans?\b|mixed nuts|sunflower seed|\bpeanuts\b"),
    ("cereal", r"\bcereal\b|granola\b|corn flakes|cheerios|\bmuesli\b"),
    ("ice_cream", r"ice cream|gelato|frozen yogurt|\bsorbet\b|popsicle"),
]
_ANCHORS = [(g, re.compile(p)) for g, p in ANCHORS if p]
_OVERRIDES = [(g, re.compile(p)) for g, p in COMPOUND_OVERRIDES]

# role_family lookup (from the catalog scheme)
FAMILY = {
    "winter_squash": "vegetables", "tomato_fresh": "vegetables", "zucchini": "vegetables",
    "onion": "vegetables", "garlic": "vegetables", "ginger": "vegetables", "potato": "vegetables",
    "carrot": "vegetables", "celery": "vegetables", "leafy_green": "vegetables", "pepper": "vegetables",
    "cucumber": "vegetables", "broccoli_cauliflower": "vegetables", "mushroom": "vegetables",
    "asparagus": "vegetables", "green_beans": "vegetables", "brussels_sprouts": "vegetables",
    "cabbage": "vegetables", "corn": "vegetables", "peas": "vegetables", "radish": "vegetables",
    "beet": "vegetables", "eggplant": "vegetables", "fresh_herb": "vegetables",
    "banana": "fruit", "apple": "fruit", "strawberries": "fruit", "blueberries": "fruit",
    "raspberries": "fruit", "blackberries": "fruit", "grapes": "fruit", "citrus_lemon": "fruit",
    "citrus_lime": "fruit", "citrus_orange": "fruit", "avocado": "fruit", "melon": "fruit",
    "stone_fruit": "fruit", "tropical_fruit": "fruit", "pear": "fruit",
    "milk": "dairy", "cheese": "dairy", "yogurt": "dairy", "butter": "dairy",
    "cream_cheese": "dairy", "cottage_or_ricotta": "dairy", "sour_cream": "dairy",
    "eggs": "dairy", "egg_whites_or_substitute": "dairy",
    "plant_milk": "milk_and_alternatives", "eggnog": "seasonal_beverage",
    "half_and_half": "cooking_fats_creamers", "heavy_cream": "cooking_fats_creamers",
    "buttermilk": "baking_acids", "pancake_waffle_mix": "baking_mixes",
    "cooking_stock_broth": "cooking_liquids", "soup": "soups",
    "tomato_paste": "tomato_bases", "canned_tomatoes": "tomato_bases",
    "pasta_sauce": "sauces", "salsa": "sauces", "soy_sauce": "condiments",
    "olive_oil": "oils", "cooking_oil": "oils", "vinegar": "condiments",
    "ketchup": "condiments", "mustard": "condiments", "mayonnaise": "condiments",
    "hot_sauce": "condiments", "salad_dressing": "condiments",
    "crackers": "snacks", "rice_cakes": "snacks", "chips": "snacks",
    "cookies_sweets": "snacks", "granola_bar": "snacks", "nuts_seeds": "snacks",
    "filled_pasta": "pasta_and_dishes", "pasta": "pasta_ingredient",
    "boxed_mac_and_cheese": "prepared_dish", "frozen_pizza": "prepared_dish",
    "frozen_or_prepared_meal": "prepared_dish", "corn_dog": "prepared_dish",
    "couscous": "grains", "rice": "grains", "oats": "grains", "quinoa_other_grain": "grains",
    "bread": "bread_and_baked", "flour": "baking", "sugar": "baking",
    "pesto": "sauces", "guacamole": "spreads", "applesauce": "fruit",
    "kombucha": "beverages", "citrus_grapefruit": "fruit", "mixed_berries": "fruit",
    "chicken": "protein", "ground_beef_or_beef": "protein", "pork": "protein",
    "turkey": "protein", "bacon_sausage": "protein", "deli_lunchmeat": "protein",
    "fish_seafood": "protein", "tofu_meat_alt": "protein",
    "beans_legumes": "legumes", "hummus_dip": "spreads", "nut_butter": "spreads",
    "jam_jelly": "spreads", "honey_syrup": "spreads",
    "water": "beverages", "soda": "beverages", "juice": "beverages", "coffee": "beverages",
    "tea": "beverages", "beer": "beverages", "wine": "beverages",
    "cereal": "breakfast", "ice_cream": "frozen",
    "baking_chips": "baking", "candy_chocolate": "snacks",
}


def classify(name, aisle, department):
    low = str(name).lower()
    attrs = {
        "organic": bool(re.search(r"organic", low)),
        "gluten_free": bool(re.search(r"gluten[ -]?free", low)),
        "fat_level": ("skim" if re.search(r"skim|non[ -]?fat|fat free|\b0 ?%", low)
                      else "2pct" if re.search(r"\b2 ?%|2 percent|reduced fat", low)
                      else "1pct" if re.search(r"\b1 ?%|1 percent|lowfat|low fat", low)
                      else "whole" if re.search(r"\bwhole\b", low) else None),
    }
    # 1. scope
    if department in NONFOOD_DEPARTMENTS or aisle in NONFOOD_AISLES:
        fam = ("OUT_OF_SCOPE_pet_food" if (department == "pets" or "food care" in str(aisle))
               else "OUT_OF_SCOPE_household" if (department == "household" or aisle in {
                   "paper goods", "trash bags liners", "cleaning products", "dish detergents",
                   "laundry", "air fresheners candles", "food storage", "kitchen supplies",
                   "more household", "plates bowls cups flatware"})
               else "OUT_OF_SCOPE_personal_care")
        return dict(cluster=fam, role_family="non_food", attributes=attrs,
                    status="out_of_scope", confidence="high",
                    reason=f"non-food aisle/department ({aisle}/{department})")
    # 2. compound overrides
    for g, pat in _OVERRIDES:
        if pat.search(low):
            return dict(cluster=g, role_family=FAMILY.get(g), attributes=attrs,
                        status="resolved", confidence="high", reason=f"compound override -> {g}")
    # 3. product-type anchors
    for g, pat in _ANCHORS:
        if pat.search(low):
            return dict(cluster=g, role_family=FAMILY.get(g), attributes=attrs,
                        status="resolved", confidence="high", reason=f"anchor -> {g}")
    return dict(cluster=None, role_family=None, attributes=attrs,
                status="unresolved", confidence="low", reason="no anchor matched")


def build(products, aisles, departments, volume=None):
    import pandas as pd
    an = dict(zip(aisles["aisle_id"], aisles["aisle"]))
    dn = dict(zip(departments["department_id"], departments["department"]))
    vol = dict(zip(volume["product_id"], volume["n"])) if volume is not None else {}
    rows = []
    for _, p in products.iterrows():
        a, d = an.get(p["aisle_id"]), dn.get(p["department_id"])
        c = classify(p["product_name"], a, d)
        rows.append({"product_id": p["product_id"], "original_name": p["product_name"],
                     "aisle": a, "department": d, "cluster": c["cluster"],
                     "role_family": c["role_family"], "attributes": json.dumps(c["attributes"]),
                     "status": c["status"], "confidence": c["confidence"], "reason": c["reason"],
                     "purchase_count": vol.get(p["product_id"], 0),
                     "classifier_version": CLASSIFIER_VERSION})
    return pd.DataFrame(rows).sort_values("purchase_count", ascending=False).reset_index(drop=True)
