# p80 P00387 Lead Lane Follow-On

This note recommends the smallest safe follow-on for the P00387 lead lane.

## Recommendation

The next smallest safe follow-on is a `P00387`-only bulk-assay support envelope.

The action to associate with it is:

`ingest_local_bulk_assay`

## Why This Is The Right Size

- `operator_next_actions_preview` already lists `P00387` as the top ligand action with `ingest_local_bulk_assay`.
- The ligand queue preview and the support-ready surface both mark `P00387` as the lead anchor.
- The stage-1 handoff keeps `P00387` first.
- The operator dashboard is still `no-go`, so the follow-on must stay report-only and avoid any ligand materialization claim.

## What It Should Capture

- `accession`
- `source_ref`
- `lead_anchor_role`
- `bulk_assay_actionability`
- `source_provenance_refs`
- `next_truthful_stage`

## What It Must Not Claim

- ligand rows are materialized
- `bundle ligands.included` is true
- `ligand_identity_group` is non-null
- `Q9UCM0` is unblocked
- the operator dashboard is release-ready

## Truth Boundary

- report-only
- no ligand row materialization
- no bundle mutation
- no latest-promotion changes
- `Q9UCM0` deferred

## Bottom Line

The smallest safe P00387 lead-lane follow-on is a report-only bulk-assay support envelope for `P00387` only, with `ingest_local_bulk_assay` as the action and no ligand materialization claim.
