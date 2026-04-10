# P61 P04637 / P31749 Anchor Materialization Order

This is a report-only order plan for the next two unresolved accession anchors.

## Current Surface Context

The current joined bridge examples are `P68871` and `P69905`. The unresolved variant-without-structure anchors are `P04637` and `P31749`.

That means the next execution order should stay on the variant side, not the already-integrated globin bridge.

## Order

1. `P04637`
   - Protein: Cellular tumor antigen p53
   - Current counts: 1439 variant rows, 0 structure-unit rows, 124 pathway refs, 13 domain refs, 1 motif ref
   - Why first: it is the broadest unresolved anchor and has the highest operator payoff. The current coverage surface already marks it as the clearest structure follow-up candidate.
   - Truth boundary: transformation-bound only, structure-missing until a future acquisition exists

2. `P31749`
   - Protein: RAC-alpha serine/threonine-protein kinase
   - Current counts: 23 variant rows, 0 structure-unit rows, 112 pathway refs, 13 domain refs, 5 motif refs
   - Why second: it is still valuable, but the current variant surface is much smaller than `P04637`, so it should follow after the broader anchor lands.
   - Truth boundary: transformation-bound only, structure-missing until a future acquisition exists

## Why This Order

`P04637` comes first because it gives the largest immediate increase in accession coverage and operator utility. `P31749` comes second because it is still unresolved and meaningful, but smaller.

The report deliberately does not move the already-integrated `P68871` and `P69905` bridge examples, and it does not claim any structure-backed join for `P04637` or `P31749`.

## Boundary

This is report-only. It does not edit code, it does not touch protected latest surfaces, and it keeps the materialization step variant-side only.

