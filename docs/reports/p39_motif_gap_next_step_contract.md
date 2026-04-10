# P39 Motif Gap Next-Step Contract

- Generated at: `2026-03-31T14:34:55.5279199-05:00`
- Scope: execution plan for the remaining true external motif gaps only
- Remaining external gaps: `mega_motif_base`, `motivated_proteins`
- Evidence paths:
  - [artifacts/status/source_coverage_matrix.json](../../artifacts/status/source_coverage_matrix.json)
  - [artifacts/status/broad_mirror_progress.json](../../artifacts/status/broad_mirror_progress.json)
  - [artifacts/status/p38_motif_gap_resolution_status.json](../../artifacts/status/p38_motif_gap_resolution_status.json)
  - [data/raw/local_registry/20260323T003221Z/import_manifest.json](../../data/raw/local_registry/20260323T003221Z/import_manifest.json)
  - [data/raw/local_registry/20260323T003221Z/mega_motif_base/inventory.json](../../data/raw/local_registry/20260323T003221Z/mega_motif_base/inventory.json)
  - [data/raw/local_registry/20260323T003221Z/motivated_proteins/inventory.json](../../data/raw/local_registry/20260323T003221Z/motivated_proteins/inventory.json)
  - [data/raw/protein_data_scope_seed/prosite/prosite.dat](../../data/raw/protein_data_scope_seed/prosite/prosite.dat)
  - [data/raw/protein_data_scope_seed/interpro/interpro.xml.gz](../../data/raw/protein_data_scope_seed/interpro/interpro.xml.gz)
  - [data/raw/protein_data_scope_seed/elm/elm_classes.tsv](../../data/raw/protein_data_scope_seed/elm/elm_classes.tsv)
  - [data/raw/protein_data_scope_seed/pfam](../../data/raw/protein_data_scope_seed/pfam)

## What We Already Have Locally

- `PROSITE` is present locally and complete in the broad mirror.
- `InterPro` is present locally and complete in the broad mirror.
- `Pfam` is present locally as a supporting family view.
- `ELM` is already imported locally, and the broad mirror has the live TSV pair even though the local registry still marks it partial/degraded.

## Why The Two Gaps Are Still Real

- `mega_motif_base` has only a missing local-registry stub: no present roots, no imported seed files, and no broad-mirror presence.
- `motivated_proteins` has only a missing local-registry stub: no present roots, no imported seed files, and no broad-mirror presence.
- Those stubs imply expected shapes, but they do not satisfy the source contract today.

## Substitute Families

- `InterPro`: canonical domain/family/site spine.
- `PROSITE`: precise sequence motifs and documentation.
- `ELM`: short linear motifs and partner-context signals.
- `Pfam`: supporting family view under the InterPro backbone.
- `RCSB motif search`: structure-linked retrieval layer, not a source replacement.

## Next Steps

1. Discover a real official surface for each external source.
2. Pin the surface to a release file, export, or reproducible query shape.
3. Capture the raw payload plus checksums and inventory metadata.
4. Normalize to a canonical motif row model keyed by UniProt accession, residue span, source-native accession or row id, organism, and evidence/provenance.
5. Keep the raw snapshot and normalized rows separate so the record can be rebuilt later.
6. Promote the source only after a stable export exists and the data shape is verified against the local substitute families.

## Per-Source Contract

- `mega_motif_base`: treat as blocked until a stable JSON or TSV export is pinned; only then map catalog and instance rows into motif normalization.
- `motivated_proteins`: treat as blocked until a stable lookup-manifest/export pair is pinned; only then map motif-linked evidence and curation-support rows into normalization.

## Truth Boundary

- No replacement URLs were invented.
- The substitute families are coverage helpers, not identity replacements.
- The remaining work is source discovery and normalization, not reinterpretation of already-imported content.
