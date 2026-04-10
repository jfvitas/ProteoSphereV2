# P64 Entity Split Candidate Truth Review

This is a report-only review of [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json). It summarizes what the preview truthfully enables now, what it still does not do, and the next executable split step.

## What It Enables Now

The preview already gives us a full split-candidate lattice:

- `1889` atomic candidate rows
- `11` linked groups
- exact leakage keys on every row
- default hard grouping via `protein_spine_group`
- validation classes for proteins, variants, and structure overlaps
- lane depth labels that separate backbone, variant, and structure-candidate layers

The preview is already useful because it turns the materialized lightweight library into split-governance inputs rather than accession-only summaries.

Current counts:

- proteins: `11`
- protein variants: `1874`
- structure units: `4`

Current buckets:

- `protein_spine`: `11`
- `variant_entity`: `1874`
- `structure_entity`: `4`

## What It Still Does Not Do

The preview does not yet produce a split result. It does not assign:

- train / validation / test labels
- fold names
- balance policies
- holdout rules

It also does not add ligand-aware axes, and it does not materialize direct structure-backed variant joins.

The most important truth boundary is still the same one the earlier contracts set:

- each row is atomic
- `protein_spine_group` is the default hard boundary
- `exact_entity_group` must never be split inside the row
- structure rows remain candidate overlap only until an explicit structure-side anchor exists

## Grounded Examples

- `protein:P04637` is a `protein_backbone` row at lane depth `1`, so it can anchor a split plan without crossing the protein spine boundary.
- `protein_variant:protein:P31749:E17K` is a `variant_entity` row at lane depth `2`, so it can stay attached to its protein spine while still carrying a unique mutation key.
- `structure_unit:protein:P68871:4HHB:B` is a `structure_candidate_overlap` row at lane depth `3`, so it carries chain and fold boundaries but still stops short of a promoted structure-backed variant join.

## Next Executable Split Step

The next executable split step should be a dry-run split assignment artifact that:

- treats `linked_group_id` as the unit that cannot be split across partitions
- keeps `exact_entity_group` atomic
- uses `protein_spine_group` as the default hard grouping boundary
- emits fold or partition assignments only after the hard groups are preserved

That is the smallest truthful step from candidate preview to an executable split plan.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim a split output that the preview does not yet materialize.
