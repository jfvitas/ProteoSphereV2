# P50 Lightweight Bundle Packaging Proposal

Date: 2026-04-01
Artifact: `p50_lightweight_bundle_packaging_proposal`

## Objective

Define the packaging format for the downloadable lightweight reference library bundle that will ship with ProteoSphere.

The packaging decision needs to support the direction already established in:

- [lightweight_reference_library_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_master_plan.md)
- [lightweight_reference_library_parallel_execution_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_parallel_execution_plan.md)
- [source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)

The bundle must stay:

- small enough to distribute through GitHub release assets
- easy to verify and version
- fast enough for local cohort planning and leakage checks
- simple enough that contributors and users can debug it
- extensible enough to add new record families and signatures without a packaging redesign

## Current Context

The current repo state still points toward a compact planning/governance bundle rather than a heavy-data bundle:

- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json) is a small canonical slice relative to the raw mirrors.
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json) is still only a first protein summary slice.
- [source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md) already commits to:
  - pinned manifests
  - compact planning index
  - canonical store
  - feature cache
  - deferred heavy payloads

That means the downloadable bundle should package the lightweight planning/governance layer, not raw source mirrors and not heavyweight packet assets.

## Options Compared

This proposal compares three packaging layouts:

1. `compressed_sqlite`
2. `partitioned_sqlite`
3. `read_only_lookup_tables`

## Evaluation Criteria

The packaging choice is scored against the criteria that matter for this repo:

- GitHub distribution simplicity
- local query performance
- implementation complexity
- schema evolution safety
- partial-update friendliness
- provenance and integrity handling
- ease of debugging
- ability to support future similarity and leakage signatures

## Option A: Compressed SQLite

### Layout

One primary SQLite database containing:

- protein core
- variant layer
- structure-unit summaries
- ligand summaries
- interaction summaries
- motif/domain/site summaries
- pathway context
- provenance tables
- similarity signatures
- leakage groups

Distributed as:

- `proteosphere-lite.sqlite.zst`
- `proteosphere-lite.manifest.json`
- `proteosphere-lite.sha256`

### Strengths

- simplest user experience
  - one file to download
  - one file to open
- strong local random lookup performance
  - SQLite indices work well for accession-first routing
- easy integrity handling
  - one manifest, one checksum root, one release ID
- easy debugging
  - contributors can inspect with standard SQLite tools
- good fit for current architecture
  - aligns with the current planning/governance emphasis
- good support for dense dictionary tables and packed signature blobs

### Weaknesses

- full-bundle replacement on every release
  - even small content changes require re-uploading the bundle
- coarse update granularity
  - users cannot easily fetch only one category expansion
- large single file risk
  - if the library grows aggressively, release-asset handling becomes less convenient

### Best Fit

- default GitHub distribution
- first stable public release
- most local desktop and CLI users

## Option B: Partitioned SQLite

### Layout

Multiple SQLite bundles split by functional area, for example:

- `proteosphere-lite-core.sqlite.zst`
- `proteosphere-lite-annotation.sqlite.zst`
- `proteosphere-lite-interactions.sqlite.zst`
- `proteosphere-lite-ligands.sqlite.zst`
- `proteosphere-lite-provenance.sqlite.zst`
- optional `proteosphere-lite-similarity.sqlite.zst`

With a shared release manifest tying them together.

### Strengths

- better update granularity
  - only changed partitions need to be replaced
- easier growth management
  - large future lanes like interaction or ligand context can expand without forcing a huge monolith
- better optional-download story
  - users can take core only, then add richer packs later
- allows clearer separation between:
  - always-needed planning data
  - optional enrichment data

### Weaknesses

- higher operational complexity
  - multiple assets
  - multiple checksums
  - version compatibility rules between partitions
- more complicated query layer
  - cross-partition joins must be handled carefully
- more room for user misconfiguration
  - missing one partition can look like missing biology rather than missing packaging

### Best Fit

- second-stage packaging once the library grows materially
- optional expansion packs
- environments where storage and download size matter more than single-file simplicity

## Option C: Read-Only Lookup Table Layout

### Layout

A set of compact read-only files, likely dictionary-coded and sorted, such as:

- accession table
- protein summary table
- ligand summary table
- interaction table
- motif/domain table
- pathway table
- provenance table
- signature tables
- dictionary tables

Wrapped with an interpreter layer and release manifest.

The physical representation could be:

- compact binary row stores
- sorted flat tables
- dictionary-coded arrays
- optionally Parquet-like or custom binary segments

### Strengths

- potentially smallest on-disk size
  - especially when tables are dense and dictionary-coded
- excellent cold-distribution efficiency if engineered well
- strong fit for purely read-only workloads
- possible to ship only narrow tables for very constrained deployments

### Weaknesses

- highest implementation complexity
- highest debugging cost
- hardest contributor ergonomics
- schema evolution becomes more fragile
- query flexibility drops unless a real indexing layer is built
- easy to over-optimize too early and spend time building a storage engine instead of the biology and planning logic

### Best Fit

- later optimization stage
- embedded or browser-like distribution targets
- highly size-constrained deployments after the schema is stable

## Comparison Summary

| Criterion | Compressed SQLite | Partitioned SQLite | Read-only Lookup Tables |
| --- | --- | --- | --- |
| GitHub release simplicity | strongest | medium | medium |
| Random local lookup | strong | strong | medium unless heavily engineered |
| Query flexibility | strong | strong | weaker by default |
| Debuggability | strongest | strong | weakest |
| Schema evolution | strong | medium | weakest |
| Partial updates | weak | strongest | medium |
| Packaging complexity | lowest | medium | highest |
| Best near-term fit | strongest | medium | weak |
| Best long-term scaling | medium | strongest | specialized |

## Recommendation

### Primary recommendation

Use `compressed_sqlite` as the default downloadable bundle.

This is the best near-term fit because it matches the current state of the project:

- the library is still being shaped
- the schema is still expanding beyond protein-only summaries
- the system needs operational clarity more than micro-optimized storage
- the bundle needs to be easy to inspect, verify, and debug

### Secondary recommendation

Design the schema and release manifest so that the monolith can later be split into `partitioned_sqlite` without changing the logical data model.

That means:

- stable table naming
- explicit release manifest
- explicit schema version
- explicit table family versioning
- clear dependency declarations between core and optional tables

### Non-recommendation for now

Do not make `read_only_lookup_tables` the default packaging format yet.

That layout is attractive for size and read-only use, but the project is not at the right maturity point to justify the extra storage-engine complexity. It should remain a future optimization track, not the primary release format.

## Recommended Release Layout

### Default GitHub bundle

Ship:

- `proteosphere-lite.sqlite.zst`
- `proteosphere-lite.release_manifest.json`
- `proteosphere-lite.sha256`

Optional human-facing files:

- `proteosphere-lite.contents.md`
- `proteosphere-lite.schema.md`

### Internal bundle structure

The SQLite file should separate logical families into tables such as:

- `proteins`
- `protein_variants`
- `structures`
- `ligands`
- `interactions`
- `motif_annotations`
- `pathway_annotations`
- `provenance_records`
- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`
- `leakage_groups`
- `dictionaries`

### Compression choice

Use `zstd` around the SQLite file, not inside the database as the primary strategy.

Reason:

- it keeps local usage simple after decompression
- it preserves normal SQLite tooling
- it avoids inventing a custom runtime just to read the bundle

## Optional Expansion Pack Path

If the bundle grows beyond the comfortable single-file distribution range, move to a two-tier layout:

### Tier 1: required core

- proteins
- variants
- motifs/domains
- pathway context
- provenance
- leakage groups
- minimal similarity signatures

### Tier 2: optional enrichments

- expanded ligand layer
- expanded interaction layer
- heavier structure-context layer
- optional wider similarity/signature packs

That migration path maps naturally to `partitioned_sqlite`.

## Integrity And Compatibility Requirements

Any chosen layout must carry:

- release ID
- schema version
- source snapshot IDs
- bundle checksum
- per-table or per-partition fingerprints
- minimum compatible interpreter version

The manifest should also declare:

- required bundle parts
- optional bundle parts
- record family counts
- build timestamp
- source provenance roots

## Interaction With The Training-Set Creator

The bundle should support the training-set creator without requiring heavyweight assets locally.

That means the bundled library must contain enough information to:

- identify proteins, variants, structures, ligands, and pairs
- compute balance statistics
- compute leakage groups
- decide packet feasibility
- emit packet blueprints

It should not try to embed:

- mmCIF payloads
- large AlphaFold assets
- raw assay dumps
- long pathway diagrams
- heavy motif instance tables

Those stay behind deferred fetch/materialization paths.

## Risks By Option

### Compressed SQLite risks

- monolithic updates
- larger single-file release asset
- potential future pressure if similarity tables grow quickly

### Partitioned SQLite risks

- partition version drift
- more complicated installer and manifest rules
- missing-part user errors

### Read-only lookup risks

- high engineering cost
- lower debuggability
- premature optimization
- risk of custom-format lock-in

## Decision

Use `compressed_sqlite` as the default downloadable lightweight bundle format.

Design it so that:

- partitions can be introduced later without a schema reset
- optional enrichment packs can be layered on top if growth demands it
- a read-only lookup-table path remains available as a later optimization, not a first release dependency

## Bottom Line

The right packaging choice for the downloadable lightweight library bundle is:

1. `compressed_sqlite` now
2. `partitioned_sqlite` later if bundle growth or optional packs justify it
3. `read_only_lookup_tables` only as a future specialized optimization track

That gives the project the lowest-friction GitHub distribution path while preserving a clean migration route as the library becomes broader and denser.
