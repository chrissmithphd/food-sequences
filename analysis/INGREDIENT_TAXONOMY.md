# Recipe Ingredient Taxonomy

Recipe-grounded ingredient categories for classifying grocery products. Built from knowledge of how 1000+ recipes across diverse cuisines (American, Italian, French, Mexican, Chinese, Indian, Thai, Mediterranean, Japanese, Korean, Middle Eastern, etc.) list their ingredients.

## Principles

1. **Recipe equivalence**: Products that serve the same role in recipes get the same ingredient label
   - "Organic Banana" and "Banana" → `banana`
   - "Whole Milk", "2% Milk", "Skim Milk" → `milk` (fat level is an attribute)
   - "Spaghetti", "Penne", "Fettuccine" → `pasta` (shape matters but base ingredient is the same)

2. **Flavor vs. identity**: Flavor modifiers don't change the product category
   - "Garlic Crackers" → `crackers` (garlic describes flavor, product is crackers)
   - "Raspberry Coffee Creamer" → `cream` (raspberry is flavor, product is cream)
   - "Vanilla Yogurt" → `yogurt` (vanilla is flavor, product is yogurt)

3. **Prepared dishes are separate**: Complete meals are not collapsed into base ingredients
   - "Mac and Cheese" → `mac_and_cheese` (prepared_dish), NOT pasta
   - "Frozen Lasagna" → `lasagna` (prepared_dish), NOT pasta
   - "Chicken Soup" → `soup` (prepared_dish), NOT chicken + broth

4. **Meaningful distinctions**: Separate ingredients when recipes distinguish them
   - `milk` vs `buttermilk` vs `plant_milk` (different recipe uses)
   - `tomato` vs `canned_tomato` vs `tomato_paste` (different forms, different uses)
   - `chicken_breast` vs `ground_chicken` (different preparations)

## Categories

### PRODUCE - FRUIT

**Bananas & Plantains**
- `banana`: All bananas (organic, conventional, any size)
- `plantain`: Cooking plantains

**Apples**
- `apple`: All apple varieties (Honeycrisp, Gala, Fuji, Granny Smith, Red Delicious, etc.)
  - Recipe use: eating fresh, baking, cooking
  - Varieties matter for texture/sweetness but same base ingredient

**Berries**
- `strawberry`: Fresh or frozen strawberries
- `blueberry`: Fresh or frozen blueberries  
- `raspberry`: Fresh or frozen raspberries
- `blackberry`: Fresh or frozen blackberries
- `cranberry`: Fresh or dried cranberries
- `mixed_berries`: Berry medleys, triple berry mixes

**Citrus**
- `lemon`: Fresh lemons (not lemonade, not lemon juice bottles)
- `lime`: Fresh limes
- `orange`: Oranges, clementines, mandarins, tangerines
- `grapefruit`: Fresh grapefruit

**Stone Fruit**
- `peach`: Fresh or frozen peaches
- `nectarine`: Fresh or frozen nectarines
- `plum`: Fresh plums
- `apricot`: Fresh or dried apricots
- `cherry`: Fresh cherries (not canned pie filling)

**Tropical Fruit**
- `mango`: Fresh or frozen mango
- `pineapple`: Fresh or frozen pineapple
- `papaya`: Fresh papaya
- `kiwi`: Fresh kiwi
- `pomegranate`: Fresh pomegranate or arils
- `dragon_fruit`: Fresh dragon fruit
- `passion_fruit`: Fresh passion fruit

**Grapes & Raisins**
- `grape`: Table grapes (red, green, seedless)
- `raisin`: Dried grapes
- `dried_fruit`: Other dried fruits (dates, figs, etc.)

**Melons**
- `watermelon`: Fresh watermelon
- `cantaloupe`: Fresh cantaloupe
- `honeydew`: Fresh honeydew
- `melon`: Other melons

**Other Fruit**
- `avocado`: Fresh avocados (Hass, etc.)
- `pear`: Fresh pears (Bartlett, Anjou, Bosc, etc.)
- `fig`: Fresh figs

### PRODUCE - VEGETABLES

**Alliums (Onion Family)**
- `onion`: Yellow, white, red, sweet onions, shallots, scallions, green onions, leeks
  - Recipe use: aromatic base, raw in salads, caramelized
  - Color/variety matters for flavor but same role

**Garlic & Ginger**
- `garlic`: Fresh garlic bulbs, cloves (not garlic powder)
- `ginger`: Fresh ginger root (not ground ginger)

**Tomatoes**
- `tomato`: Fresh tomatoes (beefsteak, roma, cherry, grape, heirloom, vine)
- `canned_tomato`: Diced, crushed, whole peeled, fire-roasted canned tomatoes
- `tomato_paste`: Concentrated tomato paste in tubes/cans
- `tomato_sauce`: Plain tomato sauce (not pasta sauce with seasonings)

**Potatoes**
- `potato`: White, yellow, red, russet potatoes (not sweet potatoes)
- `sweet_potato`: Sweet potatoes, yams

**Root Vegetables**
- `carrot`: Fresh carrots (baby, whole, etc.)
- `beet`: Fresh beets
- `radish`: Radishes
- `turnip`: Turnips
- `parsnip`: Parsnips

**Peppers**
- `bell_pepper`: Bell peppers (red, green, yellow, orange)
- `hot_pepper`: Jalapeños, serranos, habaneros, poblanos, chipotles, Thai chilies
  - Recipe distinction: heat level matters

**Leafy Greens**
- `spinach`: Fresh or frozen spinach
- `kale`: Fresh kale (any variety)
- `arugula`: Fresh arugula/rocket
- `lettuce`: Romaine, iceberg, butter lettuce, mixed greens, spring mix, salad greens
- `chard`: Swiss chard
- `collard_greens`: Collard greens
- `mustard_greens`: Mustard greens

**Cruciferous Vegetables**
- `broccoli`: Fresh or frozen broccoli
- `cauliflower`: Fresh or frozen cauliflower
- `brussels_sprouts`: Fresh or frozen Brussels sprouts
- `cabbage`: Green, red, Napa, savoy cabbage, bok choy

**Squash**
- `zucchini`: Zucchini, summer squash, yellow squash
- `butternut_squash`: Butternut squash
- `acorn_squash`: Acorn squash
- `spaghetti_squash`: Spaghetti squash (the vegetable, not pasta)
- `pumpkin`: Fresh pumpkin (not canned puree, not pumpkin spice products)

**Other Vegetables**
- `cucumber`: Cucumbers (English, Persian, pickling, etc.)
- `celery`: Fresh celery
- `corn`: Fresh, frozen, or canned corn kernels (not cornmeal, not corn chips)
- `peas`: Fresh, frozen, or canned peas (green peas, snap peas, snow peas)
- `green_beans`: Fresh or frozen green beans
- `asparagus`: Fresh asparagus
- `mushroom`: Fresh mushrooms (button, cremini, portobello, shiitake, oyster, etc.)
- `eggplant`: Fresh eggplant

**Fresh Herbs**
- `fresh_herbs`: Cilantro, parsley, basil, mint, thyme, rosemary, dill, oregano, sage, chives
  - Recipe use: fresh herbs added to dishes (not dried spices)

### DAIRY

**Milk**
- `milk`: Cow's milk (whole, 2%, 1%, skim, organic, lactose-free)
  - Recipe equivalence: Fat level matters for richness but all are "milk"
- `buttermilk`: Cultured buttermilk (distinct recipe use in baking)
- `evaporated_milk`: Canned evaporated milk
- `condensed_milk`: Sweetened condensed milk

**Plant Milk Alternatives**
- `plant_milk`: Almond milk, soy milk, oat milk, coconut milk (refrigerated), cashew milk, rice milk, hemp milk
  - Recipe use: dairy substitute

**Cream**
- `heavy_cream`: Heavy cream, whipping cream
- `half_and_half`: Half & half
- `sour_cream`: Sour cream, crème fraîche

**Butter & Ghee**
- `butter`: Salted or unsalted butter (not flavored compound butters)
- `ghee`: Clarified butter, ghee

**Yogurt**
- `yogurt`: Plain, flavored, Greek, Icelandic, skyr, kefir (all dairy yogurt)
  - Flavor/style matter for eating but same base in recipes

**Cheese**
- `cheddar`: Cheddar cheese (mild, sharp, extra sharp)
- `mozzarella`: Mozzarella (fresh, low-moisture, part-skim)
- `parmesan`: Parmesan, Parmigiano-Reggiano, Pecorino Romano
- `swiss`: Swiss, Gruyère, Emmental
- `provolone`: Provolone
- `monterey_jack`: Monterey Jack, Pepper Jack
- `american_cheese`: American cheese, cheese slices
- `feta`: Feta cheese
- `goat_cheese`: Chèvre, goat cheese
- `blue_cheese`: Blue cheese, Gorgonzola, Roquefort
- `brie`: Brie, Camembert
- `cream_cheese`: Cream cheese, mascarpone
- `ricotta`: Ricotta cheese
- `cottage_cheese`: Cottage cheese
- `queso_fresco`: Queso fresco, queso blanco
- `cheese_blend`: Shredded cheese blends, Mexican blend, Italian blend
- `string_cheese`: String cheese, cheese sticks

**Eggs**
- `eggs`: Chicken eggs (white, brown, cage-free, free-range, organic)
- `egg_whites`: Liquid egg whites, egg white products
- `egg_substitute`: Egg substitutes, egg beaters

### PROTEIN - MEAT

**Chicken**
- `chicken_breast`: Boneless, skinless chicken breasts
- `chicken_thigh`: Chicken thighs (bone-in or boneless)
- `whole_chicken`: Whole chicken, rotisserie chicken
- `ground_chicken`: Ground chicken
- `chicken_wings`: Chicken wings
- `chicken_tenders`: Chicken tenders, chicken strips

**Beef**
- `ground_beef`: Ground beef (any fat percentage)
- `steak`: Steaks (ribeye, sirloin, T-bone, filet, flank, skirt, etc.)
- `beef_roast`: Beef roasts, chuck roast, pot roast
- `stew_meat`: Beef stew meat, beef cubes
- `brisket`: Beef brisket
- `short_ribs`: Beef short ribs

**Pork**
- `pork_chop`: Pork chops
- `pork_tenderloin`: Pork tenderloin
- `pork_shoulder`: Pork shoulder, pork butt, pulled pork meat
- `ground_pork`: Ground pork
- `ham`: Ham (not deli sliced, whole or spiral ham)
- `ribs`: Pork ribs (baby back, spare ribs)

**Turkey**
- `turkey_breast`: Turkey breast
- `ground_turkey`: Ground turkey
- `whole_turkey`: Whole turkey

**Lamb & Veal**
- `lamb`: Lamb chops, lamb shoulder, ground lamb
- `veal`: Veal cutlets, veal

**Processed Meats**
- `bacon`: Bacon (pork or turkey)
- `sausage`: Fresh sausage (Italian, breakfast, bratwurst, chorizo)
- `hot_dog`: Hot dogs, frankfurters
- `deli_meat`: Sliced deli meats (turkey, ham, roast beef, chicken, salami, pepperoni, prosciutto, pastrami)

### PROTEIN - SEAFOOD

**Fish**
- `salmon`: Fresh or frozen salmon (Atlantic, sockeye, coho, etc.)
- `tuna`: Fresh tuna steaks
- `cod`: Cod, haddock
- `tilapia`: Tilapia
- `mahi_mahi`: Mahi mahi
- `halibut`: Halibut
- `trout`: Trout
- `bass`: Bass (sea bass, striped bass)
- `swordfish`: Swordfish
- `snapper`: Red snapper

**Shellfish**
- `shrimp`: Fresh or frozen shrimp, prawns
- `crab`: Crab (fresh, frozen, imitation crab)
- `lobster`: Lobster
- `scallops`: Sea scallops, bay scallops
- `mussels`: Fresh mussels
- `clams`: Fresh clams
- `oysters`: Fresh oysters

**Canned Fish**
- `canned_tuna`: Canned tuna
- `canned_salmon`: Canned salmon
- `anchovies`: Canned anchovies
- `sardines`: Canned sardines

### PROTEIN - PLANT-BASED

**Soy & Tofu**
- `tofu`: All tofu (silken, soft, firm, extra-firm)
- `tempeh`: Tempeh
- `edamame`: Edamame (fresh or frozen soybeans)

**Beans & Legumes**
- `black_beans`: Black beans (canned or dried)
- `pinto_beans`: Pinto beans
- `kidney_beans`: Kidney beans
- `white_beans`: White beans (cannellini, great northern, navy beans)
- `chickpeas`: Chickpeas, garbanzo beans
- `lentils`: Lentils (green, red, brown)
- `split_peas`: Split peas
- `lima_beans`: Lima beans
- `refried_beans`: Canned refried beans

**Meat Alternatives**
- `plant_based_burger`: Beyond Meat, Impossible Burger, plant-based burger patties
- `plant_based_meat`: Plant-based ground meat, crumbles, nuggets, strips

### GRAINS, PASTA & RICE

**Pasta**
- `pasta`: Spaghetti, penne, rigatoni, fettuccine, linguine, angel hair, rotini, fusilli, farfalle, bow tie, macaroni, orzo, shells
  - Recipe equivalence: Shape matters for sauce adherence but same base ingredient
  - NOT boxed mac and cheese (that's a prepared dish)
- `filled_pasta`: Ravioli, tortellini, tortelloni, stuffed shells
- `lasagna_noodles`: Lasagna noodles
- `egg_noodles`: Egg noodles, wide noodles

**Asian Noodles**
- `ramen_noodles`: Fresh or dried ramen noodles (not instant ramen cups)
- `rice_noodles`: Rice noodles, pad thai noodles, vermicelli
- `udon`: Udon noodles
- `soba`: Soba noodles

**Rice**
- `white_rice`: White rice (long grain, short grain, jasmine, basmati, sushi rice)
- `brown_rice`: Brown rice (long grain, short grain)
- `wild_rice`: Wild rice, wild rice blends
- `arborio_rice`: Arborio rice (risotto rice)
- `instant_rice`: Instant rice, minute rice

**Other Grains**
- `quinoa`: Quinoa (white, red, tri-color)
- `couscous`: Couscous
- `bulgur`: Bulgur wheat
- `farro`: Farro
- `barley`: Barley (pearl, hulled)
- `polenta`: Polenta, corn grits
- `oats`: Oats (rolled, steel-cut, old-fashioned; not instant oatmeal packets)

### BREAD & BAKERY

**Bread**
- `white_bread`: White bread, sandwich bread
- `wheat_bread`: Whole wheat bread, whole grain bread, multigrain bread
- `sourdough`: Sourdough bread
- `rye_bread`: Rye bread
- `baguette`: Baguettes, French bread
- `ciabatta`: Ciabatta
- `focaccia`: Focaccia

**Flatbreads**
- `tortilla`: Flour tortillas, corn tortillas, whole wheat tortillas
- `pita`: Pita bread
- `naan`: Naan bread
- `flatbread`: Flatbreads, lavash

**Buns & Rolls**
- `hamburger_bun`: Hamburger buns, burger buns
- `hot_dog_bun`: Hot dog buns
- `dinner_roll`: Dinner rolls, potato rolls
- `bagel`: Bagels (plain, everything, sesame, etc.)
- `english_muffin`: English muffins

**Baked Goods**
- `croissant`: Croissants
- `muffin`: Muffins (blueberry, corn, etc.)
- `biscuit`: Biscuits
- `cornbread`: Cornbread

### OILS, FATS & VINEGARS

**Oils**
- `olive_oil`: Olive oil, extra virgin olive oil
- `vegetable_oil`: Vegetable oil, canola oil, corn oil
- `coconut_oil`: Coconut oil
- `avocado_oil`: Avocado oil
- `sesame_oil`: Sesame oil (toasted or plain)
- `peanut_oil`: Peanut oil
- `grapeseed_oil`: Grapeseed oil
- `sunflower_oil`: Sunflower oil
- `cooking_spray`: Cooking spray (all types)

**Vinegars**
- `white_vinegar`: White vinegar, distilled vinegar
- `apple_cider_vinegar`: Apple cider vinegar
- `balsamic_vinegar`: Balsamic vinegar
- `red_wine_vinegar`: Red wine vinegar
- `white_wine_vinegar`: White wine vinegar
- `rice_vinegar`: Rice vinegar

### CONDIMENTS & SAUCES

**Basic Condiments**
- `ketchup`: Ketchup
- `mustard`: Yellow mustard, Dijon mustard, whole grain mustard, spicy mustard
- `mayonnaise`: Mayonnaise, mayo, aioli
- `hot_sauce`: Hot sauce, Sriracha, Tabasco, buffalo sauce, chili sauce
- `bbq_sauce`: BBQ sauce, barbecue sauce

**Asian Sauces**
- `soy_sauce`: Soy sauce, tamari
- `teriyaki_sauce`: Teriyaki sauce
- `hoisin_sauce`: Hoisin sauce
- `oyster_sauce`: Oyster sauce
- `fish_sauce`: Fish sauce
- `sesame_sauce`: Sesame sauce

**Other Sauces**
- `worcestershire`: Worcestershire sauce
- `liquid_smoke`: Liquid smoke

**Salsa & Mexican**
- `salsa`: Salsa (all heat levels and styles)
- `pico_de_gallo`: Fresh pico de gallo
- `guacamole`: Guacamole
- `queso`: Queso dip

**Dips & Spreads**
- `hummus`: Hummus (all flavors - chickpea is the base)
- `salad_dressing`: Salad dressings (ranch, Italian, Caesar, blue cheese, vinaigrettes, etc.)

**Pasta Sauces**
- `marinara`: Marinara sauce, pasta sauce, spaghetti sauce
- `alfredo_sauce`: Alfredo sauce
- `pesto`: Pesto sauce
- `vodka_sauce`: Vodka sauce

**Specialty Sauces**
- `curry_paste`: Curry paste (Thai red, green, yellow, etc.)
- `miso_paste`: Miso paste
- `tahini`: Tahini
- `gochujang`: Gochujang

### SPICES & SEASONINGS

**Salt & Pepper**
- `salt`: Salt (table salt, sea salt, kosher salt, Himalayan salt)
- `black_pepper`: Black pepper (ground or peppercorns)

**Common Spices**
- `garlic_powder`: Garlic powder
- `onion_powder`: Onion powder
- `paprika`: Paprika, smoked paprika
- `cumin`: Cumin (ground or seeds)
- `chili_powder`: Chili powder
- `cayenne`: Cayenne pepper
- `red_pepper_flakes`: Red pepper flakes, crushed red pepper
- `oregano`: Dried oregano
- `basil`: Dried basil
- `thyme`: Dried thyme
- `rosemary`: Dried rosemary
- `bay_leaves`: Bay leaves
- `cinnamon`: Cinnamon (ground or sticks)
- `nutmeg`: Nutmeg
- `ginger_powder`: Ground ginger
- `turmeric`: Turmeric
- `coriander`: Coriander (ground or seeds)
- `cloves`: Cloves
- `allspice`: Allspice
- `cardamom`: Cardamom

**Spice Blends**
- `italian_seasoning`: Italian seasoning
- `taco_seasoning`: Taco seasoning
- `cajun_seasoning`: Cajun seasoning, creole seasoning
- `curry_powder`: Curry powder
- `garam_masala`: Garam masala
- `everything_bagel_seasoning`: Everything bagel seasoning

### BAKING

**Flours**
- `all_purpose_flour`: All-purpose flour
- `bread_flour`: Bread flour
- `whole_wheat_flour`: Whole wheat flour
- `cake_flour`: Cake flour
- `self_rising_flour`: Self-rising flour
- `almond_flour`: Almond flour
- `coconut_flour`: Coconut flour

**Sugars**
- `white_sugar`: White sugar, granulated sugar
- `brown_sugar`: Brown sugar (light or dark)
- `powdered_sugar`: Powdered sugar, confectioners' sugar
- `raw_sugar`: Raw sugar, turbinado, demerara

**Sweeteners**
- `honey`: Honey
- `maple_syrup`: Maple syrup
- `agave`: Agave nectar, agave syrup
- `molasses`: Molasses
- `corn_syrup`: Corn syrup

**Leavening & Thickeners**
- `baking_powder`: Baking powder
- `baking_soda`: Baking soda
- `yeast`: Yeast (active dry, instant, rapid rise)
- `cornstarch`: Cornstarch

**Chocolate & Cocoa**
- `chocolate_chips`: Chocolate chips (semi-sweet, milk, dark, white)
- `baking_chocolate`: Baking chocolate bars, unsweetened chocolate
- `cocoa_powder`: Cocoa powder (natural or Dutch-processed)

**Extracts**
- `vanilla_extract`: Vanilla extract
- `almond_extract`: Almond extract

**Other Baking**
- `cornmeal`: Cornmeal

### COOKING LIQUIDS

**Broths & Stocks**
- `chicken_broth`: Chicken broth, chicken stock
- `beef_broth`: Beef broth, beef stock
- `vegetable_broth`: Vegetable broth, vegetable stock
- `bone_broth`: Bone broth

**Wine & Beer for Cooking**
- `red_wine`: Red wine (for cooking)
- `white_wine`: White wine (for cooking)
- `beer`: Beer (for cooking)

### SPREADS & JAMS

**Nut Butters**
- `peanut_butter`: Peanut butter (creamy, crunchy, natural)
- `almond_butter`: Almond butter
- `cashew_butter`: Cashew butter
- `sunflower_butter`: Sunflower seed butter

**Jams & Jellies**
- `strawberry_jam`: Strawberry jam, preserves
- `grape_jelly`: Grape jelly
- `raspberry_jam`: Raspberry jam, preserves
- `jam_other`: Other jams (apricot, blueberry, blackberry, etc.)
- `marmalade`: Marmalade

**Other Spreads**
- `applesauce`: Applesauce
- `apple_butter`: Apple butter

### BEVERAGES

**Water**
- `water`: Bottled water, spring water, sparkling water, seltzer, club soda, tonic water

**Soft Drinks**
- `soda`: Soda, cola, Coke, Pepsi, root beer, ginger ale, lemon-lime soda, Dr Pepper, etc.

**Juices**
- `orange_juice`: Orange juice
- `apple_juice`: Apple juice
- `cranberry_juice`: Cranberry juice
- `grape_juice`: Grape juice
- `lemonade`: Lemonade
- `juice_blend`: Juice blends, juice cocktails

**Coffee & Tea**
- `coffee`: Ground coffee, whole bean coffee, instant coffee
- `cold_brew`: Cold brew coffee (bottled)
- `tea`: Tea bags, loose leaf tea (black, green, herbal, chai, etc.)
- `matcha`: Matcha powder

**Other Beverages**
- `kombucha`: Kombucha
- `energy_drink`: Energy drinks
- `sports_drink`: Sports drinks (Gatorade, Powerade, etc.)
- `coconut_water`: Coconut water

**Alcohol**
- `beer`: Beer, ale, lager, IPA
- `wine`: Wine (red, white, rosé)
- `champagne`: Champagne, prosecco, sparkling wine

### NUTS & SEEDS

**Nuts**
- `almonds`: Almonds (whole, sliced, slivered)
- `walnuts`: Walnuts
- `pecans`: Pecans
- `cashews`: Cashews
- `pistachios`: Pistachios
- `peanuts`: Peanuts
- `hazelnuts`: Hazelnuts
- `macadamia_nuts`: Macadamia nuts
- `pine_nuts`: Pine nuts
- `mixed_nuts`: Mixed nuts

**Seeds**
- `sunflower_seeds`: Sunflower seeds
- `pumpkin_seeds`: Pumpkin seeds, pepitas
- `chia_seeds`: Chia seeds
- `flax_seeds`: Flax seeds, flaxseed
- `sesame_seeds`: Sesame seeds
- `poppy_seeds`: Poppy seeds

### SNACKS

**Chips & Crisps**
- `potato_chips`: Potato chips
- `tortilla_chips`: Tortilla chips
- `pita_chips`: Pita chips
- `veggie_chips`: Veggie chips, root vegetable chips

**Crackers**
- `crackers`: Crackers (saltines, Ritz, wheat, rice crackers, etc.)
- `graham_crackers`: Graham crackers

**Other Snacks**
- `pretzels`: Pretzels
- `popcorn`: Popcorn (popped or kernels)
- `rice_cakes`: Rice cakes
- `trail_mix`: Trail mix
- `granola_bar`: Granola bars, protein bars, energy bars, cereal bars
- `cookies`: Cookies (chocolate chip, sandwich cookies, etc.)
- `candy`: Candy, chocolate bars, gummies, hard candy
- `jerky`: Beef jerky, turkey jerky, meat jerky
- `fruit_snacks`: Fruit snacks, fruit leather
- `gum`: Chewing gum

### BREAKFAST

**Cereal & Granola**
- `cereal`: Breakfast cereal (corn flakes, Cheerios, etc.)
- `granola`: Granola
- `oatmeal`: Instant oatmeal packets

**Breakfast Products**
- `pancake_syrup`: Pancake syrup
- `pancake_mix`: Pancake mix
- `waffle_mix`: Waffle mix

### FROZEN FOODS

**Frozen Vegetables**
- `frozen_vegetables`: Frozen vegetables (broccoli, peas, corn, green beans, spinach, mixed vegetables)

**Frozen Fruit**
- `frozen_fruit`: Frozen fruit (berries, mango, pineapple, etc.)

**Frozen Breakfast**
- `frozen_waffles`: Frozen waffles
- `frozen_pancakes`: Frozen pancakes
- `french_toast`: Frozen French toast

**Frozen Potatoes**
- `hash_browns`: Hash browns, tater tots, frozen fries

**Ice Cream & Frozen Desserts**
- `ice_cream`: Ice cream, gelato
- `frozen_yogurt`: Frozen yogurt
- `sorbet`: Sorbet, sherbet
- `popsicles`: Popsicles, ice pops, ice cream bars

### PREPARED DISHES & MEALS

These are complete dishes, not base ingredients.

**Frozen Meals**
- `frozen_meal`: Frozen dinners, TV dinners, frozen entrées (Lean Cuisine, Stouffer's, etc.)
- `frozen_pizza`: Frozen pizza
- `frozen_burrito`: Frozen burritos
- `frozen_lasagna`: Frozen lasagna
- `pot_pie`: Frozen pot pies
- `hot_pocket`: Hot Pockets, frozen sandwiches

**Frozen Appetizers**
- `chicken_nuggets`: Chicken nuggets, chicken tenders
- `mozzarella_sticks`: Mozzarella sticks
- `corn_dogs`: Corn dogs
- `frozen_appetizer`: Other frozen appetizers (egg rolls, dumplings, etc.)

**Boxed/Packaged Meals**
- `mac_and_cheese`: Boxed mac and cheese
- `meal_kit`: Meal kits, dinner kits (Hamburger Helper, etc.)

**Soup**
- `soup`: Canned soup, condensed soup, ready-to-eat soup
- `instant_soup`: Instant soup cups

**Instant Noodles**
- `instant_ramen`: Instant ramen, cup noodles, instant noodle soups

**Chili**
- `canned_chili`: Canned chili

**Deli Prepared**
- `deli_prepared`: Prepared deli foods (salads, sandwiches, wraps, etc.)

### BABY PRODUCTS

**Baby Food**
- `baby_formula`: Baby formula, infant formula
- `baby_cereal`: Baby cereal
- `baby_food`: Baby food pouches, jars

**Baby Care**
- `diapers`: Diapers
- `baby_wipes`: Baby wipes

### PET PRODUCTS

**Pet Food**
- `dog_food`: Dog food, dog treats
- `cat_food`: Cat food, cat treats
- `pet_supplies`: Other pet supplies

### HOUSEHOLD (NON-FOOD)

**Paper Goods**
- `paper_towels`: Paper towels
- `toilet_paper`: Toilet paper, bath tissue
- `tissues`: Tissues, facial tissues
- `napkins`: Paper napkins

**Cleaning Supplies**
- `dish_soap`: Dish soap, dish detergent
- `laundry_detergent`: Laundry detergent
- `all_purpose_cleaner`: All-purpose cleaner
- `bleach`: Bleach
- `cleaning_supplies`: Other cleaning supplies

**Food Storage**
- `trash_bags`: Trash bags, garbage bags
- `food_storage_bags`: Food storage bags, Ziploc bags
- `plastic_wrap`: Plastic wrap, cling wrap
- `aluminum_foil`: Aluminum foil
- `food_containers`: Food storage containers

**Other Household**
- `air_freshener`: Air fresheners
- `candles`: Candles

### PERSONAL CARE (NON-FOOD)

**Oral Care**
- `toothpaste`: Toothpaste
- `toothbrush`: Toothbrushes
- `mouthwash`: Mouthwash
- `dental_floss`: Dental floss

**Body Care**
- `shampoo`: Shampoo
- `conditioner`: Conditioner
- `body_wash`: Body wash, bar soap
- `hand_soap`: Hand soap
- `lotion`: Body lotion, hand lotion
- `sunscreen`: Sunscreen

**Hygiene**
- `deodorant`: Deodorant, antiperspirant
- `feminine_care`: Tampons, pads, liners

**Health**
- `vitamins`: Vitamins, supplements
- `pain_reliever`: Pain relievers, cold medicine, allergy medicine

**Other Personal Care**
- `shaving_cream`: Shaving cream, razors
- `hair_care`: Hair styling products

## Usage Notes

- When a product contains multiple ingredients but is sold as one item (e.g., "Tomato Basil Pasta"), classify by the primary ingredient (pasta)
- Prepared frozen meals with multiple components → classify as prepared_dish type (frozen_meal, frozen_pizza, etc.)
- Fresh vs. frozen vs. canned: Sometimes the same ingredient (e.g., tomato vs canned_tomato), sometimes separate if recipe use differs
- "Diet", "Low Fat", "Sugar Free", "Gluten Free" → attributes, not different ingredients
- Organic → attribute, not different ingredient
