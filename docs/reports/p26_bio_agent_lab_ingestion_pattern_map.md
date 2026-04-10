# P26 Bio-Agent-Lab Ingestion Pattern Map

Date: 2026-03-23  
Scope: map the highest-yield ingestion, lifecycle, and indexing patterns from `C:\Users\jfvit\Documents\bio-agent-lab` onto the current ProteoSphere implementation surface.

## Bottom Line

ProteoSphere already has the right broad shape for manifest-driven raw acquisition, local-corpus registration, canonical materialization, and balanced dataset planning. The strongest reusable lesson from `bio-agent-lab` is not "copy more data." It is "promote lifecycle and query-readiness artifacts to first-class products."

Right now ProteoSphere is strongest at:

- online raw mirroring in [download_raw_data.py](/D:/documents/ProteoSphereV2/scripts/download_raw_data.py)
- local corpus registration in [import_local_sources.py](/D:/documents/ProteoSphereV2/scripts/import_local_sources.py) and [local_source_mirror.py](/D:/documents/ProteoSphereV2/execution/acquire/local_source_mirror.py)
- conservative canonical materialization in [raw_canonical_materializer.py](/D:/documents/ProteoSphereV2/execution/materialization/raw_canonical_materializer.py)
- planning surfaces in [corpus_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/corpus_registry.py) and [materialize_balanced_dataset_plan.py](/D:/documents/ProteoSphereV2/scripts/materialize_balanced_dataset_plan.py)

The main missing layer is the control plane between "we have the files" and "we can safely use them at scale."

## Pattern Map

| Bio-agent-lab pattern | Best existing bio-agent-lab artifact | Closest ProteoSphere surface | Current gap | Recommendation |
| --- | --- | --- | --- | --- |
| Source capability registry | `data/reports/source_capabilities.json` | [audit_data_inventory.py](/D:/documents/ProteoSphereV2/scripts/audit_data_inventory.py), [corpus_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/corpus_registry.py) | ProteoSphere can count availability, but it does not yet publish a machine-readable "implemented vs planned vs query-ready vs enabled-for-packets" source map. | Add a source capability/status artifact under `artifacts/status` and `data/planning_index` that merges online raw, local registry, packet eligibility, and canonical eligibility. |
| Source lifecycle policy | `data/reports/source_lifecycle_report.json` | [download_raw_data.py](/D:/documents/ProteoSphereV2/scripts/download_raw_data.py), [import_local_sources.py](/D:/documents/ProteoSphereV2/scripts/import_local_sources.py), [audit_data_inventory.py](/D:/documents/ProteoSphereV2/scripts/audit_data_inventory.py) | ProteoSphere records manifests, but freshness policy, targeted refresh policy, stale retention, and index readiness are still scattered across code and prose. | Emit one lifecycle report per source with packaging mode, refresh mode, retention mode, and query readiness. |
| Download ledger with task hints | `data/catalog/download_manifest.csv` | [download_raw_data.py](/D:/documents/ProteoSphereV2/scripts/download_raw_data.py), [local_source_mirror.py](/D:/documents/ProteoSphereV2/execution/acquire/local_source_mirror.py) | Current bootstrap summaries are source-scoped, but not row-scoped enough for downstream selectors to say "which exact raw payload best supports ligand or pair uplift." | Add a normalized raw acquisition ledger keyed by accession, pair, ligand, and source record id. |
| Layered extracted middle tier | `data/extracted/{assays,bound_objects,chains,entry,interfaces,provenance}` | [raw_canonical_materializer.py](/D:/documents/ProteoSphereV2/execution/materialization/raw_canonical_materializer.py) | ProteoSphere jumps too quickly from raw manifests into canonical and package planning. It lacks a stable extracted/query tier for accession-clean slices. | Create an extracted planning tier for pair, ligand, structure, and annotation slices before canonical and packet use. |
| Query-ready index status | `source_lifecycle_report.json -> index.*` | [corpus_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/corpus_registry.py) | ProteoSphere knows source presence, but not whether a source is actually indexed and cheap to query for packet selection. | Add per-source query-ready manifests with lookup paths, record counts, join keys, and generated timestamps. |
| Training manifest with completeness accounting | `data/training_examples/training_manifest.json` | [materialize_balanced_dataset_plan.py](/D:/documents/ProteoSphereV2/scripts/materialize_balanced_dataset_plan.py), `data/packages`, packet audits | ProteoSphere can score and plan, but package outputs are not yet summarized as one training-manifest contract with required sections and warning counts. | Add a package/training manifest that rolls up packet completeness, required sections, and source-status counts from real package outputs. |
| Split diagnostics as a first-class gate | `data/splits/split_diagnostics.json` | `datasets/recipes/*`, balanced cohort planning, release reports | ProteoSphere has scoring and split simulation, but there is no standard artifact that becomes the release-facing split truth surface for each materialized cohort. | Emit split diagnostics per planned/materialized cohort and link them directly from the package manifest and release bundle. |
| Release bundle manifest | `data/releases/test_v1/release_snapshot_manifest.json`, `dataset_release_manifest.json` | release reports under [docs/reports](/D:/documents/ProteoSphereV2/docs/reports) | ProteoSphere has many truthful reports, but not one implementation-grade release bundle manifest tying canonical, packages, splits, source state, and coverage into a single machine-readable contract. | Add a release bundle builder once the packet and split artifacts are live. |

## What To Reuse Directly

These `bio-agent-lab` assets are the highest-yield reference shapes for ProteoSphere to emulate, not necessarily to copy byte-for-byte:

- `C:\Users\jfvit\Documents\bio-agent-lab\data\reports\source_capabilities.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\reports\source_lifecycle_report.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\catalog\download_manifest.csv`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\training_examples\training_manifest.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\splits\split_diagnostics.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\release_snapshot_manifest.json`
- `C:\Users\jfvit\Documents\bio-agent-lab\data\releases\test_v1\dataset_release_manifest.json`

These are useful because they encode state transitions, not just payload presence.

## Recommended Next Coding Wave

### Wave 1: Lifecycle and Query-Readiness Control Plane

Priority:

1. Build a unified source lifecycle artifact.
   Target current files:
   - [audit_data_inventory.py](/D:/documents/ProteoSphereV2/scripts/audit_data_inventory.py)
   - [corpus_registry.py](/D:/documents/ProteoSphereV2/execution/acquire/corpus_registry.py)
   - [local_source_mirror.py](/D:/documents/ProteoSphereV2/execution/acquire/local_source_mirror.py)

   Output should answer:
   - Is the source present?
   - Is it query-ready?
   - What entity kinds can it support?
   - Is it safe for canonical?
   - Is it safe for packet materialization?
   - What is the refresh/retention policy?

2. Add a raw acquisition ledger.
   Target current files:
   - [download_raw_data.py](/D:/documents/ProteoSphereV2/scripts/download_raw_data.py)
   - [import_local_sources.py](/D:/documents/ProteoSphereV2/scripts/import_local_sources.py)

   The ledger should emit row-level records for accession, pair, ligand, source record id, raw path, lane kind, and provenance hints so later packet builders stop re-scanning whole manifests.

3. Insert an extracted/query tier ahead of canonical.
   Target current file:
   - [raw_canonical_materializer.py](/D:/documents/ProteoSphereV2/execution/materialization/raw_canonical_materializer.py)

   The key change is architectural: canonical should consume selected extracted slices, not raw source payloads directly whenever a richer extracted local lane exists.

## Recommended Follow-On Coding Wave

### Wave 2: Packet and Release Control Plane

Priority:

1. Add a package/training manifest rooted in real `data/packages` outputs.
   Target current file:
   - [materialize_balanced_dataset_plan.py](/D:/documents/ProteoSphereV2/scripts/materialize_balanced_dataset_plan.py)

   The artifact should carry:
   - packet counts
   - required sections
   - source status by modality
   - warning counts
   - expected vs actual packet completeness

2. Add standard split diagnostics for every planned/materialized cohort.
   This should become the formal leakage and balance truth surface that later release tasks consume.

3. Build a single release bundle manifest.
   It should point to:
   - canonical snapshot
   - source lifecycle snapshot
   - corpus registry snapshot
   - balanced dataset plan
   - package/training manifest
   - split diagnostics

## Highest-Yield Concrete Reuse Paths

- Reuse the `bio-agent-lab` lifecycle-report shape to teach ProteoSphere the difference between `present` and `query_ready`.
- Reuse the download-manifest pattern to make procurement outputs selector-friendly for packet expansion.
- Reuse the training-manifest and split-diagnostics pattern to connect packet materialization to actual training-set readiness.
- Reuse the release-snapshot pattern so the eventual QA and release lanes stop depending on many separate reports.

## Recommendation Order

1. Do not spend the next wave adding more ad hoc source-specific loaders first.
2. First add lifecycle, query-ready, and extracted-tier reporting so the current large local corpora become operable.
3. Then wire package manifests and split diagnostics so balanced training-set creation becomes measurable.
4. Only after that widen the next source-specific import wave.

## Why This Is The Best Near-Term Move

ProteoSphere already has enough raw and local data to make major progress. The highest leverage from `bio-agent-lab` is the discipline of making ingestion state, lifecycle state, index state, and training readiness explicit and machine-readable. That is the shortest path from "large corpus on disk" to "robust balanced training sets with auditable release artifacts."
