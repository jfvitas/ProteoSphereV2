# Motif Backbone Output Spec

This spec makes the step-1 motif backbone contract concrete for the first emitted summary-library surfaces.

## Grounding

- Step-1 contract: `artifacts/status/p46_motif_backbone_step1_contract.json`
- Summary record schema: `core/library/summary_record.py`
- Current coverage truth: `artifacts/status/source_coverage_matrix.json`
- Mirror truth: `artifacts/status/broad_mirror_progress.json`
- InterPro seed: `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- PROSITE seed: `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- Pfam local-registry evidence: `data/raw/local_registry/20260330T222435Z/pfam/manifest.json`
- Pfam local-registry inventory: `data/raw/local_registry/20260330T222435Z/pfam/inventory.json`

## Emission Order

1. `ProteinSummaryRecord.context.domain_references`
2. `ProteinSummaryRecord.context.motif_references`
3. `ProteinSummaryRecord.context.provenance_pointers`

## Surface 1: `domain_references`

Record shape: `SummaryReference`

Top-level fields:

- `reference_kind`
- `namespace`
- `identifier`
- `label`
- `join_status`
- `source_name`
- `source_record_id`
- `span_start`
- `span_end`
- `evidence_refs`
- `notes`

Field mapping:

- `reference_kind`: constant `domain_reference`
- `namespace`: source family name, `InterPro` or `Pfam`
- `identifier`: source primary accession
- `label`: source display label
- `join_status`: constant `joined`
- `source_name`: source family name
- `source_record_id`: source-native row id or supporting accession
- `span_start`: explicit source span start
- `span_end`: explicit source span end
- `evidence_refs`: source artifact and release boundary pointers
- `notes`: source-specific provenance and support-status notes

Source mappings:

- `InterPro`
  - Identifier rule: use `IPR accession` as the primary identifier.
  - Source record id rule: keep `member-signature accession` or the InterPro entry id separate.
  - Required source fields: `IPR accession`, `member-signature accession`, `span_start`, `span_end`, `taxon`.
  - Notes carry: `integrated vs unintegrated provenance`, `clan/set ids`.
- `Pfam`
  - Identifier rule: use the primary Pfam family or clan accession from the row.
  - Source record id rule: keep the supporting family/clan accession separate from the normalized row id.
  - Required source fields: `PF accession`, `CL accession`, `span_start`, `span_end`.
  - Notes carry: `family/clan provenance`, `member-database view`, and the fact that Pfam is supporting evidence under InterPro.

## Surface 2: `motif_references`

Record shape: `SummaryReference`

Top-level fields:

- `reference_kind`
- `namespace`
- `identifier`
- `label`
- `join_status`
- `source_name`
- `source_record_id`
- `span_start`
- `span_end`
- `evidence_refs`
- `notes`

Field mapping:

- `reference_kind`: constant `motif_reference`
- `namespace`: source family name, `PROSITE`
- `identifier`: the row's primary motif accession
- `label`: documentation or motif label
- `join_status`: constant `joined`
- `source_name`: source family name
- `source_record_id`: supporting motif record id or accession set
- `span_start`: explicit source span start
- `span_end`: explicit source span end
- `evidence_refs`: source artifact and release boundary pointers
- `notes`: source-specific provenance and motif-type notes

Source mappings:

- `PROSITE`
  - Identifier rule: use the row's primary motif accession (`PS` or `PRU` as applicable).
  - Source record id rule: keep `PDOC accession` separate from the motif accession.
  - Required source fields: `PDOC accession`, `PS accession`, `PRU accession`, `span_start`, `span_end`.
  - Notes carry: `pattern/profile identity`, `documentation accession`, and the canonical motif-lane designation.

## Surface 3: `provenance_pointers`

Record shape: `SummaryProvenancePointer`

Top-level fields:

- `provenance_id`
- `source_name`
- `source_record_id`
- `release_version`
- `release_date`
- `acquired_at`
- `checksum`
- `join_status`
- `notes`

Field mapping:

- `provenance_id`: derived stable pointer id, not a biological source field
- `source_name`: source family name
- `source_record_id`: pinned artifact or release-bound record id
- `release_version`: source release version or local registry snapshot id
- `release_date`: source release date when available
- `acquired_at`: local acquisition timestamp
- `checksum`: manifest or inventory checksum when available
- `join_status`: constant `joined`
- `notes`: release-boundary and rebuildability notes

Source mappings:

- `InterPro`
  - Source record id: `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
  - Release metadata: current InterPro release metadata from the registry/mirror truth already captured in the step-1 contract.
- `Pfam`
  - Source record id: `data/raw/local_registry/20260330T222435Z/pfam/manifest.json`
  - Release metadata: current local-registry Pfam snapshot and inventory metadata.
- `PROSITE`
  - Source record id: `data/raw/protein_data_scope_seed/prosite/prosite.dat`
  - Release metadata: current PROSITE release metadata already reflected in the registry/mirror truth.

## Truth Boundaries

- Do not infer accession, span, or organism from another source.
- Do not add ELM in this step.
- Do not add MegaMotifBase in this step.
- Do not collapse Pfam into InterPro when the source-native accession is needed.
- Do not promote a family-only row to a site-level motif call.
- Do not emit release-grade breadth claims from this slice alone.

## Bottom Line

This output spec emits three surfaces in order, keeps the source-native accession and span explicit, and preserves release-bound provenance separately from the biological references.
