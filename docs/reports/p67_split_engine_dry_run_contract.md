# p67 Split Engine Dry-Run Contract

This report-only contract defines the first safe dry-run executable surface after the current previews.

## Dry-Run Surface

The executable target is the assignment-preview-shaped dry-run surface: bind `entity_split_recipe_preview` to `entity_split_candidate_preview`, run the future split engine in dry-run mode, materialize assignment rows, validate against `entity_split_simulation_preview`, and stop before fold export.

## What Makes It Safe

- Atomic unit: `entity_signature_row`.
- Hard group: `protein_spine_group`.
- Strict no-split guards: `exact_entity_group`, `sequence_equivalence_group`, `variant_delta_group`, `structure_chain_group`, and `structure_fold_group`.
- Reserved null axes: `ligand_identity_group` and `binding_context_group`.
- Allowed families: `protein`, `protein_variant`, and `structure_unit`.

## Current Truth

The repo already has complete recipe, assignment, and simulation preview surfaces. `entity_split_assignment_preview` is still a dry-run surface and `ready_for_fold_export` is false, so the contract stops at validation and does not authorize fold export.

## Grounding

- [`artifacts/status/p66_split_engine_execution_order.json`](D:/documents/ProteoSphereV2/artifacts/status/p66_split_engine_execution_order.json)
- [`artifacts/status/entity_split_candidate_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [`artifacts/status/entity_split_recipe_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_recipe_preview.json)
- [`artifacts/status/entity_split_assignment_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_assignment_preview.json)
- [`artifacts/status/entity_split_simulation_preview.json`](D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json)
- [`artifacts/status/p65_split_recipe_to_split_engine_mapping.json`](D:/documents/ProteoSphereV2/artifacts/status/p65_split_recipe_to_split_engine_mapping.json)
- [`artifacts/status/p64_first_split_recipe_contract.json`](D:/documents/ProteoSphereV2/artifacts/status/p64_first_split_recipe_contract.json)

