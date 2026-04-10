# Ligand Support Readiness Preview

- Status: `complete`
- Surface kind: `support_only_readiness_card`
- Support rows: `4`
- Deferred accessions: `Q9UCM0`
- Bundle ligands included: `False`
- Ligand readiness ladder counts: `{"absent": 1, "grounded preview-safe": 2, "support-only": 2}`

## Support Rows

- `P00387` -> role=`lead_anchor`, lane=`bulk_assay_actionable`, blocker=`bundle_inclusion_pending_governing_promotion`, readiness=`grounded preview-safe`, next=`keep_grounded_rows_visible_and_non_governing`
- `P09105` -> role=`support_candidate`, lane=`structure_companion_only`, blocker=`no_local_ligand_evidence_yet`, readiness=`support-only`, next=`hold_for_ligand_acquisition`
- `Q2TAC2` -> role=`support_candidate`, lane=`structure_companion_only`, blocker=`no_local_ligand_evidence_yet`, readiness=`support-only`, next=`hold_for_ligand_acquisition`
- `Q9NZD4` -> role=`bridge_rescue_candidate`, lane=`rescuable_now`, blocker=`bundle_inclusion_pending_governing_promotion`, readiness=`grounded preview-safe`, next=`keep_grounded_rows_visible_and_non_governing`

## Truth Boundary

- This is a support-only ligand readiness surface for the current gap accessions. It does not materialize ligand rows, does not change bundle ligand inclusion, and keeps absent rows conservative.
