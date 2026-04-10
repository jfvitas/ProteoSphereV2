# Motif Backbone Step 1 Contract

This contract covers step 1 only: materialize the already-present `InterPro` / `PROSITE` / local `Pfam` backbone into the summary library.

## Scope

- `InterPro` is the canonical domain/family/site spine.
- `PROSITE` is the canonical curated motif lane.
- `Pfam` is the local supporting family view under `InterPro`.
- `ELM` is out of scope for this step because it remains partial.
- `MegaMotifBase` is out of scope because it remains capture-pending.

## Required Inputs

- `artifacts/status/p45_motif_next_step_priority_map.json`
- `artifacts/status/p44_mega_motifbase_source_fusion_mapping.json`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`
- `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/pfam`
- `core/library/summary_record.py`

## Join Rules

### InterPro

- Join on `UniProt accession` plus explicit `span_start` and `span_end`.
- Keep `IPR` accession and member-signature accession as source-specific identifiers.
- Preserve integrated vs unintegrated provenance.
- Emit as `SummaryRecordContext.domain_references` first.

### Pfam

- Join on `UniProt accession` plus explicit `span_start` and `span_end`.
- Keep `PF` accession and `CL` accession as source-specific identifiers.
- Treat Pfam as supporting domain evidence under the InterPro spine.
- Do not promote Pfam to canonical family truth when InterPro already covers the same span.
- Emit as `SummaryRecordContext.domain_references` with supporting status.

### PROSITE

- Join on `UniProt accession` plus explicit `span_start` and `span_end`.
- Keep `PDOC`, `PS`, and `PRU` accessions as source-specific identifiers.
- Treat PROSITE as the canonical motif lane for this step.
- Emit as `SummaryRecordContext.motif_references`.

## Output Surfaces First

1. `ProteinSummaryRecord.context.domain_references`
2. `ProteinSummaryRecord.context.motif_references`
3. `ProteinSummaryRecord.context.provenance_pointers`

## Truth Boundaries

- Do not infer accession, span, or organism from another source.
- Do not use `ELM` in this step.
- Do not use `MegaMotifBase` in this step.
- Do not collapse Pfam into InterPro when the source-specific identifier is needed for auditability.
- Do not treat a family-only label as a site-level motif call.
- Do not claim release-grade motif breadth after this step alone.

## What This Unblocks

- A populated motif/domain backbone in the summary library from sources already present locally.
- Canonical domain references from InterPro.
- Canonical motif references from PROSITE.
- Supporting family projections from local Pfam visibility.

## What Stays Blocked

- ELM promotion and instance-catalog join.
- MegaMotifBase capture and pinning.
- Motivated Proteins future-only intake.

## Evidence Paths

- `artifacts/status/p45_motif_next_step_priority_map.json`
- `artifacts/status/p44_mega_motifbase_source_fusion_mapping.json`
- `artifacts/status/p43_mega_motifbase_capture_prep_checklist.json`
- `artifacts/status/p42_mega_motifbase_acquisition_contract.json`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`
- `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/pfam`

## Bottom Line

Step 1 is a conservative materialization pass: use the real local backbone, join only on explicit accession and span, and emit the domain and motif references before anything else.
