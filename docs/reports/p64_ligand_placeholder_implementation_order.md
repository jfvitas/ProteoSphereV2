# P64 Ligand Placeholder Implementation Order

Date: 2026-04-01
Artifact: `p64_ligand_placeholder_implementation_order`

## Objective

Define the safe implementation order for adding ligand identity and binding-context placeholder fields into the `entity signature` and `split-candidate` layers later.

This is a report-only sequencing note. It does not add code and does not claim that lightweight ligand entities are materialized now.

It is grounded in:

- [p61_minimum_leakage_signature_schema.md](/D:/documents/ProteoSphereV2/docs/reports/p61_minimum_leakage_signature_schema.md)
- [p63_ligand_signature_placeholder_schema.md](/D:/documents/ProteoSphereV2/docs/reports/p63_ligand_signature_placeholder_schema.md)
- [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [p00387_local_chembl_ligand_payload.json](/D:/documents/ProteoSphereV2/artifacts/status/p00387_local_chembl_ligand_payload.json)

## Current Ground Truth

Current live state is already close to the placeholder boundary:

- [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json) has `1889` rows and already includes:
  - `ligand_identity_group = null`
  - `binding_context_group = null`
- [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json) also carries those fields through as null metadata
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json) still says:
  - `ligands.included = false`
  - `ligands.record_count = 0`
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) still shows `4124` canonical ligands upstream
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) still shows `5` ligand-related packet gaps

That means the safe path is not to populate ligand groups yet. The safe path is to wire placeholder fields through in a way that:

- does not change current leakage grouping behavior
- does not change row counts
- does not imply ligand-family readiness

## Recommendation

Use a six-step additive order.

The rule is:

- placeholder fields may appear and flow through first
- ligand identity and binding-context values stay null until lightweight ligand entities are real

## Step 1: Freeze The Placeholder Contract

Goal:

- lock the field meanings before any implementation work starts

Use as the schema basis:

- [p61_minimum_leakage_signature_schema.md](/D:/documents/ProteoSphereV2/docs/reports/p61_minimum_leakage_signature_schema.md)
- [p63_ligand_signature_placeholder_schema.md](/D:/documents/ProteoSphereV2/docs/reports/p63_ligand_signature_placeholder_schema.md)

Required outcome:

- `ligand_identity_group` and `binding_context_group` stay reserved
- `ligand_placeholder_status`, `ligand_support_refs`, and related nullable support fields are defined before any row emission changes

Why first:

- avoids ad hoc field naming and inconsistent placeholder semantics

## Step 2: Expand `entity_signature_preview` Additively

Goal:

- add the ligand placeholder support fields to entity-signature rows without changing any existing grouping logic

Fields to add:

- `ligand_placeholder_status`
- `ligand_identity_namespace`
- `ligand_identity_source_id`
- `ligand_normalization_basis`
- `binding_context_components`
- `ligand_support_refs`
- `ligand_truth_note`

Required safety rules:

- keep `row_count = 1889`
- keep existing values for:
  - `exact_entity_group`
  - `protein_spine_group`
  - `sequence_equivalence_group`
  - `variant_delta_group`
  - `structure_chain_group`
  - `structure_fold_group`
- keep `ligand_identity_group = null`
- keep `binding_context_group = null`
- do not emit any new `protein_ligand` entity rows yet

Why second:

- the entity-signature layer is the source layer for split governance
- split-candidate changes should not happen before the entity-signature contract is stable

## Step 3: Propagate The Placeholder Fields Into `entity_split_candidate_preview`

Goal:

- keep split-candidate rows schema-aligned with entity-signature rows

Required outcome:

- add the same ligand placeholder support fields into the `metadata` block
- keep the current split grouping unchanged

Must remain unchanged:

- `row_count = 1889`
- `leakage_key`
- `linked_group_id`
- `bucket`
- `validation_class`
- `lane_depth`

Must stay null:

- `metadata.ligand_identity_group`
- `metadata.binding_context_group`

Why third:

- split candidates should be a projection of entity signatures
- they should not invent ligand grouping behavior independently

## Step 4: Allow Support-Only Ligand Evidence Pointers, But Not Ligand Groups

Goal:

- let the preview surfaces carry real evidence pointers without claiming ligand-family materialization

Allowed now:

- `ligand_placeholder_status = candidate_support_only`
- `ligand_support_refs` populated from current live evidence

Grounded current examples:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`
- `ligand:Q9UCM0`
- optional evidence pointer from [p00387_local_chembl_ligand_payload.json](/D:/documents/ProteoSphereV2/artifacts/status/p00387_local_chembl_ligand_payload.json), such as `CHEMBL:CHEMBL35888`

Not allowed yet:

- assigning `ligand_identity_group`
- assigning `binding_context_group`
- emitting any new split bucket based on ligand evidence

Why fourth:

- this is the narrowest useful improvement
- it surfaces current ligand-support pressure without changing split behavior

## Step 5: Add Validation Gates Before Any Non-Null Ligand Keys

Goal:

- make it impossible to accidentally promote support-only placeholders into real ligand grouping logic

Minimum gates:

- row counts remain stable when placeholder fields are introduced
- no current non-ligand split keys change
- no row gains a non-null ligand group while:
  - [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json) still has `ligands.included = false`
  - lightweight ligand entities are absent

Operator truth note must remain:

- ligand fields are reserved or support-only
- current split boundaries still come from proteins, variants, and structures only

Why fifth:

- otherwise placeholder wiring can silently become fake split behavior

## Step 6: Only Then Unlock Non-Null Ligand Groups

This step is explicitly future-only.

Required preconditions:

1. lightweight ligand entity rows exist in the bundle
2. ligand normalization rules are stable enough to assign deterministic ligand identities
3. a binding-context construction rule exists that can combine:
   - ligand identity
   - protein spine
   - optional variant delta
   - optional structure chain context

Only after those are true may the system populate:

- `ligand_identity_group`
- `binding_context_group`

And only then may split-candidate logic introduce ligand-aware grouping or bucket rules.

## What Must Not Happen Out Of Order

Do not:

- populate `ligand_identity_group` before lightweight ligand rows exist
- populate `binding_context_group` from packet-gap refs alone
- change `leakage_key` or `linked_group_id` in split candidates during placeholder rollout
- create `protein_ligand` entity rows as part of the placeholder-only phase
- treat canonical ligand count alone as permission to emit ligand groups

## Safe Ordering Summary

The safe order is:

1. freeze field meanings
2. add nullable placeholder fields to entity signatures
3. pass those nullable fields through to split candidates
4. allow support-only evidence refs
5. add validation gates
6. unlock non-null ligand groups only after lightweight ligand materialization

## Bottom Line

The safe implementation order is deliberately conservative.

Placeholder support should flow through the entity-signature and split-candidate layers first, while:

- row counts stay unchanged
- current non-ligand grouping stays unchanged
- ligand group fields remain null

Only after lightweight ligand entities are real should ligand identity or binding-context groups participate in leakage-safe splitting.
