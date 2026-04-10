# Operator Next Actions Preview

- Status: `complete`
- Action count: `4`

## Prioritized Actions

- `1` `ligand` -> `P09105` / `hold_until_validated_local_evidence_exists` / status `blocked_pending_acquisition`
  detail: `{"best_next_action": "Extract the AlphaFold raw model for P09105 into a reusable structure companion", "best_next_source": "D:\\documents\\ProteoSphereV2\\data\\raw\\alphafold_local\\20260323T160000Z\\P09105\\AF-P09105-F1-model_v6.pdb.gz", "candidate_only_rows_non_governing": true, "current_grounded_accessions": ["P00387"], "fallback_accession": "Q2TAC2", "fallback_accession_gate_status": "blocked_pending_acquisition", "fallback_trigger_rule": "Only advance from P09105 to Q2TAC2 after the selected accession remains blocked_pending_acquisition and the blocker has been recorded without emitting new grounded ligand rows.", "gap_probe_classification": "requires_extraction", "selected_accession_gate_status": "blocked_pending_acquisition", "source_classification": "structure_companion_only"}`
- `2` `structure` -> `P31749` / `single_accession_candidate_only_promotion` / status `aligned`
  detail: `{"candidate_variant_anchor_count": 5, "deferred_accession": "P04637", "direct_structure_backed_join_certified": false}`
- `3` `split` -> `split` / `wait_for_unlock_gate_before_request_emission` / status `blocked_report_emitted`
  detail: `{"cv_fold_export_unlocked": false, "cv_folds_materialized": false, "request_scope": true}`
- `4` `duplicate_cleanup` -> `duplicate_cleanup` / `refresh_exact_duplicate_plan_before_next_execution` / status `refresh_required_after_consumed_preview_batch`
  detail: `{"all_constraints_satisfied_preview": false, "batch_size_limit": 1, "delete_enabled": false, "delete_ready_action_count": 0, "duplicate_class": "exact_duplicate_same_release", "execution_blocked": true, "preview_manifest_status": "no_current_valid_batch_requires_refresh", "refresh_required": true}`

## Truth Boundary

- This is an operator-only consolidation of the current next-step surfaces. It does not certify structure joins, does not emit a second grounded ligand accession, does not unlock fold export, and does not authorize duplicate cleanup mutation.
