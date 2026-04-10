# P59 Preview Verified Assets Gate Checklist

This report-only checklist defines the minimum exact assets and tests needed to move the lightweight bundle from `preview_generated_unverified` to `preview_generated_verified_assets`.

## Current State

The live manifest is still unverified:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

The manifest currently reports:

- `bundle_id`: `proteosphere-lite`
- `bundle_version`: `0.1.0-preview`
- `release_id`: `2026.04.01-lightweight-preview.1`
- `manifest_status`: `preview_generated_unverified`
- `validation_status`: `warning`
- `validation_warnings`: `preview_mode_missing_assets`

The current live surface counts are aligned with the manifest:

- proteins: 11
- protein variants: 1874
- structures: 4
- motif annotations: 98
- pathway annotations: 254
- provenance records: 1915

## Operator Surfaces

The checklist is grounded in the current report stack:

- [artifacts/status/p55_bundle_field_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p55_bundle_field_mapping.json)
- [artifacts/status/p56_bundle_contents_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p56_bundle_contents_contract.json)
- [artifacts/status/p58_preview_verified_gate.json](/D:/documents/ProteoSphereV2/artifacts/status/p58_preview_verified_gate.json)
- [docs/reports/proteosphere-lite.contents.md](/D:/documents/ProteoSphereV2/docs/reports/proteosphere-lite.contents.md)
- [docs/reports/proteosphere-lite.schema.md](/D:/documents/ProteoSphereV2/docs/reports/proteosphere-lite.schema.md)

## Minimum Exact Assets

The smallest truthful asset set needed to leave `preview_generated_unverified` is:

1. `proteosphere-lite.sqlite.zst`
1. `proteosphere-lite.release_manifest.json`
1. `proteosphere-lite.sha256`
1. `proteosphere-lite.contents.md`
1. `proteosphere-lite.schema.md`

These are the exact release assets and operator docs the current manifest stack expects. The release manifest must name the preview assets and checksums, and the checksum file must verify the bundle.

## Minimum Exact Tests

The promotion is still blocked until all of the following pass:

1. The preview manifest and release asset list agree.
1. The bundle checksum matches `proteosphere-lite.sha256`.
1. The manifest matches `p55_bundle_field_mapping.json`.
1. The contents document matches `p56_bundle_contents_contract.json`.
1. The live counts stay aligned with the current inventories and no invented families appear.

## What This Does Not Allow

This checklist does not authorize release-grade publication. It also does not allow any claim that the bundle is complete, that missing families are procured, or that the current warning means more than “the preview assets are not yet verified.”

## Bottom Line

`preview_generated_verified_assets` is the next truthful state only after the exact bundle asset trio exists, the operator docs remain aligned, and the manifest checks pass against the current live surfaces.
