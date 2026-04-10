# P60 Preview Bundle Handoff Note

This is the compact operator handoff for the newly verified lightweight preview bundle.

## Verified State

The lightweight bundle is now in `preview_generated_verified_assets`.

Grounding artifacts:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

The live validation reports aligned preview counts and verified assets.

## Bundle Payload to Share

Share the preview payload from:

- [artifacts/bundles/preview/proteosphere-lite.sqlite.zst](/D:/documents/ProteoSphereV2/artifacts/bundles/preview/proteosphere-lite.sqlite.zst)
- [artifacts/bundles/preview/proteosphere-lite.release_manifest.json](/D:/documents/ProteoSphereV2/artifacts/bundles/preview/proteosphere-lite.release_manifest.json)
- [artifacts/bundles/preview/proteosphere-lite.sha256](/D:/documents/ProteoSphereV2/artifacts/bundles/preview/proteosphere-lite.sha256)

The file hashes match the manifest, so the preview bundle payload is internally consistent.

## Companion Operator Docs

Include the report companions alongside the bundle when handing it off:

- [docs/reports/proteosphere-lite.contents.md](/D:/documents/ProteoSphereV2/docs/reports/proteosphere-lite.contents.md)
- [docs/reports/proteosphere-lite.schema.md](/D:/documents/ProteoSphereV2/docs/reports/proteosphere-lite.schema.md)

These are operator-facing documents, not release payload.

## Handoff Rule

Treat this as a verified preview handoff only. It is safe to share as a preview bundle, but it is not a release-grade publication and it does not claim completeness beyond the current live surfaces.

## Minimum Verification

Before passing it onward, confirm:

1. the three bundle files in `artifacts/bundles/preview` still hash-match the manifest
1. the manifest status remains `preview_generated_verified_assets`
1. the contents and schema docs remain present and aligned

## Boundary

Do not reclassify the preview as final or complete. The handoff is about sharing a verified preview, not promoting a release.
