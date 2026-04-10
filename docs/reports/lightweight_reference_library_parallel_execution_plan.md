# Lightweight Reference Library Parallel Execution Plan

Date: 2026-04-01
Scope: parallelizable execution program for procurement completion, source integration, lightweight reference library buildout, training-set creation, and storage deduplication

## Purpose

This plan turns the architecture in [lightweight_reference_library_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_master_plan.md) into an execution program that can be split across multiple agents without causing ownership collisions.

It focuses on five immediate objectives:

1. finish procurement and local-source harmonization
2. unify source provenance and reduce storage waste
3. build the lightweight reference library as a compact biological governance layer
4. use that library to create balance-aware, leakage-safe training sets
5. make heavy example materialization deterministic and auditable

## Current Starting Point

The execution plan is grounded in the current repo state:

- [broad_mirror_progress.json](/D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_progress.json)
  - broad online mirror is still incomplete, with the tail concentrated in `STRING` and `UniProt`
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
  - `53` tracked sources
  - `48` present
  - `2` partial
  - `3` missing
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
  - canonical store is `ready`
  - `11` proteins
  - `4124` ligands
  - `5138` assays
  - `0` unresolved assay cases
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
  - only a first protein-only summary slice exists
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
  - protected packet baseline is `12` packets
  - `7` complete / `5` partial

The current storage surface already spans multiple roots that can contain duplicate payloads or repeated release snapshots:

- [data/raw/protein_data_scope_seed](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed)
- [data/raw/bootstrap_runs](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs)
- [data/raw/local_registry](/D:/documents/ProteoSphereV2/data/raw/local_registry)
- [data/raw/local_registry_runs](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs)
- [data/raw/local_copies](/D:/documents/ProteoSphereV2/data/raw/local_copies)
- [data/canonical](/D:/documents/ProteoSphereV2/data/canonical)
- [data/packages](/D:/documents/ProteoSphereV2/data/packages)

That means deduplication needs to be a first-class workstream, not an afterthought.

## Parallel Workstream Model

The work is split into ten workstreams. Each workstream has a narrow purpose, an output boundary, and explicit dependencies.

### W0. Program Control And Shared Contracts

Goal:
- keep schemas, manifests, provenance, and planning contracts stable across all lanes

Outputs:
- schema/version registry
- shared claim classes
- source trust tiers
- release manifest contract
- scrape registry contract

Primary repo surfaces:
- [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md)
- [docs/reports/source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)
- [docs/reports/p29_source_trust_policy.md](/D:/documents/ProteoSphereV2/docs/reports/p29_source_trust_policy.md)
- [core/library/summary_record.py](/D:/documents/ProteoSphereV2/core/library/summary_record.py)

### W1. Procurement Completion

Goal:
- finish the broad online mirror and bring missing source classes under pinned manifests

Outputs:
- full mirror completion reports
- source-specific validators
- promotion gates
- missing-source scoreboard

Primary repo surfaces:
- [protein_data_scope](/D:/documents/ProteoSphereV2/protein_data_scope)
- [scripts/download_raw_data.py](/D:/documents/ProteoSphereV2/scripts/download_raw_data.py)
- [scripts/procurement_supervisor.py](/D:/documents/ProteoSphereV2/scripts/procurement_supervisor.py)
- [artifacts/status/broad_mirror_progress.json](/D:/documents/ProteoSphereV2/artifacts/status/broad_mirror_progress.json)

### W2. Local Corpus Harmonization

Goal:
- reconcile downloaded online content with the imported `bio-agent-lab` corpora

Outputs:
- local-vs-online equivalence map
- source-family overlap map
- stronger import manifests
- promotion rules for local-first vs online-first sources

Primary repo surfaces:
- [scripts/import_local_sources.py](/D:/documents/ProteoSphereV2/scripts/import_local_sources.py)
- [data/raw/local_registry_runs/LATEST.json](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json)
- [artifacts/status/source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)

### W3. Duplicate Detection And Storage Deduplication

Goal:
- identify content-equivalent files across raw mirrors, local copies, repeated runs, and renamed snapshots
- reclaim storage safely without corrupting provenance or breaking manifests

Outputs:
- duplicate inventory
- dedupe equivalence classes
- reclaimable-byte report
- safe cleanup plan
- content-addressed blob strategy

Primary repo surfaces:
- [data/raw/protein_data_scope_seed](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed)
- [data/raw/local_copies](/D:/documents/ProteoSphereV2/data/raw/local_copies)
- [data/raw/local_registry](/D:/documents/ProteoSphereV2/data/raw/local_registry)
- [data/raw/bootstrap_runs](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs)

### W4. Source Integration And Canonical Enrichment

Goal:
- continue converting the source spine into lineage-safe normalized objects

Outputs:
- stronger structure lane
- richer interaction lane
- motif/pathway/domain enrichment
- variant-aware canonical entities

Primary repo surfaces:
- [execution/materialization/raw_canonical_materializer.py](/D:/documents/ProteoSphereV2/execution/materialization/raw_canonical_materializer.py)
- [execution/library](/D:/documents/ProteoSphereV2/execution/library)
- [data/canonical/LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)

### W5. Lightweight Reference Library Schema And Materialization

Goal:
- turn the current protein-only summary slice into the compact full library

Outputs:
- schema v2
- library tables for proteins, variants, structures, ligands, interactions, motifs, pathways, provenance
- compact downloadable artifact

Primary repo surfaces:
- [docs/reports/lightweight_reference_library_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_master_plan.md)
- [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [execution/library/build_summary_library.py](/D:/documents/ProteoSphereV2/execution/library/build_summary_library.py)
- [core/library/entity_card.py](/D:/documents/ProteoSphereV2/core/library/entity_card.py)

### W6. Similarity, Consensus, And Leakage Signatures

Goal:
- give the library compact biological similarity and leakage-governance power

Outputs:
- similarity signature tables
- class-aware consensus engine
- overlap edges
- leakage groups for exact, family, variant, structure, ligand, interaction, and pathway scopes

Primary repo surfaces:
- [datasets/recipes/schema.py](/D:/documents/ProteoSphereV2/datasets/recipes/schema.py)
- [datasets/recipes/split_simulator.py](/D:/documents/ProteoSphereV2/datasets/recipes/split_simulator.py)
- [datasets/recipes/balanced_cohort_scorer.py](/D:/documents/ProteoSphereV2/datasets/recipes/balanced_cohort_scorer.py)
- [docs/reports/p29_source_trust_policy.md](/D:/documents/ProteoSphereV2/docs/reports/p29_source_trust_policy.md)

### W7. Training-Set Creator And Cohort Governance

Goal:
- compile user settings plus library state into unbiased, leakage-safe dataset plans

Outputs:
- cohort universe builder
- balance diagnostics
- split planner
- CV/fold planner
- external training-set audit mode

Primary repo surfaces:
- [scripts/materialize_balanced_dataset_plan.py](/D:/documents/ProteoSphereV2/scripts/materialize_balanced_dataset_plan.py)
- [scripts/dataset_design_wizard.py](/D:/documents/ProteoSphereV2/scripts/dataset_design_wizard.py)
- [artifacts/status/packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)

### W8. Packet Blueprinting And Heavy Hydration

Goal:
- plan and then build heavy training examples only after the cohort is frozen

Outputs:
- packet blueprints
- materialization routes
- asset fetch manifests
- deterministic packet builds
- packet QA

Primary repo surfaces:
- [execution/materialization/training_packet_materializer.py](/D:/documents/ProteoSphereV2/execution/materialization/training_packet_materializer.py)
- [execution/materialization/package_builder.py](/D:/documents/ProteoSphereV2/execution/materialization/package_builder.py)
- [execution/materialization/available_payload_registry.py](/D:/documents/ProteoSphereV2/execution/materialization/available_payload_registry.py)
- [data/packages](/D:/documents/ProteoSphereV2/data/packages)

### W9. Supplemental Web Capture

Goal:
- add narrow, provenance-controlled scrape enrichment only where structured sources remain thin

Outputs:
- scrape registry
- page-specific parsers
- scrape QA
- supplemental annotation lanes

Primary repo surfaces:
- [docs/reports/source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)
- [docs/reports/p29_source_trust_policy.md](/D:/documents/ProteoSphereV2/docs/reports/p29_source_trust_policy.md)

### W10. QA, Benchmarking, And Release Use

Goal:
- verify the library and training-set creator are truthful, balanced, leakage-safe, and reproducible

Outputs:
- bias audits
- leakage audits
- packet determinism tests
- user-facing evaluation workflows
- release-grade validation reports

Primary repo surfaces:
- [runs/real_data_benchmark](/D:/documents/ProteoSphereV2/runs/real_data_benchmark)
- [tests](/D:/documents/ProteoSphereV2/tests)
- [scripts/run_full_benchmark.py](/D:/documents/ProteoSphereV2/scripts/run_full_benchmark.py)

## Dependency Structure

### Hard dependencies

- `W0 -> all`
  Shared contracts must stay stable first.
- `W1 -> W4, W5, W8, W9`
  Source procurement must provide pinned input boundaries.
- `W2 -> W3, W4, W5`
  We need overlap visibility between local and online data before dedupe and fusion.
- `W3 -> W1 promotion hardening, W2 harmonization, W5 packaging`
  Deduplication must understand the real storage layout before compact artifact packaging.
- `W4 -> W5, W6`
  Canonical/source integration supplies the normalized objects that the library and signature layers depend on.
- `W5 -> W6, W7, W8`
  The lightweight library must exist before split governance and packet blueprints are finalized.
- `W6 -> W7`
  Leakage groups and similarity signatures drive intelligent splits.
- `W7 -> W8`
  Packet generation must follow a frozen cohort and split plan.
- `W8 -> W10`
  Heavy packet outputs and manifests must exist before release-grade validation.
- `W9 -> W5, W6, W10`
  Scraped enrichments should plug into the library only after registry and trust gates exist.

### Soft dependencies

- `W1` and `W2` can run in parallel.
- `W3` can start before procurement is fully finished by working on already-present roots and repeated snapshots.
- `W5` can start with protein, pathway, motif, and interaction-first slices before every source is complete.
- `W6` can start with sequence/family/pathway/motif signatures while structure and ligand tails are still improving.

## Agent-Parallel Task Map

This is the recommended parallel decomposition. Each lane is narrow enough for separate agents.

### Lane A. Remaining Procurement Tail

Tasks:
1. finish `STRING` tail validation and promotion
2. finish `UniProt` tail validation and promotion
3. refresh broad mirror progress and source verification artifacts
4. verify remaining motif/network gaps

### Lane B. Local-Online Overlap Map

Tasks:
5. compare [data/raw/protein_data_scope_seed](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed) against [data/raw/local_copies](/D:/documents/ProteoSphereV2/data/raw/local_copies)
6. compare online snapshots against [data/raw/local_registry](/D:/documents/ProteoSphereV2/data/raw/local_registry)
7. emit source-family overlap classes:
   - identical content
   - same source different release
   - same biology different provider format
   - provider mismatch / unresolved
8. define promotion priority per source family

### Lane C. Duplicate Detection

Tasks:
9. inventory every file under:
   - `data/raw/protein_data_scope_seed`
   - `data/raw/local_copies`
   - `data/raw/local_registry`
   - `data/raw/bootstrap_runs`
10. cluster by cheap prefilters:
   - file size
   - extension
   - normalized basename
   - source family
11. compute strong hashes only within candidate clusters
12. emit duplicate equivalence classes
13. separate safe and unsafe duplicate cases

### Lane D. Safe Storage Deduplication

Tasks:
14. design content-addressed blob layout
15. map current file paths to blob IDs
16. define manifest-pointer rewrite rules
17. test Windows-safe hardlink strategy for same-volume duplicates
18. define fallback copy-once pointer mode when hardlinks are unsafe
19. emit reclaimable-bytes report
20. define cleanup procedure with rollback

### Lane E. Canonical Enrichment

Tasks:
21. add protein variant/construct normalization
22. add structure-unit identity layer
23. add explicit ligand-class normalization layer
24. add richer interaction lineage layer
25. add motif/site/pathway alignment into canonical enrichment

### Lane F. Library Schema V2

Tasks:
26. define schema v2 tables
27. define compact dictionary tables
28. define provenance pointer model
29. define record-family versioning
30. define compressed downloadable artifact format

### Lane G. Source Fusion And Consensus

Tasks:
31. implement claim-class consensus rules
32. add alternates/unresolved multi-claim support
33. add family-level biological grouping
34. add binding-context grouping
35. add pathway-role grouping

### Lane H. Similarity And Leakage

Tasks:
36. implement protein similarity signatures
37. implement structure similarity signatures
38. implement ligand similarity signatures
39. implement interaction-context signatures
40. emit leakage groups by scope
41. generate overlap edges for split governance

### Lane I. Dataset Planning And Split Governance

Tasks:
42. build candidate-universe compiler
43. build class-balance and gap diagnostics
44. build split-governance engine over leakage groups
45. add CV planning mode
46. add external training-set audit mode for user-supplied PDB/accession lists

### Lane J. Packet Blueprinting

Tasks:
47. generate packet blueprints from cohort plans
48. record required modalities per example
49. record available raw assets vs missing heavy assets
50. record hydration route per example
51. add truth-safe partial vs complete packet policy

### Lane K. Heavy Hydration

Tasks:
52. hydrate experimental structures
53. hydrate predicted structures
54. build ligand features and graphs
55. build interaction graphs and interface summaries
56. run optional heavy processors like PyRosetta only after packet freeze

### Lane L. Web Enrichment

Tasks:
57. create scrape registry schema
58. define allowlisted domains and page types
59. implement accession-scoped page capture
60. implement normalized supplemental fields
61. add scrape provenance QA

### Lane M. QA And Bias Validation

Tasks:
62. validate that library summaries match source evidence
63. validate consensus conflict retention
64. validate dedupe safety and no broken manifests
65. validate leakage-group correctness on known close families
66. validate balance diagnostics on real cohorts
67. validate packet determinism and rebuild correctness
68. validate user-facing training-set audit workflows

## Duplicate-File Detection And Cleanup Strategy

This needs to be explicit because the repo now has multiple legitimate ways to hold the same bytes:

- online broad mirror downloads
- bootstrap runs
- imported local copies from `bio-agent-lab`
- registry snapshots referring to the same local corpora over time
- repeated reruns of the same release under different filenames or run folders

### Phase D1. Inventory

Build a raw inventory table with one row per file:

- absolute path
- root class
  - `broad_seed`
  - `bootstrap_run`
  - `local_copy`
  - `local_registry_snapshot`
  - `canonical`
  - `package`
- source family
- filename
- normalized basename
- extension
- size bytes
- last write time
- release or snapshot ID if inferable from path or manifest
- manifest pointers if available

### Phase D2. Candidate Clustering

Create duplicate candidate clusters using cheap keys:

- exact size
- extension
- normalized basename
- source family

This prevents hashing every file blindly on day one.

### Phase D3. Strong Hash Confirmation

For each candidate cluster, compute:

- `sha256`
- optional fast prehash on head/tail blocks to reduce cost before full hash on giant files

Classify results:

- `exact_duplicate_same_release`
- `exact_duplicate_different_path_same_source`
- `exact_duplicate_different_source_family`
- `same_name_different_content`
- `same_biology_different_format`
- `same_release_partial_vs_complete`

### Phase D4. Safety Classification

Only dedupe automatically when all of these are true:

- byte-identical content
- no manifest requires separate physical retention
- no write-in-place behavior depends on the current path
- no active download or partial file is involved
- both files are in stable snapshot roots

Unsafe or review-required cases:

- partial files
- active downloads
- same biology but not byte-identical
- same bytes but provenance policy requires separate retention
- files in temporary or currently-materializing roots

### Phase D5. Cleanup Strategy

Preferred strategy:

1. introduce a content-addressed blob root such as:
   - `data/blob_store/sha256/ab/cd/...`
2. migrate safe duplicates to a single blob
3. keep manifest pointers from all logical source paths to the blob
4. use hardlinks on the same volume when the toolchain requires a file-like path
5. keep pointer manifests when hardlinks are not safe or would hide provenance

This preserves provenance while reclaiming space.

### Phase D6. Validation

Before deleting or relinking anything, verify:

- every manifest still resolves
- every checksum still matches
- packet materializers and canonical builders still open expected files
- reclaimable byte estimates match actual disk reductions
- rollback is possible from a saved path-to-blob map

### Phase D7. Reporting

Emit these reports:

- duplicate inventory
- safe duplicate groups
- review-required groups
- reclaimable bytes by source family
- reclaimable bytes by root class
- post-cleanup verification report

## Recommended Order Of Execution

### Wave 1: Finish Procurement And Start Dedupe Planning

Run in parallel:
- Lane A
- Lane B
- Lane C
- Lane F

Reason:
- no point waiting on perfect completion before defining schema and storage strategy
- dedupe inventory can start immediately on already-present files

### Wave 2: Source Fusion And Dedupe Execution

Run in parallel:
- Lane D
- Lane E
- Lane G
- Lane H

Reason:
- dedupe and canonical/library enrichment now have enough stable source context

### Wave 3: Dataset Governance

Run in parallel:
- Lane I
- Lane J
- Lane M

Reason:
- once signatures and library tables exist, split governance and bias diagnostics can move quickly

### Wave 4: Heavy Packet Build

Run in parallel:
- Lane K
- Lane M

Reason:
- heavy hydration should happen only after blueprints and split plans are frozen

### Wave 5: Supplemental Scraping

Run in parallel:
- Lane L
- Lane M

Reason:
- scrape enrichment should enter after structured-source behavior is already stable and testable

## Concrete Deliverables

By the end of this program, the repo should have:

- a full lightweight reference library artifact
- a deduped or content-addressed raw storage surface
- a similarity and leakage signature layer
- a balance-aware dataset creator
- an external dataset audit mode
- deterministic packet blueprints and heavy materialization
- a supplemental scrape registry for high-value enrichment
- QA that proves the library reduces leakage and exposes imbalance instead of hiding it

## Immediate Next Actions

These are the next best slices to execute first:

1. inventory duplicate candidates across `protein_data_scope_seed`, `local_copies`, `local_registry`, and `bootstrap_runs`
2. emit a reclaimable-bytes and safe-dedupe report
3. define schema v2 for the lightweight library
4. implement protein variant and structure-unit records
5. implement similarity and leakage signature scaffolding
6. wire dataset planning to use the future library signatures rather than only packet completeness

## Summary

The work is now cleanly decomposed.

Procurement completion, local-source harmonization, deduplication, canonical enrichment, lightweight library buildout, similarity/leakage governance, training-set planning, packet blueprinting, heavy hydration, supplemental scraping, and QA can all be advanced in parallel as long as each lane respects the dependency structure above.

The dedupe lane is important enough to treat as a primary workstream. Without it, the repo will continue to grow redundant raw storage across online mirrors, local copies, repeated snapshots, and reruns. With it, we can reclaim space while preserving provenance and keeping every downstream manifest valid.
