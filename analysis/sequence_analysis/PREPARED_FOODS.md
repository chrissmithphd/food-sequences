# Prepared Dishes

## What counts as a prepared dish

A prepared dish is a **pre-made meal that still typically needs warming or cooking**
— a frozen dinner, frozen pizza, lasagna, pot pie, mac & cheese, deli-prepared meal.
It is not a snack (crackers, candy, cookies), not a drink, and not a cooking
ingredient. We define it as the 17 ingredient types in the taxonomy's *Prepared
Dishes & Meals* section:

> frozen_meal, frozen_pizza, frozen_burrito, frozen_lasagna, pot_pie, hot_pocket,
> chicken_nuggets, mozzarella_sticks, corn_dogs, frozen_appetizer, mac_and_cheese,
> meal_kit, soup (ready-to-eat), instant_soup, instant_ramen, canned_chili, deli_prepared

This replaces the raw per-product `is_prepared_dish` classifier flag, which was
noisy — it also marked snacks, drinks, condiments, and even produce as "prepared."
Condensed / cream-of soups are a cooking base (recipe ingredient), so they are split
into `condensed_soup` and excluded; ready-to-eat soup remains a dish.

## Reach — how many customers buy prepared meals

**59.6% of customers (122,794 of 206,062) buy at least one prepared dish.** A
majority, but far from universal — and well below the 90% you get if you count every
ready-to-eat snack as "prepared."

## How much they rely on them

Among prepared-dish buyers:

| Measure | p10 | median | p90 |
|---------|----:|-------:|----:|
| Prepared dishes as % of food items | 1.0% | **4.4%** | 15.7% |
| Orders containing a prepared dish | 7.7% | **30.0%** | 77.8% |
| Distinct prepared dish types bought | 1 | **2** | 5 |

For the typical buyer, prepared dishes are an occasional convenience — about one in
twenty items and under a third of orders — not a dietary staple. A minority lean on
them heavily (top decile: ~16% of items, ~78% of orders).

Prepared reliance does **not** rise with overall purchase volume (correlation of
prepared-item-share with order count = −0.21): heavy grocery shoppers do not buy
proportionally more prepared meals — if anything slightly less.

## Which prepared dishes are popular

![Prepared dish types by reach](figures/prepared_topics.png)

| Dish type | Customers | Items | Repeat-buyers\* |
|-----------|----------:|------:|---------------:|
| frozen_meal | 54,229 | 323,757 | 62% |
| frozen_pizza | 41,479 | 166,969 | 59% |
| soup (ready-to-eat) | 41,033 | 154,365 | 50% |
| mac_and_cheese | 35,777 | 118,454 | 54% |
| deli_prepared | 31,445 | 122,057 | 53% |
| frozen_appetizer | 25,452 | 71,095 | 47% |
| chicken_nuggets | 21,925 | 69,636 | 54% |
| frozen_burrito | 13,635 | 51,054 | 53% |
| instant_ramen | 9,284 | 21,592 | 39% |
| frozen_lasagna | 8,191 | 20,700 | 45% |

\*share of a type's buyers who bought it in ≥2 separate orders.

Frozen meals lead by a wide margin, and the category is dominated by the freezer:
frozen meals, pizza, appetizers, burritos, lasagna. Repeat-buyer rates cluster
around 50–60% — once someone buys a prepared dish type, a slim majority come back to
it, with frozen_meal (62%) and frozen_pizza (59%) the stickiest.

## Do prepared dishes reorder differently?

At the fair exact-product grain:

| Group | P(next order) | Lift above chance |
|-------|--------------:|------------------:|
| **Prepared dishes** | 29.8% | **1.44×** |
| **Base ingredients** | 28.7% | 1.29× |

A specific prepared-dish product is reordered *slightly more* than a base-ingredient
product, and more above chance (1.44× vs 1.29×) — when someone finds a frozen meal
they like, they re-buy that exact one in runs at least as tightly as a staple.

But across *different* prepared dishes for the same dish type, buyers **switch more
than they commit**: within a prepared dish type, the probability of keeping the same
product order-to-order is 49.5% (lift 1.004 — essentially chance), versus 63.6%
(lift 1.038) for base ingredients. So prepared-dish buyers lock onto individual SKUs
they like, but rotate among them within a type more readily than they rotate staples.

## What it means for a meal service

- Prepared-meal demand is real but a **minority, occasional** behavior in grocery —
  60% reach, ~4% of items for the typical buyer. A service selling *only* prepared
  meals is serving the heavy tail, not the median grocery shopper.
- The stickiness is at the **specific-dish** level (re-buy the exact frozen meal you
  liked), while customers **rotate** across the menu within a type — both repetition
  and variety matter.
- Frozen dominates. Deli-prepared is the main non-frozen prepared channel.

## Limitations

- Even restricted to the taxonomy's dish list, grocery "prepared dishes" (frozen
  dinners, canned chili) are not a clean proxy for chef-prepared meal-kit services;
  treat generalizations as hypotheses.
- Reach and shares are item/order based within the observed window; a customer who
  bought one frozen pizza once counts toward reach.
- `soup` retains ready-to-eat canned/boxed soups; the condensed/cream-of cooking
  bases were split to `condensed_soup`, but the ready-to-eat/cooking line is drawn by
  product name and has edge cases.
