from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class ValidationError(RuntimeError):
    def __init__(self, issues: list[str]) -> None:
        super().__init__("operator state validation failed")
        self.issues = issues


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("PowerShell is required for operator-state validation")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_powershell_state(repo_root: Path) -> dict[str, Any]:
    command = [
        _powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "powershell_interface.ps1"),
        "-Mode",
        "state",
        "-AsJson",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _require_keys(
    payload: dict[str, Any],
    required: list[str],
    label: str,
    issues: list[str],
) -> None:
    missing = [key for key in required if key not in payload]
    if missing:
        issues.append(f"{label} missing required keys: {', '.join(sorted(missing))}")


def _subset_counts(split_counts: dict[str, Any]) -> dict[str, Any]:
    return {key: split_counts.get(key) for key in ("train", "val", "test")}


def _matching_keys(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    return {key: actual.get(key) for key in expected}


def _is_open_gate_status(value: Any) -> bool:
    return str(value or "").strip().startswith("open")


def _record_type_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    records = payload.get("records") or payload.get("summary_records") or []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_type = str(record.get("record_type") or record.get("type") or "unknown").strip()
        if not record_type:
            record_type = "unknown"
        counts[record_type] = counts.get(record_type, 0) + 1
    return counts


def _load_materialized_summary_library(
    path_text: str | None,
    repo_root: Path,
) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    if not path_text:
        return None, None, None

    path = Path(path_text)
    if not path.is_absolute():
        path = repo_root / path

    if not path.exists():
        return path, None, f"summary library artifact missing: {path}"

    try:
        payload = _load_json(path)
    except Exception as exc:
        return path, None, f"summary library artifact unreadable: {path}: {exc}"

    if not isinstance(payload, dict):
        return path, None, f"summary library artifact must be a JSON object: {path}"
    return path, payload, None


def compose_operator_snapshot(
    repo_root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    live_state = _run_powershell_state(repo_root)
    results_dir = repo_root / "runs" / "real_data_benchmark" / "full_results"
    dashboard = _load_json(results_dir / "operator_dashboard.json")
    summary = _load_json(results_dir / "summary.json")
    run_summary = _load_json(results_dir / "run_summary.json")
    run_manifest = _load_json(results_dir / "run_manifest.json")

    snapshot = {
        "schema_version": "1.0.0",
        "generated_at": dashboard["generated_at"],
        "task_id": dashboard["task_id"],
        "source_files": {
            "queue_path": live_state["queue"]["path"],
            "orchestrator_state_path": live_state["runtime"]["state_path"],
            "library_status_paths": [
                live_state["library"]["status_files"]["schema"]["path"],
                live_state["library"]["status_files"]["builder"]["path"],
            ],
            "benchmark_results_dir": live_state["benchmark"]["results_dir"],
            "operator_dashboard_path": str(results_dir / "operator_dashboard.json"),
        },
        "queue": live_state["queue"],
        "library": live_state["library"],
        "benchmark": live_state["benchmark"],
        "runtime": live_state["runtime"],
        "dashboard": dashboard,
    }
    return snapshot, live_state, dashboard, summary, run_summary, run_manifest


def validate_snapshot(
    snapshot: dict[str, Any],
    schema: dict[str, Any],
    dashboard: dict[str, Any],
    summary: dict[str, Any],
    run_summary: dict[str, Any],
    run_manifest: dict[str, Any],
) -> list[str]:
    issues: list[str] = []

    _require_keys(snapshot, schema["required"], "operator snapshot", issues)
    for section_name in ("queue", "library", "benchmark", "runtime", "dashboard", "source_files"):
        if section_name in snapshot:
            if not isinstance(snapshot[section_name], dict):
                issues.append(f"{section_name} must be an object")
        else:
            issues.append(f"{section_name} section missing from operator snapshot")

    if snapshot.get("schema_version") != schema["properties"]["schema_version"]["const"]:
        issues.append("schema_version does not match the pinned operator schema")

    queue = snapshot.get("queue", {})
    library = snapshot.get("library", {})
    benchmark = snapshot.get("benchmark", {})
    runtime = snapshot.get("runtime", {})
    snapshot_dashboard = snapshot.get("dashboard", {})

    _require_keys(queue, schema["$defs"]["queue_state"]["required"], "queue", issues)
    _require_keys(library, schema["$defs"]["library_state"]["required"], "library", issues)
    _require_keys(benchmark, schema["$defs"]["benchmark_state"]["required"], "benchmark", issues)
    _require_keys(runtime, schema["$defs"]["runtime_state"]["required"], "runtime", issues)
    _require_keys(
        snapshot_dashboard,
        schema["$defs"]["dashboard_state"]["required"],
        "dashboard",
        issues,
    )

    if benchmark.get("benchmark_summary", {}).get("status") != summary["status"]:
        issues.append("benchmark summary status diverges from summary.json")
    if benchmark.get("benchmark_summary", {}).get("status") != snapshot_dashboard.get(
        "benchmark_summary",
        {},
    ).get("status"):
        issues.append("benchmark summary status diverges from the dashboard export")
    if benchmark.get("completion_status") != summary["status"]:
        issues.append("completion status diverges from summary.json")
    if benchmark.get("completion_status") != snapshot_dashboard.get("release_grade_status"):
        issues.append("completion status diverges from the dashboard release-grade status")

    release_target = summary.get("release_target", {})
    release_bar_closed = bool(release_target.get("benchmark_release_bar_closed"))
    operator_release_ready = bool(release_target.get("operator_release_ready"))
    expected_live_release_grade_status = (
        "closed_not_release_ready"
        if release_bar_closed and not operator_release_ready
        else ("completed" if operator_release_ready else "blocked")
    )
    if benchmark.get("release_grade_status") != expected_live_release_grade_status:
        issues.append(
            "operator release_grade_status diverges from the frozen-v1 release contract"
        )
    if snapshot_dashboard.get("assessment", {}).get("release_grade_blocked") is not (not release_bar_closed):
        issues.append("dashboard assessment release-grade blocking flag diverges from summary release_target")
    if snapshot_dashboard.get("assessment", {}).get("ready_for_release") is not operator_release_ready:
        issues.append("dashboard assessment ready_for_release diverges from summary release_target")

    summary_scope = summary.get("execution_scope", {})
    summary_split_counts = summary_scope.get("split_counts", {})
    dashboard_coverage_summary = snapshot_dashboard.get("coverage_summary", {})
    dashboard_summary = dashboard_coverage_summary.get("summary", {})
    dashboard_frozen = dashboard_coverage_summary.get("frozen_cohort", {})
    dashboard_run_context = dashboard_coverage_summary.get("run_context", {})

    if benchmark.get("selected_accession_count") != summary_scope.get("cohort_size"):
        issues.append("selected accession count diverges from summary execution scope")
    if benchmark.get("selected_accession_count") != dashboard_summary.get("total_accessions"):
        issues.append("selected accession count diverges from dashboard coverage summary")
    benchmark_split_counts = benchmark.get("split_counts", {})
    benchmark_split_subset = _matching_keys(benchmark_split_counts, summary_split_counts)
    if benchmark_split_subset != summary_split_counts:
        issues.append("benchmark split counts diverge from summary execution scope")
    if benchmark_split_counts.get("total") != summary_scope.get("cohort_size"):
        issues.append("benchmark split total diverges from summary cohort size")
    if _subset_counts(benchmark.get("split_counts", {})) != dashboard_frozen.get("split_counts"):
        issues.append("benchmark split counts diverge from dashboard frozen cohort")
    if dashboard_frozen.get("resolved_count") != summary_split_counts.get("resolved"):
        issues.append("dashboard resolved count diverges from summary scope")
    if dashboard_frozen.get("unresolved_count") != summary_split_counts.get("unresolved"):
        issues.append("dashboard unresolved count diverges from summary scope")
    if benchmark.get("release_grade_blockers") != run_summary.get("remaining_gaps"):
        issues.append("release-grade blockers diverge from run_summary remaining_gaps")
    if benchmark.get("runtime_surface") != summary_scope.get("runtime_surface"):
        issues.append("benchmark runtime surface diverges from summary execution scope")
    if benchmark.get("runtime_surface") != dashboard_run_context.get("runtime_surface"):
        issues.append("benchmark runtime surface diverges from dashboard coverage context")
    benchmark_truth = benchmark.get("truth_boundary", {})
    dashboard_truth = snapshot_dashboard.get("truth_boundary", {})
    if "allowed_statuses" in benchmark_truth:
        allowed_statuses = set(benchmark_truth.get("allowed_statuses", []))
        if not release_bar_closed and "blocked" not in allowed_statuses:
            issues.append("live operator boundary should preserve the coarse blocked label")
        if release_bar_closed and "blocked" not in allowed_statuses and "closed_not_release_ready" not in allowed_statuses:
            issues.append("live operator boundary should preserve a conservative coarse status label")
    elif "allowed_status" in benchmark_truth:
        if dashboard_truth.get("allowed_status") != benchmark_truth.get("allowed_status"):
            issues.append("dashboard truth status diverges from the live operator boundary")
    else:
        issues.append("truth boundary must declare allowed statuses or an allowed status")
    if set(benchmark_truth.get("forbidden_overclaims", [])) != set(
        dashboard_truth.get("forbidden_overclaims", [])
    ):
        issues.append("truth boundary forbidden overclaims diverge")
    if dashboard_truth.get("prototype_runtime") is not True:
        issues.append("dashboard truth boundary should remain prototype-only")
    if dashboard_truth.get("runtime_surface") != run_manifest.get("runtime_surface"):
        issues.append("dashboard truth boundary runtime surface diverges from run manifest")

    if benchmark.get("limitation_blockers"):
        unexpected_limitations = [
            limitation
            for limitation in benchmark.get("limitation_blockers", [])
            if limitation not in run_manifest.get("limitations", [])
        ]
        if unexpected_limitations:
            issues.append("limitation blockers contain entries outside run manifest limitations")

    if not isinstance(snapshot.get("source_files", {}).get("operator_dashboard_path"), str):
        issues.append("operator dashboard path must be a string")

    procurement_status = snapshot_dashboard.get("procurement_status", {})
    dictionary_preview = procurement_status.get("dictionary_preview")
    ligand_support_readiness_preview = procurement_status.get(
        "ligand_support_readiness_preview"
    )
    ligand_identity_pilot_preview = procurement_status.get(
        "ligand_identity_pilot_preview"
    )
    ligand_stage1_operator_queue_preview = procurement_status.get(
        "ligand_stage1_operator_queue_preview"
    )
    anchor_candidates = procurement_status.get("structure_followup_anchor_candidates")
    accession_matrix = procurement_status.get("operator_accession_coverage_matrix")
    structure_followup_payload_preview = procurement_status.get(
        "structure_followup_payload_preview"
    )
    structure_followup_single_accession_preview = procurement_status.get(
        "structure_followup_single_accession_preview"
    )
    structure_followup_single_accession_validation_preview = procurement_status.get(
        "structure_followup_single_accession_validation_preview"
    )
    if anchor_candidates is not None and accession_matrix is not None:
        candidate_accessions = anchor_candidates.get("candidate_accessions", [])
        high_priority_accessions = accession_matrix.get("high_priority_accessions", [])
        if anchor_candidates.get("row_count") != len(candidate_accessions):
            issues.append("structure follow-up anchor candidate count diverges from row_count")
        if candidate_accessions != high_priority_accessions:
            issues.append(
                "structure follow-up anchor candidates diverge from operator "
                "high-priority accessions"
            )
        if anchor_candidates.get("direct_structure_backed_join_materialized") is not False:
            issues.append(
                "structure follow-up anchor candidates must remain candidate-only "
                "until explicit anchors exist"
            )
    if structure_followup_payload_preview is not None:
        if structure_followup_payload_preview.get("target_accession") != "P31749":
            issues.append("structure follow-up payload preview must remain P31749-first")
        if structure_followup_payload_preview.get("payload_accessions") != [
            "P31749",
            "P04637",
        ]:
            issues.append(
                "structure follow-up payload preview must remain the narrow "
                "P31749/P04637 two-row surface"
            )
        if structure_followup_payload_preview.get("payload_row_count") != 2:
            issues.append("structure follow-up payload preview must remain two-row")
        if structure_followup_payload_preview.get("candidate_only_no_variant_anchor") is not True:
            issues.append(
                "structure follow-up payload preview must preserve candidate-only truth"
            )
        if structure_followup_payload_preview.get(
            "direct_structure_backed_join_certified"
        ) is not False:
            issues.append(
                "structure follow-up payload preview must not certify a direct join"
            )
        if structure_followup_payload_preview.get("anchor_validation_status") != "aligned":
            issues.append(
                "structure follow-up payload preview must remain tied to aligned "
                "anchor validation"
            )
        if structure_followup_payload_preview.get("candidate_variant_anchor_count_total") != 10:
            issues.append(
                "structure follow-up payload preview must preserve the current "
                "10-anchor candidate total"
            )
    if structure_followup_single_accession_preview is not None:
        if structure_followup_single_accession_preview.get("selected_accession") != "P31749":
            issues.append(
                "structure follow-up single accession preview must keep P31749 selected"
            )
        if structure_followup_single_accession_preview.get("deferred_accession") != "P04637":
            issues.append(
                "structure follow-up single accession preview must keep P04637 deferred"
            )
        if structure_followup_single_accession_preview.get("payload_row_count") != 1:
            issues.append(
                "structure follow-up single accession preview must remain single-row"
            )
        if structure_followup_single_accession_preview.get("single_accession_scope") is not True:
            issues.append(
                "structure follow-up single accession preview must remain single-accession"
            )
        if (
            structure_followup_single_accession_preview.get(
                "candidate_only_no_variant_anchor"
            )
            is not True
        ):
            issues.append(
                "structure follow-up single accession preview must remain candidate-only"
            )
        if (
            structure_followup_single_accession_preview.get(
                "direct_structure_backed_join_certified"
            )
            is not False
        ):
            issues.append(
                "structure follow-up single accession preview must not certify a direct join"
            )
        if (
            structure_followup_single_accession_preview.get("ready_for_operator_preview")
            is not True
        ):
            issues.append(
                "structure follow-up single accession preview must remain operator-preview ready"
            )
    if structure_followup_single_accession_validation_preview is not None:
        if (
            structure_followup_single_accession_validation_preview.get(
                "selected_accession"
            )
            != "P31749"
        ):
            issues.append(
                "structure follow-up single accession validation preview must keep "
                "P31749 selected"
            )
        if (
            structure_followup_single_accession_validation_preview.get(
                "deferred_accession"
            )
            != "P04637"
        ):
            issues.append(
                "structure follow-up single accession validation preview must keep "
                "P04637 deferred"
            )
        if (
            structure_followup_single_accession_validation_preview.get(
                "anchor_validation_status"
            )
            != "aligned"
        ):
            issues.append(
                "structure follow-up single accession validation preview must remain aligned"
            )
        if (
            structure_followup_single_accession_validation_preview.get(
                "direct_structure_backed_join_certified"
            )
            is not False
        ):
            issues.append(
                "structure follow-up single accession validation preview must not "
                "certify a direct join"
            )
        if (
            structure_followup_single_accession_validation_preview.get(
                "ready_for_operator_preview"
            )
            is not True
        ):
            issues.append(
                "structure follow-up single accession validation preview must remain "
                "operator-preview ready"
            )
    if dictionary_preview is not None:
        if dictionary_preview.get("row_count", 0) <= 0:
            issues.append("dictionary preview must carry at least one row")
        if dictionary_preview.get("namespace_count", 0) <= 0:
            issues.append("dictionary preview must carry at least one namespace")
        if dictionary_preview.get("ready_for_bundle_preview") is not True:
            issues.append("dictionary preview must remain bundle-preview ready")
        if dictionary_preview.get("biological_content_family") is not False:
            issues.append("dictionary preview must remain packaging-only, not biological")
    if ligand_support_readiness_preview is not None:
        if ligand_support_readiness_preview.get("row_count") != 4:
            issues.append("ligand support readiness preview must remain four-row")
        if ligand_support_readiness_preview.get("support_accessions") != [
            "P00387",
            "P09105",
            "Q2TAC2",
            "Q9NZD4",
        ]:
            issues.append(
                "ligand support readiness preview support accessions diverge from "
                "the narrow four-row scope"
            )
        if ligand_support_readiness_preview.get("deferred_accessions") != ["Q9UCM0"]:
            issues.append(
                "ligand support readiness preview must keep Q9UCM0 deferred"
            )
        if ligand_support_readiness_preview.get("bundle_ligands_included") is not False:
            issues.append(
                "ligand support readiness preview must not imply bundle ligand inclusion"
            )
        if ligand_support_readiness_preview.get("ligand_rows_materialized") is not False:
            issues.append(
                "ligand support readiness preview must remain non-materialized"
            )
        if ligand_support_readiness_preview.get("q9ucm0_deferred") is not True:
            issues.append(
                "ligand support readiness preview must keep q9ucm0_deferred=true"
            )
        if ligand_support_readiness_preview.get("ready_for_operator_preview") is not True:
            issues.append(
                "ligand support readiness preview must remain operator-preview ready"
            )
    if ligand_identity_pilot_preview is not None:
        if ligand_identity_pilot_preview.get("row_count") != 4:
            issues.append("ligand identity pilot preview must remain four-row")
        if ligand_identity_pilot_preview.get("first_accession") != "P00387":
            issues.append("ligand identity pilot preview must keep P00387 first")
        if ligand_identity_pilot_preview.get("second_accession") != "Q9NZD4":
            issues.append("ligand identity pilot preview must keep Q9NZD4 second")
        if ligand_identity_pilot_preview.get("deferred_accession") != "Q9UCM0":
            issues.append("ligand identity pilot preview must keep Q9UCM0 deferred")
        if ligand_identity_pilot_preview.get("report_only") is not True:
            issues.append("ligand identity pilot preview must remain report-only")
        if ligand_identity_pilot_preview.get("ligand_rows_materialized") is not False:
            issues.append("ligand identity pilot preview must remain non-materialized")
        if ligand_identity_pilot_preview.get("bundle_ligands_included") is not False:
            issues.append(
                "ligand identity pilot preview must not imply bundle ligand inclusion"
            )
        if ligand_identity_pilot_preview.get("ready_for_operator_preview") is not True:
            issues.append(
                "ligand identity pilot preview must remain operator-preview ready"
            )
    if ligand_stage1_operator_queue_preview is not None:
        if ligand_stage1_operator_queue_preview.get("row_count") != 4:
            issues.append("ligand stage1 operator queue preview must remain four-row")
        if ligand_stage1_operator_queue_preview.get("ordered_accessions") != [
            "P00387",
            "Q9NZD4",
            "P09105",
            "Q2TAC2",
        ]:
            issues.append(
                "ligand stage1 operator queue preview ordered accessions diverge "
                "from the stage-1 scope"
            )
        if ligand_stage1_operator_queue_preview.get("deferred_accession") != "Q9UCM0":
            issues.append(
                "ligand stage1 operator queue preview must keep Q9UCM0 deferred"
            )
        if ligand_stage1_operator_queue_preview.get("report_only") is not True:
            issues.append(
                "ligand stage1 operator queue preview must remain report-only"
            )
        if ligand_stage1_operator_queue_preview.get("ligand_rows_materialized") is not False:
            issues.append(
                "ligand stage1 operator queue preview must remain non-materialized"
            )
        if ligand_stage1_operator_queue_preview.get("bundle_ligands_included") is not False:
            issues.append(
                "ligand stage1 operator queue preview must not imply bundle ligand inclusion"
            )
        if ligand_stage1_operator_queue_preview.get("q9ucm0_deferred") is not True:
            issues.append(
                "ligand stage1 operator queue preview must keep q9ucm0_deferred=true"
            )
        if ligand_stage1_operator_queue_preview.get("ready_for_operator_preview") is not True:
            issues.append(
                "ligand stage1 operator queue preview must remain operator-preview ready"
            )

    split_input = procurement_status.get("split_engine_input_preview")
    split_dry_run = procurement_status.get("split_engine_dry_run_validation")
    split_fold_gate = procurement_status.get("split_fold_export_gate_preview")
    split_fold_gate_validation = procurement_status.get(
        "split_fold_export_gate_validation"
    )
    split_fold_staging = procurement_status.get("split_fold_export_staging_preview")
    split_fold_staging_validation = procurement_status.get(
        "split_fold_export_staging_validation"
    )
    split_post_staging = procurement_status.get(
        "split_post_staging_gate_check_preview"
    )
    split_post_staging_validation = procurement_status.get(
        "split_post_staging_gate_check_validation"
    )
    split_fold_request = procurement_status.get("split_fold_export_request_preview")
    split_fold_request_validation = procurement_status.get(
        "split_fold_export_request_validation"
    )
    duplicate_first_execution_preview = procurement_status.get(
        "duplicate_cleanup_first_execution_preview"
    )
    operator_next_actions_preview = procurement_status.get(
        "operator_next_actions_preview"
    )
    if (
        split_input is not None
        and split_dry_run is not None
        and split_fold_gate is not None
    ):
        if split_fold_gate.get("dry_run_validation_status") != split_dry_run.get("status"):
            issues.append(
                "split fold-export gate preview dry-run status diverges from "
                "split_engine_dry_run_validation"
            )
        if split_fold_gate.get("candidate_row_count") != split_dry_run.get("candidate_row_count"):
            issues.append(
                "split fold-export gate preview candidate row count diverges from "
                "split_engine_dry_run_validation"
            )
        if split_fold_gate.get("assignment_count") != split_dry_run.get("assignment_count"):
            issues.append(
                "split fold-export gate preview assignment count diverges from "
                "split_engine_dry_run_validation"
            )
        gate_unlocked = bool(split_fold_gate.get("cv_fold_export_unlocked"))
        if split_fold_gate.get("ready_for_fold_export") is not gate_unlocked:
            issues.append(
                "split fold-export gate preview ready_for_fold_export must match unlock state"
            )
        if split_fold_gate.get("cv_folds_materialized") != split_input.get("cv_folds_materialized"):
            issues.append(
                "split fold-export gate preview cv_folds_materialized diverges from "
                "split_engine_input_preview"
            )
        if split_fold_gate.get("final_split_committed") != split_dry_run.get(
            "final_split_committed"
        ):
            issues.append(
                "split fold-export gate preview final_split_committed diverges from "
                "split_engine_dry_run_validation"
            )
    if split_fold_gate is not None and split_fold_gate_validation is not None:
        if split_fold_gate_validation.get("status") != "aligned":
            issues.append("split fold-export gate validation must remain aligned")
        if split_fold_gate_validation.get("gate_status") != split_fold_gate.get("status"):
            issues.append(
                "split fold-export gate validation gate status diverges from "
                "split_fold_export_gate_preview"
            )
        if split_fold_gate_validation.get("candidate_row_count") != split_fold_gate.get(
            "candidate_row_count"
        ):
            issues.append(
                "split fold-export gate validation candidate row count diverges from "
                "split_fold_export_gate_preview"
            )
        if split_fold_gate_validation.get("assignment_count") != split_fold_gate.get(
            "assignment_count"
        ):
            issues.append(
                "split fold-export gate validation assignment count diverges from "
                "split_fold_export_gate_preview"
            )
        if split_fold_gate_validation.get("cv_fold_export_unlocked") != split_fold_gate.get(
            "cv_fold_export_unlocked"
        ):
            issues.append(
                "split fold-export gate validation unlock state diverges from preview"
            )
    if split_fold_staging is not None:
        expected_staging_status = (
            "complete"
            if split_fold_staging.get("cv_fold_export_unlocked")
            else "blocked_report_emitted"
        )
        if split_fold_staging.get("status") != expected_staging_status:
            issues.append(
                "split fold-export staging preview status must match its unlock state"
            )
        if split_fold_staging.get("stage_id") != "run_scoped_fold_export_staging":
            issues.append("split fold-export staging preview stage id must remain stable")
        if split_fold_staging.get("run_scoped_only") is not True:
            issues.append("split fold-export staging preview must remain run-scoped only")
        if split_fold_staging.get("cv_fold_export_unlocked") != split_fold_gate.get(
            "cv_fold_export_unlocked"
        ):
            issues.append(
                "split fold-export staging preview unlock state diverges from gate preview"
            )
        if split_fold_staging.get("cv_folds_materialized") != split_fold_gate.get(
            "cv_folds_materialized"
        ):
            issues.append(
                "split fold-export staging preview materialization state diverges from gate preview"
            )
        if split_fold_staging.get("final_split_committed") is not False:
            issues.append("split fold-export staging preview must not commit a split")
        if split_fold_gate is not None:
            staging_gate_status = split_fold_staging.get("gate_status")
            split_gate_status = split_fold_gate.get("status")
            if _is_open_gate_status(staging_gate_status) != _is_open_gate_status(split_gate_status):
                issues.append(
                    "split fold-export staging preview gate status diverges from "
                    "split_fold_export_gate_preview"
                )
            if split_fold_staging.get("candidate_row_count") != split_fold_gate.get(
                "candidate_row_count"
            ):
                issues.append(
                    "split fold-export staging preview candidate row count diverges from "
                    "split_fold_export_gate_preview"
                )
            if split_fold_staging.get("assignment_count") != split_fold_gate.get(
                "assignment_count"
            ):
                issues.append(
                    "split fold-export staging preview assignment count diverges from "
                    "split_fold_export_gate_preview"
                )
            if split_fold_staging.get("dry_run_validation_status") != split_fold_gate.get(
                "dry_run_validation_status"
            ):
                issues.append(
                    "split fold-export staging preview dry-run status diverges from "
                    "split_fold_export_gate_preview"
                )
            if split_fold_staging.get("blocked_reasons") != split_fold_gate.get(
                "blocked_reasons"
            ):
                issues.append(
                    "split fold-export staging preview blocked reasons diverge from "
                    "split_fold_export_gate_preview"
                )
    if split_fold_staging is not None and split_fold_staging_validation is not None:
        if split_fold_staging_validation.get("status") != "aligned":
            issues.append("split fold-export staging validation must remain aligned")
        if split_fold_staging_validation.get("stage_status") != split_fold_staging.get(
            "status"
        ):
            issues.append(
                "split fold-export staging validation stage status diverges from "
                "split_fold_export_staging_preview"
            )
        if split_fold_staging_validation.get("gate_status") != split_fold_staging.get(
            "gate_status"
        ):
            issues.append(
                "split fold-export staging validation gate status diverges from "
                "split_fold_export_staging_preview"
            )
        if split_fold_staging_validation.get("candidate_row_count") != split_fold_staging.get(
            "candidate_row_count"
        ):
            issues.append(
                "split fold-export staging validation candidate row count diverges from "
                "split_fold_export_staging_preview"
            )
        if split_fold_staging_validation.get("assignment_count") != split_fold_staging.get(
            "assignment_count"
        ):
            issues.append(
                "split fold-export staging validation assignment count diverges from "
                "split_fold_export_staging_preview"
            )
        if split_fold_staging_validation.get("run_scoped_only") is not True:
            issues.append("split fold-export staging validation must remain run-scoped only")
        if split_fold_staging_validation.get("cv_fold_export_unlocked") != split_fold_staging.get(
            "cv_fold_export_unlocked"
        ):
            issues.append(
                "split fold-export staging validation unlock state diverges from preview"
            )
        if split_fold_staging_validation.get("cv_folds_materialized") != split_fold_staging.get(
            "cv_folds_materialized"
        ):
            issues.append(
                "split fold-export staging validation materialization state diverges from preview"
            )
    if split_post_staging is not None:
        expected_post_stage_status = (
            "complete"
            if split_post_staging.get("cv_fold_export_unlocked")
            else "blocked_report_emitted"
        )
        if split_post_staging.get("status") != expected_post_stage_status:
            issues.append(
                "split post-staging gate check preview status must match its unlock state"
            )
        if split_post_staging.get("stage_id") != "cv_fold_export_unlock_gate_check":
            issues.append(
                "split post-staging gate check preview stage id must remain stable"
            )
        if split_post_staging.get("run_scoped_only") is not True:
            issues.append(
                "split post-staging gate check preview must remain run-scoped only"
            )
        if split_post_staging.get("cv_fold_export_unlocked") != split_fold_staging.get(
            "cv_fold_export_unlocked"
        ):
            issues.append(
                "split post-staging gate check preview unlock state diverges from staging preview"
            )
        if split_post_staging.get("cv_folds_materialized") != split_fold_staging.get(
            "cv_folds_materialized"
        ):
            issues.append(
                "split post-staging gate check preview materialization state diverges from staging preview"
            )
        if split_post_staging.get("final_split_committed") is not False:
            issues.append(
                "split post-staging gate check preview must not commit a split"
            )
        if split_fold_staging is not None:
            if _is_open_gate_status(split_post_staging.get("gate_status")) != _is_open_gate_status(
                split_fold_staging.get("gate_status")
            ):
                issues.append(
                    "split post-staging gate check preview gate status diverges from "
                    "split_fold_export_staging_preview"
                )
            if split_post_staging.get("candidate_row_count") != split_fold_staging.get(
                "candidate_row_count"
            ):
                issues.append(
                    "split post-staging gate check preview candidate row count diverges "
                    "from split_fold_export_staging_preview"
                )
            if split_post_staging.get("assignment_count") != split_fold_staging.get(
                "assignment_count"
            ):
                issues.append(
                    "split post-staging gate check preview assignment count diverges "
                    "from split_fold_export_staging_preview"
                )
            if split_post_staging.get("blocked_reasons") != split_fold_staging.get(
                "blocked_reasons"
            ):
                issues.append(
                    "split post-staging gate check preview blocked reasons diverge from "
                    "split_fold_export_staging_preview"
                )
    if split_post_staging is not None and split_post_staging_validation is not None:
        if split_post_staging_validation.get("status") != "aligned":
            issues.append("split post-staging gate check validation must remain aligned")
        if split_post_staging_validation.get("stage_status") != split_post_staging.get(
            "status"
        ):
            issues.append(
                "split post-staging gate check validation stage status diverges from "
                "split_post_staging_gate_check_preview"
            )
        if split_post_staging_validation.get("gate_status") != split_post_staging.get(
            "gate_status"
        ):
            issues.append(
                "split post-staging gate check validation gate status diverges from "
                "split_post_staging_gate_check_preview"
            )
        if split_post_staging_validation.get("candidate_row_count") != split_post_staging.get(
            "candidate_row_count"
        ):
            issues.append(
                "split post-staging gate check validation candidate row count diverges "
                "from split_post_staging_gate_check_preview"
            )
        if split_post_staging_validation.get("assignment_count") != split_post_staging.get(
            "assignment_count"
        ):
            issues.append(
                "split post-staging gate check validation assignment count diverges "
                "from split_post_staging_gate_check_preview"
            )
        if split_post_staging_validation.get("run_scoped_only") is not True:
            issues.append(
                "split post-staging gate check validation must remain run-scoped only"
            )
        if split_post_staging_validation.get("cv_fold_export_unlocked") != split_post_staging.get(
            "cv_fold_export_unlocked"
        ):
            issues.append(
                "split post-staging gate check validation unlock state diverges from preview"
            )
        if split_post_staging_validation.get("cv_folds_materialized") != split_post_staging.get(
            "cv_folds_materialized"
        ):
            issues.append(
                "split post-staging gate check validation materialization state diverges from preview"
            )
    if split_fold_request is not None:
        expected_request_status = (
            "complete" if split_fold_request.get("cv_fold_export_unlocked") else "blocked_report_emitted"
        )
        if split_fold_request.get("status") != expected_request_status:
            issues.append("split fold-export request preview status must match its unlock state")
        if split_fold_request.get("stage_id") != "run_scoped_fold_export_request":
            issues.append("split fold-export request preview stage id must remain stable")
        if split_fold_request.get("stage_shape") != "request_manifest":
            issues.append(
                "split fold-export request preview stage shape must remain "
                "request_manifest"
            )
        expected_today_status = (
            "fulfilled" if split_fold_request.get("cv_fold_export_unlocked") else "blocked today"
        )
        if split_fold_request.get("today_status") != expected_today_status:
            issues.append("split fold-export request preview today status must match its unlock state")
        if split_fold_request.get("request_only_no_fold_materialization") != (
            not bool(split_fold_request.get("cv_fold_export_unlocked"))
        ):
            issues.append("split fold-export request preview request-only flag diverges from unlock state")
        if split_fold_request.get("cv_fold_export_unlocked") != split_post_staging.get(
            "cv_fold_export_unlocked"
        ):
            issues.append("split fold-export request preview unlock state diverges from post-staging preview")
        if split_fold_request.get("cv_folds_materialized") != split_post_staging.get(
            "cv_folds_materialized"
        ):
            issues.append("split fold-export request preview materialization state diverges from post-staging preview")
        if split_fold_request.get("final_split_committed") is not False:
            issues.append("split fold-export request preview must not commit a split")
        if split_post_staging is not None:
            if split_fold_request.get("candidate_row_count") != split_post_staging.get(
                "candidate_row_count"
            ):
                issues.append(
                    "split fold-export request preview candidate row count diverges from "
                    "split_post_staging_gate_check_preview"
                )
            if split_fold_request.get("assignment_count") != split_post_staging.get(
                "assignment_count"
            ):
                issues.append(
                    "split fold-export request preview assignment count diverges from "
                    "split_post_staging_gate_check_preview"
                )
    if split_fold_request is not None and split_fold_request_validation is not None:
        if split_fold_request_validation.get("status") != "aligned":
            issues.append("split fold-export request validation must remain aligned")
        if split_fold_request_validation.get("stage_status") != split_fold_request.get(
            "status"
        ):
            issues.append(
                "split fold-export request validation stage status diverges from "
                "split_fold_export_request_preview"
            )
        if _is_open_gate_status(split_fold_request_validation.get("gate_status")) != _is_open_gate_status(
            split_post_staging.get("gate_status")
        ):
            issues.append(
                "split fold-export request validation gate status diverges from "
                "split_post_staging_gate_check_preview"
            )
        if split_fold_request_validation.get("candidate_row_count") != split_fold_request.get(
            "candidate_row_count"
        ):
            issues.append(
                "split fold-export request validation candidate row count diverges from "
                "split_fold_export_request_preview"
            )
        if split_fold_request_validation.get("assignment_count") != split_fold_request.get(
            "assignment_count"
        ):
            issues.append(
                "split fold-export request validation assignment count diverges from "
                "split_fold_export_request_preview"
            )
        if split_fold_request_validation.get("run_scoped_only") is not True:
            issues.append("split fold-export request validation must remain run-scoped only")
        if split_fold_request_validation.get("cv_fold_export_unlocked") != split_fold_request.get(
            "cv_fold_export_unlocked"
        ):
            issues.append("split fold-export request validation unlock state diverges from preview")
        if split_fold_request_validation.get("cv_folds_materialized") != split_fold_request.get(
            "cv_folds_materialized"
        ):
            issues.append("split fold-export request validation materialization state diverges from preview")
    if duplicate_first_execution_preview is not None:
        if duplicate_first_execution_preview.get("status") != "complete":
            issues.append("duplicate cleanup first execution preview must remain complete")
        if (
            duplicate_first_execution_preview.get("execution_status")
            != "refresh_required_after_consumed_preview_batch"
        ):
            issues.append(
                "duplicate cleanup first execution preview must acknowledge when the "
                "staged batch has been consumed"
            )
        if duplicate_first_execution_preview.get("batch_size_limit") != 1:
            issues.append(
                "duplicate cleanup first execution preview must remain single-batch"
            )
        if (
            duplicate_first_execution_preview.get("preview_manifest_status")
            != "no_current_valid_batch_requires_refresh"
        ):
            issues.append(
                "duplicate cleanup first execution preview must mirror the current "
                "delete-ready manifest refresh status"
            )
        if duplicate_first_execution_preview.get("refresh_required") is not True:
            issues.append(
                "duplicate cleanup first execution preview must flag refresh required"
            )
        if duplicate_first_execution_preview.get("report_only") is not True:
            issues.append("duplicate cleanup first execution preview must remain report-only")
        if duplicate_first_execution_preview.get("delete_enabled") is not False:
            issues.append(
                "duplicate cleanup first execution preview must not enable deletion"
            )
        if duplicate_first_execution_preview.get("latest_surfaces_mutated") is not False:
            issues.append(
                "duplicate cleanup first execution preview must not mutate latest surfaces"
            )
        if duplicate_first_execution_preview.get("ready_for_operator_preview") is not True:
            issues.append(
                "duplicate cleanup first execution preview must remain operator-preview ready"
            )
    if operator_next_actions_preview is not None:
        if operator_next_actions_preview.get("row_count") != 4:
            issues.append("operator next actions preview must remain four-row")
        if operator_next_actions_preview.get("lanes") != [
            "ligand",
            "structure",
            "split",
            "duplicate_cleanup",
        ]:
            issues.append(
                "operator next actions preview lane ordering diverges from the "
                "current steering surface"
            )
        if operator_next_actions_preview.get("first_ligand_accession") != "P09105":
            issues.append(
                "operator next actions preview must keep P09105 as the selected next "
                "grounded ligand target"
            )
        if (
            operator_next_actions_preview.get("first_ligand_lane_status")
            != "blocked_pending_acquisition"
        ):
            issues.append(
                "operator next actions preview must keep the first ligand lane "
                "blocked pending acquisition"
            )
        if operator_next_actions_preview.get("structure_accession") != "P31749":
            issues.append(
                "operator next actions preview must keep P31749 as structure action"
            )
        if operator_next_actions_preview.get("duplicate_cleanup_refresh_required") is not True:
            issues.append(
                "operator next actions preview must acknowledge when the staged "
                "delete-ready batch has been consumed and needs refresh"
            )
        if operator_next_actions_preview.get("report_only") is not True:
            issues.append("operator next actions preview must remain report-only")
        if operator_next_actions_preview.get("ready_for_operator_preview") is not True:
            issues.append(
                "operator next actions preview must remain operator-preview ready"
            )

    return issues


def validate_operator_state(repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = _repo_root() if repo_root is None else repo_root
    schema_path = repo_root / "artifacts" / "schemas" / "operator_state.schema.json"
    schema = _load_json(schema_path)
    snapshot, live_state, dashboard, summary, run_summary, run_manifest = (
        compose_operator_snapshot(repo_root)
    )

    issues = validate_snapshot(snapshot, schema, dashboard, summary, run_summary, run_manifest)

    library_state = snapshot.get("library", {})
    materialized_path, materialized_payload, materialized_error = (
        _load_materialized_summary_library(
            library_state.get("materialized_path"),
            repo_root,
        )
    )
    if library_state.get("materialized"):
        if materialized_path is None:
            issues.append("library.materialized is true but materialized_path is missing")
        elif materialized_payload is None:
            issues.append(materialized_error or "summary library artifact is unavailable")
        else:
            artifact_library_id = str(materialized_payload.get("library_id") or "").strip() or None
            artifact_source_manifest_id = (
                str(materialized_payload.get("source_manifest_id") or "").strip() or None
            )
            artifact_record_count = materialized_payload.get("record_count")
            if artifact_record_count is None:
                artifact_record_count = len(
                    materialized_payload.get("records")
                    or materialized_payload.get("summary_records")
                    or []
                )
            artifact_record_types = _record_type_counts(materialized_payload)

            if artifact_library_id != library_state.get("materialized_library_id"):
                issues.append("materialized library id diverges from the artifact payload")
            if artifact_source_manifest_id != library_state.get("materialized_source_manifest_id"):
                issues.append("materialized source manifest id diverges from the artifact payload")
            if artifact_record_count != library_state.get("materialized_record_count"):
                issues.append("materialized record count diverges from the artifact payload")
            if artifact_record_types != library_state.get("materialized_record_types", {}):
                issues.append("materialized record types diverge from the artifact payload")
    elif materialized_payload is not None:
        issues.append("summary library artifact is present but library.materialized is false")

    if issues:
        raise ValidationError(issues)

    return {
        "status": "ok",
        "schema_version": snapshot["schema_version"],
        "task_id": snapshot["task_id"],
        "checks": [
            {"name": "schema_contract", "passed": True},
            {"name": "dashboard_parity", "passed": True},
            {"name": "summary_parity", "passed": True},
            {"name": "run_manifest_parity", "passed": True},
        ],
        "parity": {
            "completion_status": snapshot["benchmark"]["completion_status"],
            "dashboard_status": dashboard["dashboard_status"],
            "release_grade_status": snapshot["benchmark"]["release_grade_status"],
            "selected_accession_count": snapshot["benchmark"]["selected_accession_count"],
            "cohort_size": summary["execution_scope"]["cohort_size"],
            "split_counts": snapshot["benchmark"]["split_counts"],
            "truth_boundary": snapshot["benchmark"]["truth_boundary"],
        },
        "source_files": snapshot["source_files"],
        "live_state": {
            "queue_task_count": live_state["queue"]["task_count"],
            "library_materialized": live_state["library"]["materialized"],
            "library_materialized_path": live_state["library"]["materialized_path"],
            "library_materialized_library_id": live_state["library"]["materialized_library_id"],
            "library_materialized_source_manifest_id": live_state["library"][
                "materialized_source_manifest_id"
            ],
            "library_materialized_record_count": live_state["library"][
                "materialized_record_count"
            ],
            "library_materialized_record_types": live_state["library"][
                "materialized_record_types"
            ],
            "library_materialized_error": live_state["library"]["materialized_error"],
            "benchmark_release_ready": live_state["benchmark"]["release_ready"],
            "runtime_supervisor_running": live_state["runtime"]["supervisor_running"],
        },
    }


def _print_human(result: dict[str, Any]) -> None:
    print("Operator state validation passed.")
    print(f"  task_id: {result['task_id']}")
    print(f"  schema_version: {result['schema_version']}")
    print(f"  completion_status: {result['parity']['completion_status']}")
    print(f"  dashboard_status: {result['parity']['dashboard_status']}")
    print(f"  selected_accession_count: {result['parity']['selected_accession_count']}")
    print(f"  cohort_size: {result['parity']['cohort_size']}")
    print(f"  queue_task_count: {result['live_state']['queue_task_count']}")
    print(f"  runtime_supervisor_running: {result['live_state']['runtime_supervisor_running']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the live operator state against the pinned contract."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text.",
    )
    args = parser.parse_args(argv)

    try:
        result = validate_operator_state()
    except ValidationError as exc:
        payload = {"status": "error", "issues": exc.issues}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Operator state validation failed.")
            for issue in exc.issues:
                print(f"  - {issue}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive fallback for live execution.
        payload = {"status": "error", "issues": [str(exc)]}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Operator state validation failed.")
            print(f"  - {exc}")
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
