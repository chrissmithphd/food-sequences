#!/usr/bin/env python3
"""
LLM-assisted product classification — reviewed pilot (v3.0).

The classifier is an LLM (model_id below) reasoning per the prompt in
analysis/food_classification/prompt_v3.md: identify what the product IS, then assign
a recipe-equivalence group from the shared catalog. These pilot outputs were produced
by that model and are cached here verbatim; this script serializes them to a versioned
cache + a human-review sheet and runs supporting checks (regex is used only to flag
possible contradictions, never to assign groups).

Scope: contrasting aisles containing known hard cases. NOT catalog-wide. Downstream
recipe/novelty analysis must wait until the mapping is validated as reliable.
"""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from food_sequences.config import DATA_PROCESSED

MODEL_ID = "us.anthropic.claude-opus-4-8"
PROMPT_VERSION = "v3.0"
CDIR = Path(__file__).parent.parent / "analysis" / "food_classification"

# product_id -> (product_type, base_food, prep_state, named_ingredient_role,
#                recipe_group, status, confidence, reason)
DECISIONS = {
    3738:  ("skin/body care","calendula balm","non-food","product","OUT_OF_SCOPE_personal_care","out_of_scope","high","baby diaper care, not food"),
    18441: ("condiment","ketchup","shelf-stable","product","ketchup","resolved","high","tomato ketchup condiment"),
    7751:  ("condiment","ketchup","shelf-stable","product","ketchup","resolved","high","'tomato' describes base; product is ketchup"),
    35898: ("condiment","hot sauce","shelf-stable","product","hot_sauce","resolved","high","chili hot sauce"),
    44628: ("condiment","mustard","shelf-stable","product","mustard","resolved","high","dijon mustard"),
    27796: ("condiment","mayonnaise","shelf-stable","product","mayonnaise","resolved","high","mayonnaise"),
    40821: ("condiment","mayonnaise","shelf-stable","ingredient: olive oil (minor)","mayonnaise","resolved","high","product is mayonnaise; olive oil is an ingredient, not the product"),
    39561: ("snack crackers","crackers","shelf-stable","flavor: cheddar","crackers","resolved","high","cheddar is a flavor; product is crackers"),
    34262: ("snack crackers","crackers","shelf-stable","base: almond/nut","crackers","resolved","medium","nut-based crackers (nut thins)"),
    22474: ("snack crackers","crackers","shelf-stable","flavor: cheddar","crackers","resolved","high","cheddar flavor; crackers"),
    2091:  ("snack crackers","crackers","shelf-stable","base: almond/rice","crackers","resolved","medium","nut & rice crackers"),
    24810: ("snack","rice cakes","shelf-stable","product","rice_cakes","resolved","high","puffed brown rice cakes"),
    40268: ("snack crackers","crackers","shelf-stable","product (gluten-free attr)","crackers","resolved","high","gluten-free crackers"),
    17471: ("pet food","dog biscuits","non-food","product","OUT_OF_SCOPE_pet_food","out_of_scope","high","dog biscuits"),
    722:   ("pet food","dog treats","non-food","flavor: chicken & rice","OUT_OF_SCOPE_pet_food","out_of_scope","high","dog treats; chicken is flavor"),
    23329: ("pet food","dog food","non-food","content: chicken & rice","OUT_OF_SCOPE_pet_food","out_of_scope","medium","name alone ambiguous; aisle=dog food care indicates pet food"),
    24115: ("pet food","dog treats","non-food","flavor: beef","OUT_OF_SCOPE_pet_food","out_of_scope","high","beef jerky dog treat"),
    39719: ("filled pasta","tortellini","fresh","filling: ricotta/parmesan/romano","filled_pasta","resolved","high","cheese is the filling; product is filled pasta"),
    4193:  ("filled pasta","ravioli","fresh","filling: spinach & cheese","filled_pasta","resolved","high","filled pasta; filling not loose cheese"),
    2124:  ("filled pasta","ravioli","fresh","filling: cheese","filled_pasta","resolved","high","cheese ravioli = filled pasta"),
    165:   ("filled pasta","ravioli","fresh","filling: mushroom","filled_pasta","resolved","high","mushroom is the filling"),
    31865: ("filled pasta","ravioli","fresh","filling: cheese","filled_pasta","resolved","high","four cheese ravioli = filled pasta"),
    43659: ("pasta","pasta","dry","product (shape linguine, gluten-free)","pasta","resolved","high","plain pasta; not filled"),
    22935: ("fresh vegetable","onion","raw","product","onion","resolved","high","yellow onion"),
    24964: ("fresh vegetable","garlic","raw","product","garlic","resolved","high","garlic bulb"),
    45007: ("fresh vegetable","zucchini","raw","product","zucchini","resolved","high","zucchini (summer squash)"),
    49683: ("fresh vegetable","cucumber","raw","product","cucumber","resolved","high","kirby cucumber"),
    30391: ("fresh vegetable","cucumber","raw","product","cucumber","resolved","high","cucumber"),
    4605:  ("fresh vegetable","onion","raw","product","onion","resolved","high","yellow onions"),
    17794: ("fresh vegetable","carrot","raw","product","carrot","resolved","high","carrots"),
    27104: ("fresh vegetable","cauliflower","raw","product","cauliflower","resolved","high","cauliflower"),
    21295: ("fresh vegetable","winter squash","raw","product","winter_squash","resolved","high","spaghetti squash is a vegetable, NOT pasta"),
    38996: ("fresh vegetable","tomato","raw","variety: grape","tomato_fresh","resolved","high","'grape' is the tomato variety, not grapes"),
    5099:  ("snack crackers","crackers","shelf-stable","flavor: onion & garlic; base: black bean","crackers","resolved","high","product is crackers; garlic/onion are flavors (aisle mis-filed as vegetables)"),
    42110: ("mac & cheese kit","boxed mac and cheese","kit","product","boxed_mac_and_cheese","resolved","high","macaroni + cheese kit"),
    35004: ("mac & cheese kit","boxed mac and cheese","kit","product","boxed_mac_and_cheese","resolved","high","shells & cheddar kit"),
    36772: ("mac & cheese kit","boxed mac and cheese","kit","product","boxed_mac_and_cheese","resolved","high","mac & cheese kit"),
    1090:  ("mac & cheese kit","boxed mac and cheese","kit","product","boxed_mac_and_cheese","resolved","high","shells & cheddar mac & cheese"),
    33636: ("mac & cheese kit","boxed mac and cheese","kit","product","boxed_mac_and_cheese","resolved","high","shells & white cheddar kit"),
    18599: ("grain side","couscous","shelf-stable","flavor: garlic","couscous","resolved","high","couscous; garlic is a flavor"),
    27845: ("dairy milk","milk","liquid","product (whole)","milk","resolved","high","cow milk; fat is attribute"),
    5785:  ("dairy milk","milk","liquid","product (2%)","milk","resolved","high","cow milk; fat is attribute"),
    23909: ("dairy milk","milk","liquid","product (2%)","milk","resolved","high","cow milk; fat is attribute"),
    4210:  ("dairy milk","milk","liquid","product (whole)","milk","resolved","high","cow milk; fat is attribute"),
    38689: ("dairy milk","milk","liquid","product (reduced fat)","milk","resolved","high","cow milk; fat is attribute"),
    19348: ("dairy milk","milk","liquid","product (fat free)","milk","resolved","high","cow milk; fat is attribute"),
    31506: ("oil","olive oil","shelf-stable","product","olive_oil","resolved","high","extra virgin olive oil"),
    21195: ("oil","olive oil","shelf-stable","product","olive_oil","resolved","high","organic EVOO"),
    10644: ("oil","olive oil","shelf-stable","product","olive_oil","resolved","high","italian EVOO"),
    48697: ("oil","canola oil","shelf-stable","product","cooking_oil","resolved","high","neutral cooking oil"),
    18963: ("condiment","vinegar","shelf-stable","product","vinegar","resolved","high","apple cider vinegar"),
    21903: ("fresh vegetable","spinach","raw","product","leafy_green","resolved","high","baby spinach"),
    27966: ("fruit","raspberries","raw","product","raspberries","resolved","high","raspberries"),
    39275: ("fruit","blueberries","raw","product","blueberries","resolved","high","blueberries"),
    40706: ("fresh vegetable","tomato","raw","variety: grape","tomato_fresh","resolved","high","grape tomato is a tomato, not grapes"),
    4920:  ("fruit","grapes","raw","product","grapes","resolved","high","table grapes (contrast with grape tomato)"),
    42265: ("fresh vegetable","carrot","raw","product","carrot","resolved","high","baby carrots"),
    37927: ("prepared snack","corn dog","prepared-dish","content: chicken","corn_dog","resolved","medium","human corn dog (NOT pet food despite 'dog')"),
    26475: ("skin/body care","facial towelettes","non-food","product","OUT_OF_SCOPE_personal_care","out_of_scope","high","facial cleansing wipes"),
    26367: ("skin/body care","toner","non-food","product","OUT_OF_SCOPE_personal_care","out_of_scope","high","witch hazel toner"),
    42052: ("personal care","hand sanitizer","non-food","product","OUT_OF_SCOPE_personal_care","out_of_scope","high","hand sanitizer"),
    16082: ("skin/body care","facial scrub","non-food","product","OUT_OF_SCOPE_personal_care","out_of_scope","high","facial scrub"),
    45535: ("cooking liquid","chicken broth","shelf-stable","product","cooking_stock_broth","resolved","high","chicken broth"),
    46720: ("cooking liquid","chicken broth","shelf-stable","product","cooking_stock_broth","resolved","high","chicken broth"),
    9092:  ("cooking liquid","vegetable broth","shelf-stable","product","cooking_stock_broth","resolved","high","vegetable broth"),
    1999:  ("cooking liquid","chicken broth","shelf-stable","product","cooking_stock_broth","resolved","high","chicken broth"),
    5769:  ("cooking liquid","chicken stock","shelf-stable","product","cooking_stock_broth","resolved","high","stock ~ broth in role"),
    18479: ("cooking liquid","vegetable broth","shelf-stable","product","cooking_stock_broth","resolved","high","vegetable broth"),
    7515:  ("filled pasta","ravioli","fresh","filling: spinach & ricotta","filled_pasta","resolved","high","product is filled pasta; ricotta is filling (aisle 'specialty cheeses' misleads)"),
}

FIELDS = ["product_type","base_food","prep_state","named_ingredient_role",
          "recipe_group","status","confidence","reason"]


def main():
    catalog = json.loads((CDIR / "group_catalog_v3.json").read_text())
    groups = catalog["groups"]
    products = pd.read_parquet(DATA_PROCESSED / "products.parquet")
    aisles = pd.read_parquet(DATA_PROCESSED / "aisles.parquet")
    depts = pd.read_parquet(DATA_PROCESSED / "departments.parquet")
    pm = products.merge(aisles, on="aisle_id").merge(depts, on="department_id")
    prior = pl.read_parquet(DATA_PROCESSED / "order_products_prior.parquet").select(["product_id"])
    train = pl.read_parquet(DATA_PROCESSED / "order_products_train.parquet").select(["product_id"])
    vol = pl.concat([prior, train]).group_by("product_id").len().rename({"len": "n"}).to_pandas()
    pm = pm.merge(vol, on="product_id", how="left").fillna({"n": 0})
    pm["n"] = pm["n"].astype(int)
    meta = pm.set_index("product_id")

    records, contradictions = [], []
    for pid, dec in DECISIONS.items():
        d = dict(zip(FIELDS, dec))
        grp = d["recipe_group"]
        in_catalog = grp in groups
        if not in_catalog and d["status"] == "resolved":
            d["status"] = "proposed_group"
            contradictions.append((pid, f"group '{grp}' not in catalog"))
        role_family = groups.get(grp, {}).get("role_family")
        m = meta.loc[pid]
        records.append({
            "product_id": int(pid), "name": m["product_name"], "aisle": m["aisle"],
            "department": m["department"], "purchase_count": int(m["n"]),
            "role_family": role_family, **d,
            "model_id": MODEL_ID, "prompt_version": PROMPT_VERSION, "labeled_on": str(date.today()),
        })

    df = pd.DataFrame(records).sort_values("purchase_count", ascending=False)

    # Supporting regex check (NOT a classifier): flag group vs name-word mismatches to review
    import re
    for _, r in df.iterrows():
        nm = r["name"].lower()
        if r["recipe_group"] == "tomato_fresh" and "grape" in nm and "tomato" in nm:
            pass  # correctly handled
        if re.search(r"\bdog\b", nm) and r["role_family"] != "non_food" and "corn dog" not in nm:
            contradictions.append((r["product_id"], "name has 'dog' but not out_of_scope — check"))

    CDIR.mkdir(parents=True, exist_ok=True)
    with open(CDIR / "classifications_v3.jsonl", "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    # Human-review sheet: top-10 by volume (high-impact) + random sample of the rest
    df = df.reset_index(drop=True)
    high = df.head(10).copy(); high["review_bucket"] = "high_volume"
    rest = df.iloc[10:].sample(n=min(15, len(df) - 10), random_state=0).copy()
    rest["review_bucket"] = "random"
    review = pd.concat([high, rest])
    review["human_correct"] = ""  # reviewer fills: y / n / partial
    review[["review_bucket","product_id","name","aisle","product_type","base_food",
            "recipe_group","role_family","status","confidence","reason","human_correct"]]\
        .to_csv(CDIR / "review_sheet_v3.csv", index=False)

    # Report: coverage vs accuracy (accuracy pending human review)
    n = len(df)
    print(f"Pilot classified: {n} products  (model={MODEL_ID}, prompt={PROMPT_VERSION})")
    print(f"  status: " + ", ".join(f"{k}={v}" for k, v in df['status'].value_counts().items()))
    print(f"  in-scope resolved: {(df['status']=='resolved').sum()}; out_of_scope: {(df['status']=='out_of_scope').sum()}")
    conf = df[df.status=='resolved']['confidence'].value_counts()
    print(f"  confidence (resolved): " + ", ".join(f"{k}={v}" for k,v in conf.items()))
    print(f"  distinct recipe groups used: {df['recipe_group'].nunique()}")
    print(f"\n  COVERAGE is reported here; ACCURACY is pending human review of review_sheet_v3.csv")
    print(f"  (self-reported confidence is NOT evidence of correctness)")

    print("\n--- cited error cases: regex-first result -> v3 LLM result ---")
    cite = {38996:"grape tomato", 7515:"spinach ricotta ravioli", 5099:"garlic crackers",
            40821:"mayo w/ olive oil", 21295:"spaghetti squash", 37927:"chicken corn dog", 3738:"calendula"}
    for pid, lbl in cite.items():
        row = df[df.product_id==pid].iloc[0]
        print(f"  {lbl:22s} -> {row['recipe_group']}  ({row['status']}, {row['product_type']})")

    if contradictions:
        print("\n--- flags to review ---")
        for pid, msg in contradictions:
            print(f"  [{pid}] {msg}")

    print(f"\n✓ wrote classifications_v3.jsonl + review_sheet_v3.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
