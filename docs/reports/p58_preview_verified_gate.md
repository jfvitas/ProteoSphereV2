# P58 Preview Verified Gate

This report-only note defines what would be required to move the current preview manifest from `preview_generated_unverified` to `preview_generated_verified_assets` without claiming release readiness.

## Current State

The preview remains unverified until there is a real run-scoped preview manifest and a matching set of verified bundle assets.

The gate is grounded in:

- [artifacts/status/p57_bundle_preview_gate.json](/D:/documents/ProteoSphereV2/artifacts/status/p57_bundle_preview_gate.json)
- [docs/reports/p57_bundle_preview_gate.md](/D:/documents/ProteoSphereV2/docs/reports/p57_bundle_preview_gate.md)
- [artifacts/status/p55_bundle_field_mapping.json](/D:/documents/ProteoSphereV2/artifacts/status/p55_bundle_field_mapping.json)
- [docs/reports/p55_bundle_field_mapping.md](/D:/documents/ProteoSphereV2/docs/reports/p55_bundle_field_mapping.md)
- [artifacts/status/p56_bundle_contents_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p56_bundle_contents_contract.json)
- [docs/reports/p56_bundle_contents_contract.md](/D:/documents/ProteoSphereV2/docs/reports/p56_bundle_contents_contract.md)

## What Must Exist

To move into `preview_generated_verified_assets`, the repo needs all of the following:

- a generated preview manifest artifact
- the preview manifest checksum file
- the preview SQLite bundle asset
- the preview contents document
- a release-manifest entry that names the preview assets and their checksums

## What Must Be Verified

The generated assets must be checked for:

1. internal consistency between the preview manifest and the asset list
1. checksum agreement between the preview bundle and its checksum file
1. alignment with the bundle field mapping in `p55_bundle_field_mapping`
1. alignment with the bundle contents contract in `p56_bundle_contents_contract`
1. preservation of the current live surfaces only, without invented families or completeness claims

## Still Not Release Ready

Even after the preview assets are verified, the state is still not release ready. This transition only proves that the preview assets are coherent and check out against the report stack.

That means the gate must still reject:

- release-grade publication claims
- final completeness claims
- any claim that missing families have been procured
- any claim that `ELM`, `mega_motif_base`, or `motivated_proteins` are resolved beyond the current report truth

## Gate Logic

The state can move to `preview_generated_verified_assets` only when:

- the preview manifest exists
- the preview assets are present and checksum-verified
- the preview contents still match the report contracts
- the preview is still treated as a preview, not a release

## Bottom Line

`preview_generated_verified_assets` is a stronger preview state, not a release state. It says the preview assets are real and internally consistent, but it does not say the bundle is ready for public release.
