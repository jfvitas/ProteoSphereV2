# P60 Lightweight Accession Coverage Surface Proposal

This is a report-only proposal for a compact operator-facing accession surface for the lightweight library.

## What The Operator Can See Today

The repo already exposes separate surfaces for proteins, variants, structures, and accession-level candidate bridges.

- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [structure_variant_candidate_map.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_variant_candidate_map.json)

The current gap is not another family total. It is a single accession-level readout that fuses these surfaces into one operator triage view.

## Proposal

Add one read-only surface:

- `lightweight_library_accession_coverage_surface`

Recommended future output path:

- [artifacts/status/lightweight_library_accession_coverage_surface.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_library_accession_coverage_surface.json)

## Minimal Row Shape

Each row should answer:

- accession
- protein name
- whether the protein summary is present
- how many variant rows exist
- how many structure-unit rows exist
- whether the accession is a candidate bridge
- the next operator action
- operator priority
- a short truth note

## Current Accessions To Surface

- `P68871` and `P69905` are the current integrated examples. They already have protein, variant, and structure coverage, and the candidate map records them as bridge candidates.
- `P04637` and `P31749` are variant-rich but still structure-missing.
- `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4` are protein-only current-slice accessions.
- `P69892` and `P02042` are the next credible globin extension targets from the current local evidence, but they are not yet materialized in the lightweight library.
- `P02100` stays blocked until explicit local variant evidence appears.

## Why This Is The Smallest Useful Step

This adds operator value without changing any protected latest surface and without inventing new biological joins.

It is smaller than adding a new materializer because it only fuses already-visible surfaces.
It is more useful than another count surface because it gives accession-level actionability.

## Boundary

This proposal is report-only. It does not edit code, mutate manifests, or weaken protected latest surfaces.

