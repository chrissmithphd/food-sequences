"""
Recipe-ingredient food clustering (v2).

A cluster is what a recipe's ingredient line names: swapping within a cluster does
not change what a cook would write ("1 cup milk", "1 onion", "2 cups chicken broth").
Only flavor- or role-changing differences split clusters. Brand, organic, size,
and fat level are ATTRIBUTES, not cluster boundaries.

The cluster scheme is recipe-role judgment; this module applies it to product names.
Unmatched names are left `unresolved` (never force-fit). Output is frozen to a
versioned CSV; see docs/FOOD_ONTOLOGY.md for the documented ontology.
"""

import json
import re

FOOD_ROLES_VERSION = "v2"

# Ordered recipe-ingredient recognizers: (role_family, cluster, pattern).
# First match wins, so put role-overriding / more-specific patterns first
# (e.g. a prepared dish before its base ingredient; plant milk before milk).
RULES = [
    # --- prepared dishes / kits must beat their base ingredients ---
    ("prepared_dish", "boxed_mac_and_cheese", r"mac.{0,6}cheese|macaroni & chee|macaroni and chee|shells? & chee|shells? and chee"),
    ("prepared_dish", "frozen_pizza", r"\bpizza\b(?!.*(dough|crust mix|sauce))"),
    ("prepared_dish", "frozen_or_prepared_meal", r"\bdinner\b|\bentree\b|lasagna with|with meat sauce|tv dinner|frozen meal|pot pie|burrito|\bbowl\b|lean cuisine|smart ones|hot pocket"),
    ("soups", "soup", r"\bsoup\b|chowder|bisque|ramen bowl|cup noodle|instant noodle"),

    # --- dairy & alternatives (plant before dairy; role splits) ---
    ("milk_and_alternatives", "plant_milk", r"almond ?milk|\bsoy ?milk|oat ?milk|cashew ?milk|rice milk|hemp ?milk|flax ?milk|pea protein milk|macadamia ?milk|almondmilk|soymilk|oatmilk"),
    ("milk_and_alternatives", "coconut_milk", r"coconut ?milk|coconut cream"),
    ("baking_acids", "buttermilk", r"\bbuttermilk\b(?!.*(pancake|waffle|mix|biscuit|bread|dressing|ranch))"),
    ("seasonal_beverage", "eggnog", r"egg ?nog"),
    ("cooking_fats_creamers", "half_and_half", r"half (and|&) half|half-and-half"),
    ("cooking_fats_creamers", "heavy_cream", r"heavy cream|whipping cream|\bcream\b(?!.*(cheese|cheeze|sour|ice|coffee|of ))"),
    ("dairy", "sour_cream", r"sour cream"),
    ("dairy", "cream_cheese", r"cream chee"),
    ("dairy", "cottage_or_ricotta", r"cottage cheese|ricotta"),
    ("dairy", "cheese", r"\bchee(se|z)\b|cheddar|mozzarella|parmesan|parmigian|provolone|swiss chee|monterey|colby|feta|gouda|brie|gruyere|pepper jack|string cheese|shredded.*chee|grated.*chee"),
    ("dairy", "yogurt", r"yogurt|yoghurt|kefir|skyr"),
    ("dairy", "butter", r"\bbutter\b(?!.*(nut|peanut|almond|cashew|cocoa|apple|body))"),
    ("dairy", "milk", r"\bmilk\b|whole milk|reduced fat milk|2% |1% milk|skim milk"),
    ("eggs", "eggs", r"\beggs?\b(?!.*(nog|plant|beater|substitute|roll|white only))"),
    ("eggs", "egg_whites_or_substitute", r"egg white|egg substitute|egg beater"),

    # --- cooking liquids & canned tomato bases ---
    ("cooking_liquids", "stock_or_broth", r"\bbroth\b|\bstock\b|bouillon|bone broth"),
    ("tomato_bases", "tomato_paste", r"tomato paste"),
    ("tomato_bases", "canned_tomatoes", r"(diced|crushed|whole peeled|stewed|fire roasted).{0,12}tomato|tomato.{0,6}(diced|crushed|sauce can)|canned tomato"),
    ("sauces", "pasta_sauce", r"pasta sauce|marinara|spaghetti sauce|alfredo|pizza sauce|arrabbiata|bolognese|vodka sauce"),
    ("sauces", "salsa", r"\bsalsa\b|pico de gallo"),

    # --- pasta / grains / starches (ingredient) ---
    ("pasta_ingredient", "filled_pasta", r"ravioli|tortellini|tortelloni|agnolotti"),
    ("pasta_ingredient", "pasta", r"spaghetti|penne|rigatoni|macaroni|fettuccin|fettucin|linguin|rotini|fusilli|lasagn|farfalle|\bziti\b|\borzo\b|vermicelli|gnocchi|pappardelle|\bpasta\b|egg noodle|\bnoodle"),
    ("grains", "rice", r"\brice\b(?!.*(cake|milk|vinegar|paper|krispies|a roni))"),
    ("grains", "oats", r"\boats?\b|oatmeal|rolled oats|steel cut"),
    ("grains", "quinoa_other_grain", r"quinoa|couscous|barley|farro|bulgur|polenta"),
    ("bread_and_baked", "bread", r"\bbread\b|baguette|sourdough|ciabatta|\bbun\b|\brolls?\b|bagel|english muffin|pita|naan"),
    ("bread_and_baked", "tortilla_flatbread", r"tortilla|flatbread|\bwraps?\b"),
    ("baking", "flour", r"\bflour\b"),
    ("baking", "sugar", r"\bsugar\b(?!.*(snap|free gum))"),

    # --- proteins ---
    ("protein", "chicken", r"\bchicken\b(?!.*(broth|stock|soup|flavor|bouillon|salad dressing))"),
    ("protein", "ground_beef_or_beef", r"ground beef|\bbeef\b(?!.*(broth|stock|jerky|flavor|bouillon))"),
    ("protein", "pork", r"\bpork\b|\bham\b(?!burger)"),
    ("protein", "turkey", r"\bturkey\b(?!.*(broth|stock))"),
    ("protein", "bacon_sausage", r"\bbacon\b|sausage|hot dog|frankfurter|bratwurst|chorizo"),
    ("protein", "deli_lunchmeat", r"lunch ?meat|deli (meat|slices)|sliced (turkey|ham|chicken|roast beef)|pepperoni|salami|prosciutto"),
    ("protein", "fish_seafood", r"salmon|\btuna\b|tilapia|cod\b|shrimp|crab|\bfish\b|haddock|mahi|halibut"),
    ("protein", "tofu_meat_alt", r"\btofu\b|tempeh|seitan|meatless|plant.?based.*(burger|chicken|meat)|beyond|impossible"),

    # --- produce: fruit (variety/organic/size = attributes) ---
    ("produce_fruit", "banana", r"\bbanana"),
    ("produce_fruit", "apple", r"\bapple\b(?!.*(sauce|juice|cider|vinegar))|honeycrisp|fuji|gala|granny smith"),
    ("produce_fruit", "berry_strawberry", r"strawberr"),
    ("produce_fruit", "berry_blueberry", r"blueberr"),
    ("produce_fruit", "berry_raspberry", r"raspberr"),
    ("produce_fruit", "berry_blackberry", r"blackberr"),
    ("produce_fruit", "grape", r"\bgrapes?\b(?!fruit)"),
    ("produce_fruit", "citrus_lemon", r"\blemon\b(?!ade)"),
    ("produce_fruit", "citrus_lime", r"\blimes?\b"),
    ("produce_fruit", "citrus_orange", r"\borange\b(?!.*juice)|clementine|mandarin|tangerine"),
    ("produce_fruit", "avocado", r"avocado|hass"),
    ("produce_fruit", "melon", r"watermelon|cantaloupe|honeydew|\bmelon\b"),
    ("produce_fruit", "stone_fruit", r"peach|nectarine|plum\b|apricot|\bcherr"),
    ("produce_fruit", "tropical_fruit", r"mango|pineapple|papaya|kiwi|\bfig\b|pomegranate|\bdates?\b"),
    ("produce_fruit", "pear", r"\bpears?\b"),

    # --- produce: vegetables & aromatics ---
    ("produce_veg", "onion", r"\bonions?\b|shallot|scallion|green onion|leek"),
    ("produce_veg", "garlic", r"\bgarlic\b(?!.*(bread|powder|salt))"),
    ("produce_veg", "ginger", r"\bginger\b(?!.*(ale|bread|snap))"),
    ("produce_veg", "tomato_fresh", r"\btomato(es)?\b(?!.*(paste|sauce|soup|canned|diced|crushed|dried|sun))"),
    ("produce_veg", "potato", r"\bpotato(es)?\b(?!.*(chip|frozen fries|tots))|\byam\b|sweet potato"),
    ("produce_veg", "carrot", r"\bcarrots?\b"),
    ("produce_veg", "celery", r"\bcelery\b"),
    ("produce_veg", "leafy_green", r"spinach|\bkale\b|arugula|romaine|lettuce|spring mix|salad greens|chard|collard"),
    ("produce_veg", "bell_pepper", r"bell pepper|sweet pepper"),
    ("produce_veg", "cucumber", r"cucumber"),
    ("produce_veg", "zucchini_squash", r"zucchini|squash|courgette"),
    ("produce_veg", "broccoli_cauliflower", r"broccoli|cauliflower"),
    ("produce_veg", "mushroom", r"mushroom|cremini|portobello|shiitake"),
    ("produce_veg", "asparagus", r"asparagus"),
    ("produce_veg", "pepper", r"bell pepper|sweet pepper|jalape|poblano|serrano|red peppers?\b|green peppers?\b|mini sweet pepper"),
    ("produce_veg", "green_beans", r"green beans|string beans"),
    ("produce_veg", "brussels_sprouts", r"brussels? sprout"),
    ("produce_veg", "cabbage", r"cabbage|bok choy"),
    ("produce_veg", "corn", r"\bcorn\b(?!.*(flake|starch|bread|meal|syrup|chip|tortilla))"),
    ("produce_veg", "peas", r"\bpeas\b(?!.*(nut|crisp))|snap peas?\b(?!.*crisp)|snow peas?"),
    ("produce_veg", "radish", r"radish"),
    ("produce_veg", "beet", r"\bbeets?\b"),
    ("produce_veg", "eggplant", r"eggplant|aubergine"),
    ("produce_veg", "fresh_herb", r"\bcilantro\b|\bparsley\b|\bbasil\b(?!.*(sauce|pesto))|\bmint\b|\bthyme\b|\brosemary\b|\bdill\b"),
    ("legumes", "beans_legumes", r"black beans|garbanzo|chickpea|kidney beans|pinto beans|cannellini|navy beans|refried beans|\blentils?\b|\bbeans\b(?!.*(green|coffee|vanilla|jelly|bean dip))"),
    ("spreads", "hummus_dip", r"\bhummus\b"),

    # --- condiments / fats / spreads ---
    ("condiments", "olive_oil", r"olive oil"),
    ("condiments", "cooking_oil", r"\b(vegetable|canola|avocado|coconut|grapeseed) oil\b|cooking oil"),
    ("condiments", "vinegar", r"vinegar"),
    ("condiments", "soy_sauce", r"soy sauce|tamari"),
    ("condiments", "hot_sauce", r"hot sauce|sriracha|tabasco|buffalo sauce"),
    ("condiments", "ketchup", r"ketchup|catsup"),
    ("condiments", "mustard", r"\bmustard\b"),
    ("condiments", "mayo", r"mayonnaise|\bmayo\b"),
    ("condiments", "salad_dressing", r"salad dressing|ranch dressing|vinaigrette|italian dressing"),
    ("spreads", "nut_butter", r"peanut butter|almond butter|cashew butter|\bnut butter"),
    ("spreads", "jam_jelly", r"\bjam\b|jelly|preserves|fruit spread|marmalade"),
    ("spreads", "honey_syrup", r"\bhoney\b|maple syrup|\bsyrup\b|agave"),

    # --- beverages ---
    ("beverages", "water", r"\bwater\b(?!.*(melon|chestnut|cress))|seltzer|sparkling water|club soda"),
    ("beverages", "soda", r"\bsoda\b|\bcola\b|soft drink|\bpop\b|root beer|ginger ale"),
    ("beverages", "juice", r"\bjuice\b|lemonade|apple cider\b"),
    ("beverages", "coffee", r"\bcoffee\b|espresso|\blatte\b|cold brew"),
    ("beverages", "tea", r"\btea\b(?!spoon)|matcha|chai"),
    ("beverages", "beer", r"\bbeer\b|\bale\b(?!rgy)|lager|ipa\b"),
    ("beverages", "wine", r"\bwine\b|chardonnay|cabernet|merlot|pinot|rose\b|champagne|prosecco"),

    # --- snacks ---
    ("snacks", "chips", r"\bchips\b|tortilla chips|potato chips|pretzel"),
    ("snacks", "crackers", r"\bcrackers?\b"),
    ("snacks", "cookies_sweets", r"\bcookies?\b|\bcandy\b|chocolate bar|\bbrownie"),
    ("snacks", "granola_bar", r"granola bar|energy bar|protein bar|cereal bar"),
    ("snacks", "nuts_seeds", r"\balmonds?\b|\bcashews?\b|\bwalnuts?\b|\bpistachio|\bpecans?\b|mixed nuts|sunflower seed|\bpeanuts\b"),
    ("breakfast", "cereal", r"\bcereal\b|granola\b|corn flakes|cheerios|\bmuesli\b"),
    ("frozen", "ice_cream", r"ice cream|gelato|frozen yogurt|sorbet|popsicle"),
]

# Pre-compile
_COMPILED = [(fam, clu, re.compile(pat)) for fam, clu, pat in RULES]


def _attributes(low):
    return {
        "organic": bool(re.search(r"organic", low)),
        "gluten_free": bool(re.search(r"gluten[ -]?free", low)),
        "fat_level": ("skim" if re.search(r"\bskim|non[ -]?fat|fat free|\b0 ?%", low)
                      else "1pct" if re.search(r"\b1 ?%|1 percent|lowfat|low fat", low)
                      else "2pct" if re.search(r"\b2 ?%|2 percent|reduced fat", low)
                      else "whole" if re.search(r"\bwhole\b", low) else None),
        "flavored": bool(re.search(r"chocolate|strawberr|vanilla|flavored", low)),
    }


def classify_product(name):
    """Return dict(role_family, cluster, attributes, confidence, status, reason)."""
    low = str(name).lower()
    attrs = _attributes(low)
    for fam, clu, pat in _COMPILED:
        if pat.search(low):
            return dict(role_family=fam, cluster=clu, attributes=attrs,
                        confidence="high", status="resolved",
                        reason=f"recipe-ingredient match -> {clu}")
    return dict(role_family=None, cluster=None, attributes=attrs,
                confidence="low", status="unresolved",
                reason="no recipe-ingredient cluster matched")


def build_roles(products, aisles, volume=None):
    """
    products: DataFrame[product_id, product_name, aisle_id, ...]
    aisles:   DataFrame[aisle_id, aisle]
    volume:   optional DataFrame[product_id, n] purchase counts for ranking
    Returns long DataFrame with the frozen role schema (one row per product).
    """
    import pandas as pd

    aname = dict(zip(aisles["aisle_id"], aisles["aisle"]))
    vol = dict(zip(volume["product_id"], volume["n"])) if volume is not None else {}
    rows = []
    for _, p in products.iterrows():
        c = classify_product(p["product_name"])
        rows.append({
            "product_id": p["product_id"],
            "original_name": p["product_name"],
            "aisle": aname.get(p["aisle_id"]),
            "role_family": c["role_family"],
            "cluster": c["cluster"],
            "attributes": json.dumps(c["attributes"]),
            "confidence": c["confidence"],
            "status": c["status"],
            "reason": c["reason"],
            "purchase_count": vol.get(p["product_id"], 0),
            "roles_version": FOOD_ROLES_VERSION,
        })
    df = pd.DataFrame(rows)
    return df.sort_values("purchase_count", ascending=False).reset_index(drop=True)
