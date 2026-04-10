# P63 Ligand Signature Placeholder Schema

Date: 2026-04-01
Artifact: `p63_ligand_signature_placeholder_schema`

## Objective

Propose the minimum placeholder schema needed to add `ligand identity` and `binding-context` groups into the future entity-signature layer, without claiming that lightweight ligand entities are materialized now.

This is a report-only note. It does not add code and does not change any current bundle or signature artifact.

It is grounded in:

- [p61_minimum_leakage_signature_schema.md](/D:/documents/ProteoSphereV2/docs/reports/p61_minimum_leakage_signature_schema.md)
- [leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [p00387_local_chembl_ligand_payload.json](/D:/documents/ProteoSphereV2/artifacts/status/p00387_local_chembl_ligand_payload.json)

## Current Truth Boundary

Current live status is:

- the bundle manifest declares the `ligands` family, but it is not materialized in the lightweight bundle
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json) shows:
  - `ligands.included = false`
  - `ligands.record_count = 0`
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) still shows `4124` canonical ligands upstream
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) shows `5` current ligand-related packet gaps:
  - `ligand:P00387`
  - `ligand:P09105`
  - `ligand:Q2TAC2`
  - `ligand:Q9NZD4`
  - `ligand:Q9UCM0`

So the right move is not to pretend ligand signatures exist now. The right move is to reserve the smallest future-ready fields so the entity-signature schema does not need another redesign when lightweight ligand rows arrive.

## Recommendation

The minimum placeholder should be additive to the `entity_signature_rows` contract proposed in `P61`.

Add these ligand-related fields now:

- `ligand_placeholder_status`
- `ligand_identity_group`
- `ligand_identity_namespace`
- `ligand_identity_source_id`
- `ligand_normalization_basis`
- `binding_context_group`
- `binding_context_components`
- `ligand_support_refs`
- `ligand_truth_note`

All of them may be `null` for current protein, variant, and structure rows.

## Why This Is The Minimum Placeholder

These fields are enough to support later ligand-aware splitting because they separate two different concerns:

- `ligand_identity_group`
  - are these chemically the same ligand identity?
- `binding_context_group`
  - is this effectively the same protein-ligand example context for split safety?

That is the smallest future-ready distinction that matters.

Anything beyond this would overreach into not-yet-materialized ligand chemistry and structure detail.

## Proposed Field Contract

### `ligand_placeholder_status`

Purpose:

- explicitly distinguish `not materialized yet` from `future candidate visible`

Allowed values:

- `not_materialized`
- `candidate_support_only`
- `future_ready_reserved`

Current truthful default:

- `not_materialized`

### `ligand_identity_group`

Purpose:

- future normalized ligand identity split key

Current truthful default:

- `null`

Future meaning:

- all rows that should be treated as the same ligand identity should share this key

Example future forms:

- `ligand:CHEMBL:CHEMBL35888`
- `ligand:normalized:<stable_hash>`

### `ligand_identity_namespace`

Purpose:

- preserve which namespace the current future-ready ligand key came from

Current truthful default:

- `null`

Future examples:

- `CHEMBL`
- `BindingDB`
- `ChEBI`
- `PDB_CCD`

### `ligand_identity_source_id`

Purpose:

- preserve the raw source identifier used to seed the ligand identity key

Current truthful default:

- `null`

Future examples:

- `CHEMBL35888`

### `ligand_normalization_basis`

Purpose:

- record what kind of evidence was used to normalize the ligand key

Allowed future values:

- `namespace_id`
- `canonical_smiles`
- `inchikey`
- `cross_source_merged`
- `unresolved`

Current truthful default:

- `null`

### `binding_context_group`

Purpose:

- future split key that combines ligand identity with its biological context

Current truthful default:

- `null`

Future meaning:

- rows that share the same effective binding example should collide here even if the entity type differs

Example future forms:

- `bindctx:protein:P00387|ligand:CHEMBL:CHEMBL35888`
- `bindctx:protein:P68871|structure_chain:PDB:4HHB:B:2-147|ligand:<normalized_key>`

### `binding_context_components`

Purpose:

- make the binding-context construction explicit and debuggable

Recommended nested fields:

- `protein_spine_group`
- `variant_delta_group`
- `structure_chain_group`
- `ligand_identity_group`

Current truthful default:

- all component fields null except whichever non-ligand groups already exist on the row

### `ligand_support_refs`

Purpose:

- preserve narrow evidence pointers before lightweight ligand rows exist

Current truthful use:

- can point to current packet-fix or local-payload references without claiming bundle inclusion

Examples from current live artifacts:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`
- `ligand:Q9UCM0`

### `ligand_truth_note`

Purpose:

- make the null or placeholder status explicit so users do not interpret reserved fields as materialized ligand coverage

Current truthful default:

- `Ligand fields are reserved only. Lightweight ligand entities are not materialized in the current bundle.`

## How This Fits Into `P61`

`P61` already proposes:

- `ligand_identity_group`
- `binding_context_group`

`P63` is the minimum expansion needed to make those two fields operationally safe:

- add explicit placeholder status
- add explicit identity namespace/source ID
- add explicit normalization basis
- add explicit support refs and truth note
- add explicit binding-context components

That is enough to avoid ambiguity later.

## Current Grounded Example: `P00387`

Current live facts:

- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json) has `ligand:P00387` as an unresolved packet source ref
- [p00387_local_chembl_ligand_payload.json](/D:/documents/ProteoSphereV2/artifacts/status/p00387_local_chembl_ligand_payload.json) shows real ligand-support evidence, including:
  - `ligand_chembl_id`
  - `canonical_smiles`
  - `molregno`
  - `target_chembl_id`

Minimum truthful placeholder interpretation today:

- `ligand_placeholder_status = candidate_support_only`
- `ligand_identity_group = null`
- `ligand_identity_namespace = null`
- `ligand_identity_source_id = null`
- `ligand_normalization_basis = null`
- `binding_context_group = null`
- `ligand_support_refs = ["ligand:P00387", "CHEMBL:CHEMBL35888"]`

Why:

- there is real support evidence
- there is not yet a materialized lightweight ligand entity
- there is not yet a normalized ligand identity contract in the bundle

## Current Grounded Example: Protein Rows Without Ligand Support

For rows like:

- `P02042`
- `P02100`
- `P69892`

the truthful placeholder state today is:

- `ligand_placeholder_status = not_materialized`
- `ligand_identity_group = null`
- `binding_context_group = null`
- `ligand_support_refs = []`

That is important because it separates:

- `no current ligand support seen`
from
- `support exists but no ligand entity is materialized yet`

## Future Ligand-Ready Promotion Rule

These placeholder fields should remain placeholders until both are true:

1. a lightweight ligand entity family exists in the bundle
2. ligand normalization rules are stable enough to assign `ligand_identity_group` deterministically

Until then:

- `ligand_identity_group` stays null
- `binding_context_group` stays null
- `ligand_support_refs` may still carry narrow live evidence pointers

## Explicit Exclusions

This placeholder schema should not yet encode:

- ligand class hierarchy
- scaffold buckets
- physicochemical bins
- binding affinity buckets
- ligand-ligand similarity hashes
- pose-level or coordinate-level context

Those are downstream design questions. The placeholder only needs to reserve identity and context split fields safely.

## Bottom Line

The minimum placeholder needed now is not a ligand signature system.

It is a small nullable field set inside the future entity-signature layer that:

- reserves `ligand_identity_group`
- reserves `binding_context_group`
- records placeholder status and narrow support refs
- stays null until lightweight ligand entities are actually materialized

That is the smallest honest way to make the entity-signature schema future ligand-ready without overclaiming current ligand coverage.
