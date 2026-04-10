# P64 First Split Recipe Contract

This report-only contract defines the first executable recipe configuration that should consume [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json).

## Preview Grounding

The current candidate preview already has the right shape for a first split recipe:

- `1889` rows
- `11` linked groups
- default atomic unit: `entity_signature_row`
- default hard group: `protein_spine_group`

That means the recipe can start from current preview rows instead of waiting on any new materialization.

## Recipe

The first executable recipe should be:

- input artifact: `entity_split_candidate_preview`
- input row type: `entity_signature_row`
- atomic unit: `entity_signature_row`
- hard grouping: `protein_spine_group`

Hard no-split guards:

- `exact_entity_group`
- `sequence_equivalence_group`
- `variant_delta_group`
- `structure_chain_group`
- `structure_fold_group`

Soft balance or diagnostic axes only:

- `taxon_group`
- `motif_domain_architecture_group`
- `pathway_context_group`

Reserved and null for now:

- `ligand_identity_group`
- `binding_context_group`

## How It Should Work

The recipe should:

1. load the candidate preview rows
1. cluster everything by `protein_spine_group`
1. refuse to split any exact entity, exact sequence, variant signature, or structure chain/fold group
1. use taxon, motif/domain architecture, and pathway context only for balance or diagnostics
1. emit a split plan or report, not a mutation

## Why This Is The First Executable Recipe

This is the first executable recipe because it can run on what already exists:

- current proteins
- current protein variants
- current structure units

It does not need ligand rows, interaction rows, or any new acquisition.

It also matches the current split-mapping contract, which treats `entity_signature_row` as the atomic unit and `protein_spine_group` as the default hard group.

## Grounded Examples

- `protein:P04637` is the largest unresolved spine cluster and should stay together before any soft balancing.
- `protein:P31749` is the smaller unresolved kinase cluster and should follow the same hard-spine rule.
- `protein:P68871` and `protein:P69905` are the integrated bridge examples and should remain grouped by their own spines.

## Exclusions

This recipe must not:

- consume ligand rows
- consume interaction rows
- widen into ligand identity or binding-context grouping
- rewrite protected latest surfaces
- mutate the candidate preview
- claim that `P04637` or `P31749` already has a structure unit

## Boundary

This is report-only. It does not edit code, and it only proposes the first executable configuration for the current candidate preview surface.

