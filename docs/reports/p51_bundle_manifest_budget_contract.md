# P51 Bundle Manifest Budget Contract

Date: 2026-04-01
Artifact: `p51_bundle_manifest_budget_contract`

## Objective

Define the downloadable lightweight-library bundle manifest contract and the size-budget policy that should govern GitHub release distribution.

This proposal is grounded in:

- [p50_lightweight_bundle_packaging_proposal.md](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md)
- [lightweight_reference_library_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_master_plan.md)
- [source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)

## Current Context

The current repo still supports a compact planning/governance bundle, not a heavy-data bundle:

- the current summary library is still a first-slice protein-only artifact with `11` records in [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- the canonical slice is still small by raw-data standards in [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md) explicitly keeps heavy payloads deferred
- motif and interaction breadth is still incomplete in [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)

That means the bundle manifest and budget contract should assume:

- a compact compressed SQLite core bundle
- optional future expansion packs
- no raw source mirrors
- no heavyweight packet assets

## Primary Bundle Shape

The default downloadable bundle remains:

- `proteosphere-lite.sqlite.zst`
- `proteosphere-lite.release_manifest.json`
- `proteosphere-lite.sha256`

Optional human-facing sidecars:

- `proteosphere-lite.contents.md`
- `proteosphere-lite.schema.md`

## Manifest Contract

The manifest should be machine-readable and release-stable.

### Required top-level fields

- `bundle_id`
- `bundle_kind`
- `bundle_version`
- `schema_version`
- `release_id`
- `created_at`
- `packaging_layout`
- `compression`
- `artifact_files`
- `required_assets`
- `optional_assets`
- `table_families`
- `record_counts`
- `source_snapshot_ids`
- `source_coverage_summary`
- `build_inputs`
- `integrity`
- `compatibility`
- `budget_status`
- `content_scope`
- `exclusions`

### Required semantic meaning

#### `bundle_id`

Stable identifier for the bundle family.

Example:
- `proteosphere-lite`

#### `bundle_kind`

Distinguishes:
- `core_default`
- `optional_expansion`
- `debug_bundle`

Default bundle should use:
- `core_default`

#### `bundle_version`

Semantic version for the bundle payload and manifest together.

This must change when:
- table families change
- bundle packaging changes
- release content changes materially

#### `schema_version`

Schema version for the logical library shape, not just the release.

This should stay stable across content-only refreshes.

#### `release_id`

Human and machine readable release token.

Example:
- `2026.04.01-core.1`

#### `packaging_layout`

Allowed values:
- `compressed_sqlite`
- `partitioned_sqlite`
- `read_only_lookup_tables`

Current required value:
- `compressed_sqlite`

#### `compression`

Must explicitly declare:
- algorithm
- optional level
- uncompressed filename

Example:
- `{"algorithm":"zstd","container":"sqlite","filename":"proteosphere-lite.sqlite"}`

#### `artifact_files`

Full list of files included in the release bundle with:
- filename
- size_bytes
- sha256
- required flag
- role

#### `required_assets`

Minimum assets needed for normal library use.

Default required assets:
- `proteosphere-lite.sqlite.zst`
- `proteosphere-lite.release_manifest.json`
- `proteosphere-lite.sha256`

#### `optional_assets`

Useful but non-blocking release assets such as:
- contents docs
- schema docs
- changelog excerpts

#### `table_families`

List of logical content families present in the bundle, such as:

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

Each table family entry should carry:
- `family_name`
- `included`
- `required`
- `record_count`
- `dictionary_coded`
- `notes`

#### `record_counts`

Bundle-wide counts for the included lightweight records.

This should be the first compact health check users see after download.

#### `source_snapshot_ids`

Every bundle must point back to the exact upstream source snapshot boundaries that produced it.

This should include:
- source name
- release or snapshot ID
- manifest ID or hash

#### `source_coverage_summary`

A compact snapshot of what source classes were materially available at bundle build time.

This should include:
- source count
- present / partial / missing counts
- notable gaps

#### `build_inputs`

References to the internal inputs that produced the bundle, such as:
- canonical source path
- summary library source path
- signature materializer release
- packet or coverage artifacts used for governance surfaces

#### `integrity`

Required fields:
- bundle sha256
- manifest sha256
- optional per-table fingerprints

#### `compatibility`

Required fields:
- minimum supported interpreter/tool version
- compatible schema versions
- whether optional expansions are supported

#### `budget_status`

Required fields:
- compressed_size_bytes
- uncompressed_size_bytes
- soft_target_bytes
- warning_threshold_bytes
- hard_cap_bytes
- budget_class
- cap_compliance

#### `content_scope`

Must explicitly say what this bundle is for.

Default scope:
- `planning_governance_only`

#### `exclusions`

Must explicitly declare what is intentionally not in the bundle.

## Size-Budget Contract

The bundle should remain intentionally small and predictable.

### Why a budget is needed

Without a budget, the lightweight library will drift toward becoming a second raw-data mirror. That would break the design intent.

The budget contract is therefore a product boundary, not just an optimization target.

## Budget Classes

### Class A: Target

Compressed size:
- `<= 64 MiB`

Uncompressed size:
- `<= 256 MiB`

Meaning:
- ideal default release shape
- should stay easy to distribute, cache, and inspect

### Class B: Acceptable

Compressed size:
- `> 64 MiB` and `<= 128 MiB`

Uncompressed size:
- `<= 512 MiB`

Meaning:
- still acceptable for GitHub release distribution
- requires explanation of what drove the growth

### Class C: Warning

Compressed size:
- `> 128 MiB` and `<= 256 MiB`

Meaning:
- bundle is still usable, but release notes must call out why
- expansion-pack split should be considered

### Class D: Hard Cap Exceeded

Compressed size:
- `> 256 MiB`

Meaning:
- default bundle should not be published in this state
- the content must either be reduced or split into partitions

## What Counts Against the Budget

Counts against the default bundle budget:

- core SQLite payload
- embedded dictionary tables
- similarity and leakage signatures
- provenance pointers
- compact annotation summaries

Does not count against the default bundle budget:

- raw mirrors
- deferred heavyweight assets
- packet payloads
- optional docs
- future optional enrichment packs

## Budget Guardrails By Table Family

The manifest should also expose per-family size estimates or proportions.

Recommended soft limits by family in the default bundle:

- proteins + variants: `<= 15%`
- motifs/domains/pathways: `<= 20%`
- ligands: `<= 20%`
- interactions: `<= 20%`
- provenance + dictionaries: `<= 10%`
- similarity + leakage signatures: `<= 25%`

These are guardrails, not hard caps. They exist to detect when one family starts dominating the supposedly lightweight bundle.

## Default Exclusions

The default bundle must exclude:

- raw mmCIF, PDB, BCIF, PAE, and MSA assets
- raw assay tables and long assay text
- full MITAB or PSI-MI payloads
- full pathway diagrams or BioPAX/SBML
- full motif instance tables and logos
- cryo-EM maps and validation payloads
- heavy packet outputs

## Trigger For Partitioned Packaging

Move from the single default bundle to optional partitioned packaging when any of these are true:

1. compressed size exceeds `128 MiB` for two consecutive planned releases
2. one logical family exceeds `35%` of the compressed bundle
3. optional enrichment content is frequently changing while core is stable
4. a significant user group only needs a subset of the library

## Required Manifest Acceptance Checks

Before a bundle is considered valid, the manifest should prove:

1. required files are present
2. checksums are valid
3. schema version is declared
4. source snapshot IDs are present
5. budget status is declared
6. excluded content classes are declared
7. record counts are non-null for included table families

## Recommended Default Manifest Example Shape

The contract should be capable of expressing a release like:

- bundle kind: `core_default`
- layout: `compressed_sqlite`
- content scope: `planning_governance_only`
- compressed size class: `A` or `B`
- optional future packs: `none` or listed but not required

## Practical Recommendation

For the next implementation wave, the bundle contract should assume:

- one compressed SQLite core bundle
- one manifest JSON
- one checksum file
- optional human docs
- a hard rule that anything heavy enough to push the core past the budget belongs in a deferred fetch path or future expansion pack

## Bottom Line

The default downloadable lightweight library bundle should be treated as a compact governance artifact with a strict manifest and a strict size budget.

The right contract is:

- explicit manifest fields
- explicit content inclusions and exclusions
- explicit checksum and compatibility metadata
- explicit size budgets with target, warning, and hard-cap thresholds

That keeps the bundle honest, GitHub-friendly, and aligned with the project’s stated architecture rather than letting it expand into an unmanaged second data mirror.
