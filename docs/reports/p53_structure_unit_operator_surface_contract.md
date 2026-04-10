# Structure Unit Operator Surface Contract

This report-only contract defines how the new structure-unit artifact should appear in operator, runtime, and procurement surfaces without overstating readiness.

## Grounding

- Structure-unit summary library: `artifacts/status/structure_unit_summary_library.json`
- Structure-unit report: `docs/reports/structure_unit_summary_library.md`
- Structure-unit join mapping: `artifacts/status/p51_structure_motif_join_mapping.json`
- Summary-library v2 bridge: `artifacts/status/p29_summary_library_v2_bridge.json`
- Summary-library next slices: `artifacts/status/p29_summary_library_next_slices.json`
- Wave status with structure-unit operator slice: `artifacts/status/execution_wave_2_status.json`
- Summary record schema: `core/library/summary_record.py`
- Current coverage truth: `artifacts/status/source_coverage_matrix.json`
- Mirror truth: `artifacts/status/broad_mirror_progress.json`

## Operator Surface

The operator-facing view should show the artifact as a rebuildable feature-cache library, not as release-grade completeness.

Minimum fields to expose:

- `library_id`
- `schema_version`
- `source_manifest_id`
- `record_count`
- `index_guidance`
- `storage_guidance`
- `lazy_loading_guidance`
- `example_structure_id`
- `example_protein_refs`

Operator semantics:

- Show the current library id and source-manifest id exactly as stored.
- Show the record count as a small, truth-bearing count, not as a completeness claim.
- Show the structure-unit surface as `feature_cache`, with coordinate-heavy hydration deferred.
- Show that the operator surface is queued in `execution_wave_2_status.json` as `structure_unit_operator_surface`, but do not mark it release-grade.

## Runtime Surface

The runtime artifact should remain readable as a compact library export that can be rebuilt from current local evidence.

Minimum runtime fields to preserve:

- `record_type`
- `summary_id`
- `protein_ref`
- `structure_source`
- `structure_id`
- `variant_ref`
- `structure_kind`
- `model_id`
- `entity_id`
- `chain_id`
- `assembly_id`
- `residue_span_start`
- `residue_span_end`
- `resolution_or_confidence`
- `experimental_or_predicted`
- `mapping_status`
- `structure_relation_notes`
- `join_status`
- `join_reason`
- `context`
- `notes`

Runtime semantics:

- Keep experimental and predicted structures separate.
- Keep the structure-unit artifact in `feature_cache`.
- Keep `cross_references`, `motif_references`, `domain_references`, `pathway_references`, and `provenance_pointers` visible in context.
- Defer coordinate-heavy and full mapping payloads until selection.

## Procurement Surface

The procurement-facing view should describe what is already satisfied by current seed or registry evidence and what is still only conditional.

Ready-now evidence:

- `InterPro` from `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `PROSITE` from `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `Reactome` from `data/raw/protein_data_scope_seed/reactome`
- `CATH` from `data/raw/local_registry/20260330T222435Z/cath/manifest.json` and `data/raw/local_registry/20260330T222435Z/cath/inventory.json`
- `SCOP` from `data/raw/local_registry/20260330T222435Z/scope/manifest.json` and `data/raw/local_registry/20260330T222435Z/scope/inventory.json`

Conditional evidence:

- `ELM` is partial in the current registry, but pinned TSV exports are present at `data/raw/protein_data_scope_seed/elm/elm_classes.tsv` and `data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv`.

Future-only lanes:

- `mega_motif_base`
- `motivated_proteins`

Procurement semantics:

- Do not scrape the ready-now sources.
- Use the local registry and pinned seed files first.
- If ELM needs to participate in a future structure-linked view, use the pinned TSV exports before considering any scrape-based fallback.
- Keep future-only motif lanes out of the structure-unit operator surface until they have real payloads.

## Readiness Boundary

- This contract is operator-visible and runtime-readable.
- It is not a release-grade claim.
- The artifact should be described as `feature_cache`, rebuildable, and source-backed, not complete.

## Bottom Line

The structure-unit artifact should appear as a small, source-backed, deferred-hydration library object in operator/runtime surfaces, with procurement metadata limited to already-procured or registry-known sources and no freshness claims beyond that boundary.
