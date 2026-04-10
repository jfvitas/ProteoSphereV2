# P65 Split Recipe To Split Engine Mapping

This report-only contract defines the data contract needed to map the current split recipe previews into a future split engine execution interface.

## Preview Chain

The current preview chain is:

- [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [entity_split_recipe_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_recipe_preview.json)
- [entity_split_simulation_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_simulation_preview.json)
- [p64_first_split_recipe_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_first_split_recipe_contract.json)

The future engine should treat the candidate preview as input, the recipe preview as the executable config shape, and the simulation preview as the validation envelope.

## Contract

The first executable recipe remains:

- atomic unit: `entity_signature_row`
- hard grouping: `protein_spine_group`
- strict no-split guards:
  - `exact_entity_group`
  - `sequence_equivalence_group`
  - `variant_delta_group`
  - `structure_chain_group`
  - `structure_fold_group`
- soft axes only:
  - `taxon_group`
  - `motif_domain_architecture_group`
  - `pathway_context_group`
- reserved null axes:
  - `ligand_identity_group`
  - `binding_context_group`

## Data Contract

The future split engine must be able to read:

- `canonical_id`
- `entity_family`
- `accession`
- `protein_ref`
- `linked_group_id`
- `bucket`
- `validation_class`
- `lane_depth`
- the entity metadata split keys

It must also be able to validate:

- candidate row count
- linked group count
- assignment count
- rejected count
- split counts
- target counts
- family counts by split
- largest groups by split

## What The Engine Should Do

1. Cluster rows by `protein_spine_group`.
1. Refuse to split exact entity, exact sequence, variant, or structure-chain/fold groups.
1. Use taxon, motif/domain architecture, and pathway context only for balancing or diagnostics.
1. Preserve ligand-related axes as null.
1. Emit assignments and collision summaries, not mutations.

## Why The Mapping Is Needed

The recipe preview already describes the split behavior, and the simulation preview already shows how it behaves today. What is still missing is the contract that tells a future engine exactly which fields to ingest and which guards must fail closed.

## Exclusions

This contract does not:

- mutate the candidate preview
- rewrite protected latest surfaces
- introduce ligand or interaction entities
- weaken hard grouping
- commit a release split

## Boundary

This is report-only. It defines the future split engine data contract without editing code or changing any protected surfaces.

