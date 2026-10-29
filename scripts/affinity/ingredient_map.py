#!/usr/bin/env python3
"""Map external recipe-ingredient strings onto the project's 543-ingredient taxonomy.

External recipe corpora (What's Cooking, Food.com) list ingredients as free text
("ground cumin", "extra-virgin olive oil", "garlic cloves"). To compute affinity
statistics in the *same* vocabulary the grocery pipeline uses, every such string is
normalized to one of the existing slugs defined in `data/INGREDIENT_TAXONOMY.md`.

We reuse the existing taxonomy rather than inventing a competing one. The taxonomy's
own synonym lists (the text after each "- `slug`: ..." line) are the primary evidence; a
small curated override table (`data/affinity/ingredient_overrides.csv`) covers common
recipe terms the taxonomy doesn't spell out. Nothing is force-matched: unresolved
strings are reported, not guessed.

Deliberate consequence of the existing abstraction: lumped slugs absorb their members
by design — "cilantro", "basil", "mint" all normalize to `fresh_herbs`; "chipotle",
"poblano" to `hot_pepper`. That lost granularity is a measured detectability limit for
the affinity work, documented in the report, not patched here.

Usage:
    uv run python -I scripts/affinity/ingredient_map.py coverage \
        whats_cooking data/external/whats_cooking/train.json
    uv run python -I scripts/affinity/ingredient_map.py coverage \
        food_com data/external/food_com/RAW_recipes.csv
"""
from __future__ import annotations

import ast
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TAXONOMY_PATH = ROOT / "data" / "INGREDIENT_TAXONOMY.md"
OVERRIDES_PATH = ROOT / "data" / "affinity" / "ingredient_overrides.csv"
AFFINITY_DIR = ROOT / "data" / "affinity"

# Preparation / size / quality words that don't change an ingredient's identity.
# Intentionally excludes color and type words (green, red, sweet, hot) that often DO
# change identity (green onion, sweet potato, hot pepper).
DESCRIPTORS = {
    "ground", "fresh", "freshly", "dried", "dry", "chopped", "minced", "sliced",
    "diced", "crushed", "grated", "shredded", "ground", "whole", "halved", "quartered",
    "large", "small", "medium", "extra", "virgin", "extravirgin", "kosher", "sea",
    "fine", "finely", "coarse", "coarsely", "boneless", "skinless", "unsalted",
    "salted", "reduced", "lowfat", "nonfat", "fat", "free", "light", "lite", "lean",
    "cooked", "uncooked", "raw", "frozen", "canned", "ripe", "roasted", "toasted",
    "prepared", "instant", "pure", "organic", "natural", "plain", "unsweetened",
    "sweetened", "soft", "firm", "hard", "warm", "cold", "hot", "cool", "room",
    "temperature", "boiling", "melted", "softened", "beaten", "peeled", "seeded",
    "stemmed", "trimmed", "rinsed", "drained", "packed", "sifted", "crumbled",
    "shaved", "julienned", "cubed", "mashed", "ground", "powdered", "granulated",
    "allpurpose", "purpose", "all", "pure", "good", "quality", "best", "store",
    "bought", "homemade", "low", "high", "no", "with", "without", "and", "or", "of",
    "for", "to", "into", "in", "the", "a", "an", "about", "approximately",
    # units / containers / counts
    "cup", "cups", "tablespoon", "tablespoons", "tbsp", "teaspoon", "teaspoons", "tsp",
    "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs", "gram", "grams", "g",
    "kg", "ml", "l", "liter", "liters", "pint", "pints", "quart", "quarts", "gallon",
    "inch", "inches", "piece", "pieces", "head", "heads", "stalk",
    "stalks", "sprig", "sprigs", "bunch", "bunches", "leaf", "leaves", "slice",
    "slices", "strip", "strips", "can", "cans", "jar", "jars", "bottle", "package",
    "packages", "pkg", "container", "box", "bag", "pinch", "dash", "handful",
}

_WORD_RE = re.compile(r"[a-z]+(?:-[a-z]+)?")


def _singularize(w: str) -> str:
    if len(w) <= 3 or w.endswith("ss"):
        return w
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("oes"):
        return w[:-2]
    if w.endswith("s"):
        return w[:-1]
    return w


def clean(s: str) -> tuple[str, frozenset[str]]:
    """Return (normalized phrase, token set) with descriptors/units/quantities stripped."""
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)          # drop parentheticals
    s = s.replace("&", " ")
    toks = _WORD_RE.findall(s)
    out = []
    for t in toks:
        t = t.replace("-", "")
        if not t or t in DESCRIPTORS or t.isdigit():
            continue
        out.append(_singularize(t))
    return " ".join(out), frozenset(out)


def parse_taxonomy(path: Path = TAXONOMY_PATH):
    """slug -> {category, description, phrases:set}. Phrases = slug name + synonyms."""
    slugs: dict[str, dict] = {}
    category = None
    line_re = re.compile(r"^- `([a-z0-9_]+)`:\s*(.*)$")
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("### "):
            category = line[4:].strip()
        m = line_re.match(line)
        if not m:
            continue
        slug, desc = m.group(1), m.group(2)
        phrases: set[str] = set()
        name_norm, _ = clean(slug.replace("_", " "))
        if name_norm:
            phrases.add(name_norm)
        # synonyms = comma / "or" / semicolon separated fragments of the description
        desc_clean = re.sub(r"\([^)]*\)", " ", desc)
        for frag in re.split(r"[,;]| or | and ", desc_clean):
            norm, toks = clean(frag)
            # keep short, specific fragments; drop empties and over-long clauses
            if norm and 1 <= len(toks) <= 4:
                phrases.add(norm)
        slugs[slug] = {"category": category, "description": desc, "phrases": phrases}
    return slugs


class IngredientMapper:
    def __init__(self):
        self.slugs = parse_taxonomy()
        self.phrase2slug: dict[str, str] = {}
        self.head2slugs: dict[str, set[str]] = {}
        # longer (more specific) phrases registered first so they win ties
        for slug, info in self.slugs.items():
            for ph in sorted(info["phrases"], key=lambda p: -len(p.split())):
                self.phrase2slug.setdefault(ph, slug)
                head = ph.split()[-1]
                self.head2slugs.setdefault(head, set()).add(slug)
        # multi-token phrases, longest first, for subset matching
        self._multi = sorted(
            ((ph, slug) for ph, slug in self.phrase2slug.items() if " " in ph),
            key=lambda kv: -len(kv[0].split()),
        )
        self.overrides = self._load_overrides()

    def _load_overrides(self) -> dict[str, str]:
        ov: dict[str, str] = {}
        if OVERRIDES_PATH.exists():
            with open(OVERRIDES_PATH) as f:
                for row in csv.DictReader(f):
                    key, _ = clean(row["external_string"])
                    slug = row["slug"].strip()
                    if slug and slug != "UNMAPPED":
                        ov[key] = slug
        return ov

    def map(self, s: str) -> tuple[str | None, str]:
        """Return (slug or None, method)."""
        norm, toks = clean(s)
        if not norm:
            return None, "empty"
        if norm in self.overrides:
            return self.overrides[norm], "override"
        if norm in self.phrase2slug:
            return self.phrase2slug[norm], "exact"
        # "<specifier> <generic-head>" -> specifier, e.g. "parmesan cheese" -> parmesan,
        # "lemon juice" -> lemon. Safe because real compound slugs (garlic_powder,
        # soy_sauce, tomato_sauce, plant_milk, ...) were already caught by exact match
        # above; only generic heads whose specific form is NOT a slug reach here.
        parts = norm.split()
        GENERIC_TAIL = {"cheese", "sauce", "oil", "vinegar", "wine", "juice",
                        "broth", "stock", "zest"}
        if len(parts) >= 2 and parts[-1] in GENERIC_TAIL:
            spec = " ".join(parts[:-1])
            if spec in self.phrase2slug:
                return self.phrase2slug[spec], "specifier"
        # most-specific multi-token phrase fully contained in the string's tokens
        for ph, slug in self._multi:
            pt = ph.split()
            if all(t in toks for t in pt):
                return slug, "subset"
        # unambiguous head-noun match
        head = norm.split()[-1]
        cands = self.head2slugs.get(head)
        if cands and len(cands) == 1:
            return next(iter(cands)), "head"
        if head in self.phrase2slug:
            return self.phrase2slug[head], "head"
        return None, "unmapped"


# --------------------------------------------------------------------------- #
# dataset loaders (yield ingredient-string lists; raw data is untrusted input)
# --------------------------------------------------------------------------- #
def iter_whats_cooking(path: str):
    for r in json.load(open(path)):
        yield r["ingredients"]


def iter_food_com(path: str):
    csv.field_size_limit(10**7)
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                yield ast.literal_eval(row["ingredients"])
            except (ValueError, SyntaxError):
                continue


LOADERS = {"whats_cooking": iter_whats_cooking, "food_com": iter_food_com}


def coverage(src: str, path: str):
    mapper = IngredientMapper()
    mentions = Counter()        # string -> count
    for ings in LOADERS[src](path):
        mentions.update(ings)
    method_mentions = Counter()
    mapped_mentions = 0
    mapped_unique = 0
    unmapped: list[tuple[str, int]] = []
    for s, n in mentions.items():
        slug, method = mapper.map(s)
        method_mentions[method] += n
        if slug:
            mapped_mentions += n
            mapped_unique += 1
        else:
            unmapped.append((s, n))
    total_mentions = sum(mentions.values())
    print(f"[{src}] unique strings: {len(mentions):,} | total mentions: {total_mentions:,}")
    print(f"  mapped unique:   {mapped_unique:,} ({mapped_unique/len(mentions)*100:.1f}%)")
    print(f"  mapped mentions: {mapped_mentions:,} ({mapped_mentions/total_mentions*100:.1f}%)")
    print("  by method (mention-weighted):")
    for m, c in method_mentions.most_common():
        print(f"    {m:10s} {c:9,} ({c/total_mentions*100:4.1f}%)")
    unmapped.sort(key=lambda kv: -kv[1])
    AFFINITY_DIR.mkdir(parents=True, exist_ok=True)
    out = AFFINITY_DIR / f"unmapped_{src}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["external_string", "mentions"])
        w.writerows(unmapped[:400])
    um_mentions = sum(n for _, n in unmapped)
    print(f"  unmapped: {len(unmapped):,} strings, {um_mentions:,} mentions "
          f"({um_mentions/total_mentions*100:.1f}%). Top 400 -> {out.name}")
    print("  top 30 unmapped by frequency:")
    for s, n in unmapped[:30]:
        print(f"    {n:6,}  {s}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "coverage":
        coverage(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
