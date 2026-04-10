# P65 Entity Split Recipe Truth Review

This is a report-only review of [entity_split_recipe_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_recipe_preview.json), [entity_split_simulation_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json), and [p64_first_split_recipe_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_first_split_recipe_contract.json). It summarizes what the live recipe preview enables now, what it still defers, and the next executable split step.

## What It Enables Now

The recipe preview is already an executable-facing view of the first split recipe contract:

- recipe ID `protein_spine_first_split_recipe_v1`
- input artifact `entity_split_candidate_preview`
- atomic unit `entity_signature_row`
- primary hard group `protein_spine_group`

The live simulation shows that the recipe can consume all current candidate rows:

- `1889` assigned rows
- `0` rejected rows
- split counts produced for `train`, `val`, and `test`

That means the recipe is already useful as a truthful split blueprint. It can explain how the current preview behaves without mutating the preview or any protected surface.

## What It Still Does Not Do

The preview still does not commit a release split. It also does not make the counts match the requested targets exactly:

- train: `1440` vs target `1322`
- val: `266` vs target `283`
- test: `183` vs target `284`

It also still keeps ligand axes reserved:

- `ligand_identity_group` remains null
- `binding_context_group` remains null

And it does not split inside any atomic row or hard group boundary:

- `exact_entity_group`
- `sequence_equivalence_group`
- `variant_delta_group`
- `structure_chain_group`
- `structure_fold_group`
- `protein_spine_group`

## Grounded Examples

- `protein:P04637` is still the largest hard spine cluster, so the recipe must keep it atomic under `protein_spine_group`.
- `protein:P31749` is the smaller variant-rich spine cluster and should follow the same hard grouping rule.
- `protein:P68871` and `protein:P69905` show how the current simulation already treats structure-overlap rows as part of the same protein-spine cluster while preserving chain and fold leakage boundaries.

The simulation itself is still report-only:

- `1889` assigned rows
- `0` rejected rows
- `0` leakage collisions

## Next Executable Split Step

The next executable split step should export a locked dry-run split plan from `protein_spine_first_split_recipe_v1` that:

- preserves `linked_group_id` atomicity
- keeps `protein_spine_group` as the first hard boundary
- records diagnostics against the target counts
- remains a report-only artifact until a release split is explicitly approved

That is the smallest truthful step from recipe preview to an executable split plan.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim a finalized train/val/test release split.
