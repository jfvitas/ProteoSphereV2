# P26 Data And Training Gap Assessment

Date: 2026-03-23  
Task: `P26-A001`

## Current State

- Online raw procurement is present for `6/6` currently wired online sources, with `34` downloaded raw files under `data/raw`.
- Local `bio-agent-lab` procurement is materially larger: `39` registered sources, `33` effectively present, `2` partial, `7` missing, and about `153.6 GB` indexed through the local registry.
- Canonical materialization is currently healthy again on the assay lane: `11` proteins, `4124` ligands, `5138` assays, `0` structures, `9273` total records in `data/canonical/LATEST.json`.
- The recipe and split-planning stack exists and is deterministic on the frozen benchmark slice, but real packet completeness is still weak and bounded.

## What Is Working

- Manifest-driven raw storage exists for online snapshots in `data/raw` and local mirrors in `data/raw/local_registry`.
- Canonical sequence and assay lanes currently resolve without unresolved cases on the present materialized slice.
- Leakage-aware recipe replay and split simulation are implemented and reproducible for the frozen 12-accession cohort.
- PowerShell operator workflows can inspect runtime, queue, soak, and readiness state.

## What Is Not Dialed In Yet

- Procurement breadth is not the same thing as usable training breadth.
  The online layer is still a narrow probe slice, and the canonical store currently covers only two proteins.
- Real multimodal packet quality is improving, but it is not yet release-grade.
  The latest packet status board now shows `7` complete packets and `5` partial packets, while the benchmark usefulness audit still remains narrow.
- `data/packages` is not yet serving as a robust materialized training-packet library.
- PPI, ligand, structure, and annotation coverage are still too uneven to claim well-balanced release-grade training sets.

## Highest Priority Gaps

1. Expand the corpus registry from the existing raw manifests and local registry so candidate proteins, pairs, ligands, and annotation-backed rows can be scored at scale.
2. Export a planning-grade source coverage matrix that distinguishes online raw, local registry, and missing lanes for procurement decisions.
3. Score candidates for balanced cohort construction using modality completeness, evidence depth, and leakage-safe diversity instead of the current frozen benchmark slice alone.
4. Materialize real training packets into `data/packages` from manifest-driven inputs so packet quality can be audited on actual package outputs, not only benchmark sidecars.
5. Publish a joined readiness matrix that connects source procurement, corpus expansion, and packet readiness so the next benchmark/training wave can be selected deliberately.

## Immediate Parallelizable Work

- `P26-T002` source coverage matrix exporter
- `P26-T003` corpus expansion registry builder
- `P26-T004` balanced cohort scorer
- `P26-T005` training packet materializer
- `P26-T006` balanced dataset planning CLI
- `P26-I007` procurement and packet readiness matrix

## Operational Read

The release lane is currently healthy but gated by the ongoing weeklong soak. That makes this the right moment to redirect parallel agent capacity into data breadth, packet quality, and balanced training-set readiness so the system is materially stronger by the time the soak gate clears.
