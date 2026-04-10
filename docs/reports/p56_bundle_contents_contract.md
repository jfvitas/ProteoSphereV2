# P56 Bundle Contents Contract

This report-only contract defines what the lightweight bundle contents document should say for the current library slice.

## Purpose

The `proteosphere-lite.contents.md` companion should explain the bundle at a glance without overstating completeness. It should describe:

- which current lightweight surfaces are actually included
- which families are declared but not yet populated
- which source lanes are truth-bearing vs conditional
- which payloads remain out of scope for the first bundle

## Current Bundle Surfaces

The bundle contents document should treat these as the current executable surfaces:

- `proteins`
- `structures`
- `motif_annotations`
- `pathway_annotations`
- `provenance_records`

These surfaces are grounded in:

- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [artifacts/status/structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [artifacts/status/p51_structure_motif_join_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p51_structure_motif_join_mapping.json)
- [artifacts/status/p50_motif_pathway_enrichment_tranche.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_motif_pathway_enrichment_tranche.json)
- [artifacts/status/p55_bundle_field_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p55_bundle_field_mapping.json)

## Declared But Not Yet Populated

The bundle contents document should explicitly mark these as future families or empty placeholders:

- `protein_variants`
- `ligands`
- `interactions`
- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `leakage_groups`
- `dictionaries`

These families are part of the planned bundle layout, but they are not yet populated in the current live bundle slice.

## Source Truth Classes

The bundle contents document should distinguish the following source classes:

- `truth-bearing now`: `UniProt`, `InterPro`, `PROSITE`, `Reactome`, `Pfam`, `CATH`, `SCOP`, and `SIFTS` where already represented in the live summaries
- `conditional`: `ELM`, because it is only partially present in the local registry and should remain pinned-export first
- `future-only`: `mega_motif_base` and `motivated_proteins`

It should not imply that conditional or future-only lanes are part of the current bundle payload.

## Required Sections In The Contents Doc

The contents document should include these sections in order:

1. Bundle identity
1. Release assets
1. Included surfaces
1. Declared-empty surfaces
1. Source truth and gating
1. Excluded payload families
1. Truth boundaries

Each section should stay concise and should avoid implementation detail that belongs in exporter code.

## Exact Wording Constraints

The contents document should:

- say that record counts are current counts, not completeness claims
- say that `ELM` is conditional and not scrape-first
- say that `mega_motif_base` and `motivated_proteins` remain outside the live bundle
- say that `protein_variants` is declared for schema v2 but not yet populated
- say that `structures` currently come from the structure-unit feature-cache slice, not from coordinate-heavy payloads

## Exclusions

The contents document should not include:

- raw source mirrors
- coordinate-heavy structure payloads
- full motif instance tables
- search-result scrape payloads
- heavy interaction or ligand dumps
- invented release checksums or completeness percentages

## Bottom Line

The bundle contents document is a human-readable inventory of what the lightweight bundle currently contains and what it only reserves for later. It should stay aligned with the report-only field mapping and the current live summary artifacts.
