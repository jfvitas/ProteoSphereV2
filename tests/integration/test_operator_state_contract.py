from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from importlib import util
from pathlib import Path

import pytest

from core.library.summary_record import (
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_operator_state.py"


def _load_validator_module():
    spec = util.spec_from_file_location("validate_operator_state", VALIDATOR_PATH)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("PowerShell is required for the operator-state contract integration test")


def _run_validator(*extra_args: str) -> dict:
    command = [
        sys.executable,
        str(VALIDATOR_PATH),
        *extra_args,
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _materialized_protein_record() -> ProteinSummaryRecord:
    return ProteinSummaryRecord(
        summary_id="protein:P12345",
        protein_ref="protein:P12345",
        protein_name="Example protein",
        organism_name="Homo sapiens",
        taxon_id=9606,
        sequence_checksum="abc123",
        sequence_version="2026_03",
        sequence_length=6,
        gene_names=("GENE1",),
        aliases=("P12345",),
        join_status="joined",
        context=SummaryRecordContext(
            storage_notes=("already materialized",),
        ),
    )


def test_operator_state_validator_confirms_live_parity() -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator-state contract integration test")

    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "export_operator_dashboard.py")],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    payload = _run_validator("--json")
    dashboard = json.loads(
        (
            REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "operator_dashboard.json"
        ).read_text(encoding="utf-8")
    )

    assert payload["status"] == "ok"
    assert payload["schema_version"] == "1.0.0"
    assert payload["task_id"] == "P6-T029"
    assert payload["parity"]["completion_status"] == "completed"
    assert payload["parity"]["dashboard_status"] == "completed"
    assert payload["parity"]["release_grade_status"] == "closed_not_release_ready"
    assert payload["parity"]["selected_accession_count"] == 12
    assert payload["parity"]["cohort_size"] == 12
    assert payload["parity"]["split_counts"]["train"] == 8
    assert payload["parity"]["split_counts"]["val"] == 2
    assert payload["parity"]["split_counts"]["test"] == 2
    assert payload["source_files"]["operator_dashboard_path"].endswith("operator_dashboard.json")
    assert dashboard["procurement_status"]["canonical_latest"]["status"] == "ready"
    assert (
        dashboard["procurement_status"]["canonical_latest"]["unresolved_counts"][
            "assay_unresolved_cases"
        ]
        == 0
    )
    assert dashboard["procurement_status"]["summary_library_inventory"]["record_count"] == 11
    assert (
        dashboard["procurement_status"]["summary_library_inventory"]["record_type_counts"][
            "protein_variant"
        ]
        == 0
    )
    assert (
        dashboard["procurement_status"]["protein_variant_library_inventory"][
            "record_type_counts"
        ]["protein_variant"]
        == dashboard["procurement_status"]["protein_variant_library_inventory"]["record_count"]
    )
    assert (
        dashboard["procurement_status"]["protein_variant_library_inventory"]["record_count"] > 0
    )
    assert (
        dashboard["procurement_status"]["structure_unit_library_inventory"][
            "record_type_counts"
        ]["structure_unit"]
        == 4
    )
    assert (
        dashboard["procurement_status"]["protein_similarity_signature_preview"][
            "row_count"
        ]
        == 11
    )
    assert dashboard["procurement_status"]["protein_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["dictionary_preview"]["row_count"] > 0
    assert dashboard["procurement_status"]["dictionary_preview"]["namespace_count"] > 0
    assert "Reactome" in dashboard["procurement_status"]["dictionary_preview"]["namespaces"]
    assert dashboard["procurement_status"]["dictionary_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["dictionary_preview"][
        "biological_content_family"
    ] is False
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "row_count"
    ] > 0
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "included_namespaces"
    ] == ["InterPro", "PROSITE", "Pfam"]
    assert dashboard["procurement_status"]["motif_domain_compact_preview_family"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "row_count"
    ] == 2
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "accession_count"
    ] == 2
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "source_overlap_accessions"
    ] == ["P69905", "P09105"]
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "candidate_only_row_count"
    ] == 2
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is False
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "interaction_family_materialized"
    ] is False
    assert dashboard["procurement_status"]["interaction_similarity_signature_preview"][
        "direct_interaction_family_claimed"
    ] is False
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["status"] == "aligned"
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["row_count"] == 2
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["candidate_only_accessions"] == ["P69905", "P09105"]
    assert dashboard["procurement_status"][
        "interaction_similarity_signature_validation"
    ]["bundle_safe_immediately"] is False
    assert dashboard["procurement_status"]["sabio_rk_support_preview"]["status"] == "complete"
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "supported_accession_count"
    ] == 3
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "supported_accessions"
    ] == ["P00387", "P04637", "P31749"]
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "live_kinetic_ids_verified"
    ] is False
    assert dashboard["procurement_status"]["sabio_rk_support_preview"][
        "dashboard_blocked"
    ] is True
    assert dashboard["procurement_status"]["procurement_tail_freeze_gate_preview"][
        "gate_status"
    ] == "ready_to_freeze_complete_mirror"
    assert dashboard["procurement_status"]["procurement_tail_freeze_gate_preview"][
        "remaining_gap_file_count"
    ] == 0
    assert dashboard["procurement_status"]["procurement_tail_freeze_gate_preview"][
        "not_yet_started_file_count"
    ] == 0
    assert dashboard["procurement_status"][
        "string_interaction_materialization_plan_preview"
    ]["report_only"] is True
    assert dashboard["procurement_status"][
        "uniref_cluster_materialization_plan_preview"
    ]["report_only"] is True
    assert dashboard["procurement_status"]["pdb_enrichment_scrape_registry_preview"][
        "row_count"
    ] == 2
    assert dashboard["procurement_status"]["structure_entry_context_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["pdb_enrichment_harvest_preview"][
        "harvested_structure_count"
    ] == 2
    assert dashboard["procurement_status"]["binding_measurement_registry_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["interaction_context_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["protein_origin_context_preview"][
        "error_count"
    ] == 0
    assert dashboard["procurement_status"]["ligand_context_scrape_registry_preview"][
        "row_count"
    ] >= 1
    assert dashboard["procurement_status"]["targeted_page_scrape_registry_preview"][
        "page_scraping_started"
    ] is False
    assert dashboard["procurement_status"]["post_tail_library_forecast"][
        "governing"
    ] is False
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "support_accessions"
    ] == ["P00387", "P09105", "Q2TAC2", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "deferred_accessions"
    ] == ["Q9UCM0"]
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "bundle_ligands_included"
    ] is False
    assert dashboard["procurement_status"]["ligand_support_readiness_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "selected_accession"
    ] == "P09105"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "selected_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "fallback_accession"
    ] == "Q2TAC2"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "fallback_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_gate_preview"][
        "can_materialize_new_grounded_accession_now"
    ] is False
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "selected_accession"
    ] == "P09105"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "selected_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "fallback_accession"
    ] == "Q2TAC2"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "fallback_accession_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["next_real_ligand_row_decision_preview"][
        "minimum_grounded_promotion_evidence_count"
    ] == 3
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "first_accession"
    ] == "P00387"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "second_accession"
    ] == "Q9NZD4"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "ordered_accessions"
    ] == ["P00387", "Q9NZD4", "P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "grounded_accession_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "grounded_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "first_accession_evidence_kind"
    ] == "local_chembl_bulk_assay_summary"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "row_complete_operator_summary"
    ] is True
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "deferred_accession"
    ] == "Q9UCM0"
    assert dashboard["procurement_status"]["ligand_identity_pilot_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "ordered_accessions"
    ] == ["P00387", "Q9NZD4", "P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "deferred_accession"
    ] == "Q9UCM0"
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["ligand_stage1_operator_queue_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "accession"
    ] == "P00387"
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "target_chembl_id"
    ] == "CHEMBL2146"
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "rows_emitted"
    ] == 25
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["p00387_ligand_extraction_validation_preview"][
        "canonical_ligand_materialization_claimed"
    ] is False
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "accession"
    ] == "Q9NZD4"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "best_pdb_id"
    ] == "1Y01"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "component_id"
    ] == "CHK"
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["q9nzd4_bridge_validation_preview"][
        "candidate_only"
    ] is True
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "row_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "validated_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "aligned_row_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "candidate_only_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_stage1_validation_panel_preview"][
        "bundle_ligands_included"
    ] is False
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "ordered_accessions"
    ] == ["P00387", "Q9NZD4", "P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "grounded_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "held_support_only_accessions"
    ] == ["P09105", "Q2TAC2"]
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "candidate_only_accessions"
    ] == []
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "ready_for_operator_preview"
    ] is True
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "ligand_rows_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_identity_core_materialization_preview"][
        "bundle_ligands_included"
    ] is False
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "materialized_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "grounded_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "candidate_only_accessions"
    ] == []
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "grounded_row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "candidate_only_row_count"
    ] == 0
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "ligand_rows_materialized"
    ] is True
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "bundle_ligands_included"
    ] is True
    assert dashboard["procurement_status"]["ligand_row_materialization_preview"][
        "canonical_ligand_materialization_claimed"
    ] is False
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "accession_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "exact_identity_group_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "chemical_series_group_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "candidate_only_count"
    ] == 1
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "ligand_rows_materialized"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_preview"][
        "canonical_ligand_reconciliation_claimed"
    ] is False
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "gate_status"
    ] == "ready_for_signature_preview"
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "identity_core_preview_row_count"
    ] == 4
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "identity_core_grounded_accession_count"
    ] == 2
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "ligands_materialized"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "ligand_record_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "next_unlocked_stage"
    ] == "ligand_similarity_signature_preview"
    assert dashboard["procurement_status"]["ligand_similarity_signature_gate_preview"][
        "ligand_similarity_signatures_materialized"
    ] is False
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "row_count"
    ] == 24
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "grounded_accessions"
    ] == ["P00387"]
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "candidate_only_accessions"
    ] == ["Q9NZD4"]
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "policy_mode"
    ] == "mixed_grounded_and_candidate_only_preview"
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "candidate_only_rows_non_governing"
    ] is True
    assert dashboard["procurement_status"]["ligand_similarity_signature_validation"][
        "split_claims_changed"
    ] is False
    assert (
        dashboard["procurement_status"]["structure_similarity_signature_preview"][
            "row_count"
        ]
        == 4
    )
    assert dashboard["procurement_status"]["structure_similarity_signature_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert (
        dashboard["procurement_status"]["structure_variant_bridge_summary"][
            "overlap_protein_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_variant_bridge_summary"][
        "overlap_proteins"
    ] == ["protein:P68871", "protein:P69905"]
    assert (
        dashboard["procurement_status"]["structure_variant_candidate_map"][
            "candidate_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_variant_candidate_map"][
        "candidate_statuses"
    ] == ["candidate_only_no_variant_anchor"]
    assert (
        dashboard["procurement_status"]["structure_followup_anchor_candidates"][
            "row_count"
        ]
        == 2
    )
    assert dashboard["procurement_status"]["structure_followup_anchor_candidates"][
        "candidate_accessions"
    ] == ["P04637", "P31749"]
    assert dashboard["procurement_status"]["structure_followup_anchor_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["structure_followup_anchor_validation"][
        "issues"
    ] == []
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "target_accession"
    ] == "P31749"
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "payload_accessions"
    ] == ["P31749", "P04637"]
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "payload_row_count"
    ] == 2
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "candidate_only_no_variant_anchor"
    ] is True
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "direct_structure_backed_join_certified"
    ] is False
    assert dashboard["procurement_status"]["structure_followup_payload_preview"][
        "candidate_variant_anchor_count_total"
    ] == 10
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "selected_accession"
    ] == "P31749"
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "deferred_accession"
    ] == "P04637"
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "payload_row_count"
    ] == 1
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "single_accession_scope"
    ] is True
    assert dashboard["procurement_status"]["structure_followup_single_accession_preview"][
        "direct_structure_backed_join_certified"
    ] is False
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["selected_accession"] == "P31749"
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["deferred_accession"] == "P04637"
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["anchor_validation_status"] == "aligned"
    assert dashboard["procurement_status"][
        "structure_followup_single_accession_validation_preview"
    ]["direct_structure_backed_join_certified"] is False
    assert dashboard["procurement_status"]["entity_signature_preview"]["row_count"] > 0
    assert dashboard["procurement_status"]["entity_signature_preview"][
        "ligand_groups_materialized"
    ] is False
    assert dashboard["procurement_status"]["entity_split_candidate_preview"][
        "ready_for_split_engine"
    ] is True
    assert dashboard["procurement_status"]["entity_split_candidate_preview"][
        "default_hard_group"
    ] == "protein_spine_group"
    assert dashboard["procurement_status"]["entity_split_simulation_preview"][
        "final_split_committed"
    ] is False
    assert dashboard["procurement_status"]["entity_split_simulation_preview"][
        "assignment_count"
    ] > 0
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "recipe_id"
    ] == "protein_spine_first_split_recipe_v1"
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "primary_hard_group"
    ] == "protein_spine_group"
    assert dashboard["procurement_status"]["entity_split_recipe_preview"][
        "ready_for_recipe_export"
    ] is True
    assert dashboard["procurement_status"]["entity_split_assignment_preview"][
        "group_row_count"
    ] == 11
    assert dashboard["procurement_status"]["entity_split_assignment_preview"][
        "ready_for_fold_export"
    ] is False
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "recipe_id"
    ] == "protein_spine_first_split_recipe_v1"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "ready_for_split_engine_dry_run"
    ] is True
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_non_governing_preview_ready"
    ] is True
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "ligand_governing_split_ready"
    ] is True
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_ligand_rows_status"
    ] == "available_non_governing"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_ligand_grounded_accession_count"
    ] == 2
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_motif_domain_status"
    ] == "available_non_governing"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "supplemental_interaction_similarity_status"
    ] == "blocked_candidate_only"
    assert dashboard["procurement_status"]["split_engine_input_preview"][
        "cv_folds_materialized"
    ] is True
    assert dashboard["procurement_status"]["split_engine_dry_run_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_engine_dry_run_validation"][
        "issue_count"
    ] == 0
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "status"
    ] == "open_run_scoped_materialized"
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "gate_id"
    ] == "cv_fold_export_unlock_gate"
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "dry_run_validation_status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "cv_fold_export_unlocked"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_gate_preview"][
        "ready_for_fold_export"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_gate_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_gate_validation"][
        "gate_status"
    ] == "open_run_scoped_materialized"
    assert dashboard["procurement_status"]["split_fold_export_gate_validation"][
        "cv_fold_export_unlocked"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "stage_id"
    ] == "run_scoped_fold_export_staging"
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_staging_preview"][
        "cv_fold_export_unlocked"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_staging_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_staging_validation"][
        "stage_status"
    ] == "complete"
    assert dashboard["procurement_status"]["split_fold_export_staging_validation"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "stage_id"
    ] == "cv_fold_export_unlock_gate_check"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_post_staging_gate_check_preview"][
        "cv_fold_export_unlocked"
    ] is True
    assert dashboard["procurement_status"]["split_post_staging_gate_check_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_validation"][
        "stage_status"
    ] == "complete"
    assert dashboard["procurement_status"]["split_post_staging_gate_check_validation"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "stage_id"
    ] == "run_scoped_fold_export_request"
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "request_only_no_fold_materialization"
    ] is False
    assert dashboard["procurement_status"]["split_fold_export_request_preview"][
        "cv_fold_export_unlocked"
    ] is True
    assert dashboard["procurement_status"]["split_fold_export_request_validation"][
        "status"
    ] == "aligned"
    assert dashboard["procurement_status"]["split_fold_export_request_validation"][
        "stage_status"
    ] == "complete"
    assert dashboard["procurement_status"]["split_fold_export_request_validation"][
        "run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "status"
    ] == "complete"
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "execution_status"
    ] == "refresh_required_after_consumed_preview_batch"
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "preview_manifest_status"
    ] == "no_current_valid_batch_requires_refresh"
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "batch_size_limit"
    ] == 1
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "refresh_required"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_first_execution_preview"][
        "delete_enabled"
    ] is False
    assert dashboard["procurement_status"][
        "duplicate_cleanup_delete_ready_manifest_preview"
    ]["preview_manifest_status"] == "no_current_valid_batch_requires_refresh"
    assert dashboard["procurement_status"][
        "duplicate_cleanup_delete_ready_manifest_preview"
    ]["action_count"] == 0
    assert dashboard["procurement_status"][
        "duplicate_cleanup_post_delete_verification_contract_preview"
    ]["ready_for_post_delete_checklist"] is False
    assert dashboard["procurement_status"][
        "duplicate_cleanup_first_execution_batch_manifest_preview"
    ]["batch_manifest_status"] == "preview_frozen_not_authorized"
    assert dashboard["procurement_status"][
        "duplicate_cleanup_first_execution_batch_manifest_preview"
    ]["first_action_matches_exemplar"] is True
    assert dashboard["procurement_status"][
        "duplicate_cleanup_first_execution_batch_manifest_preview"
    ]["delete_enabled"] is False
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "row_count"
    ] == 4
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "lanes"
    ] == ["ligand", "structure", "split", "duplicate_cleanup"]
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_accession"
    ] == "P09105"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_lane_status"
    ] == "blocked_pending_acquisition"
    assert "AlphaFold raw model for P09105" in dashboard["procurement_status"][
        "operator_next_actions_preview"
    ]["first_ligand_best_next_action"]
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_fallback_accession"
    ] == "Q2TAC2"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "first_ligand_fallback_gate_status"
    ] == "blocked_pending_acquisition"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "structure_accession"
    ] == "P31749"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "structure_deferred_accession"
    ] == "P04637"
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "split_run_scoped_only"
    ] is True
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "duplicate_cleanup_batch_size_limit"
    ] == 1
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "duplicate_cleanup_refresh_required"
    ] is True
    assert dashboard["procurement_status"]["operator_next_actions_preview"][
        "report_only"
    ] is True
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "row_count"
    ] == 12
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "grounded_ligand_accessions"
    ] == ["P00387", "Q9NZD4"]
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "candidate_only_ligand_accessions"
    ] == []
    assert dashboard["procurement_status"]["training_set_eligibility_matrix_preview"][
        "candidate_only_rows_non_governing"
    ] is True
    assert dashboard["procurement_status"]["missing_data_policy_preview"][
        "policy_category_count"
    ] == 5
    assert dashboard["procurement_status"]["missing_data_policy_preview"][
        "core_rule_count"
    ] == 5
    assert dashboard["procurement_status"]["missing_data_policy_preview"][
        "deletion_default"
    ] is False
    assert "BioGRID guarded procurement first wave" in dashboard["procurement_status"][
        "missing_data_policy_preview"
    ]["top_scrape_targets"]
    assert (
        dashboard["procurement_status"]["operator_accession_coverage_matrix"][
            "protein_accession_count"
        ]
        == 11
    )
    assert dashboard["procurement_status"]["operator_accession_coverage_matrix"][
        "high_priority_accessions"
    ] == ["P04637", "P31749"]
    assert dashboard["procurement_status"]["leakage_signature_preview"][
        "candidate_overlap_accessions"
    ] == ["P68871", "P69905"]
    assert dashboard["procurement_status"]["leakage_group_preview"]["row_count"] == 11
    assert dashboard["procurement_status"]["leakage_group_preview"][
        "ready_for_bundle_preview"
    ] is True
    assert dashboard["procurement_status"]["leakage_group_preview"][
        "final_fold_export_committed"
    ] is False
    assert dashboard["procurement_status"]["bundle_manifest_validation"]["status"] == (
        "aligned_current_preview_with_verified_assets"
    )
    assert dashboard["procurement_status"]["bundle_manifest_validation"][
        "schema_doc_exists"
    ] is True
    assert dashboard["procurement_status"]["duplicate_cleanup_executor"]["status"] == (
        "usable_with_notes"
    )
    assert (
        dashboard["procurement_status"]["duplicate_cleanup_executor"]["validation_status"]
        in {"passed", "warning"}
    )

    library_state = payload["live_state"]
    if library_state["library_materialized"]:
        assert library_state["library_materialized_path"]
        assert library_state["library_materialized_library_id"]
        assert library_state["library_materialized_record_count"] > 0
        assert library_state["library_materialized_record_types"]
    else:
        assert library_state["library_materialized_path"] is None
        assert library_state["library_materialized_library_id"] is None
        assert library_state["library_materialized_source_manifest_id"] is None
        assert library_state["library_materialized_record_count"] == 0
        assert library_state["library_materialized_record_types"] == {}
        assert library_state["library_materialized_error"] is None


def test_operator_state_validator_rejects_missing_required_sections() -> None:
    module = _load_validator_module()
    schema_path = REPO_ROOT / "artifacts" / "schemas" / "operator_state.schema.json"
    results_dir = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
    dashboard_path = results_dir / "operator_dashboard.json"
    summary_path = results_dir / "summary.json"
    run_summary_path = results_dir / "run_summary.json"
    run_manifest_path = results_dir / "run_manifest.json"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    snapshot = {
        "schema_version": "1.0.0",
        "generated_at": dashboard["generated_at"],
        "task_id": dashboard["task_id"],
        "source_files": {
            "queue_path": "queue.json",
            "orchestrator_state_path": "orchestrator_state.json",
            "library_status_paths": ["schema.json", "builder.json"],
            "benchmark_results_dir": "results",
            "operator_dashboard_path": "operator_dashboard.json",
        },
        "queue": {"path": "queue.json"},
        "library": {"status_files": {}},
        "benchmark": {},
        "runtime": {},
        "dashboard": dashboard,
    }

    issues = module.validate_snapshot(
        snapshot,
        schema,
        dashboard,
        summary,
        run_summary,
        run_manifest,
    )

    assert any("queue" in issue for issue in issues)
    assert any("benchmark" in issue for issue in issues)


def test_operator_state_validator_surfaces_materialized_summary_library_fields(
    tmp_path,
    monkeypatch,
) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator-state contract integration test")

    module = _load_validator_module()
    live_state = module._run_powershell_state(REPO_ROOT)
    materialized_library = SummaryLibrarySchema(
        library_id="summary-library:materialized",
        source_manifest_id="manifest:materialized",
        records=(
            _materialized_protein_record(),
            ProteinProteinSummaryRecord(
                summary_id="pair:ppi:materialized",
                protein_a_ref="protein:P12345",
                protein_b_ref="protein:Q99999",
                interaction_type="physical association",
                interaction_id="EBI-0001",
                interaction_refs=("IM-12345-1", "EBI-0001"),
                evidence_refs=("PMID:12345",),
                organism_name="Homo sapiens",
                taxon_id=9606,
                physical_interaction=True,
                join_status="joined",
            ),
        ),
    )
    materialized_path = tmp_path / "summary_library.json"
    materialized_path.write_text(
        json.dumps(materialized_library.to_dict(), indent=2),
        encoding="utf-8",
    )

    fake_live_state = copy.deepcopy(live_state)
    fake_live_state["library"] = {
        **fake_live_state["library"],
        "materialized": True,
        "materialized_path": str(materialized_path),
        "materialized_error": None,
        "materialized_library_id": materialized_library.library_id,
        "materialized_source_manifest_id": materialized_library.source_manifest_id,
        "materialized_record_count": materialized_library.record_count,
        "materialized_record_types": {
            "protein": 1,
            "protein_protein": 1,
        },
        "schema_task_done": True,
        "builder_task_done": True,
        "ready_for_materialization": False,
    }

    monkeypatch.setattr(module, "_run_powershell_state", lambda repo_root: fake_live_state)

    payload = module.validate_operator_state(REPO_ROOT)

    assert payload["live_state"]["library_materialized"] is True
    assert payload["live_state"]["library_materialized_path"] == str(materialized_path)
    assert payload["live_state"]["library_materialized_library_id"] == (
        "summary-library:materialized"
    )
    assert payload["live_state"]["library_materialized_source_manifest_id"] == (
        "manifest:materialized"
    )
    assert payload["live_state"]["library_materialized_record_count"] == 2
    assert payload["live_state"]["library_materialized_record_types"] == {
        "protein": 1,
        "protein_protein": 1,
    }
