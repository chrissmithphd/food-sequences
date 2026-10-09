"""
Delayed-reordering measurement.

Corrects an earlier error: adjacent-basket overlap was mistaken for reordering.
This module measures reordering properly, using the full purchase history and
Instacart's `reordered` field, with right-censoring for incomplete follow-up.

Definitions (used consistently everywhere):
  interval          = next_purchase_order - prev_purchase_order   (>= 1)
  intervening orders = interval - 1                               (>= 0)
  A single-purchase (customer, product) history has NO interval — it is MISSING,
  never 0. Its lone purchase contributes only a right-censored observation.

Weighting variants for the reorder curve:
  event-weighted          : every purchase occurrence counts equally
                            (frequent buyers / products dominate)
  customer-product-weighted: each (customer, product) pair counts equally
  customer-weighted        : each customer counts equally
"""

import numpy as np
import pandas as pd

T_MAX = 101  # order_number maxes at 100


def build_cohort_maps(products, aisles, departments, meal_like_aisles, broad_departments):
    """Return (meal_like_product_ids, broad_product_ids) as sets."""
    aisle_name_to_id = dict(zip(aisles["aisle"], aisles["aisle_id"]))
    meal_aisle_ids = {aisle_name_to_id[a] for a in meal_like_aisles if a in aisle_name_to_id}

    dept_name_to_id = dict(zip(departments["department"], departments["department_id"]))
    broad_dept_ids = {dept_name_to_id[d] for d in broad_departments if d in dept_name_to_id}

    meal_like = set(products.loc[products["aisle_id"].isin(meal_aisle_ids), "product_id"])
    broad = set(products.loc[products["department_id"].isin(broad_dept_ids), "product_id"])
    return meal_like, broad


class ReorderAccumulator:
    """Accumulates reconciliation, basket composition, and KM histograms across batches."""

    def __init__(self):
        # Reconciliation of history-based indicator vs Instacart `reordered`
        self.recon = {"agree_1": 0, "agree_0": 0, "hist1_field0": 0, "hist0_field1": 0}

        # Basket composition (orders with a predecessor), pooled item counts
        self.comp_pooled = {"from_prior": 0, "older_absent": 0, "first_observed": 0}
        # Per-customer composition fractions (for customer-weighting)
        self.cust_comp_rows = []  # list of (from_prior_frac, older_frac, first_frac)

        # KM histograms: for each cohort and weighting, events[t] and censored[t]
        self.cohorts = ["all", "meal_like", "broad"]
        self.weightings = ["event", "cp", "cust"]
        self.events = {(c, w): np.zeros(T_MAX) for c in self.cohorts for w in self.weightings}
        self.censored = {(c, w): np.zeros(T_MAX) for c in self.cohorts for w in self.weightings}

        self.n_single_pairs = 0
        self.n_multi_pairs = 0
        self.n_events = 0

    def add_occurrence(self, interval_or_censor, is_event, cohort_flags, w_cp, w_cust):
        """Record one purchase occurrence into the KM histograms."""
        t = int(interval_or_censor)
        if t >= T_MAX:
            t = T_MAX - 1
        target = self.events if is_event else self.censored
        for c in ("all",) + cohort_flags:
            target[(c, "event")][t] += 1.0
            target[(c, "cp")][t] += w_cp
            target[(c, "cust")][t] += w_cust


def process_user_batch(purchases, cohort_meal, cohort_broad, acc, event_rows,
                        item_col="product_id", do_composition=True):
    """
    Process one batch of users' purchases.

    purchases: DataFrame with [user_id, order_number, product_id, reordered].
    item_col: the repeat unit — "product_id" (exact SKU) or "aisle_id"
              (same kind of food, possibly different brand/variant).
    do_composition: reconciliation + basket composition only make sense at the
              product level (Instacart's `reordered` is product-level), so this
              is True for the product pass and False for the aisle pass.
    acc: ReorderAccumulator (mutated).
    event_rows: list to append repeat-event records to.
    """
    purchases = purchases.sort_values(["user_id", "order_number", item_col])

    for user_id, ug in purchases.groupby("user_id", sort=False):
        total_orders = int(ug["order_number"].max())

        if do_composition:
            # O(1) field lookup instead of a per-item boolean filter
            field_map = dict(zip(zip(ug["order_number"], ug["product_id"]), ug["reordered"]))
            baskets = ug.groupby("order_number")["product_id"].apply(set).to_dict()
            seen_so_far = set()
            cust_counts = {"from_prior": 0, "older_absent": 0, "first_observed": 0}
            for o in range(1, total_orders + 1):
                basket = baskets.get(o, set())
                prior_basket = baskets.get(o - 1, set()) if o >= 2 else set()
                for pid in basket:
                    hist_reorder = 1 if pid in seen_so_far else 0
                    field_reorder = int(field_map.get((o, pid), 0))
                    if hist_reorder == 1 and field_reorder == 1:
                        acc.recon["agree_1"] += 1
                    elif hist_reorder == 0 and field_reorder == 0:
                        acc.recon["agree_0"] += 1
                    elif hist_reorder == 1:
                        acc.recon["hist1_field0"] += 1
                    else:
                        acc.recon["hist0_field1"] += 1
                    if o >= 2:
                        if pid in prior_basket:
                            acc.comp_pooled["from_prior"] += 1
                            cust_counts["from_prior"] += 1
                        elif pid in seen_so_far:
                            acc.comp_pooled["older_absent"] += 1
                            cust_counts["older_absent"] += 1
                        else:
                            acc.comp_pooled["first_observed"] += 1
                            cust_counts["first_observed"] += 1
                seen_so_far |= basket
            tot = sum(cust_counts.values())
            if tot > 0:
                acc.cust_comp_rows.append((
                    cust_counts["from_prior"] / tot,
                    cust_counts["older_absent"] / tot,
                    cust_counts["first_observed"] / tot,
                ))

        # --- Repeat events + KM occurrences, keyed on item_col ---
        # Distinct order_numbers the item appeared in (an item can occur once per order)
        item_orders = ug.groupby(item_col)["order_number"].apply(lambda s: sorted(set(s.tolist())))
        n_user_occurrences = sum(len(v) for v in item_orders)
        w_cust_each = 1.0 / n_user_occurrences if n_user_occurrences else 0.0

        for iid, onums in item_orders.items():
            k = len(onums)
            flags = []
            if iid in cohort_meal:
                flags.append("meal_like")
            if iid in cohort_broad:
                flags.append("broad")
            flags = tuple(flags)
            w_cp_each = 1.0 / k

            if k == 1:
                acc.n_single_pairs += 1
            else:
                acc.n_multi_pairs += 1

            for i in range(k - 1):
                interval = onums[i + 1] - onums[i]
                acc.add_occurrence(interval, True, flags, w_cp_each, w_cust_each)
                acc.n_events += 1
                if event_rows is not None:
                    event_rows.append((
                        user_id, iid, onums[i], onums[i + 1],
                        interval, interval - 1,
                        1 if "meal_like" in flags else 0,
                        1 if "broad" in flags else 0,
                    ))
            censor = total_orders - onums[-1]
            acc.add_occurrence(censor, False, flags, w_cp_each, w_cust_each)


def km_reorder_probability(events, censored):
    """
    Discrete Kaplan-Meier. Returns dict n -> P(reorder within n orders)
    for n in 1..T_MAX-1, plus survival array.
    """
    surv = np.ones(T_MAX)
    s = 1.0
    for t in range(1, T_MAX):
        risk = events[t:].sum() + censored[t:].sum()
        e = events[t]
        if risk > 0:
            s *= (1.0 - e / risk)
        surv[t] = s
    prob_within = {n: 1.0 - surv[n] for n in range(1, T_MAX)}
    return prob_within, surv
