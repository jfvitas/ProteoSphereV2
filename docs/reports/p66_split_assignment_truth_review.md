# P66 Split Assignment Truth Review

This is a report-only review of [entity_split_assignment_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_assignment_preview.json), grounded in [entity_split_simulation_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json) and [entity_split_recipe_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_recipe_preview.json). It summarizes what the live linked-group assignment surface now proves and what still remains deferred.

## What It Proves Now

The assignment surface already proves a dry-run linked-group assignment:

- `11` linked groups
- `1889` assigned entity rows
- `1889` candidate rows represented
- one split assignment per linked group

It also proves the split composition at a useful operator level:

- `test`: `9` linked groups
- `train`: `1` linked group
- `val`: `1` linked group

The largest groups are the same ones the simulation and recipe previews highlight:

- `protein:P04637` in `train`
- `protein:P68871` in `val`
- `protein:P69905` and `protein:P31749` in `test`

That means the assignment surface is not just a count summary. It is a truthful dry-run map of where each linked protein-spine cluster currently lands.

## What It Still Does Not Do

The surface still does not commit a release split, and it still does not export a CV fold set.

It also still falls short of the requested target counts shown by the simulation preview:

- train: `1440` vs target `1322`
- val: `266` vs target `283`
- test: `183` vs target `284`

The assignment surface also stays within the current hard boundary:

- no rows are split inside a `linked_group_id`
- no ligand-aware axes are introduced
- no protected latest surface is mutated

## Grounded Examples

- `protein:P04637` proves that the largest variant-rich cluster stays intact and lands entirely in `train`.
- `protein:P68871` proves that a structure-overlap cluster can stay intact and land entirely in `val`.
- `protein:P69905` proves that a mixed protein / variant / structure group can stay intact and land entirely in `test`.

The simulation and recipe previews back this up by showing the same protein-spine-first behavior, just at different stages of the pipeline.

## Next Executable Split Step

The next executable split step should be a fold-prep assignment artifact that:

- preserves `linked_group_id` atomicity
- records per-split diagnostics
- keeps `protein_spine_group` as the hard boundary
- remains report-only until a release split is explicitly approved

That is the smallest truthful step from the current assignment surface toward an executable split export.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim a final fold set or release split that the preview does not yet materialize.
