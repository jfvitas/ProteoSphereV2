# Motif Backbone Validation Contract

This contract defines the minimum validation checks for the step-1 motif backbone surfaces.

## Grounding

- Step-1 contract: `artifacts/status/p46_motif_backbone_step1_contract.json`
- Output spec: `artifacts/status/p47_motif_backbone_output_spec.json`
- Summary record schema: `core/library/summary_record.py`
- Current coverage truth: `artifacts/status/source_coverage_matrix.json`
- Mirror truth: `artifacts/status/broad_mirror_progress.json`
- InterPro seed: `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- PROSITE seed: `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- Pfam local-registry manifest: `data/raw/local_registry/20260330T222435Z/pfam/manifest.json`
- Pfam local-registry inventory: `data/raw/local_registry/20260330T222435Z/pfam/inventory.json`

## Minimum Validation Checks

### 1. Domain surface shape

- Every `domain_references` row must expose the exact `SummaryReference` fields from the output spec.
- `reference_kind` must be `domain_reference`.
- `namespace` and `source_name` must stay aligned with `InterPro` or `Pfam`.
- `identifier` must be source-native and non-empty.
- `span_start` and `span_end` must both be explicit.
- `evidence_refs` must not be empty.
- `join_status` must be `joined`.

### 2. Motif surface shape

- Every `motif_references` row must expose the exact `SummaryReference` fields from the output spec.
- `reference_kind` must be `motif_reference`.
- `namespace` and `source_name` must stay aligned with `PROSITE`.
- `identifier` must be the primary motif accession for the row.
- `span_start` and `span_end` must both be explicit.
- `evidence_refs` must not be empty.
- `join_status` must be `joined`.

### 3. Provenance pointer shape

- Every `provenance_pointers` row must expose the exact `SummaryProvenancePointer` fields from the output spec.
- `provenance_id` must be non-empty and derived, not guessed from biology.
- `source_name` must be one of `InterPro`, `Pfam`, or `PROSITE`.
- `source_record_id` must point at a pinned artifact or release-bound record id.
- `join_status` must be `joined`.

### 4. Evidence alignment

- InterPro validation must cite `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`.
- PROSITE validation must cite `data/raw/protein_data_scope_seed/prosite/prosite.dat`.
- Pfam validation must cite `data/raw/local_registry/20260330T222435Z/pfam/manifest.json` and `data/raw/local_registry/20260330T222435Z/pfam/inventory.json`.
- InterPro and PROSITE are expected to be complete in the mirror truth.
- Pfam is validated from local-registry visibility, not from broad-mirror presence.

### 5. Truth boundaries

- Do not accept ELM in this step.
- Do not accept MegaMotifBase in this step.
- Do not infer accession, span, or organism from another source.
- Do not collapse Pfam into InterPro when the source-native accession matters.
- Do not promote a family-only row to a site-level motif call.

## Pass Criteria

Validation passes only when all three surfaces are present, the field contracts match the output spec, and each surface is anchored to the correct source evidence.

## Bottom Line

This contract keeps the step-1 motif backbone honest: exact fields, explicit spans, pinned provenance, and no leakage from future lanes.
