from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def listify(values: Any) -> list[str]:
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


def selected_rows(balanced_dataset_plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in (balanced_dataset_plan.get("selected_rows") or [])
        if isinstance(row, dict)
    ]


def rows_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = dict(row)
    return indexed


def packet_rows_by_accession(packet_deficit_dashboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return rows_by_accession(
        [row for row in (packet_deficit_dashboard.get("packets") or []) if isinstance(row, dict)]
    )


def training_state(eligibility_row: dict[str, Any]) -> str:
    task = eligibility_row.get("task_eligibility") or {}
    ligand = (task.get("grounded_ligand_similarity_preview") or {}).get("status")
    full_packet = (task.get("full_packet_current_latest") or {}).get("status")
    if ligand == "eligible_for_task":
        return "governing_ready_but_package_blocked"
    if full_packet == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    return "preview_visible_non_governing"


def requested_modalities() -> tuple[str, ...]:
    return ("sequence", "structure", "ligand", "ppi", "variant")


def present_modalities(eligibility_row: dict[str, Any]) -> list[str]:
    present = listify(eligibility_row.get("packet_present_modalities"))
    if int(eligibility_row.get("variant_count") or 0) > 0:
        present = listify([*present, "variant"])
    return present


def missing_modalities(eligibility_row: dict[str, Any]) -> list[str]:
    present = set(present_modalities(eligibility_row))
    return [modality for modality in requested_modalities() if modality not in present]


def packet_lane_for_state(state: str) -> str:
    if state == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    if state == "governing_ready_but_package_blocked":
        return "governing_ready_but_package_blocked"
    return "non_governing_materializable"


def materialization_mode_for_state(state: str) -> str:
    if state == "blocked_pending_acquisition":
        return "deficit_only_packet_stub"
    if state == "governing_ready_but_package_blocked":
        return "governing_ready_visibility_only_stub"
    return "support_only_packet_stub"


def build_packet_completeness_matrix_preview(
    eligibility_matrix: dict[str, Any],
    balanced_dataset_plan: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> dict[str, Any]:
    eligibility_by_accession = rows_by_accession(eligibility_matrix.get("rows") or [])
    packet_by_accession = packet_rows_by_accession(packet_deficit_dashboard)
    rows: list[dict[str, Any]] = []
    modality_missing_counts = Counter()
    lane_counts = Counter()
    for row in selected_rows(balanced_dataset_plan):
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        eligibility_row = eligibility_by_accession.get(accession, {})
        packet_row = packet_by_accession.get(accession, {})
        state = training_state(eligibility_row)
        lane = packet_lane_for_state(state)
        lane_counts[lane] += 1
        missing = missing_modalities(eligibility_row)
        for modality in missing:
            modality_missing_counts[modality] += 1
        rows.append(
            {
                "accession": accession,
                "split": row.get("split"),
                "packet_status": (
                    eligibility_row.get("packet_status")
                    or row.get("packet_expectation", {}).get("status")
                ),
                "training_state": state,
                "packet_lane": lane,
                "requested_modalities": list(requested_modalities()),
                "present_modalities": present_modalities(eligibility_row),
                "missing_modalities": missing,
                "packet_manifest_path": packet_row.get("manifest_path"),
                "deficit_source_refs": listify(packet_row.get("deficit_source_refs")),
            }
        )

    return {
        "artifact_id": "training_packet_completeness_matrix_preview",
        "schema_id": "proteosphere-training-packet-completeness-matrix-preview-2026-04-04",
        "status": "report_only",
        "generated_at": utc_now(),
        "row_count": len(rows),
        "summary": {
            "selected_accession_count": len(rows),
            "packet_lane_counts": dict(lane_counts),
            "missing_modality_counts": dict(modality_missing_counts),
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This matrix is pre-package only. It reports packet completeness and deficits "
                "for the current cohort without mutating protected latest manifests."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_split_alignment_recheck_preview(
    balanced_dataset_plan: dict[str, Any],
    split_simulation_preview: dict[str, Any],
) -> dict[str, Any]:
    selected = selected_rows(balanced_dataset_plan)
    split_rows = rows_by_accession(split_simulation_preview.get("rows") or [])
    mismatches: list[dict[str, Any]] = []
    matched_count = 0
    for row in selected:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        simulated = split_rows.get(accession, {})
        planned_split = str(row.get("split") or "").strip()
        simulated_split = str(simulated.get("split") or "").strip()
        if planned_split and planned_split == simulated_split:
            matched_count += 1
            continue
        mismatches.append(
            {
                "accession": accession,
                "planned_split": planned_split,
                "simulated_split": simulated_split or "missing",
            }
        )

    split_counts = Counter(str(row.get("split") or "unknown") for row in selected)
    return {
        "artifact_id": "training_split_alignment_recheck_preview",
        "schema_id": "proteosphere-training-split-alignment-recheck-preview-2026-04-04",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "selected_accession_count": len(selected),
            "matched_accession_count": matched_count,
            "mismatch_count": len(mismatches),
            "expected_split_counts": dict(split_counts),
            "expected_8_2_2_layout": dict(split_counts) == {"train": 8, "val": 2, "test": 2},
            "package_ready": bool(split_simulation_preview.get("summary", {}).get("package_ready")),
        },
        "mismatches": mismatches,
        "truth_boundary": {
            "summary": (
                "This is a split consistency recheck only. It compares current cohort selections "
                "to the frozen simulated split and does not alter split state."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def materialize_pre_tail_packet_stubs(
    *,
    output_root: Path,
    eligibility_matrix: dict[str, Any],
    balanced_dataset_plan: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> dict[str, Any]:
    eligibility_by_accession = rows_by_accession(eligibility_matrix.get("rows") or [])
    packet_by_accession = packet_rows_by_accession(packet_deficit_dashboard)
    rows: list[dict[str, Any]] = []
    lane_counts = Counter()
    output_root.mkdir(parents=True, exist_ok=True)

    for row in selected_rows(balanced_dataset_plan):
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        eligibility_row = eligibility_by_accession.get(accession, {})
        packet_row = packet_by_accession.get(accession, {})
        state = training_state(eligibility_row)
        lane = packet_lane_for_state(state)
        mode = materialization_mode_for_state(state)
        lane_counts[lane] += 1
        stub_dir = output_root / accession
        stub_dir.mkdir(parents=True, exist_ok=True)
        stub_path = stub_dir / "packet_stub.json"
        payload = {
            "packet_id": f"pretail-stub-{accession.lower()}",
            "accession": accession,
            "canonical_id": str(row.get("canonical_id") or f"protein:{accession}"),
            "split": row.get("split"),
            "training_state": state,
            "packet_lane": lane,
            "materialization_mode": mode,
            "requested_modalities": list(requested_modalities()),
            "present_modalities": present_modalities(eligibility_row),
            "missing_modalities": missing_modalities(eligibility_row),
            "packet_manifest_path": packet_row.get("manifest_path"),
            "deficit_source_refs": listify(packet_row.get("deficit_source_refs")),
            "notes": [
                "pre-tail packet stub only",
                "non-mutating visibility artifact",
            ],
        }
        write_json(stub_path, payload)
        rows.append(
            {
                "accession": accession,
                "split": row.get("split"),
                "training_state": state,
                "packet_lane": lane,
                "materialization_mode": mode,
                "stub_path": str(stub_path).replace("\\", "/"),
                "missing_modalities": payload["missing_modalities"],
            }
        )

    return {
        "artifact_id": "training_packet_materialization_queue_preview",
        "schema_id": "proteosphere-training-packet-materialization-queue-preview-2026-04-04",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "selected_accession_count": len(rows),
            "packet_lane_counts": dict(lane_counts),
            "stub_root": str(output_root).replace("\\", "/"),
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "These packet stubs are visibility-only scaffolds. They do not promote package "
                "state and do not mutate protected latest package manifests."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_external_dataset_remediation_template_preview(
    assessment_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
) -> dict[str, Any]:
    sub_audits = assessment_preview.get("sub_audits") or {}
    top_issue_categories = resolution_preview.get("summary", {}).get("top_issue_categories") or []
    artifact_map = {
        "binding": "external_dataset_binding_audit_preview",
        "modality": "external_dataset_modality_audit_preview",
        "provenance": "external_dataset_provenance_audit_preview",
        "structure": "external_dataset_structure_audit_preview",
        "leakage": "external_dataset_leakage_audit_preview",
    }
    action_map = {
        "binding": "keep binding rows support-only until case-specific validation passes",
        "modality": "resolve mapping or acquisition blockers before training",
        "provenance": "keep provenance explicit and avoid collapsing mixed trust tiers",
        "structure": "preserve PDB-to-UniProt alignment and keep adjacent context separate",
        "leakage": "preserve frozen split boundaries and remove duplicate or cross-split entities",
    }
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in list(sub_audits.keys()) + [
        str(row.get("issue_category") or "").strip() for row in top_issue_categories
    ]:
        category_text = str(category or "").strip()
        if not category_text or category_text in seen:
            continue
        seen.add(category_text)
        rows.append(
            {
                "issue_category": category_text,
                "current_verdict": sub_audits.get(category_text),
                "supporting_artifact": artifact_map.get(category_text),
                "recommended_action": action_map.get(
                    category_text,
                    "keep this issue category advisory and fail-closed until explicitly resolved",
                ),
            }
        )
    return {
        "artifact_id": "external_dataset_remediation_template_preview",
        "schema_id": "proteosphere-external-dataset-remediation-template-preview-2026-04-04",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "overall_verdict": assessment_preview.get("summary", {}).get("overall_verdict"),
            "template_row_count": len(rows),
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This template maps known flaw categories to remediation actions using current "
                "internal truth surfaces. It is advisory and does not bless datasets for training."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def build_external_dataset_resolution_diff_preview(
    split_simulation_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
) -> dict[str, Any]:
    claimed_rows = rows_by_accession(split_simulation_preview.get("rows") or [])
    resolved_rows = rows_by_accession(
        resolution_preview.get("accession_resolution_rows") or []
    )
    rows: list[dict[str, Any]] = []
    unresolved_count = 0
    conflicted_count = 0
    for accession, claim in claimed_rows.items():
        resolved = resolved_rows.get(accession, {})
        resolution_state = str(resolved.get("resolution_state") or "missing").strip()
        blocking_gates = listify(resolved.get("blocking_gates"))
        if resolution_state in {"blocked", "missing"}:
            unresolved_count += 1
        if blocking_gates:
            conflicted_count += 1
        rows.append(
            {
                "accession": accession,
                "claimed_split": claim.get("split"),
                "claimed_bucket": claim.get("bucket"),
                "resolved_state": resolution_state,
                "worst_verdict": resolved.get("worst_verdict"),
                "blocking_gates": blocking_gates,
                "remaining_issue_categories": listify(resolved.get("issue_categories")),
            }
        )
    rows.sort(key=lambda row: row["accession"])
    return {
        "artifact_id": "external_dataset_resolution_diff_preview",
        "schema_id": "proteosphere-external-dataset-resolution-diff-preview-2026-04-04",
        "status": "report_only",
        "generated_at": utc_now(),
        "summary": {
            "claimed_accession_count": len(claimed_rows),
            "resolved_accession_count": len(resolved_rows),
            "unresolved_or_blocked_count": unresolved_count,
            "conflicted_accession_count": conflicted_count,
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This diff compares intake-style accession claims to current internal resolution "
                "state. It remains advisory and fail-closed."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }
