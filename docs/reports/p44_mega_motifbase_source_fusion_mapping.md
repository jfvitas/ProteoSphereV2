# MegaMotifBase Source Fusion Mapping

This note maps the currently acquired motif/domain sources into the summary library and shows how the future `MegaMotifBase` lane should fuse without inventing rows.

## Current Joinable Backbone

- `InterPro` is the canonical domain/family/site spine.
- `Pfam` is a supporting family view under `InterPro`.
- `PROSITE` is the canonical curated motif lane.
- `ELM` is the short-linear-motif lane with explicit partner-context sensitivity.

## Summary Library Surfaces

- `InterPro` can populate `SummaryRecordContext.domain_references` and `SummaryRecordContext.motif_references`.
- `Pfam` should populate `SummaryRecordContext.domain_references`.
- `PROSITE` should populate `SummaryRecordContext.motif_references`.
- `ELM` should populate `SummaryRecordContext.motif_references`.
- `MegaMotifBase`, once captured, should append support-only motif or domain references and never overwrite the canonical source label.

## Fields That Can Corroborate Each Other

- `UniProt accession` is the shared protein spine across all motif and domain rows.
- `span_start` and `span_end` corroborate the same site or domain only when both sides make the span explicit.
- `taxon` and `organism` corroborate species compatibility, but they do not replace accession or span.
- `source_record_id` and `evidence_refs` corroborate capture lineage and rebuildability, not biological identity.
- `reference_kind` corroborates whether the row belongs in `motif_references` or `domain_references`.

## Fields That Must Stay Source-Specific

- `InterPro`: `IPRxxxxx`, member-signature accession, integrated vs unintegrated provenance, clan/set ids.
- `Pfam`: `PFxxxxx`, `CLxxxxx`, member-database provenance, family/clan identity.
- `PROSITE`: `PDOCxxxxx`, `PSxxxxx`, `PRUxxxxx`, pattern/profile identity, documentation accessions.
- `ELM`: `ELME#####`, instance accession or row id, evidence count, partner-context hints.
- `MegaMotifBase`: page/query fingerprint, family/superfamily ids, and any source-native ids captured later.

## Merge Rules

1. Prefer `InterPro` for canonical family/domain labeling.
2. Use `Pfam` as supporting evidence beneath the `InterPro` spine.
3. Use `PROSITE` as the canonical site-level motif source.
4. Use `ELM` when instance coordinates and organism are explicit.
5. Add `MegaMotifBase` only as supplemental support once a real payload exists.
6. Never infer accession, span, organism, or release identity from another source.

## MegaMotifBase Intake Rule

`MegaMotifBase` remains capture pending. When it arrives, the row should map into the same `SummaryReference` shape as the other motif sources, but it should stay source-specific unless the accession and span are explicit and stable.

## Evidence Paths

- `artifacts/status/p43_mega_motifbase_capture_prep_checklist.json`
- `artifacts/status/p42_mega_motifbase_acquisition_contract.json`
- `artifacts/status/p41_motif_breadth_action_map.json`
- `artifacts/status/p40_motif_scope_completeness_view.json`
- `artifacts/status/p39_motif_gap_next_step_contract.json`
- `artifacts/status/p29_motif_fusion_plan.json`
- `artifacts/status/p29_motif_execution_slice.json`
- `artifacts/status/p31_local_source_facts.json`
- `artifacts/status/p31_online_source_facts.json`
- `core/library/summary_record.py`
- `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `data/raw/protein_data_scope_seed/pfam`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/elm/elm_classes.tsv`
- `data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv`

## Bottom Line

The motif library should join by `UniProt accession` plus explicit `span_start` and `span_end`, then keep the source-native identifiers separate so canonical sources stay canonical and `MegaMotifBase` can be added later without namespace drift.
