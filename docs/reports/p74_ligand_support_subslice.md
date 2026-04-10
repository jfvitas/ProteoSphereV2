# p74 Ligand Support Sub-Slice

This report identifies the narrowest ligand support-only sub-slice that can be stated truthfully today from the current pilot proposal and live evidence.

## Result

The smallest unblocked slice is a four-row support-only readiness card for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`.

`Q9UCM0` stays deferred because the live packet evidence still shows unresolved `structure:Q9UCM0` and `ppi:Q9UCM0` blockers.

## Why This Is The Narrowest Truthful Slice

- The pilot proposal already isolates four ligand-only gap proteins that can be described without claiming bundle mutation.
- The live bundle manifest still has `ligands.included=false` and `ligands.record_count=0`, so the truthful move today is a support surface, not ligand materialization.
- The operator dashboard remains `no-go`, with `release_grade_status=blocked_on_release_grade_bar`, so this must stay report-only.
- `Q9UCM0` is not part of the first support lane because it is still multi-modality blocked.

## Support-Only Contract

| Field | Value |
| --- | --- |
| Surface | `ligand_identity_support_readiness_preview_v1` |
| Kind | `report_card` |
| Support rows | `4` |
| Accessions | `P00387`, `P09105`, `Q2TAC2`, `Q9NZD4` |
| Deferred accession | `Q9UCM0` |
| Truth boundary | report-only, no bundle mutation, no latest-promotion change |

Minimum support fields:
- `accession`
- `pilot_role`
- `pilot_lane_status`
- `current_blocker`
- `next_stage_target`
- `source_provenance_refs`

Explicit exclusions:
- ligand row materialization
- `ligand_identity_group`
- `binding_context_group`
- ligand similarity signatures
- interaction family materialization
- operator state schema changes

## Next Truthful Stage

The next stage after this support card is the `ligand_identity_core_pilot` from the existing stage1 ligand contract and execution order artifacts.

That later stage is still blocked on actual ligand-family materialization and on keeping grouping fields null until the bundle is truthfully populated.

## Bottom Line

The narrowest unblocked ligand support-only sub-slice is a four-row readiness card for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`, with `Q9UCM0` deferred and all ligand materialization claims held back.
