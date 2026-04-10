# P55 Variant Publication Validation Contract

Report-only validation contract for the first executable `protein_variant` publication surface.

## Truth Boundary

- This contract is report-only.
- It does not authorize publication execution.
- It does not rewrite protected latest surfaces.
- It requires the dashboard and inventory surfaces to stay truth-bearing, additive, and accession-scoped.

## Grounding

- Protein-variant materializer contract: `artifacts/status/p53_protein_variant_materializer_contract.json`
- Protein-variant evidence hunt: `artifacts/status/p54_variant_evidence_hunt.json`
- Protected surface validation: `artifacts/status/p51_protected_surface_validation_contract.json`
- Structure-unit publication pattern: `artifacts/status/p53_structure_unit_publication_validation_contract.json`
- Structure-unit operator surface pattern: `artifacts/status/p53_structure_unit_operator_surface_contract.json`
- Current summary-library inventory: `artifacts/status/summary_library_inventory.json`
- Execution-wave transition notes: `artifacts/status/execution_wave_2_status.json`
- V2 bridge contract: `artifacts/status/p29_summary_library_v2_bridge.json`
- V2 materialization contract: `artifacts/status/p51_v2_source_fusion_materialization_contract.json`

## First Executable Slice

The first truthful protein-variant slice stays narrow:

- Supported accessions: `P04637`, `P31749`
- Supported variant kinds: `natural_variant`, `point_mutation`, `small_indel`, `isoform_variant`
- Unsupported scope: construct-only records without explicit local construct labels, broad accession coverage across the full IntAct mutation export, and name-only variant inference

The contract keeps construct support deferred unless later evidence provides explicit construct lineage.

## Current Inventory Baseline

The current inventory remains protein-only:

- `summary-library-inventory`
- `summary-library:protein-materialized:v1`
- `record_count`: `11`
- `record_type_counts`: `protein=11`, `protein_variant=0`, `protein_protein=0`, `protein_ligand=0`, `structure_unit=0`
- `join_status_counts`: `joined=11`
- `storage_tier_counts`: `feature_cache=11`

That baseline is important because the new protein-variant surface must stay additive rather than rewriting the existing protein materialization.

## Operator Dashboard Requirements

The dashboard-facing publication surface should look like a compact feature-cache artifact, not a completeness claim.

Minimum fields to expose:

- `library_id`
- `schema_version`
- `source_manifest_id`
- `record_count`
- `record_type_counts`
- `join_status_counts`
- `storage_tier_counts`
- `supported_accessions`
- `supported_variant_kinds`
- `unsupported_scope`
- `publication_intent`
- `release_grade_ready`
- `truth_boundary`

Truth rules:

- Show the library id and source manifest id exactly as stored.
- Show the record count as a truth-bearing count, not as completeness.
- Show protein_variant as additive to the existing protein materialization surface.
- Keep `release_grade_ready` false until a separate release contract says otherwise.
- Show only the supported accessions and supported variant kinds from the first executable slice.

## Inventory Requirements

The inventory surface should become the row-level truth anchor for publication.

Minimum inventory fields:

- `inventory_id`
- `library_id`
- `schema_version`
- `source_manifest_id`
- `record_count`
- `record_type_counts`
- `join_status_counts`
- `storage_tier_counts`
- `protein_variant_count`
- `accession_coverage`
- `variant_kind_counts`
- `partial_record_count`
- `truth_boundary`

Row-level fields to preserve:

- `record_type`
- `summary_id`
- `protein_ref`
- `variant_signature`
- `variant_kind`
- `is_partial`
- `parent_protein_ref`
- `mutation_list`
- `sequence_delta_signature`
- `construct_type`
- `variant_relation_notes`
- `join_status`
- `join_reason`
- `context`
- `notes`

Truth rules:

- Keep protein_variant separate from the base protein record rather than collapsing it into protein.
- Keep partial rows partial when accession lineage, mutation list, sequence delta, or construct evidence is incomplete.
- Show only the evidence-backed accessions for the first slice until new support is procured.
- Do not mark the inventory release-grade-ready merely because the first slice exists.

## Publication Validation

Before any publication surface lands, require all of the following:

- publication writes only to a versioned or run-scoped output path, never to a protected latest filename
- source_manifest_id is pinned and preserved in the published artifact, dashboard, and inventory
- protein_variant publication is additive and does not rewrite existing protein, protein_protein, protein_ligand, or structure_unit records
- operator dashboard and inventory agree on record_count, record_type_counts, accession coverage, and partiality
- supported accessions stay limited to `P04637` and `P31749` until new evidence extends the first executable slice
- construct-only and name-only claims remain deferred or partial
- publication outputs stay separate from canonical, bootstrap, and local-registry latest surfaces

Publication targets:

- `artifacts/status/protein_variant_summary_library.json`
- `docs/reports/protein_variant_summary_library.md`
- `artifacts/status/summary_library_inventory.json`

## Post-Action Validation

After publication, verify the inventory and protected surfaces still tell the same truth.

Publication checks:

- parse `data/canonical/LATEST.json` successfully
- parse `data/packages/LATEST.json` successfully
- parse `data/packages/LATEST.partial.json` successfully
- parse `data/raw/bootstrap_runs/LATEST.json` successfully
- parse `data/raw/local_registry_runs/LATEST.json` successfully
- confirm no protected-surface file content changed as a side effect of publication
- confirm any new protein_variant publication artifact lives outside protected latest paths
- confirm the operator dashboard and inventory surface agree on `source_manifest_id`, `record_count`, and supported accessions

Inventory checks:

- confirm the inventory exposes `protein_variant` as a separate record type
- confirm `protein_variant` count is greater than zero once materialization lands
- confirm the base protein record counts remain unchanged by the new publication surface
- confirm `join_status_counts` and `storage_tier_counts` remain present
- confirm partial rows remain partial rather than being coerced into a complete claim
- confirm the inventory still limits the first slice to the current supported accessions until new evidence is procured

## Non-Goals

- No code edits
- No publication execution
- No cleanup execution
- No canonical latest rewrites
- No package latest rewrites
- No bootstrap or local registry latest rewrites
- No construct-only or name-only inference
- No release-grade claim

## Bottom Line

The first executable protein_variant publication surface should appear as a feature-cache artifact that is narrow, accession-scoped, and additive. The operator dashboard should show the slice as truth-bearing but not complete, and the inventory should expose row-level evidence without collapsing protein_variant back into the base protein record.
