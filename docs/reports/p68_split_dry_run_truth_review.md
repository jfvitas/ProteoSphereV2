# P68 Split Dry Run Truth Review

This is a report-only review of [split_engine_input_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/split_engine_input_preview.json), [split_engine_dry_run_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/split_engine_dry_run_validation.json), [entity_split_assignment_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_assignment_preview.json), and [entity_split_simulation_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json). It focuses on what the dry-run validator now proves and what still blocks fold export.

## What The Validator Proves Now

The dry-run validator proves parity across the current split-engine handoff surfaces:

- the recipe input preview
- the linked-group assignment preview
- the split simulation preview

It confirms all of the following match:

- recipe input artifact
- candidate row count
- assignment count
- assignment vs simulation count
- split group counts
- row-level split counts
- largest group order

The important operator-facing result is that the split engine is now internally consistent. The handoff surface is ready for dry-run execution, and the preview surfaces agree on the linked-group behavior.

## What Still Blocks Fold Export

Fold export is still blocked because the explicit readiness gate is false:

- `fold_export_ready = false`
- `final_split_committed = false`
- `cv_folds_materialized = false`

The simulation also still misses the requested target counts:

- train: `1440` vs target `1322`
- val: `266` vs target `283`
- test: `183` vs target `284`

So the validator proves parity, but it does not prove a fold-export-ready or release-ready state.

## Grounded Examples

- `protein:P04637` is stably assigned to `train`, and the assignment and simulation surfaces agree on that hard group landing.
- `protein:P68871` is stably assigned to `val`, with its structure-overlap rows still attached to the same linked group.
- `protein:P69905` is stably assigned to `test`, with mixed protein, variant, and structure composition kept atomic.

Those examples show that the validator is validating the current linked-group behavior, not authorizing a fold export.

## Next Executable Split Step

The next executable split step should be a fold-prep artifact, but only after the `fold_export_ready` gate turns true. Until then, the truthful state is still dry-run parity without fold commitment.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim fold export readiness that the current validation explicitly denies.
