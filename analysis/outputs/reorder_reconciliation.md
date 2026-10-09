# Reorder Reconciliation: History Indicator vs Instacart `reordered`

For every purchase row, a history-based indicator (product seen in any earlier
order by this customer) is compared to Instacart's `reordered` field.

| Case | Count | % of all purchase rows |
|---|---|---|
| Both say reorder (hist=1, field=1) | 19,903,887 | 59.29% |
| Both say first-time (hist=0, field=0) | 13,663,953 | 40.71% |
| History=reorder, field=first | 0 | 0.0000% |
| History=first, field=reorder | 0 | 0.0000% |
| **Agreement** | **33,567,840** | **100.000%** |

Total purchase rows: 33,567,840

A history indicator built from the data reproduces Instacart's `reordered` field
to within 0.000% of rows, confirming the two measure the
same thing. All later reorder analysis uses the full-history indicator so it can
also measure *delayed* reorders (gaps of several orders), which the `reordered`
flag marks but does not quantify.
