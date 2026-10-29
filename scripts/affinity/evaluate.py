#!/usr/bin/env python3
"""Held-out evaluation: can ingredient signatures actually identify food profiles?

A list of associated ingredients is not proof a profile is detectable. This tests it
directly, with leakage control: recipes are split train/test, profile signatures are
learned from TRAIN only, and recipes in TEST are classified and scored against their
true labels.

Two tasks:
  1. Cuisine (What's Cooking, single-label, 20 classes) — accuracy, macro-F1, top
     confusions, vs. two baselines (majority prior; frequency-only, i.e. no
     distinctiveness weighting).
  2. Meal style & composition (Food.com, multi-label) — per-profile one-vs-rest
     average precision, so we see which profiles are reliably recognizable from
     ingredients and which are not.

Scorer is an interpretable Naive-Bayes log-likelihood-ratio: for a recipe's ingredient
set S and profile p,
    score(p) = sum over slug in S of log( P(slug|p) / P(slug|background) )
(add-1 smoothed). The frequency-only baseline drops the background term, keeping only
P(slug|p), so the gap between them measures what *distinctiveness* (lift) buys.

Writes data/affinity/evaluation_report.csv. Usage:
  uv run python -I scripts/affinity/evaluate.py
"""
from __future__ import annotations

import ast
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingredient_map import IngredientMapper  # noqa: E402
from build_associations import AFFINITIES, recipe_affinities_foodcom  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
EXT = ROOT / "data" / "external"
OUT = ROOT / "data" / "affinity"
SEED = 17
TEST_FRAC = 0.2


def load_corpus(mapper, cache):
    """Return (cuisine_recipes, meal_recipes). Each item = (labels, frozenset slugs)."""
    def to_slugs(strings):
        out = set()
        for raw in strings:
            if raw not in cache:
                s, _ = mapper.map(raw)
                cache[raw] = s
            if cache[raw]:
                out.add(cache[raw])
        return frozenset(out)

    cuisine = []
    cu2aff = {next(iter(sel)): aid for aid, _, _, _, sel, src in AFFINITIES
              if src == "whatscooking"}
    for r in json.load(open(EXT / "whats_cooking" / "train.json")):
        aid = cu2aff.get(r["cuisine"])
        if aid:
            cuisine.append((aid, to_slugs(r["ingredients"])))

    meal = []
    csv.field_size_limit(10**7)
    with open(EXT / "food_com" / "RAW_recipes.csv") as f:
        for row in csv.DictReader(f):
            try:
                tags = set(ast.literal_eval(row["tags"]))
                ings = ast.literal_eval(row["ingredients"])
            except (ValueError, SyntaxError):
                continue
            labels = recipe_affinities_foodcom(tags)
            if labels:
                meal.append((labels, to_slugs(ings)))
    return cuisine, meal


def split(items):
    rng = random.Random(SEED)
    idx = list(range(len(items)))
    rng.shuffle(idx)
    cut = int(len(idx) * (1 - TEST_FRAC))
    tr = {i for i in idx[:cut]}
    return [items[i] for i in idx[:cut]], [items[i] for i in idx[cut:]]


def train_logweights(train, labels, multilabel):
    """Return (logratio[label][slug], logfreq[label][slug], priors, vocab)."""
    N = len(train)
    label_n = Counter()
    label_slug = defaultdict(Counter)
    bg_slug = Counter()
    vocab = set()
    for labs, slugs in train:
        labs = labs if multilabel else [labs]
        for sl in slugs:
            bg_slug[sl] += 1
            vocab.add(sl)
        for a in labs:
            label_n[a] += 1
            for sl in slugs:
                label_slug[a][sl] += 1
    V = len(vocab) or 1
    logratio = {}
    logfreq = {}
    for a in labels:
        n = label_n[a] or 1
        lr, lf = {}, {}
        for sl in vocab:
            p_in = (label_slug[a][sl] + 1) / (n + 2)
            p_bg = (bg_slug[sl] + 1) / (N + 2)
            lr[sl] = math.log(p_in / p_bg)
            lf[sl] = math.log(p_in)
        logratio[a] = lr
        logfreq[a] = lf
    priors = {a: label_n[a] / N for a in labels}
    return logratio, logfreq, priors, vocab


def score(slugs, weights, labels, vocab):
    out = {}
    for a in labels:
        w = weights[a]
        out[a] = sum(w[sl] for sl in slugs if sl in vocab)
    return out


def eval_cuisine(cuisine):
    labels = [aid for aid, _, _, _, _, src in AFFINITIES if src == "whatscooking"]
    tr, te = split(cuisine)
    logratio, logfreq, priors, vocab = train_logweights(tr, labels, multilabel=False)
    majority = max(priors, key=priors.get)

    def accuracy(weights):
        correct = 0
        conf = Counter()
        per = defaultdict(lambda: [0, 0, 0])  # label -> [tp, fp, fn]
        for true, slugs in te:
            sc = score(slugs, weights, labels, vocab)
            pred = max(sc, key=sc.get) if sc else majority
            correct += (pred == true)
            if pred != true:
                conf[(true, pred)] += 1
            per[true][0 if pred == true else 2] += 1
            if pred != true:
                per[pred][1] += 1
        acc = correct / len(te)
        f1s = []
        for a in labels:
            tp, fp, fn = per[a]
            prec = tp / (tp + fp) if tp + fp else 0
            rec = tp / (tp + fn) if tp + fn else 0
            f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0)
        return acc, sum(f1s) / len(f1s), conf

    acc_lr, f1_lr, conf = accuracy(logratio)
    acc_maj = priors[majority]
    print("=== CUISINE (What's Cooking, 20-way single-label, held-out 20%) ===")
    print(f"  test recipes: {len(te):,}")
    print(f"  majority baseline (always {majority[2:]}):   acc {acc_maj:.3f}")
    print(f"  ingredient NB classifier:                   acc {acc_lr:.3f}  macroF1 {f1_lr:.3f}")
    print("  (for single-label argmax the background/lift term cancels, so frequency")
    print("   and distinctiveness weighting give the same prediction here.)")
    print("  top confusions (true -> predicted):")
    for (t, p), c in conf.most_common(8):
        print(f"    {t[2:]:14s} -> {p[2:]:14s} {c}")
    return [("cuisine", "majority", round(acc_maj, 3), ""),
            ("cuisine", "ingredient_nb", round(acc_lr, 3), round(f1_lr, 3))]


def eval_meal(meal):
    labels = [aid for aid, _, dim, _, _, src in AFFINITIES
              if src == "foodcom" and dim in ("meal_style", "composition", "flavor")]
    tr, te = split(meal)
    logratio, _, priors, vocab = train_logweights(tr, labels, multilabel=True)

    # one-vs-rest average precision per profile
    print("\n=== MEAL STYLE & COMPOSITION (Food.com, multi-label, held-out 20%) ===")
    print(f"  test recipes: {len(te):,}")
    rows = []
    scored = {a: [] for a in labels}   # a -> list of (score, is_true)
    for labs, slugs in te:
        labset = set(labs)
        sc = score(slugs, logratio, labels, vocab)
        for a in labels:
            scored[a].append((sc[a], a in labset))
    print(f"  {'profile':18s} {'prevalence':>10} {'avg_prec':>9} {'lift_vs_prev':>12}")
    for a in labels:
        pairs = sorted(scored[a], key=lambda t: -t[0])
        pos = sum(1 for _, y in pairs if y)
        prev = pos / len(pairs) if pairs else 0
        # average precision
        tp = 0
        ap = 0.0
        for i, (_, y) in enumerate(pairs, 1):
            if y:
                tp += 1
                ap += tp / i
        ap = ap / pos if pos else 0
        lift = ap / prev if prev else 0
        name = a
        print(f"  {name:18s} {prev:10.3f} {ap:9.3f} {lift:11.1f}x")
        rows.append(("meal", a, round(prev, 4), round(ap, 4)))
    return rows


def main():
    mapper = IngredientMapper()
    cache = {}
    cuisine, meal = load_corpus(mapper, cache)
    rows = eval_cuisine(cuisine)
    rows += eval_meal(meal)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "evaluation_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task", "method_or_profile", "accuracy_or_prevalence", "f1_or_avgprec"])
        w.writerows(rows)
    print("\nSaved evaluation_report.csv")


if __name__ == "__main__":
    main()
