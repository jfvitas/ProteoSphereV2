# P65 Ligand Signature Stage 1 Contract

## Objective

Define the first safe ligand-related expansion for the lightweight leakage and split surfaces without enabling ligand joins, ligand-aware grouping, or split behavior changes.

This note is grounded in:

- [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [p64_ligand_placeholder_implementation_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_ligand_placeholder_implementation_order.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)

## Current Live Constraints

- `entity_signature_preview` has `1889` rows.
- `entity_split_candidate_preview` has `1889` rows.
- Both surfaces already carry `ligand_identity_group = null` and `binding_context_group = null`.
- The current ligand pressure is packet-gap only, not lightweight-ligand materialization.
- The live ligand gap set is exactly five accessions:
  - `P00387`
  - `P09105`
  - `Q2TAC2`
  - `Q9NZD4`
  - `Q9UCM0`

Those map directly to the current packet-gap refs:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`
- `ligand:Q9UCM0`

## Stage 1 Goal

Stage 1 should only surface ligand-related pressure as support metadata.

It should not:

- normalize ligand identities
- join ligand rows across sources
- create protein-ligand entity rows
- populate `ligand_identity_group`
- populate `binding_context_group`
- alter split keys or split buckets

## First Safe Fields

Add only these new support-only fields.

For entity-signature rows:

- `ligand_placeholder_status`
- `ligand_support_refs`
- `ligand_truth_note`

For split-candidate metadata:

- `metadata.ligand_placeholder_status`
- `metadata.ligand_support_refs`
- `metadata.ligand_truth_note`

These fields are additive only.

The existing reserved fields must remain present and null:

- `ligand_identity_group`
- `binding_context_group`
- `metadata.ligand_identity_group`
- `metadata.binding_context_group`

## Default Behavior

For every row without current ligand packet pressure:

- `ligand_placeholder_status = not_materialized`
- `ligand_support_refs = []`
- `ligand_truth_note = stage1_support_only:no_ligand_join:no_materialized_ligand_entity`

This applies to all current rows except the five protein rows named in the packet deficit dashboard.

## Targeted Stage 1 Support Rows

Only these rows should move to support-only ligand status in stage 1:

- `protein:P00387` with `ligand_support_refs = ["ligand:P00387"]`
- `protein:P09105` with `ligand_support_refs = ["ligand:P09105"]`
- `protein:Q2TAC2` with `ligand_support_refs = ["ligand:Q2TAC2"]`
- `protein:Q9NZD4` with `ligand_support_refs = ["ligand:Q9NZD4"]`
- `protein:Q9UCM0` with `ligand_support_refs = ["ligand:Q9UCM0"]`

For those five rows:

- `ligand_placeholder_status = candidate_support_only`
- `ligand_truth_note = support_only_packet_gap_ref:no_normalized_ligand_identity:no_binding_context`

No other current row should carry ligand support in stage 1.

## Strict No-Join Boundaries

Stage 1 must not perform any ligand join work.

Explicitly forbidden:

- deriving `ligand_identity_group` from `ligand:<accession>` refs
- deriving `binding_context_group` from packet-gap refs
- joining ChEMBL, BindingDB, ChEBI, PDB CCD, BioLiP, or canonical ligand rows into stage-1 signature fields
- inferring ligand equality from shared protein accession
- creating `protein_ligand` entity rows
- introducing ligand-aware buckets or validation classes
- changing `leakage_key`
- changing `linked_group_id`
- changing `bucket`
- changing `validation_class`
- changing `lane_depth`

## What Counts as Allowed Evidence

Allowed now:

- packet deficit refs in the form `ligand:<accession>`
- narrow support-only opaque evidence notes

Not allowed now:

- normalized ligand identifiers
- ligand equivalence classes
- binding-site classes
- residue-level binding-context grouping
- cross-source consensus for ligand identity

## Split Safety Requirements

The split surface must remain behaviorally identical in stage 1.

Required invariants:

- `entity_signature_preview` row count stays `1889`
- `entity_split_candidate_preview` row count stays `1889`
- all existing non-ligand grouping keys remain unchanged
- all split-assignment fields remain unchanged
- all ligand grouping fields remain null

The only permitted split-surface difference is additive metadata propagation of the three new support-only fields.

## Exit Criteria

Stage 1 is complete when:

- every row has explicit support-only ligand placeholder values
- exactly the five current ligand-gap proteins carry `candidate_support_only`
- every ligand grouping field is still null
- no split logic changes are introduced
- no new entity family is introduced

## Bottom Line

`P65` defines a narrow first step: propagate explicit ligand pressure for the five current packet-gap proteins without allowing any ligand join behavior. The stage is safe only if it remains additive, support-only, and strictly non-normalizing.
