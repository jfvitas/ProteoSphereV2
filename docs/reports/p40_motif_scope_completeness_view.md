# Motif Scope Completeness View

This view updates the motif completeness story with the current next-step contract. The imported motif/domain backbone is real and useful: `InterPro` and `PROSITE` are complete in the local registry, `Pfam` is present locally as a supporting family view, and `ELM` is present but still partial. That is enough to support a meaningful motif/domain layer, but not enough to call the library release-grade yet.

## Imported Coverage

- `InterPro`: complete imported coverage, canonical domain/family/site spine.
- `PROSITE`: complete imported coverage, curated sequence motif/profile source.
- `Pfam`: present in the imported registry as a supporting family view under `InterPro`.
- `ELM`: partial imported coverage, short linear motif and partner-context source.

## Remaining True External Gaps

- `mega_motif_base`: still a true external gap.
- `motivated_proteins`: still a true external gap.

## Readiness Judgment

The library is broad enough to be a useful motif/domain backbone, but it is not yet deep enough for release-grade motif support. The reasons are simple and current: `ELM` is still partial, and the two remaining motif lanes are not satisfied by any imported or mirrored content.

## Next-Step Contract

The execution contract for the unresolved gaps is to treat them as discovery-and-normalization work only:

1. Find the official surface for each external source.
2. Pin a stable release file, export, or reproducible query shape.
3. Capture checksummed raw payloads and inventory metadata.
4. Normalize to UniProt accession, residue span, source-native id, organism, and provenance.
5. Keep raw snapshots and normalized rows separate until the shape is verified.

## Evidence Paths

- `artifacts/status/p39_motif_gap_next_step_contract.json`
- `artifacts/status/p38_motif_gap_resolution_status.json`
- `artifacts/status/source_coverage_matrix.json`
- `artifacts/status/broad_mirror_progress.json`
- `data/raw/protein_data_scope_seed/interpro/interpro.xml.gz`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/elm/elm_classes.tsv`
- `data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv`
- `data/raw/protein_data_scope_seed/pfam`
