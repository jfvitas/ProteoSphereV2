# MegaMotifBase Capture Prep Checklist

This checklist is the concrete handoff from the acquisition contract to a row-level capture shape. It is intentionally implementation-oriented, but it does not claim a payload has been captured yet.

## Capture Surface

Use the public MegaMotifBase surfaces already named in the contract:

- `https://caps.ncbs.res.in/MegaMotifbase/`
- `http://caps.ncbs.res.in/MegaMotifbase/download.html`
- `http://caps.ncbs.res.in/MegaMotifbase/search.html`
- `http://caps.ncbs.res.in/MegaMotifbase/famlist.html`
- `http://caps.ncbs.res.in/MegaMotifbase/sflist.html`

The local registry still shows the lane as missing, so the capture-prep shape must stay scrape-only until a real payload exists.

## Library Mapping

The summary library receives MegaMotifBase evidence as `SummaryReference` rows attached to `ProteinSummaryRecord.context.motif_references` or `ProteinSummaryRecord.context.domain_references`.

### Motif-level rows

- Map to `motif_references`.
- Set `reference_kind = "motif"`.
- Set `namespace = "mega_motif_base"`.
- Set `identifier` to the source-native motif id, or the page/query id if the page is the only stable handle.
- Set `label` only from a label explicitly shown by the source.
- Set `source_name = "mega_motif_base"`.
- Set `source_record_id` to the exact row id, page id, or captured-page fingerprint.
- Set `span_start` and `span_end` only when the source gives explicit residue coordinates.
- Put source capture URLs, family/superfamily ids, organism, and capture notes in `notes` or provenance metadata.

### Family or superfamily rows

- Map to `domain_references` when the source row is really family-level or superfamily-level support.
- Set `reference_kind = "domain"`.
- Set `namespace = "mega_motif_base"`.
- Set `identifier` to the family or superfamily id shown by the source.
- Keep span fields only if the source row explicitly gives a stable span.
- Do not pretend a family table row is a site-level motif call.

## Required Fields

Each captured row must have:

- `source_native_id`
- `source_record_id`
- `source_page_url` or a stable query fingerprint
- `uniprot_accession` when the row is joinable
- `organism` when the row is joinable
- `span_start` and `span_end` when the row is joinable as a site-level motif
- `evidence_refs`
- `release_version` or a stable page fingerprint

## Never Infer

Do not infer any of the following:

- UniProt accession
- residue span
- organism
- release version
- source-native id
- page fingerprint
- family or superfamily membership
- provenance or checksum values

If any of those are missing, the row stays capture-only or deferred.

## Merge Rules

- `InterPro` stays the canonical domain/family/site backbone.
- `PROSITE` stays the canonical curated motif/profile source.
- `Pfam` stays a supporting family view under `InterPro`.
- `ELM` stays the short-linear-motif and partner-context lane.
- `MegaMotifBase` only adds supplementary evidence.
- If a MegaMotifBase hit matches an existing `protein_ref` and span, append it as an additional `SummaryReference`, do not replace the canonical label.
- If a MegaMotifBase family row overlaps a `PROSITE`, `ELM`, or `InterPro` row, keep the source identity separate and let the higher-confidence source remain canonical.

## Capture Checklist

1. Capture the exact page URL or export file URL.
2. Record the retrieval timestamp and checksum or page fingerprint.
3. Extract the source-native motif, family, or superfamily identifier.
4. Extract the UniProt accession only if the source explicitly gives it.
5. Extract residue span only if the source explicitly gives it.
6. Extract organism only if the source explicitly gives it.
7. Route motif hits to `motif_references`.
8. Route family or superfamily support to `domain_references`.
9. Keep raw capture rows separate from normalized summary rows.
10. Leave the row deferred if the span, accession, or organism is absent.

## Evidence Paths

- `artifacts/status/p42_mega_motifbase_acquisition_contract.json`
- `artifacts/status/p41_motif_breadth_action_map.json`
- `artifacts/status/p40_motif_scope_completeness_view.json`
- `artifacts/status/p39_motif_gap_next_step_contract.json`
- `artifacts/status/p29_motif_fusion_plan.json`
- `artifacts/status/p29_motif_execution_slice.json`
- `core/library/summary_record.py`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`

## Bottom Line

The capture-prep shape is simple: preserve source-native identity, require explicit accession/span/organism before joining, and keep MegaMotifBase as supplemental evidence unless and until the source surface becomes a stable export.
