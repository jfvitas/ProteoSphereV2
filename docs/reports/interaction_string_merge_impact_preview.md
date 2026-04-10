# Interaction STRING Merge Impact Preview

- Status: `report_only`
- Policy label: `report_only_non_governing`
- Preview rows: `2`
- Candidate-only rows: `2`
- STRING surface state: `partial_on_disk`
- Procurement gate: `ready_to_freeze_complete_mirror`

## Merge Impact

- Merge changes split or leakage: `False`
- Bundle safe immediately: `False`
- Non-governing until tail completion: `True`
- Procurement tail completion required: `True`

## Truth Boundary

- This is a report-only impact preview for the STRING merge lane. It does not materialize STRING rows, does not change split or leakage claims, and does not become governing until the procurement tail freeze gate clears.
