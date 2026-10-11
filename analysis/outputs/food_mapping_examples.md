# Food-Equivalence Mapping v1 — Examples for Review

Three levels: SKU (product) → equivalent food (`subgroup`) → family. Brand and minor form are ignored at the subgroup level; attributes (organic, dietary, flavor, physical form, prepared-vs-ingredient) are preserved.

## Brand-equivalence: different SKUs, same equivalent food

**pasta / spaghetti** — these distinct products map to one equivalent food:

- Organic Spaghetti Style Pasta
- Multigrain Spaghetti Style Pasta
- Organic Gluten Free Quinoa Spaghetti
- Green Lentil Spaghetti Pasta
- Spaghetti Rigati Pasta

**milk / whole** — these distinct products map to one equivalent food:

- Organic Whole Grassmilk Milk
- Ultra-Filtered Whole Milk
- Milk Whole
- Whole Milk
- Organic Whole Chocolate Milk

**eggs / large** — these distinct products map to one equivalent food:

- Organic Large Grade A Eggs
- Free Range Organic Brown Large Egg
- Large Brown Grade AA Eggs
- Large Pasteurized Eggs
- Large AA Eggs

## Meaningful distinctions retained (same family, different subgroup/attribute)

Shape kept as subgroup within the pasta family:

- `spaghetti`: Organic Spaghetti Style Pasta
- `penne`: Penne Rigate With Spinach
- `macaroni`: Organic Whole Wheat Elbows
- `lasagna_sheet`: Dry Pasta Lasagne

Dietary distinction kept as attribute (same subgroup, flagged):

- Gluten Free Pasta Penne Rigate  (gluten_free=true)
- Organic Gluten Free Quinoa Spaghetti  (gluten_free=true)
- Gluten Free Penne Rigate  (gluten_free=true)
- Elbows Gluten Free Pasta  (gluten_free=true)

## Hard cases / boundaries (left separate or flagged)

**Ingredient vs. finished dish — excluded_prepared (NOT mapped as the ingredient):**

- [pasta] Deluxe Macaroni & Cheese Dinner — name indicates a prepared dish, not an ingredient pasta
- [pasta] Organic Macaroni & Cheese Alphabet Dinner — name indicates a prepared dish, not an ingredient pasta
- [eggs] Mediterranean Scramble — prepared egg dish, not the egg ingredient

**Filled pasta (ravioli/tortellini) — distinct subgroup, medium confidence:**

- Wild Chanterelle Mushroom Ravioli
- Three Cheese Ravioli
- Cheese Ravioli
- Ravioli, Five Cheese, Value Pack
- Porcini Mushroom And Truffle Triangles

**Ambiguous — left UNRESOLVED (no forced match):**

- [pasta] Zita Cut, No. 118 — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Organic 100% Whole Wheat Chiocciole — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Casareccia — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Tubetti Rigati No 72 Pasta — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Mostaccioli Pasta — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Tofette — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Veggie Bows Pasta — pasta aisle but no recognized shape keyword — left unresolved
- [pasta] Wagon Wheels Dry Pasta — pasta aisle but no recognized shape keyword — left unresolved