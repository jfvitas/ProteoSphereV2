# P54 Bundle Manifest Export Contract

Date: 2026-04-01
Artifact: `p54_bundle_manifest_export_contract`

## Objective

Define a `report-only executable contract` for a future manifest exporter that turns the preview model in [p53_bundle_manifest_example.md](/D:/documents/ProteoSphereV2/docs/reports/p53_bundle_manifest_example.md) into a real script surface.

This artifact does not add code. It defines what a future exporter script must accept, emit, validate, and refuse to claim.

The contract is grounded in:

- [p50_lightweight_bundle_packaging_proposal.md](/D:/documents/ProteoSphereV2/docs/reports/p50_lightweight_bundle_packaging_proposal.md)
- [p51_bundle_manifest_budget_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p51_bundle_manifest_budget_contract.md)
- [p53_bundle_manifest_example.md](/D:/documents/ProteoSphereV2/docs/reports/p53_bundle_manifest_example.md)
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)

## Why A Dedicated Export Contract Is Needed

`P53` is a truthful static example. It is not yet an execution surface.

A real exporter needs to make three things explicit:

- which repo artifacts are authoritative for which manifest fields
- which fields can be estimated versus measured
- when the exporter must refuse to produce a publish-grade manifest

Without that contract, the first implementation will be too loose and will drift away from the honesty boundaries already established in `P51` and `P53`.

## Proposed Script Surface

Recommended future script path:

- `scripts/export_bundle_manifest.py`

Recommended primary command shape:

```powershell
python scripts\export_bundle_manifest.py `
  --mode example_from_current_surfaces `
  --output artifacts\status\bundle_manifest.generated.json `
  --summary docs\reports\bundle_manifest.generated.md
```

Recommended measured command shape:

```powershell
python scripts\export_bundle_manifest.py `
  --mode measured_from_built_bundle `
  --bundle-path dist\proteosphere-lite.sqlite.zst `
  --manifest-path dist\proteosphere-lite.release_manifest.json `
  --checksum-path dist\proteosphere-lite.sha256 `
  --output artifacts\status\bundle_manifest.measured.json `
  --summary docs\reports\bundle_manifest.measured.md
```

## Execution Modes

The exporter should support exactly three modes.

### `example_from_current_surfaces`

Purpose:

- emit a truthful preview/debug manifest from current repo surfaces

Behavior:

- uses current library and coverage artifacts
- estimates bundle sizes
- emits placeholder integrity values
- defaults to `bundle_kind = debug_bundle`
- must not claim a built release asset exists

This is the mode that operationalizes `P53`.

### `measured_from_built_bundle`

Purpose:

- emit a real manifest for a physically built bundle

Behavior:

- requires the built compressed SQLite asset and companion files
- measures exact file sizes
- computes or verifies real checksums
- may emit `core_default` only if all `P51` acceptance checks pass

### `validate_existing_manifest`

Purpose:

- validate a manifest that already exists

Behavior:

- reads an existing manifest
- checks field presence, budget compliance, input consistency, and honesty boundaries
- emits validation status without regenerating the main manifest unless explicitly requested

## Required Inputs

The exporter should accept these logical inputs.

### Contract and proposal inputs

- [p50_lightweight_bundle_packaging_proposal.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_lightweight_bundle_packaging_proposal.json)
- [p51_bundle_manifest_budget_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p51_bundle_manifest_budget_contract.json)

### Current-surface grounding inputs

- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)

### Optional measured-mode inputs

- built bundle asset, expected default:
  - `dist/proteosphere-lite.sqlite.zst`
- built manifest sidecar, expected default:
  - `dist/proteosphere-lite.release_manifest.json`
- checksum root file, expected default:
  - `dist/proteosphere-lite.sha256`
- optional human docs:
  - `dist/proteosphere-lite.contents.md`
  - `dist/proteosphere-lite.schema.md`

## Required Outputs

The exporter should be able to emit:

- one machine-readable manifest JSON
- one optional markdown summary

Recommended default output roles:

- primary manifest:
  - `artifacts/status/<name>.json`
- human summary:
  - `docs/reports/<name>.md`

## Field Sourcing Contract

Each field should come from a specific source or computation path.

### Fixed or policy-driven fields

- `bundle_id`
  - fixed default: `proteosphere-lite`
- `packaging_layout`
  - from `P50`, default `compressed_sqlite`
- `required_assets`
  - from `P51`
- `optional_assets`
  - from `P51`
- `content_scope`
  - default from `P51`, currently `planning_governance_only`
- `table_families`
  - family list from `P51`

### Current-surface derived fields

- `record_counts`
  - derived from [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json) for currently materialized lightweight families
- `source_snapshot_ids`
  - derived from current summary-library source lineage and [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
- `source_coverage_summary`
  - derived from [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
- `build_inputs`
  - literal paths to all repo artifacts used in the export

### Measured-mode derived fields

- `artifact_files[*].size_bytes`
  - measured from files on disk
- `artifact_files[*].sha256`
  - computed or verified from files on disk
- `integrity`
  - computed from the built artifacts
- `budget_status`
  - computed from measured file sizes using `P51` budget classes

### Example-mode only estimated fields

- `artifact_files[*].size_bytes`
  - estimated
- `artifact_files[*].sha256`
  - placeholder value
- `integrity`
  - placeholder or explicitly estimated status
- `budget_status`
  - computed from estimated sizes and flagged as estimated, not measured

## Recommended Export Rules

The exporter should follow this sequence.

1. Load `P50` and `P51`.
2. Resolve mode-specific required inputs.
3. Read current repo surfaces.
4. Build the canonical family list from `P51`.
5. Populate included-family counts only for materialized families.
6. Populate zero-count excluded families explicitly.
7. Derive source lineage and coverage summary.
8. In measured mode, measure asset sizes and hashes.
9. In example mode, mark sizes and integrity as estimated.
10. Compute budget class and cap compliance.
11. Run acceptance checks.
12. Refuse invalid publish-grade outputs.

## Honesty Boundaries

The exporter must enforce these rules.

### The exporter must not:

- emit `core_default` in example mode
- synthesize real checksums for assets that do not exist
- mark non-materialized families as included
- infer structure, ligand, interaction, signature, or leakage-group counts from canonical state alone when those families are not materialized in the lightweight bundle
- claim `required_files_present = true` in measured mode if required assets are missing

### The exporter may:

- emit an estimated preview manifest in example mode
- carry canonical counts as context in notes or metadata
- emit `debug_bundle` or `preview_bundle` based on current surfaces

## Acceptance States

The exporter should classify outputs into one of these states.

- `estimated_preview_valid`
  - contract-valid preview manifest from repo surfaces
- `measured_release_candidate_valid`
  - built artifact present and all required checks pass
- `validation_only_passed`
  - existing manifest satisfies contract rules
- `contract_error`
  - required field or policy violation
- `input_error`
  - missing or unreadable input
- `integrity_error`
  - measured asset checksum or size mismatch
- `budget_error`
  - size budget missing or hard cap exceeded

## Exit Code Contract

Recommended future exit codes:

- `0`
  - success
- `2`
  - contract violation
- `3`
  - missing required input
- `4`
  - integrity failure
- `5`
  - budget failure

## Current Repo Grounding

If the exporter were run in `example_from_current_surfaces` mode today, it should ground itself in:

- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
  - `11` proteins
  - `13` motif refs
  - `85` domain refs
  - `254` pathway refs
  - `17` provenance pointers
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)
  - `11` proteins
  - `4124` ligands
  - `5138` assays
  - `0` unresolved assay cases
- [source_coverage_matrix.json](/D:/documents/ProteoSphereV2/artifacts/status/source_coverage_matrix.json)
  - `53` tracked sources
  - `48` present
  - `2` partial
  - `3` missing

That means the exporter should still produce a preview/debug manifest, not a final `core_default` bundle manifest.

## Bottom Line

`P54` converts the static `P53` example into a future execution contract.

The essential rule is simple:

- `P53` defines what a truthful preview manifest looks like
- `P54` defines how a script must generate that manifest, when it may upgrade to a measured release manifest, and when it must refuse to do so

That gives the repo a clean path from report-only examples to a real export surface without weakening the truth boundaries already established in `P50` through `P53`.
