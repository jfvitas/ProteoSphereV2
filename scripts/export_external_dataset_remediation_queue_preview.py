from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from external_dataset_assessment_support import read_json, write_json  # noqa: E402

DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_LEAKAGE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_leakage_audit_preview.json"
)
DEFAULT_MODALITY_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_modality_audit_preview.json"
)
DEFAULT_BINDING_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_binding_audit_preview.json"
)
DEFAULT_STRUCTURE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_structure_audit_preview.json"
)
DEFAULT_PROVENANCE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)

BLOCKING_VERDICTS = {
    "blocked_pending_acquisition",
    "blocked_pending_cleanup",
    "blocked_pending_mapping",
    "unsafe_for_training",
}

PRIORITY_BUCKET_ORDER = {
    "p0_blocker": 0,
    "p1_follow_up": 1,
    "p2_support_context": 2,
    "p3_monitor": 3,
}

CATEGORY_ORDER = {
    "modality": 0,
    "leakage": 1,
    "structure": 2,
    "binding": 3,
    "provenance": 4,
}

SOURCE_ARTIFACT_FALLBACKS = {
    "resolution_preview": "external_dataset_resolution_preview",
    "issue_matrix_preview": "external_dataset_issue_matrix_preview",
    "acceptance_gate_preview": "external_dataset_acceptance_gate_preview",
    "leakage": "external_dataset_leakage_audit_preview",
    "modality": "external_dataset_modality_audit_preview",
    "binding": "external_dataset_binding_audit_preview",
    "structure": "external_dataset_structure_audit_preview",
    "provenance": "external_dataset_provenance_audit_preview",
}


def _ensure_dict(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _sorted_unique(*values: Any) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        for text in _listify(value):
            normalized.setdefault(text.casefold(), text)
    return sorted(normalized.values(), key=str.casefold)


def _rank_verdict(verdict: str) -> int:
    if verdict in BLOCKING_VERDICTS:
        return 3
    if verdict == "usable_with_caveats":
        return 2
    if verdict == "audit_only":
        return 1
    return 0


def _artifact_id(payload: dict[str, Any], fallback: str) -> str:
    return str(payload.get("artifact_id") or fallback).strip()


def _issue_rows(issue_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = issue_matrix.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _resolution_rows(resolution_preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = resolution_preview.get("accession_resolution_rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _accession_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def _priority_bucket(issue_category: str, verdict: str) -> str:
    if verdict in BLOCKING_VERDICTS:
        return "p0_blocker"
    if issue_category in {"modality", "leakage", "structure"}:
        return "p1_follow_up"
    if issue_category in {"binding", "provenance"}:
        return "p2_support_context"
    return "p3_monitor"


def _queue_row_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str, str]:
    return (
        PRIORITY_BUCKET_ORDER.get(str(row.get("priority_bucket") or ""), 99),
        -_rank_verdict(str(row.get("worst_verdict") or "")),
        CATEGORY_ORDER.get(str(row.get("issue_category") or ""), 99),
        str(row.get("blocking_gate") or "").casefold(),
        str(row.get("accession") or "").casefold(),
    )


def _supporting_artifacts(
    *,
    row: dict[str, Any],
    resolution_row: dict[str, Any],
    source_artifacts: dict[str, str],
) -> list[str]:
    issue_category = str(row.get("issue_category") or "").strip()
    category_artifact = source_artifacts.get(issue_category, "")
    return _sorted_unique(
        resolution_row.get("supporting_artifacts"),
        row.get("source_artifacts"),
        source_artifacts["resolution_preview"],
        source_artifacts["issue_matrix_preview"],
        source_artifacts["acceptance_gate_preview"],
        category_artifact,
    )


def build_external_dataset_remediation_queue_preview(
    resolution_preview: dict[str, Any],
    issue_matrix_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    leakage_audit: dict[str, Any],
    modality_audit: dict[str, Any],
    binding_audit: dict[str, Any],
    structure_audit: dict[str, Any],
    provenance_audit: dict[str, Any],
) -> dict[str, Any]:
    resolution_preview = _ensure_dict(resolution_preview, "resolution preview")
    issue_matrix_preview = _ensure_dict(issue_matrix_preview, "issue matrix preview")
    acceptance_gate_preview = _ensure_dict(
        acceptance_gate_preview, "acceptance gate preview"
    )
    leakage_audit = _ensure_dict(leakage_audit, "leakage audit")
    modality_audit = _ensure_dict(modality_audit, "modality audit")
    binding_audit = _ensure_dict(binding_audit, "binding audit")
    structure_audit = _ensure_dict(structure_audit, "structure audit")
    provenance_audit = _ensure_dict(provenance_audit, "provenance audit")

    resolution_summary = _ensure_dict(
        resolution_preview.get("summary") or {}, "resolution summary"
    )
    issue_summary = _ensure_dict(issue_matrix_preview.get("summary") or {}, "issue matrix summary")
    acceptance_summary = _ensure_dict(
        acceptance_gate_preview.get("summary") or {}, "acceptance gate summary"
    )
    leakage_summary = _ensure_dict(leakage_audit.get("summary") or {}, "leakage summary")
    modality_summary = _ensure_dict(modality_audit.get("summary") or {}, "modality summary")
    binding_summary = _ensure_dict(binding_audit.get("summary") or {}, "binding summary")
    structure_summary = _ensure_dict(structure_audit.get("summary") or {}, "structure summary")
    provenance_summary = _ensure_dict(
        provenance_audit.get("summary") or {}, "provenance summary"
    )

    resolution_rows = _resolution_rows(resolution_preview)
    resolution_by_accession = _accession_index(resolution_rows)
    issue_rows = _issue_rows(issue_matrix_preview)

    source_artifacts = {
        name: _artifact_id(payload, fallback)
        for name, payload, fallback in [
            (
                "resolution_preview",
                resolution_preview,
                SOURCE_ARTIFACT_FALLBACKS["resolution_preview"],
            ),
            (
                "issue_matrix_preview",
                issue_matrix_preview,
                SOURCE_ARTIFACT_FALLBACKS["issue_matrix_preview"],
            ),
            (
                "acceptance_gate_preview",
                acceptance_gate_preview,
                SOURCE_ARTIFACT_FALLBACKS["acceptance_gate_preview"],
            ),
            ("leakage", leakage_audit, SOURCE_ARTIFACT_FALLBACKS["leakage"]),
            ("modality", modality_audit, SOURCE_ARTIFACT_FALLBACKS["modality"]),
            ("binding", binding_audit, SOURCE_ARTIFACT_FALLBACKS["binding"]),
            ("structure", structure_audit, SOURCE_ARTIFACT_FALLBACKS["structure"]),
            ("provenance", provenance_audit, SOURCE_ARTIFACT_FALLBACKS["provenance"]),
        ]
    }

    queue_rows: list[dict[str, Any]] = []
    for row in issue_rows:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        resolution_row = dict(resolution_by_accession.get(accession) or {})
        worst_verdict = str(
            resolution_row.get("worst_verdict")
            or row.get("verdict")
            or issue_summary.get("overall_verdict")
            or "usable_with_caveats"
        )
        issue_category = str(row.get("issue_category") or "").strip()
        blocking_gates = _sorted_unique(resolution_row.get("blocking_gates"))
        blocking_gate = blocking_gates[0] if blocking_gates else issue_category
        priority_bucket = _priority_bucket(issue_category, worst_verdict)
        queue_rows.append(
            {
                "accession": accession,
                "issue_category": issue_category,
                "remediation_action": str(row.get("remediation_action") or "").strip(),
                "priority_bucket": priority_bucket,
                "blocking_gate": blocking_gate,
                "worst_verdict": worst_verdict,
                "supporting_artifacts": _supporting_artifacts(
                    row=row,
                    resolution_row=resolution_row,
                    source_artifacts=source_artifacts,
                ),
            }
        )

    queue_rows.sort(key=_queue_row_sort_key)

    rows_by_accession: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in queue_rows:
        rows_by_accession[str(row.get("accession") or "")].append(row)

    priority_bucket_counts = Counter(row["priority_bucket"] for row in queue_rows)
    blocked_queue_rows = [row for row in queue_rows if row["priority_bucket"] == "p0_blocker"]
    remediation_action_by_gate = {
        str(item.get("issue_category") or "").strip(): str(
            item.get("remediation_action") or ""
        ).strip()
        for item in acceptance_summary.get("top_remediation_categories") or []
        if isinstance(item, dict) and str(item.get("issue_category") or "").strip()
    }

    top_blocking_gates = [
        {
            "blocking_gate": blocking_gate,
            "queue_row_count": count,
            "remediation_action": remediation_action_by_gate.get(blocking_gate, ""),
        }
        for blocking_gate, count in Counter(
            row["blocking_gate"] for row in blocked_queue_rows if row["blocking_gate"]
        ).most_common(5)
    ]

    top_priority_accessions = []
    for accession in sorted(rows_by_accession, key=str.casefold):
        accession_rows = rows_by_accession[accession]
        blocked_rows = [row for row in accession_rows if row["priority_bucket"] == "p0_blocker"]
        best_priority = min(
            PRIORITY_BUCKET_ORDER.get(row["priority_bucket"], 99) for row in accession_rows
        )
        top_priority_accessions.append(
            {
                "accession": accession,
                "priority_bucket": next(
                    row["priority_bucket"]
                    for row in accession_rows
                    if PRIORITY_BUCKET_ORDER.get(row["priority_bucket"], 99) == best_priority
                ),
                "worst_verdict": max(
                    accession_rows, key=lambda item: _rank_verdict(str(item["worst_verdict"]))
                )["worst_verdict"],
                "issue_categories": sorted(
                    {row["issue_category"] for row in accession_rows if row["issue_category"]},
                    key=str.casefold,
                ),
                "blocking_gates": sorted(
                    {row["blocking_gate"] for row in accession_rows if row["blocking_gate"]},
                    key=str.casefold,
                ),
                "blocking_row_count": len(blocked_rows),
            }
        )

    top_priority_accessions.sort(
        key=lambda item: (
            PRIORITY_BUCKET_ORDER.get(str(item.get("priority_bucket") or ""), 99),
            -_rank_verdict(str(item.get("worst_verdict") or "")),
            -int(item.get("blocking_row_count") or 0),
            str(item.get("accession") or "").casefold(),
        )
    )

    blocked_accession_count = len(
        {row["accession"] for row in blocked_queue_rows if row.get("accession")}
    )
    overall_queue_verdict = str(
        acceptance_summary.get("overall_gate_verdict")
        or issue_summary.get("overall_verdict")
        or resolution_summary.get("overall_resolution_verdict")
        or "usable_with_caveats"
    )
    if overall_queue_verdict not in {
        "usable_with_caveats",
        "blocked_pending_acquisition",
        "blocked_pending_cleanup",
        "blocked_pending_mapping",
        "unsafe_for_training",
        "audit_only",
    }:
        overall_queue_verdict = "usable_with_caveats"

    return {
        "artifact_id": "external_dataset_remediation_queue_preview",
        "schema_id": "proteosphere-external-dataset-remediation-queue-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            resolution_preview.get("generated_at")
            or issue_matrix_preview.get("generated_at")
            or acceptance_gate_preview.get("generated_at")
            or ""
        ),
        "summary": {
            "dataset_accession_count": int(acceptance_summary.get("dataset_accession_count") or 0),
            "remediation_queue_row_count": len(queue_rows),
            "queue_accession_count": len(rows_by_accession),
            "blocked_queue_row_count": len(blocked_queue_rows),
            "blocked_accession_count": blocked_accession_count,
            "overall_queue_verdict": overall_queue_verdict,
            "priority_bucket_counts": dict(priority_bucket_counts),
            "top_blocking_gates": top_blocking_gates,
            "top_priority_accessions": top_priority_accessions[:5],
        },
        "rows": queue_rows,
        "source_artifacts": source_artifacts,
        "supporting_artifacts": {
            "resolution_verdict": resolution_summary.get("overall_resolution_verdict"),
            "issue_matrix_verdict": issue_summary.get("overall_verdict"),
            "acceptance_gate_verdict": acceptance_summary.get("overall_gate_verdict"),
            "sub_audits": {
                "leakage": leakage_summary.get("duplicate_accession_count"),
                "modality": modality_summary.get("blocked_full_packet_accession_count"),
                "binding": binding_summary.get("measured_accession_count"),
                "structure": structure_summary.get("seed_structure_overlap_accession_count"),
                "provenance": provenance_summary.get("row_level_resolution_supported"),
            },
        },
        "truth_boundary": {
            "summary": (
                "This remediation queue is advisory, fail-closed, and non-mutating. "
                "It only reorganizes the current external-assessment artifacts into "
                "operator follow-up rows and does not authorize training-safe use."
            ),
            "report_only": True,
            "fail_closed": True,
            "non_mutating": True,
            "training_safe_acceptance_not_implied": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an advisory external dataset remediation queue preview."
    )
    parser.add_argument("--resolution-preview", type=Path, default=DEFAULT_RESOLUTION_PREVIEW)
    parser.add_argument("--issue-matrix-preview", type=Path, default=DEFAULT_ISSUE_MATRIX_PREVIEW)
    parser.add_argument(
        "--acceptance-gate-preview", type=Path, default=DEFAULT_ACCEPTANCE_GATE_PREVIEW
    )
    parser.add_argument("--leakage-audit", type=Path, default=DEFAULT_LEAKAGE_AUDIT_PREVIEW)
    parser.add_argument("--modality-audit", type=Path, default=DEFAULT_MODALITY_AUDIT_PREVIEW)
    parser.add_argument("--binding-audit", type=Path, default=DEFAULT_BINDING_AUDIT_PREVIEW)
    parser.add_argument("--structure-audit", type=Path, default=DEFAULT_STRUCTURE_AUDIT_PREVIEW)
    parser.add_argument("--provenance-audit", type=Path, default=DEFAULT_PROVENANCE_AUDIT_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_remediation_queue_preview(
        read_json(args.resolution_preview),
        read_json(args.issue_matrix_preview),
        read_json(args.acceptance_gate_preview),
        read_json(args.leakage_audit),
        read_json(args.modality_audit),
        read_json(args.binding_audit),
        read_json(args.structure_audit),
        read_json(args.provenance_audit),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
