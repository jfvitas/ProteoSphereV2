from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_interaction_string_merge_impact_preview(tmp_path: Path) -> None:
    preview_json = tmp_path / "interaction_similarity_signature_preview.json"
    validation_json = tmp_path / "interaction_similarity_signature_validation.json"
    handoff_json = tmp_path / "interaction_similarity_operator_handoff.json"
    plan_json = tmp_path / "string_interaction_materialization_plan_preview.json"
    gate_json = tmp_path / "procurement_tail_freeze_gate_preview.json"
    output_json = tmp_path / "interaction_string_merge_impact_preview.json"
    output_md = tmp_path / "interaction_string_merge_impact_preview.md"

    preview_json.write_text(
        json.dumps(
            {
                "artifact_id": "interaction_similarity_signature_preview",
                "schema_id": "proteosphere-interaction-similarity-signature-preview-2026-04-02",
                "status": "complete",
                "row_count": 2,
                "rows": [
                    {
                        "signature_id": "interaction_similarity:P69905",
                        "protein_ref": "protein:P69905",
                        "accession": "P69905",
                        "interaction_similarity_group": "group:1",
                        "candidate_only": True,
                        "biogrid_registry_state": "present",
                        "biogrid_disk_state": "present",
                        "biogrid_matched_row_count": 221,
                        "string_registry_state": "missing",
                        "string_disk_state": "partial_on_disk",
                        "intact_registry_state": "present",
                        "intact_disk_state": "present",
                        "intact_probe_state": "present",
                        "intact_probe_row_count": 5,
                    },
                    {
                        "signature_id": "interaction_similarity:P09105",
                        "protein_ref": "protein:P09105",
                        "accession": "P09105",
                        "interaction_similarity_group": "group:1",
                        "candidate_only": True,
                        "biogrid_registry_state": "present",
                        "biogrid_disk_state": "present",
                        "biogrid_matched_row_count": 30,
                        "string_registry_state": "missing",
                        "string_disk_state": "partial_on_disk",
                        "intact_registry_state": "present",
                        "intact_disk_state": "present",
                        "intact_probe_state": "present",
                        "intact_probe_row_count": 5,
                    },
                ],
                "summary": {
                    "accession_count": 2,
                    "unique_interaction_similarity_group_count": 1,
                    "candidate_only_row_count": 2,
                    "biogrid_matched_row_total": 251,
                    "string_top_level_file_present_count": 24,
                    "string_top_level_file_partial_count": 2,
                    "string_top_level_file_missing_count": 0,
                    "intact_present_count": 2,
                    "source_overlap_accessions": ["P69905", "P09105"],
                },
                "source_surfaces": {
                    "string": {"disk_state": "partial_on_disk"},
                },
                "bundle_alignment": {
                    "bundle_status": "preview_generated_verified_assets",
                    "interaction_similarity_signatures_included": False,
                    "interaction_similarity_signatures_record_count": 0,
                },
                "truth_boundary": {
                    "report_only": True,
                    "ready_for_bundle_preview": False,
                    "interaction_family_materialized": False,
                    "direct_interaction_family_claimed": False,
                    "string_family_materialized": False,
                    "intact_pair_evidence_claimed": False,
                    "candidate_only_rows": True,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    validation_json.write_text(
        json.dumps(
            {
                "artifact_id": "interaction_similarity_signature_validation",
                "schema_id": "proteosphere-interaction-similarity-signature-validation-2026-04-02",
                "status": "aligned",
                "validation": {
                    "row_count": 2,
                    "accession_count": 2,
                    "unique_interaction_similarity_group_count": 1,
                    "candidate_only_accessions": ["P69905", "P09105"],
                    "biogrid_matched_row_total": 251,
                    "intact_present_count": 2,
                    "bundle_interaction_similarity_signatures_record_count": 0,
                    "bundle_interaction_similarity_signatures_included": False,
                    "issue_count": 0,
                    "issues": [],
                },
                "truth_boundary": {
                    "report_only": True,
                    "bundle_safe_immediately": False,
                    "bundle_interaction_similarity_signatures_included": False,
                    "bundle_interaction_similarity_signatures_record_count": 0,
                    "interaction_family_materialized": False,
                    "direct_interaction_family_claimed": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    handoff_json.write_text(
        json.dumps(
            {
                "artifact_id": "interaction_similarity_operator_handoff",
                "schema_id": "proteosphere-interaction-similarity-operator-handoff-2026-04-02",
                "report_type": "interaction_similarity_operator_handoff",
                "status": "report_only",
                "policy_family": "interaction_similarity_compact_family",
                "policy_label": "report_only_non_governing",
                "generated_at": "2026-04-02T15:28:38.690792+00:00",
                "source_artifacts": {
                    "interaction_similarity_signature_preview": (
                        "artifacts/status/interaction_similarity_signature_preview.json"
                    ),
                    "interaction_similarity_signature_validation": (
                        "artifacts/status/interaction_similarity_signature_validation.json"
                    ),
                    "lightweight_bundle_manifest": (
                        "artifacts/status/lightweight_bundle_manifest.json"
                    ),
                },
                "current_state": {
                    "preview_status": "complete",
                    "validation_status": "aligned",
                    "preview_row_count": 2,
                    "candidate_only_row_count": 2,
                    "source_overlap_accessions": ["P69905", "P09105"],
                    "biogrid_matched_row_total": 251,
                    "string_surface_state": "partial_on_disk",
                    "string_top_level_file_present_count": 24,
                    "string_top_level_file_partial_count": 2,
                    "string_top_level_file_missing_count": 0,
                    "intact_surface_state": "present_on_disk",
                    "intact_accession_file_present_count": 2,
                    "intact_probe_row_total": 10,
                    "bundle_interaction_similarity_signatures_included": False,
                    "bundle_interaction_similarity_signatures_record_count": 0,
                    "bundle_manifest_status": "preview_generated_verified_assets",
                },
                "truth_boundary": {
                    "summary": (
                        "This is a compact operator handoff note for the interaction "
                        "similarity lane. It is report-only, candidate-only, and "
                        "deliberately does not claim bundle inclusion or direct "
                        "interaction-family materialization."
                    ),
                    "report_only": True,
                    "bundle_safe_immediately": False,
                    "candidate_only_rows": True,
                    "direct_interaction_family_materialized": False,
                    "bundle_inclusion_claimed": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    plan_json.write_text(
        json.dumps(
            {
                "artifact_id": "string_interaction_materialization_plan_preview",
                "schema_id": (
                    "proteosphere-string-interaction-materialization-plan-preview-2026-04-02"
                ),
                "status": "report_only",
                "generated_at": "2026-04-02T19:45:02.810290+00:00",
                "mirror_completion_status": "blocked_pending_zero_gap",
                "remaining_gap_file_count": 2,
                "tracked_remaining_transfer_files": [
                    "protein.links.full.v12.0.txt.gz",
                    "uniref100.xml.gz",
                ],
                "supported_accession_count": 2,
                "supported_accessions": ["P09105", "P69905"],
                "current_interaction_preview_status": "complete",
                "planned_families": [],
                "planned_join_route": {"source_alias_tables_required": True},
                "forecast": {
                    "interaction_readiness_before_tail": "candidate-only non-governing",
                    "interaction_readiness_after_tail_validation": "grounded preview-safe",
                },
                "source_context": {
                    "broad_mirror_status": "partial",
                    "procurement_gate_status": "blocked_pending_zero_gap",
                },
                "truth_boundary": {
                    "summary": (
                        "This is a forecast and materialization plan only. It does "
                        "not materialize STRING rows, does not alter split/leakage "
                        "behavior, and does not mark STRING complete before the "
                        "procurement tail freeze gate clears."
                    ),
                    "report_only": True,
                    "materialization_started": False,
                    "governing": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    gate_json.write_text(
        json.dumps(
            {
                "artifact_id": "procurement_tail_freeze_gate_preview",
                "schema_id": "proteosphere-procurement-tail-freeze-gate-preview-2026-04-02",
                "status": "complete",
                "gate_status": "blocked_pending_zero_gap",
                "remaining_gap_file_count": 2,
                "freeze_conditions": {
                    "remaining_gap_files_zero": False,
                    "not_yet_started_file_count_zero": True,
                    "string_complete": False,
                    "uniprot_complete": False,
                },
                "truth_boundary": {
                    "summary": (
                        "This is a report-only procurement freeze gate. It does not "
                        "mutate the broad mirror surfaces and does not mark the "
                        "mirror complete unless all tracked freeze conditions are "
                        "true."
                    ),
                    "report_only": True,
                    "complete_mirror_locked": False,
                    "freeze_requires_zero_gap": True,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_interaction_string_merge_impact_preview.py"),
            "--interaction-similarity-signature-preview",
            str(preview_json),
            "--interaction-similarity-signature-validation",
            str(validation_json),
            "--interaction-similarity-operator-handoff",
            str(handoff_json),
            "--string-interaction-materialization-plan-preview",
            str(plan_json),
            "--procurement-tail-freeze-gate-preview",
            str(gate_json),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "report_only"
    assert payload["policy_label"] == "report_only_non_governing"
    assert payload["current_state"]["candidate_only_row_count"] == 2
    assert payload["current_state"]["string_surface_state"] == "partial_on_disk"
    assert payload["current_state"]["procurement_gate_status"] == "blocked_pending_zero_gap"
    assert payload["merge_impact"]["merge_changes_split_or_leakage"] is False
    assert payload["merge_impact"]["bundle_safe_immediately"] is False
    assert payload["merge_impact"]["non_governing_until_tail_completion"] is True
    assert payload["truth_boundary"]["interaction_family_materialized"] is False
    assert payload["truth_boundary"]["string_family_materialized"] is False
    assert payload["truth_boundary"]["procurement_tail_completion_required"] is True
    assert "STRING Merge Impact Preview" in output_md.read_text(encoding="utf-8")
