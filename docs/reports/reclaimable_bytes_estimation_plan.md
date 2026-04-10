# Reclaimable Bytes Estimation Plan

Date: 2026-04-01
Artifact: `reclaimable_bytes_estimation_plan`

## Purpose

This report defines how reclaimable bytes should be estimated once duplicate-file inventory work starts. It is intentionally estimation-focused, not cleanup-focused. The goal is to answer:

- which storage roots are likely wasting space
- which duplicate classes are safe to count toward reclaimable storage
- which classes must be excluded or down-weighted
- how confident we are in the estimate

This report is grounded in the current ProteoSphere storage layout:

- [data/raw/protein_data_scope_seed](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed)
- [data/raw/bootstrap_runs](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs)
- [data/raw/local_registry](/D:/documents/ProteoSphereV2/data/raw/local_registry)
- [data/raw/local_registry_runs](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs)
- [data/raw/local_copies](/D:/documents/ProteoSphereV2/data/raw/local_copies)
- [data/canonical](/D:/documents/ProteoSphereV2/data/canonical)
- [data/packages](/D:/documents/ProteoSphereV2/data/packages)

It also follows the workstream and dedupe model in [lightweight_reference_library_parallel_execution_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_parallel_execution_plan.md).

## What Counts As Reclaimable

For estimation purposes, reclaimable bytes are bytes that could be removed or deduplicated without losing required provenance or breaking current materialization guarantees.

That means the estimate should be conservative.

The estimate should count only bytes that fall into one of these buckets:

1. `exact_duplicate_same_release`
   Byte-identical copies of the same source payload stored in multiple locations.
2. `exact_duplicate_repeated_snapshot`
   Byte-identical files repeated across reruns or repeated manifest snapshots.
3. `exact_duplicate_local_vs_online`
   Byte-identical files present both in local mirror imports and online mirror roots.
4. `exact_duplicate_renamed_payload`
   Same content under different names or run folders.

The estimate should not count:

1. `same biology, different format`
   Example: XML vs TSV vs JSON views of the same source data.
2. `partial vs complete`
   In-progress `.part` files or interrupted downloads.
3. `same source, different release`
   Example: different month stamps or release versions.
4. `derived outputs`
   Canonical, feature-cache, or package artifacts that are not raw-payload duplicates.
5. `active write targets`
   Files still being downloaded, refreshed, or materialized.

## Root Classes

Each file should first be assigned a storage root class. Estimation should roll up by these classes.

| Root class | Repo path | Why it matters |
| --- | --- | --- |
| `broad_seed` | [data/raw/protein_data_scope_seed](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed) | Main online mirror, likely overlaps with local copies and repeated reruns |
| `bootstrap_run` | [data/raw/bootstrap_runs](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs) | May reference or duplicate targeted acquisition outputs |
| `local_registry_snapshot` | [data/raw/local_registry](/D:/documents/ProteoSphereV2/data/raw/local_registry) | Registry snapshots may repeatedly point at or inventory the same local corpus |
| `local_registry_run` | [data/raw/local_registry_runs](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs) | Repeated summary snapshots, usually metadata-heavy and low-value for physical cleanup |
| `local_copy` | [data/raw/local_copies](/D:/documents/ProteoSphereV2/data/raw/local_copies) | High-probability overlap with both `bio-agent-lab` assets and online mirrors |
| `canonical` | [data/canonical](/D:/documents/ProteoSphereV2/data/canonical) | Excluded by default from raw dedupe estimates |
| `package` | [data/packages](/D:/documents/ProteoSphereV2/data/packages) | Excluded by default from raw dedupe estimates |

## Duplicate Classes

The estimation pass should classify candidates into these duplicate classes:

### Class A: Exact duplicate, same source, same release

Definition:
- full `sha256` match
- same source family
- same release or snapshot lineage

Estimate policy:
- count as fully reclaimable except for one retained keeper copy

Confidence:
- highest

### Class B: Exact duplicate, different path, same logical payload

Definition:
- full `sha256` match
- same source family
- same normalized basename or manifest lineage
- path differs due to rerun folder, rename, or copy target

Estimate policy:
- count as fully reclaimable except for one retained keeper copy

Confidence:
- high

### Class C: Exact duplicate, local vs online mirror

Definition:
- full `sha256` match
- one file under online mirror, one under local copy or local registry derived root

Estimate policy:
- count as reclaimable only if provenance can be preserved via pointer or retained manifest link

Confidence:
- medium to high depending on manifest alignment

### Class D: Exact duplicate, repeated registry metadata

Definition:
- repeated identical metadata exports, inventories, or registry manifests across snapshot runs

Estimate policy:
- count as reclaimable, but report separately from heavy payload bytes

Confidence:
- high, but operational savings may be small

### Class E: Same name, different content

Definition:
- basename matches
- source family matches
- checksum differs

Estimate policy:
- not reclaimable

Confidence:
- excluded

### Class F: Same biology, different representation

Definition:
- known semantic equivalence, but content differs because format differs

Estimate policy:
- not reclaimable in the physical-byte estimate

Confidence:
- excluded

### Class G: Partial or active artifacts

Definition:
- `.part`, temp, interrupted, or currently-written payloads

Estimate policy:
- excluded from reclaimable-byte totals

Confidence:
- excluded until stabilized

## Estimation Formula

For each exact-duplicate equivalence class:

`reclaimable_bytes_class = total_member_bytes - retained_bytes`

Where:

- `total_member_bytes` is the sum of bytes of all safe class members
- `retained_bytes` is the size of the single keeper copy that would remain after cleanup

For exact duplicates of equal size, this simplifies to:

`reclaimable_bytes_class = (member_count - 1) * file_size`

For the total estimate:

`reclaimable_bytes_total = sum(reclaimable_bytes_class for all included classes)`

## Confidence Tiers

The estimate should carry a confidence tier for each class and each aggregate.

### Tier 0: Excluded

Used for:
- active downloads
- partial files
- same-biology-different-format
- unresolved provenance cases

Interpretation:
- do not count in reclaimable totals

### Tier 1: Low confidence

Requirements:
- candidate grouped by basename and size only
- no strong hash yet

Interpretation:
- planning hint only
- never include in “safe reclaimable” totals

### Tier 2: Medium confidence

Requirements:
- strong hash match
- source family match
- release/snapshot match is likely but not fully proven from manifests

Interpretation:
- include in `potential_reclaimable_bytes`
- do not include in `safe_reclaimable_bytes`

### Tier 3: High confidence

Requirements:
- strong hash match
- source family and release lineage align
- no active writes
- manifests or inventory records can preserve provenance after dedupe

Interpretation:
- include in `safe_reclaimable_bytes`

### Tier 4: Cleanup-ready

Requirements:
- Tier 3 plus an explicit keeper-path rule and rollback mapping

Interpretation:
- safe to move into execution planning

## Exclusions

The reclaimable-byte estimate must exclude the following by default:

- all `.part`, temp, and interrupted artifacts
- any file touched by a currently running downloader
- canonical store outputs under [data/canonical](/D:/documents/ProteoSphereV2/data/canonical)
- packet outputs under [data/packages](/D:/documents/ProteoSphereV2/data/packages)
- files whose only evidence is basename similarity
- same-biology-different-format representations
- files under review for manifest or provenance ambiguity

## Rollups

The estimate should be reported at four levels:

1. `by duplicate class`
2. `by root class`
3. `by source family`
4. `global total`

Recommended top-level metrics:

- `candidate_duplicate_file_count`
- `hashed_candidate_file_count`
- `exact_duplicate_class_count`
- `potential_reclaimable_bytes`
- `safe_reclaimable_bytes`
- `excluded_bytes`
- `largest_reclaimable_root_classes`
- `largest_reclaimable_source_families`

## Keeper Selection Rule

When a class is reclaimable, the estimate should assume one retained keeper copy.

Preferred keeper selection order:

1. retain the copy directly referenced by the most authoritative manifest
2. if tied, retain the copy under the most stable root
   - prefer `broad_seed` or durable local source over transient run folders
3. if still tied, retain the shortest and most stable canonical path

This matters because reclaimable-byte estimates should reflect a realistic cleanup path, not an idealized one.

## Practical Current Interpretation

Based on the current repo layout, the highest-likelihood future reclaimable pools are:

- repeated raw payloads between [data/raw/protein_data_scope_seed](/D:/documents/ProteoSphereV2/data/raw/protein_data_scope_seed) and [data/raw/local_copies](/D:/documents/ProteoSphereV2/data/raw/local_copies)
- repeated run-bound outputs under [data/raw/bootstrap_runs](/D:/documents/ProteoSphereV2/data/raw/bootstrap_runs)
- repeated metadata and snapshot inventories across [data/raw/local_registry](/D:/documents/ProteoSphereV2/data/raw/local_registry) and [data/raw/local_registry_runs](/D:/documents/ProteoSphereV2/data/raw/local_registry_runs)

The lowest-confidence cleanup candidates are:

- current active `STRING` and `UniProt` tail downloads
- files whose semantic equivalence is biological rather than byte-identical
- any payloads where manifest lineage is not yet reconciled between local and online sources

## Deliverables The Estimation Pass Should Produce

1. a machine-readable estimate artifact
2. a human-readable summary report
3. a list of excluded classes and reasons
4. a keeper-selection preview
5. a root-level reclaimable-bytes rollup
6. a source-family reclaimable-bytes rollup

## Bottom Line

The reclaimable-byte estimate must be conservative and rooted in exact duplicates, not approximate biological overlap.

The right sequence is:

1. inventory
2. cluster
3. hash
4. classify
5. estimate
6. review
7. only then plan cleanup

That approach gives a storage-saving estimate that is useful for prioritization without overstating how much space can actually be reclaimed safely.
