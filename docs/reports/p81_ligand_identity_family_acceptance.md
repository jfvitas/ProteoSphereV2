# P81 Ligand Identity Family Acceptance

This is a report-only acceptance review of whether the current ligand identity pilot preview is safe to include as a compact preview bundle family without claiming real ligand row materialization, grounded in [ligand_identity_pilot_preview.json](D:/documents/ProteoSphereV2/artifacts/status/ligand_identity_pilot_preview.json), [ligand_support_readiness_preview.json](D:/documents/ProteoSphereV2/artifacts/status/ligand_support_readiness_preview.json), [p00387_local_chembl_ligand_payload.json](D:/documents/ProteoSphereV2/artifacts/status/p00387_local_chembl_ligand_payload.json), [local_bridge_ligand_payloads.real.json](D:/documents/ProteoSphereV2/artifacts/status/local_bridge_ligand_payloads.real.json), and [lightweight_bundle_manifest.json](D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json).

## Verdict

**No.**

The current pilot is safe to keep as a report-only operator preview, but it is not yet safe to include as a compact bundle family because the bundle still excludes ligands, reports zero ligand records, and the evidence trail is still support-only rather than a normalized ligand family.

## Current Truth

The bundle boundary is still explicit:

- `ligands.included = false`
- `ligands.record_count = 0`
- `bundle_kind = debug_bundle`
- `bundle_budget_class = A`
- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`

The pilot preview itself is also explicit:

- it has 4 rows
- it remains report-only
- it does not materialize ligand rows
- it keeps `Q9UCM0` deferred

## Why The Answer Is No

The pilot is good operator guidance, but not yet a bundle family:

- `P00387` has local ChEMBL payload support, but that payload is fresh-run scoped only and does not promote the protected latest snapshot.
- `Q9NZD4` is the only clear bridge-rescue case, and it is still a rescue preview rather than a materialized ligand row.
- `P09105` and `Q2TAC2` remain `structure_companion_only` and still say `no_local_ligand_evidence_yet`.
- `Q9UCM0` is still deferred because the required acquisition is not there yet.

The support-readiness surface confirms the same boundary:

- it is ready for operator preview
- it still reports `bundle_ligands_included = false`
- it still reports `bundle_ligand_record_count = 0`

## What Is Safe Now

What is safe today is narrower than bundle-family inclusion:

- keep the pilot as a report-only operator preview
- use the four-row ordering as support guidance
- keep `Q9UCM0` deferred
- keep the bundle ligands family excluded until real ligand rows exist

## What Would Change The Answer

This would become a yes only after the repo has:

- a truly materialized ligand family in the bundle manifest
- non-zero ligand record counts backed by canonicalized ligand rows
- a validation surface that certifies ligand rows rather than support-only preview records

## Boundary

This note is report-only. It does not authorize release promotion, does not mutate bundle assets, and does not claim real ligand materialization. The safest answer for the current state is no, but the preview remains useful as operator guidance.
