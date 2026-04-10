# P57 Variant Structure Accession Shortlist

This is a report-only shortlist for the first actionable accessions that can close the current structure-variant disjointness.

## Bottom Line

The current specialized surfaces are disjoint:

- the materialized protein-variant surface currently covers `P04637` and `P31749`
- the materialized structure-unit surface currently covers `P68871` and `P69905`
- there is no accession overlap yet

The first actionable bridge is therefore to expand the variant side for the existing structure-unit accessions, starting with `P68871`, then `P69905`.

## Why This Shortlist

The repo's own join map and bridge plan already say the same thing: the cleanest truthful path is to materialize accession-scoped variant rows for the structure-unit anchors that already exist. That avoids inventing structure coverage for variant-only accessions and keeps the bridge accession-first.

## Ranked Shortlist

1. `P68871`
2. `P69905`

Both accessions already exist on the protein and structure-unit surfaces, and both still need a protein-variant counterpart to make the join truthful.

### `P68871`

- Current materialized surfaces: protein, structure_unit
- Missing surface: protein_variant
- Existing structure-unit rows:
  - `structure_unit:protein:P68871:4HHB:B`
  - `structure_unit:protein:P68871:4HHB:D`
- Why it is first: it is already a stable structure anchor, so adding an explicit variant record is the smallest step that creates a real accession overlap.

### `P69905`

- Current materialized surfaces: protein, structure_unit
- Missing surface: protein_variant
- Existing structure-unit rows:
  - `structure_unit:protein:P69905:4HHB:A`
  - `structure_unit:protein:P69905:4HHB:C`
- Why it is second: it is the parallel structure anchor and the second direct path to closing the disjointness set.

## Parked, Not Shortlisted

- `P04637` stays parked because it is already variant-backed but has no current structure-unit surface in the materialized structure-unit library.
- `P31749` stays parked for the same reason.

## Actionable Reading

If we want to close the gap with the least ambiguity, the next move is:

1. materialize a variant row for `P68871`
2. materialize a variant row for `P69905`
3. refresh the join map and packet-facing surfaces

That path is grounded in already materialized proteins, variants, and structure-unit surfaces only, and it keeps the current disjointness report honest until the join actually exists.
