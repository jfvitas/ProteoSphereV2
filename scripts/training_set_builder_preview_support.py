from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_MISSING_DATA_POLICY = (
    REPO_ROOT / "artifacts" / "status" / "missing_data_policy_preview.json"
)
DEFAULT_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_BALANCED_DATASET_PLAN = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "balanced_dataset_plan.json"
)
DEFAULT_EXTERNAL_COHORT_AUDIT = REPO_ROOT / "artifacts" / "status" / "external_cohort_audit.json"
DEFAULT_PACKET_DEFICIT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_SPLIT_ENGINE_INPUT = REPO_ROOT / "artifacts" / "status" / "split_engine_input_preview.json"
DEFAULT_SPLIT_DRY_RUN_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_dry_run_validation.json"
)
DEFAULT_SPLIT_FOLD_EXPORT_GATE = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_gate_preview.json"
)
DEFAULT_SPLIT_POST_STAGING_GATE_CHECK = (
    REPO_ROOT / "artifacts" / "status" / "split_post_staging_gate_check_preview.json"
)
DEFAULT_SPLIT_RECIPE = REPO_ROOT / "artifacts" / "status" / "entity_split_recipe_preview.json"
DEFAULT_SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
DEFAULT_TRAINING_PACKET_AUDIT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "training_packet_audit.json"
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    normalized: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            normalized.setdefault(text.casefold(), text)
    return list(normalized.values())


def _index_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def _packet_status(row: dict[str, Any]) -> str:
    packet_expectation = row.get("packet_expectation") or {}
    status = str(packet_expectation.get("status") or "").strip()
    return status or "unknown"


def _ligand_task_status(row: dict[str, Any]) -> str:
    task = row.get("task_eligibility") or {}
    preview = task.get("grounded_ligand_similarity_preview") or {}
    return str(preview.get("status") or "").strip()


def _training_state(row: dict[str, Any]) -> str:
    ligand_status = _ligand_task_status(row)
    if ligand_status == "eligible_for_task":
        return "governing_ready"
    if ligand_status == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    if ligand_status in {"library_only", "candidate_only_non_governing"}:
        return "preview_visible_non_governing"
    full_packet = (row.get("task_eligibility") or {}).get("full_packet_current_latest") or {}
    if str(full_packet.get("status") or "").strip() == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    return "preview_visible_non_governing"


def _recommended_next_step(
    accession: str,
    eligibility_row: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> str:
    state = _training_state(eligibility_row)
    if state == "governing_ready":
        return "keep_visible_for_preview_compilation"
    if state == "preview_visible_non_governing":
        ladder = str(eligibility_row.get("ligand_readiness_ladder") or "").strip()
        if ladder == "candidate-only non-governing":
            return "keep_non_governing_until_real_ligand_rows_exist"
        return "keep_visible_as_support_only"

    for deficit in packet_deficit_dashboard.get("modality_deficits") or []:
        if not isinstance(deficit, dict):
            continue
        if accession not in _listify(deficit.get("packet_accessions")):
            continue
        refs = _listify(deficit.get("top_source_fix_refs"))
        if refs:
            return f"wait_for_source_fix:{refs[0]}"
    return "wait_for_upstream_acquisition"


def _current_blocker(
    accession: str,
    training_state: str,
    blocked_reasons: list[str],
    eligibility_row: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> str | None:
    if training_state == "governing_ready":
        return blocked_reasons[0] if blocked_reasons else None
    if training_state == "blocked_pending_acquisition":
        return _recommended_next_step(accession, eligibility_row, packet_deficit_dashboard)
    return None


def build_cohort_compiler_preview(
    eligibility_matrix: dict[str, Any],
    missing_data_policy: dict[str, Any],
    balanced_dataset_plan: dict[str, Any],
    external_cohort_audit: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> dict[str, Any]:
    del missing_data_policy
    del external_cohort_audit

    selected_rows = [
        row for row in balanced_dataset_plan.get("selected_rows") or [] if isinstance(row, dict)
    ]
    eligibility_rows = _index_by_accession(eligibility_matrix.get("rows") or [])

    compiled_rows: list[dict[str, Any]] = []
    blocked_full_packet: list[str] = []
    candidate_only_ligand: list[str] = []

    for row in selected_rows:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        eligibility_row = eligibility_rows.get(accession, {})
        packet_status = _packet_status(row)
        ligand_status = _ligand_task_status(eligibility_row)
        if packet_status == "missing":
            blocked_full_packet.append(accession)
        if ligand_status == "candidate_only_non_governing":
            candidate_only_ligand.append(accession)
        compiled_rows.append(
            {
                "accession": accession,
                "split": row.get("split"),
                "bucket": row.get("bucket"),
                "packet_status": packet_status,
                "training_set_state": _training_state(eligibility_row),
                "ligand_readiness_ladder": eligibility_row.get("ligand_readiness_ladder"),
                "recommended_next_step": _recommended_next_step(
                    accession,
                    eligibility_row,
                    packet_deficit_dashboard,
                ),
                "source_lanes": _listify(row.get("source_lanes")),
            }
        )

    summary = balanced_dataset_plan.get("summary") or {}
    return {
        "artifact_id": "cohort_compiler_preview",
        "schema_id": "proteosphere-training-set-cohort-compiler-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "row_count": len(compiled_rows),
        "summary": {
            "candidate_universe_count": int(
                eligibility_matrix.get("summary", {}).get("accession_count")
                or len(eligibility_rows)
            ),
            "selected_count": len(compiled_rows),
            "blocked_full_packet_accessions": blocked_full_packet,
            "candidate_only_ligand_accessions": candidate_only_ligand,
            "split_assignment_ready": bool(
                summary.get("leakage_safe")
                or balanced_dataset_plan.get("packet_materialization_mode") == "report_only_preview"
            ),
            "selected_split_counts": summary.get("selected_split_counts", {}),
            "selected_modality_coverage": summary.get(
                "selected_modality_coverage",
                {},
            ),
        },
        "rows": compiled_rows,
        "truth_boundary": {
            "summary": (
                "This cohort compiler is report-only. It ranks the current cohort for "
                "operator review and does not mutate manifests or authorize training."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_balance_diagnostics_preview(
    eligibility_matrix: dict[str, Any],
    missing_data_policy: dict[str, Any],
    balanced_dataset_plan: dict[str, Any],
    external_cohort_audit: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> dict[str, Any]:
    del eligibility_matrix
    del missing_data_policy
    del external_cohort_audit
    del packet_deficit_dashboard

    selected_rows = [
        row for row in balanced_dataset_plan.get("selected_rows") or [] if isinstance(row, dict)
    ]
    split_counts = Counter(str(row.get("split") or "unknown") for row in selected_rows)
    bucket_counts = Counter(str(row.get("bucket") or "unknown") for row in selected_rows)
    thin_coverage_count = sum(1 for row in selected_rows if bool(row.get("thin_coverage")))
    mixed_evidence_count = sum(1 for row in selected_rows if bool(row.get("mixed_evidence")))

    return {
        "artifact_id": "balance_diagnostics_preview",
        "schema_id": "proteosphere-balance-diagnostics-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "selected_count": len(selected_rows),
            "split_counts": dict(split_counts),
            "bucket_counts": dict(bucket_counts),
            "thin_coverage_count": thin_coverage_count,
            "mixed_evidence_count": mixed_evidence_count,
            "requested_modalities": _listify(balanced_dataset_plan.get("requested_modalities")),
        },
        "rows": selected_rows,
        "truth_boundary": {
            "summary": (
                "These diagnostics are descriptive only. They support balancing and "
                "triage, but they do not widen the cohort or override leakage rules."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_package_readiness_preview(
    eligibility_matrix: dict[str, Any],
    missing_data_policy: dict[str, Any],
    balanced_dataset_plan: dict[str, Any],
    external_cohort_audit: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_engine_dry_run_validation: dict[str, Any],
    split_fold_export_gate_preview: dict[str, Any],
    split_post_staging_gate_check_preview: dict[str, Any],
) -> dict[str, Any]:
    del eligibility_matrix
    del missing_data_policy
    del balanced_dataset_plan
    del external_cohort_audit

    packet_summary = packet_deficit_dashboard.get("summary") or {}
    split_execution = split_engine_input_preview.get("execution_readiness") or {}
    unlock = split_fold_export_gate_preview.get("unlock_readiness") or {}
    post_stage = split_post_staging_gate_check_preview.get("gate_check") or {}

    blocked_reasons: list[str] = []
    if not bool(split_execution.get("assignment_ready")):
        blocked_reasons.append("assignment_ready=false")
    if not bool(split_execution.get("fold_export_ready")):
        blocked_reasons.append("fold_export_ready=false")
    if not bool(unlock.get("cv_fold_export_unlocked")):
        blocked_reasons.append("cv_fold_export_unlocked=false")
    if split_engine_dry_run_validation.get("status") not in {"ok", "aligned"}:
        blocked_reasons.append("split_dry_run_not_aligned")
    if str(post_stage.get("gate_status") or "blocked") != "open":
        blocked_reasons.append("split_post_staging_gate_closed")

    ready_for_package = not blocked_reasons
    readiness_state = "ready_for_package" if ready_for_package else "blocked_pending_unlock"

    return {
        "artifact_id": "package_readiness_preview",
        "schema_id": "proteosphere-package-readiness-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "readiness_state": readiness_state,
        "summary": {
            "packet_count": int(packet_summary.get("packet_count") or 0),
            "judgment_counts": packet_summary.get("judgment_counts", {}),
            "completeness_counts": packet_summary.get("completeness_counts", {}),
            "fold_export_ready": bool(split_execution.get("fold_export_ready")),
            "cv_fold_export_unlocked": bool(unlock.get("cv_fold_export_unlocked")),
            "final_split_committed": bool(
                split_engine_input_preview.get("truth_boundary", {}).get("final_split_committed")
            ),
            "ready_for_package": ready_for_package,
            "readiness_state": readiness_state,
            "blocker_count": len(blocked_reasons),
            "blocked_reasons": blocked_reasons,
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only package readiness view. It does not mutate "
                "packet manifests or authorize release packaging."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_training_set_readiness_preview(
    eligibility_matrix: dict[str, Any],
    missing_data_policy: dict[str, Any],
    balanced_dataset_plan: dict[str, Any],
    external_cohort_audit: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
    split_engine_input_preview: dict[str, Any],
    split_fold_export_gate_preview: dict[str, Any],
    package_readiness_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package_payload = package_readiness_preview or build_package_readiness_preview(
        eligibility_matrix,
        missing_data_policy,
        balanced_dataset_plan,
        external_cohort_audit,
        packet_deficit_dashboard,
        split_engine_input_preview,
        {},
        split_fold_export_gate_preview,
        {},
    )

    selected_rows = [
        row for row in balanced_dataset_plan.get("selected_rows") or [] if isinstance(row, dict)
    ]
    eligibility_rows = _index_by_accession(eligibility_matrix.get("rows") or [])
    readiness_rows: list[dict[str, Any]] = []
    blocked_reasons = list(package_payload.get("summary", {}).get("blocked_reasons") or [])
    readiness_state_counts: Counter[str] = Counter()

    for row in selected_rows:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        eligibility_row = eligibility_rows.get(accession, {})
        training_state = _training_state(eligibility_row)
        readiness_state_counts[training_state] += 1
        package_state = (
            "ready_for_package"
            if training_state == "governing_ready"
            and bool(package_payload.get("summary", {}).get("ready_for_package"))
            else (
                "blocked_pending_acquisition"
                if training_state == "blocked_pending_acquisition"
                else "visible_non_governing"
            )
        )
        readiness_rows.append(
            {
                "accession": accession,
                "split": row.get("split"),
                "training_set_state": training_state,
                "packet_status": _packet_status(row),
                "current_blocker": _current_blocker(
                    accession,
                    training_state,
                    blocked_reasons,
                    eligibility_row,
                    packet_deficit_dashboard,
                ),
                "recommended_next_step": _recommended_next_step(
                    accession,
                    eligibility_row,
                    packet_deficit_dashboard,
                ),
                "package_state": package_state,
            }
        )

    audit_results = external_cohort_audit.get("audit_results") or {}
    external_audit_decision = (
        (audit_results.get("overall") or {}).get("decision")
        or (audit_results.get("overall") or {}).get("status")
        or "audit_only"
    )
    package_ready = bool(package_payload.get("summary", {}).get("ready_for_package"))
    readiness_state = (
        "package_ready_previewable" if package_ready else "preview_ready_non_governing"
    )

    return {
        "artifact_id": "training_set_readiness_preview",
        "schema_id": "proteosphere-training-set-readiness-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "readiness_state": readiness_state,
        "summary": {
            "accession_count": int(
                eligibility_matrix.get("summary", {}).get("accession_count")
                or len(eligibility_rows)
            ),
            "selected_count": len(readiness_rows),
            "blocked_reasons": blocked_reasons,
            "assignment_ready": bool(
                (split_engine_input_preview.get("execution_readiness") or {}).get(
                    "assignment_ready"
                )
            ),
            "fold_export_ready": bool(
                (split_engine_input_preview.get("execution_readiness") or {}).get(
                    "fold_export_ready"
                )
            ),
            "package_ready": package_ready,
            "external_audit_decision": external_audit_decision,
            "release_ready": False,
            "selected_split_counts": (balanced_dataset_plan.get("summary") or {}).get(
                "selected_split_counts", {}
            ),
            "governing_ready_count": readiness_state_counts.get("governing_ready", 0),
            "preview_visible_non_governing_count": readiness_state_counts.get(
                "preview_visible_non_governing", 0
            ),
            "blocked_pending_acquisition_count": readiness_state_counts.get(
                "blocked_pending_acquisition", 0
            ),
            "readiness_state_counts": dict(readiness_state_counts),
            "candidate_only_rows_non_governing": bool(
                missing_data_policy.get("truth_boundary", {}).get(
                    "candidate_only_rows_non_governing"
                )
            ),
        },
        "five_questions": {
            "eligible_now": {
                "status": "preview_only",
                "detail": (
                    "Rows can be reviewed and packet-planned now, but they remain "
                    "non-governing until explicit package and release authorization."
                ),
            },
            "blocked_now": {
                "status": "blocked" if blocked_reasons else "clear",
                "detail": blocked_reasons,
            },
            "leakage_safe": {
                "status": "preview_only",
                "detail": bool((balanced_dataset_plan.get("summary") or {}).get("leakage_safe")),
            },
            "package_ready_now": {
                "status": (
                    "clear"
                    if package_payload.get("summary", {}).get("ready_for_package")
                    else "blocked"
                ),
                "detail": package_payload.get("summary", {}).get("blocked_reasons", []),
            },
            "preview_only_remaining": {
                "status": "preview_only",
                "detail": (
                    "Training-set building remains report-only until explicit package "
                    "and release authorization is granted."
                ),
            },
        },
        "readiness_rows": readiness_rows,
        "truth_boundary": {
            "summary": (
                "This surface is report-only. It supports cohort design and readiness "
                "review, but it does not authorize packaging, release, or split changes."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_training_set_builder_session_preview(
    readiness: dict[str, Any],
    cohort_compiler: dict[str, Any],
    package_readiness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_id": "training_set_builder_session_preview",
        "schema_id": "proteosphere-training-set-builder-session-preview-2026-04-03",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "session_state": "ready_for_operator_review",
            "selected_count": (cohort_compiler.get("summary") or {}).get("selected_count"),
            "package_ready": (package_readiness.get("summary") or {}).get("ready_for_package"),
            "blocked_reasons": (readiness.get("summary") or {}).get(
                "blocked_reasons",
                [],
            ),
        },
        "recommended_cli_commands": [
            "python scripts/training_set_builder_cli.py compile-cohort",
            "python scripts/training_set_builder_cli.py balance-diagnostics",
            "python scripts/training_set_builder_cli.py assess-readiness",
            "python scripts/training_set_builder_cli.py plan-package",
            "python scripts/training_set_builder_cli.py session",
        ],
        "truth_boundary": {
            "summary": (
                "This session preview is report-only. It summarizes the current "
                "training-set builder state without materializing any package."
            ),
            "report_only": True,
        },
    }


def render_markdown(title: str, payload: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Generated at: `{payload.get('generated_at')}`",
    ]
    summary = payload.get("summary")
    if isinstance(summary, dict):
        lines.extend(["", "## Summary", ""])
        for key, value in summary.items():
            lines.append(f"- `{key}` = `{json.dumps(value, sort_keys=True)}`")
    for key in ("rows", "readiness_rows"):
        rows = payload.get(key)
        if not isinstance(rows, list) or not rows:
            continue
        lines.extend(["", f"## {key.replace('_', ' ').title()}", ""])
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            accession = row.get("accession")
            if accession:
                detail = row.get("training_set_state") or row.get("packet_status")
                lines.append(f"- `{accession}` -> `{detail}`")
    truth_boundary = payload.get("truth_boundary") or {}
    if truth_boundary.get("summary"):
        lines.extend(["", "## Truth Boundary", "", f"- {truth_boundary['summary']}"])
    lines.append("")
    return "\n".join(lines)
