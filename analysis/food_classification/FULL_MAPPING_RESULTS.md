# Full-Catalog Classification (v4) — Results and Honest Accuracy

All **49,688** products are classified and frozen in
[`analysis/outputs/food_mapping_v4.csv`](../outputs/food_mapping_v4.csv). This was done
with a **code reproduction** of the LLM pilot judgment (`src/food_sequences/food_classifier.py`)
so the result is replicable. It is *not* per-item LLM labeling of all 49k.

## Coverage (every product has a status)
- resolved in-scope: **87.5% of purchase volume** (30,530 products, 117 clusters)
- out_of_scope (pet food / personal care / household, by department+aisle): 4.1%
- unresolved (left unlabeled, not force-fit): 8.4%

## Fidelity vs the LLM pilot — and why it overstates accuracy
Against the 69 v3 pilot gold labels, v4 agrees **68/69 (99%)** (the one difference is
`cauliflower` vs a `broccoli_cauliflower` merge). **But the pilot set was clean**, so 99%
is an optimistic ceiling, not the real accuracy.

## Honest accuracy on a random sample (n=40, reviewer-scored)
Scoring a *random* 40-product sample by hand gives roughly **~80% correct (≈32/40)** —
materially below the 99% pilot agreement. The gap is the whole point: word/rule logic
cannot do semantics on the messy tail. Residual error classes observed:

| error class | example | v4 (wrong) | should be |
|---|---|---|---|
| dish treated as ingredient | Chicken Quesadillas | chicken | prepared dish |
| dish treated as ingredient | Lasagna, Vegetable, with Daiya Cheeze | pasta | prepared dish |
| dip/sauce treated as flavor | Cucumber & Garlic Tzatziki | garlic | yogurt dip/sauce |
| flavor treated as product | Coffee Creamer White Chocolate Raspberry | raspberries | coffee creamer |
| flavor treated as product | Mini Carrot Cupcakes | carrot | cupcakes/bakery |
| brand trap | Chips Ahoy! (cookies) | candy_chocolate | cookies |
| coverage miss | Tapioca Pudding; Veggie Burgers | unresolved | pudding; meat-alt |

Systematic high-volume versions of these (chocolate/baking chips mis-read as snack
chips, "milk chocolate" as milk) were fixed; the remaining errors are genuinely
semantic (is the named food the product, a flavor, a filling, or a finished dish?).

## What this means
- **Coverage ≠ accuracy, and self-reported "resolved/high confidence" ≠ correct.** The
  classifier is most reliable on the simple high-volume head (produce, milk, broth,
  plain pasta) and least reliable on prepared dishes, flavored products, and brand names.
- **Closing the gap requires genuine per-item LLM labeling**, which is not feasible
  inline for 49k in one pass. The pilot workflow (`classify_pilot.py`) is the mechanism;
  it would need to be run in batches against an LLM to replace the rule reproduction on
  the ambiguous tail.

## Gate (unchanged)
Do **not** run downstream recipe/novelty analysis on the full v4 mapping yet: the
long-tail error rate (~20% on a random sample) would propagate. Options: (a) restrict
downstream to high-confidence head clusters, or (b) LLM-label the ambiguous/prepared
tail in batches first. v1/v2/v3-pilot are superseded; v4 is the current full mapping
with the reliability caveats above.
