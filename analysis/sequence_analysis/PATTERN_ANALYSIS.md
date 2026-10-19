# Purchase Pattern Classification

For each user-ingredient pair with 2+ purchases (users with 10+ orders), classify the purchasing pattern:

## Pattern Definitions

- **Persistent Staple**: Purchased in >50% of orders with runs of 3+ consecutive purchases
- **Regular Rotation**: Appears every few orders with consistent gaps (2-5 orders between purchases, low variance)
- **Burst then Absence**: Multiple purchases clustered early (<30% of order history), then stops
- **Return after Break**: Purchases, gap of 5+ orders, then resumes
- **Irregular/Mixed**: Doesn't fit clear patterns above

## Results

Total user-ingredient pairs analyzed: 3,401,385

| Pattern | Count | Percentage |
|---------|-------|------------|
| Persistent Staple | 341,011 | 10.0% |
| Regular Rotation | 241,767 | 7.1% |
| Burst then Absence | 59,556 | 1.8% |
| Return after Break | 1,047,207 | 30.8% |
| Irregular/Mixed | 1,711,844 | 50.3% |

## Interpretation

1. **Most ingredients show irregular usage:** 50.3% don't fit clean patterns, suggesting complex purchasing behavior.

2. **True staples are rare:** Only 10.0% of ingredients are persistent staples bought in >50% of orders.

3. **Returns are common:** 30.8% show breaks of 5+ orders followed by resumption, suggesting ingredients are revisited after long gaps.

4. **Meal subscription implications:** Customers don't settle into fixed routines. They rotate through ingredients, take breaks, and return. Meal services should expect similar variety-seeking behavior.

## Methodology

- Analysis limited to users with 10+ orders (need sufficient history)
- Only user-ingredient pairs with 2+ purchases (need repeat behavior)
- Patterns are mutually exclusive and exhaustive
- Classification based on purchase frequency, gap patterns, and timing
