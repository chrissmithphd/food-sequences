#!/usr/bin/env python3
"""Validate the food-affinity reference dataset and emit coverage/quality tables.

Reads the committed reference CSVs (plus the 543-ingredient volumes) and reports:
  - coverage of the 543-slug taxonomy and of grocery purchase volume,
  - per-affinity evidence grade (strong / moderate / weak) with its top signatures,
  - measured overlap between affinities (shared distinctive ingredients), which is the
    evidence for grouping affinities rather than forcing fine distinctions.

Writes data/affinity/coverage_report.csv and data/affinity/affinity_overlap.csv and
prints a summary. Measured only — no model, no customer data.

Usage: uv run python -I scripts/affinity/validate.py
"""
from __future__ import annotations

import csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
AFF = ROOT / "data" / "affinity"

DISTINCT_LIFT = 2.0        # lift threshold for "distinctive"
DISTINCT_SUPPORT = 20


def main():
    affinities = list(csv.DictReader(open(AFF / "affinities.csv")))
    assoc = list(csv.DictReader(open(AFF / "ingredient_associations.csv")))
    ai = pl.read_csv(ROOT / "analysis" / "ingredients" / "all_ingredients.csv")

    all543 = set(ai["ingredient"].to_list())
    tot_vol = ai["purchases"].sum()

    by_aff: dict[str, list[dict]] = defaultdict(list)
    for r in assoc:
        by_aff[r["affinity_id"]].append(r)

    assoc_slugs = {r["slug"] for r in assoc}
    distinct_slugs = {r["slug"] for r in assoc
                      if float(r["lift"]) >= DISTINCT_LIFT and int(r["support"]) >= DISTINCT_SUPPORT}

    covered = ai.filter(pl.col("ingredient").is_in(assoc_slugs))
    print("=== taxonomy + volume coverage ===")
    print(f"543 slugs with any association: {len(assoc_slugs & all543)} "
          f"({len(assoc_slugs & all543)/len(all543)*100:.0f}%)")
    print(f"543 slugs with distinctive (lift>={DISTINCT_LIFT}) evidence: "
          f"{len(distinct_slugs & all543)}")
    print(f"grocery purchase volume covered: {covered['purchases'].sum()/tot_vol*100:.1f}%")

    # per-affinity distinctive signatures + evidence grade
    def grade(nrec, ndist):
        if nrec >= 1000 and ndist >= 5:
            return "strong"
        if nrec >= 500 and ndist >= 3:
            return "moderate"
        return "weak"

    dist_sets: dict[str, set[str]] = {}
    rows = []
    for a in affinities:
        aid, dim, src = a["affinity_id"], a["dimension"], a["source"]
        nrec = int(a["n_recipes"]) if a["n_recipes"] else 0
        if not src:   # sensory-flavor catalog-only
            rows.append([aid, dim, src, nrec, 0, 0, "unmeasured", ""])
            continue
        ds = [r for r in by_aff[aid]
              if float(r["lift"]) >= DISTINCT_LIFT and int(r["support"]) >= DISTINCT_SUPPORT]
        ds.sort(key=lambda r: -float(r["lift"]))
        dist_sets[aid] = {r["slug"] for r in ds}
        top = "; ".join(f"{r['slug']}({float(r['lift']):.0f}x)" for r in ds[:5])
        rows.append([aid, dim, src, nrec, len(by_aff[aid]), len(ds),
                     grade(nrec, len(ds)), top])

    with open(AFF / "coverage_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["affinity_id", "dimension", "source", "n_recipes",
                    "n_associations", "n_distinctive", "evidence_grade",
                    "top_distinctive_ingredients"])
        w.writerows(rows)

    grades = [r[6] for r in rows]
    print("\n=== evidence grades ===")
    for g in ("strong", "moderate", "weak", "unmeasured"):
        print(f"  {g:10s} {grades.count(g)}")

    # measured overlap between affinities (shared distinctive ingredients)
    overlap = []
    ids = list(dist_sets)
    for a, b in combinations(ids, 2):
        sa, sb = dist_sets[a], dist_sets[b]
        if len(sa) < 3 or len(sb) < 3:
            continue
        inter = sa & sb
        union = sa | sb
        j = len(inter) / len(union) if union else 0
        if j >= 0.25:
            overlap.append([a, b, round(j, 3), len(inter),
                            "; ".join(sorted(inter)[:6])])
    overlap.sort(key=lambda r: -r[2])
    with open(AFF / "affinity_overlap.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["affinity_a", "affinity_b", "jaccard_distinctive",
                    "n_shared", "shared_ingredients"])
        w.writerows(overlap)

    print(f"\n=== top affinity overlaps (merge candidates), {len(overlap)} pairs >= 0.25 ===")
    for r in overlap[:15]:
        print(f"  {r[2]:.2f}  {r[0]:16s} ~ {r[1]:16s}  [{r[4]}]")


if __name__ == "__main__":
    main()
