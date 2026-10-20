# Processing the Full Dataset

How the sequence analyses run over the entire Instacart dataset (~30M purchase
rows, 3.3M orders, 206K customers) without subsampling and without exhausting memory.
This is an implementation note; it has no bearing on the findings, which are computed
over the whole dataset.

## Constraint

The analysis environment caps available memory. The full purchase table — all of
`order_products_prior` and `order_products_train` joined to `orders` and the product
classification — is ~30.4M rows (~1.6 GB as a single dataframe). Holding that frame
*and* performing a whole-table sort or self-join needs several copies and overruns the
budget.

## Approach: one lazy pipeline, two collect modes

`scripts/sequence_analysis/audit_reorder_probability.py` defines a single lazy polars
pipeline (`_events_lazy`) and exposes it two ways:

- **`load_events()`** — collects the whole table at once (streaming engine). Used by
  analyses whose heaviest step is a group-by, which polars streams within the budget.
- **`iter_events(chunk_users=20000)`** — yields the table in user-id ranges. Each
  customer's full order history falls inside one range, so any *per-customer*
  computation (deduplication, within-customer windows and sorts, per-customer
  aggregation) is exact within a chunk; callers accumulate across chunks.

Because customers are independent and each is whole within a chunk, burst processing
is **exact, not approximate** — it produces identical results to processing the whole
table at once, it simply never holds more than one chunk's rows in memory.

## Which analyses use bursts

Analyses that sort or self-join at whole-table scale consume `iter_events()` and
accumulate:

| Analysis | What accumulates across bursts |
|----------|--------------------------------|
| Co-occurrence (Part 8) | per-ingredient order counts; within-order pair counts |
| Calendar time (Part 10) | per-order-gap day-gap values → aggregate quantiles |
| Customer behavior (Part 9) | one metrics row per customer |
| Exploration (Part 7) | per-order-position sums and counts; per-customer half rates |

Peak memory stays near ~1.2 GB for every analysis.

## Rule of thumb for new analyses

- If the heaviest operation is a per-customer sort or a within-order self-join, use
  `iter_events()` and accumulate.
- If it is a single group-by/aggregation, `load_events()` is fine.
- Never subsample the input to save memory — chunk it instead; the result is identical.
