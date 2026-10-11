# Stage 1: Equivalence-Level Reorder Comparison

Censoring-aware P(reorder within n orders), event-weighted, within-basket deduplicated. Higher levels collapse brand/shape/fat-level switches into 'same food' reorders.

## pasta

| grouping level | n=1 | n=2 | n=3 | n=5 | n=10 | user-key pairs |
|---|---|---|---|---|---|---|
| sku | 15.2% | 24.4% | 31.0% | 39.8% | 51.5% | 161,645 |
| equivalent_food | 16.5% | 26.5% | 33.8% | 43.5% | 56.4% | 145,384 |
| family | 25.7% | 41.0% | 51.2% | 64.0% | 78.7% | 79,065 |

## milk

| grouping level | n=1 | n=2 | n=3 | n=5 | n=10 | user-key pairs |
|---|---|---|---|---|---|---|
| sku | 48.5% | 67.1% | 75.3% | 82.2% | 87.6% | 164,756 |
| equivalent_food | 51.6% | 71.0% | 79.4% | 86.4% | 91.5% | 134,877 |
| family | 56.0% | 75.7% | 84.0% | 90.5% | 95.1% | 100,933 |

## eggs

| grouping level | n=1 | n=2 | n=3 | n=5 | n=10 | user-key pairs |
|---|---|---|---|---|---|---|
| sku | 35.1% | 52.9% | 62.6% | 72.4% | 81.2% | 129,642 |
| equivalent_food | 38.2% | 57.5% | 67.9% | 78.4% | 87.4% | 105,404 |
| family | 40.6% | 60.7% | 71.5% | 82.0% | 90.6% | 90,859 |
