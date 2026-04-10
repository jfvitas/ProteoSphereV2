# p66 Split Engine Execution Order

This report-only note defines the exact future execution order for the split path using the current preview chain.

## Order

1. Load and bind `entity_split_recipe_preview` to `entity_split_candidate_preview` through `p65_split_recipe_to_split_engine_mapping` and `p64_first_split_recipe_contract`.
2. Run the future split engine over the candidate preview as `entity_signature_row` atoms under `protein_spine_group` hard grouping.
3. Validate the resulting assignments against `entity_split_assignment_preview` and `entity_split_simulation_preview`.
4. Export fold outputs only if the assignment surface is validated and the fold gate is open.

## Truth Boundary

The current repo state supports the recipe preview, assignment preview, and simulation preview, but not a committed split. `entity_split_assignment_preview` is still a dry-run surface, and `ready_for_fold_export` is false, so fold export remains blocked today.

## What Must Hold

- Atomic unit: `entity_signature_row`.
- Hard group: `protein_spine_group`.
- Strict leakage guards: `exact_entity_group`, `sequence_equivalence_group`, `variant_delta_group`, `structure_chain_group`, and `structure_fold_group`.
- Reserved null axes: `ligand_identity_group` and `binding_context_group`.

## Grounding

- [`artifacts/status/entity_split_candidate_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [`artifacts/status/entity_split_recipe_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_recipe_preview.json)
- [`artifacts/status/entity_split_assignment_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_assignment_preview.json)
- [`artifacts/status/entity_split_simulation_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json)
- [`artifacts/status/p65_split_recipe_to_split_engine_mapping.json`](D:/documents/ProteoSphereV2/artifacts/status/p65_split_recipe_to_split_engine_mapping.json)
- [`artifacts/status/p64_first_split_recipe_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p64_first_split_recipe_contract.json)
