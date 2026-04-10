# Lightweight Library Enrichment Backlog

This backlog ranks the next condense-first steps for the lightweight library across motif, pathway, and structural-class coverage.

## Grounding

- Motif backbone step-1 contract: `artifacts/status/p46_motif_backbone_step1_contract.json`
- Motif backbone output spec: `artifacts/status/p47_motif_backbone_output_spec.json`
- Motif backbone validation contract: `artifacts/status/p48_motif_backbone_validation_contract.json`
- Summary-library materializer slice: `artifacts/status/p29_summary_library_materializer_slice.json`
- Summary record schema: `core/library/summary_record.py`
- Current coverage truth: `artifacts/status/source_coverage_matrix.json`
- Mirror truth: `artifacts/status/broad_mirror_progress.json`

## Ranked Next Actions

### 1. Materialize the motif backbone into the lightweight library

Sources:

- `InterPro`
- `PROSITE`
- local-registry `Pfam`

What local evidence already supports:

- `InterPro` is complete in the registry and complete in the mirror truth.
- `PROSITE` is complete in the registry and complete in the mirror truth.
- `Pfam` is present in the local registry and can be used as supporting domain evidence.

What this unlocks:

- `domain_references`
- `motif_references`
- `provenance_pointers`
- span-aware motif/domain joins with explicit source identity

What stays deferred:

- `ELM` promotion remains separate because the current lane is still partial.
- `mega_motif_base` and `motivated_proteins` remain future-only capture lanes.

Scrape policy:

- Do not scrape these sources.
- Use the current local registry and pinned seed/release files only.

### 2. Condense Reactome pathway annotations into the lightweight library

Sources:

- `Reactome`

What local evidence already supports:

- Reactome is complete in the registry and complete in the mirror truth.
- The existing materializer slice already expects `pathway_references`.

What this unlocks:

- `pathway_references`
- `provenance_pointers`
- pathway context alongside accession-first protein cards

What stays deferred:

- Deeper event neighborhoods and full pathway expansion can stay lazy.
- No new pathway scrape is needed for the lightweight condensation layer.

Scrape policy:

- Do not scrape Reactome for this backlog item.
- Use the local seed and registry truth already present in the repo.

### 3. Condense CATH and SCOP into the lightweight library

Sources:

- `CATH`
- `SCOP`

What local evidence already supports:

- Both are present in the local registry.
- Both are visible as structural-classification coverage in the current matrix.
- Their registry evidence exists without needing a new procurement pass.

What this unlocks:

- lightweight classification references for structural class labels
- source-specific provenance for classification lookups
- a compact bridge into the library without turning class labels into motif/domain claims

What stays deferred:

- A dedicated protein-class surface is not present in the current summary record schema.
- The first pass should stay lightweight and source-specific rather than inventing a new record type.

Scrape policy:

- Do not scrape CATH or SCOP.
- Use the local-registry manifests and inventories only.

## Deferred Lanes Not Ranked Here

- `ELM` remains partial and should only be promoted from a pinned export surface.
- `mega_motif_base` remains missing and needs future procurement or capture-registry work.
- `motivated_proteins` remains missing and needs future procurement or capture-registry work.

## Bottom Line

The fastest honest path is to condense what is already locally evidenced: motif/domain first, pathway second, structural classification third. Scraping should stay out of those lanes unless a future-only source has no pinned export at all.
