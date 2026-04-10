# Motif Breadth Action Map

This map turns the current motif scope view into a concrete acquisition and normalization plan.

## Strong Enough For Current Library Use

- `InterPro`: canonical domain/family/site backbone.
- `PROSITE`: curated sequence motif and profile layer.
- `Pfam`: supporting family view under `InterPro`.
- `ELM`: usable as a partial short-linear-motif source, but still not complete enough for release-grade breadth.

## Still Missing For Release-Grade Breadth

- `ELM` completion is still needed.
- `mega_motif_base` remains a true external gap.
- `motivated_proteins` remains a true external gap.

## Concrete Next Moves

1. Promote the remaining mirrored `ELM` content into the local registry, then normalize it with the same accession/span/provenance contract already used for the motif lane.
2. Acquire `mega_motif_base` from its official surface once discovered, pin a stable payload or export shape, and normalize raw rows separately from derived rows.
3. Acquire `motivated_proteins` the same way, with checksummed raw capture and the same accession/span/provenance contract.
4. Keep `InterPro`, `PROSITE`, and `Pfam` as the current library backbone while the external gaps are closed.
5. Do not promote the motif lane to release-grade breadth until the imported `ELM` shape is complete and the two external sources are either landed or explicitly deferred.

## Evidence Paths

- `artifacts/status/p40_motif_scope_completeness_view.json`
- `artifacts/status/p39_motif_gap_next_step_contract.json`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`
- `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/elm/elm_classes.tsv`
- `data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv`
- `data/raw/protein_data_scope_seed/pfam`
