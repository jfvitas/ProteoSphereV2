# Motif Pathway Enrichment Tranche

This report-only tranche condenses the current motif, pathway, and adjacent structural-class evidence into the lightweight library without touching implementation code.

## Grounding

- Motif backbone step-1 contract: `artifacts/status/p46_motif_backbone_step1_contract.json`
- Motif backbone output spec: `artifacts/status/p47_motif_backbone_output_spec.json`
- Motif backbone validation contract: `artifacts/status/p48_motif_backbone_validation_contract.json`
- Lightweight-library backlog: `artifacts/status/p49_lightweight_library_enrichment_backlog.json`
- Summary-library materializer slice: `artifacts/status/p29_summary_library_materializer_slice.json`
- Summary record schema: `core/library/summary_record.py`
- Current coverage truth: `artifacts/status/source_coverage_matrix.json`
- Mirror truth: `artifacts/status/broad_mirror_progress.json`

## Execution Tranche

### 1. Motif backbone condensation

Sources:

- `InterPro`
- `PROSITE`
- local-registry `Pfam`

Local evidence now:

- `InterPro` is present and complete.
- `PROSITE` is present and complete.
- `Pfam` is present in the local registry and can support domain evidence.

What this emits:

- `domain_references`
- `motif_references`
- `provenance_pointers`

What it unlocks:

- a span-aware motif/domain backbone in the lightweight library
- explicit source-native identifiers and provenance boundaries

What stays deferred:

- `ELM` promotion remains separate because the lane is still partial.
- `mega_motif_base` and `motivated_proteins` remain future-only.

Scrape policy:

- Do not scrape these sources.
- Use the current local registry and pinned seed/release files only.

### 2. Reactome pathway condensation

Sources:

- `Reactome`

Local evidence now:

- Reactome is present and complete in the current registry and mirror truth.
- The summary-library materializer slice already anticipates pathway references.

What this emits:

- `pathway_references`
- `provenance_pointers`

What it unlocks:

- compact pathway context alongside accession-first protein cards
- lazy expansion later if deeper pathway neighborhoods are needed

What stays deferred:

- full pathway neighborhood expansion
- any extra scrape-based pathway recovery

Scrape policy:

- Do not scrape Reactome for this tranche.

### 3. Structural-class condensation

Sources:

- `CATH`
- `SCOP`

Local evidence now:

- both are present in the local registry
- both are visible in the current coverage matrix

What this emits:

- `cross_references`
- `provenance_pointers`

What it unlocks:

- lightweight structural-class labels without inventing a new record type
- source-specific provenance for class lookups

What stays deferred:

- a dedicated protein-class surface is not present in the current summary record schema
- this lane should remain lightweight and source-specific

Scrape policy:

- Do not scrape CATH or SCOP.

## Deferred Lanes

- `ELM` is partial and should be promoted from a pinned export surface, not scraped, unless that export disappears.
- `mega_motif_base` remains missing and needs future procurement or capture-registry work.
- `motivated_proteins` remains missing and needs future procurement or capture-registry work.

## Bottom Line

The tranche is execution-ready from already-procured or registry-known sources: motif backbone first, Reactome second, structural-class support third. Scraping should stay out of these ranked steps.
