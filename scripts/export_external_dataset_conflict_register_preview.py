from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from external_dataset_assessment_support import read_json, write_json  # noqa: E402

DEFAULT_ISSUE_MATRIX_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_issue_matrix_preview.json"
)
DEFAULT_RISK_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_risk_register_preview.json"
)
DEFAULT_FLAW_TAXONOMY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_flaw_taxonomy_preview.json"
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
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_conflict_register_preview.json"
)

VERDICT_RANK = {
    "blocked_pending_cleanup": 4,
    "blocked_pending_mapping": 3,
    "blocked_pending_acquisition": 2,
    "audit_only": 1,
    "usable_with_caveats": 0,
}


def _load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


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
    return VERDICT_RANK.get(verdict, -1)


def _worst_verdict(*verdicts: str) -> str:
    ranked = [verdict for verdict in verdicts if verdict]
    if not ranked:
        return "audit_only"
    return max(ranked, key=_rank_verdict)


def _row_count(value: Any, *, list_key: str | None = None) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("issue_row_count", "row_count", "count", "dataset_accession_count"):
            item = value.get(key)
            if isinstance(item, int):
                return item
            if isinstance(item, str) and item.isdigit():
                return int(item)
        if list_key and isinstance(value.get(list_key), list):
            return len(value[list_key])
    return 0


def _issue_rows(issue_matrix_preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = issue_matrix_preview.get("rows") or []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _normalize_conflict_row(row: dict[str, Any]) -> dict[str, Any]:
    issue_category = str(row.get("issue_category") or row.get("category") or "").strip()
    verdict = str(row.get("verdict") or row.get("worst_verdict") or "").strip()
    priority_bucket = str(row.get("priority_bucket") or "").strip()
    severity = str(row.get("severity") or "").strip()
    if not severity:
        if priority_bucket == "p0_blocker" or verdict.startswith("blocked"):
            severity = "high"
        elif priority_bucket.startswith("p1"):
            severity = "medium"
        else:
            severity = "low"

    issue_summary = str(row.get("issue_summary") or row.get("summary") or "").strip()
    if not issue_summary:
        if issue_category == "modality":
            issue_summary = "Mapping or acquisition conflict blocks the dataset."
        elif issue_category == "provenance":
            issue_summary = "Provenance conflict should remain explicit."
        elif issue_category == "structure":
            issue_summary = "Structure alignment conflict must stay caveated."
        elif issue_category == "binding":
            issue_summary = "Binding conflict should remain support-only."
        else:
            issue_summary = "Conflict identified in the external dataset preview."

    return {
        "accession": str(row.get("accession") or "").strip(),
        "issue_category": issue_category,
        "verdict": verdict or "usable_with_caveats",
        "severity": severity,
        "priority_bucket": priority_bucket,
        "blocking_gate": str(row.get("blocking_gate") or "").strip(),
        "issue_summary": issue_summary,
        "remediation_action": str(row.get("remediation_action") or "").strip(),
        "source_artifacts": _sorted_unique(
            row.get("source_artifacts"),
            row.get("supporting_artifacts"),
        ),
    }


def _grouped_categories(issue_matrix_preview: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = issue_matrix_preview.get("grouped_by_issue_category") or []
    if grouped:
        return [dict(row) for row in grouped if isinstance(row, dict)]

    rows = _issue_rows(issue_matrix_preview)
    categories: dict[str, dict[str, Any]] = {}
    for row in rows:
        category = str(row.get("issue_category") or "").strip()
        if not category:
            continue
        entry = categories.setdefault(
            category,
            {
                "issue_category": category,
                "issue_row_count": 0,
                "affected_accessions": [],
                "worst_verdict": "usable_with_caveats",
                "remediation_action": (
                    row.get("remediation_action") or "review manually before training"
                ),
            },
        )
        entry["issue_row_count"] += 1
        accession = str(row.get("accession") or "").strip()
        if accession and accession not in entry["affected_accessions"]:
            entry["affected_accessions"].append(accession)
        entry["worst_verdict"] = _worst_verdict(
            entry["worst_verdict"],
            str(row.get("verdict") or ""),
        )
        if row.get("remediation_action"):
            entry["remediation_action"] = str(row.get("remediation_action") or "").strip()
    return list(categories.values())


def _conflict_rows(
    issue_matrix_preview: dict[str, Any],
    risk_register_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [_normalize_conflict_row(row) for row in _issue_rows(issue_matrix_preview)]
    if not rows:
        rows = [
            _normalize_conflict_row(row)
            for row in (risk_register_preview.get("top_risk_rows") or [])
            if isinstance(row, dict)
        ]
    rows.sort(
        key=lambda row: (
            -_rank_verdict(str(row.get("verdict") or "")),
            0 if str(row.get("severity") or "") == "high" else 1,
            str(row.get("issue_category") or "").casefold(),
            str(row.get("accession") or "").casefold(),
        )
    )
    return rows[:10]


def build_external_dataset_conflict_register_preview(
    issue_matrix_preview: dict[str, Any],
    risk_register_preview: dict[str, Any],
    flaw_taxonomy_preview: dict[str, Any],
    binding_audit_preview: dict[str, Any],
    structure_audit_preview: dict[str, Any],
    provenance_audit_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
) -> dict[str, Any]:
    issue_summary = dict(issue_matrix_preview.get("summary") or {})
    risk_summary = dict(risk_register_preview.get("summary") or {})
    flaw_summary = dict(flaw_taxonomy_preview.get("summary") or {})
    provenance_summary = dict(provenance_audit_preview.get("summary") or {})
    resolution_summary = dict(resolution_preview.get("summary") or {})

    category_rows = _grouped_categories(issue_matrix_preview)
    conflict_category_counts = {
        str(row.get("issue_category") or "").strip(): int(row.get("issue_row_count") or 0)
        for row in category_rows
        if str(row.get("issue_category") or "").strip()
    }
    if not conflict_category_counts:
        conflict_category_counts = dict(issue_summary.get("issue_category_counts") or {})
    if not conflict_category_counts:
        conflict_category_counts = dict(flaw_summary.get("category_counts") or {})

    top_conflict_categories = [
        {
            "issue_category": str(row.get("issue_category") or "").strip(),
            "issue_row_count": int(row.get("issue_row_count") or 0),
            "affected_accessions": _sorted_unique(row.get("affected_accessions")),
            "worst_verdict": str(row.get("worst_verdict") or "").strip(),
            "remediation_action": str(row.get("remediation_action") or "").strip(),
        }
        for row in sorted(
            category_rows,
            key=lambda row: (
                -int(row.get("issue_row_count") or 0),
                str(row.get("issue_category") or "").casefold(),
            ),
        )
    ][:5]

    top_conflict_rows = _conflict_rows(issue_matrix_preview, risk_register_preview)
    dataset_accession_count = int(issue_summary.get("dataset_accession_count") or 0)
    if not dataset_accession_count:
        dataset_accession_count = int(risk_summary.get("dataset_accession_count") or 0)
    if not dataset_accession_count:
        dataset_accession_count = int(flaw_summary.get("dataset_accession_count") or 0)

    blocked_gate_count = int(risk_summary.get("blocked_gate_count") or 0)
    if not blocked_gate_count:
        blocked_gate_count = int(resolution_summary.get("blocked_gate_count") or 0)

    overall_verdict = _worst_verdict(
        str(issue_summary.get("overall_verdict") or ""),
        str(risk_summary.get("overall_verdict") or ""),
        str(flaw_summary.get("overall_verdict") or ""),
        str(resolution_summary.get("overall_resolution_verdict") or ""),
        str(binding_audit_preview.get("verdict") or ""),
        str(structure_audit_preview.get("verdict") or ""),
        str(provenance_audit_preview.get("verdict") or ""),
    )

    if not overall_verdict:
        overall_verdict = "audit_only"

    mapping_conflict_present = bool(
        conflict_category_counts.get("modality")
        or flaw_summary.get("blocking_category_counts", {}).get("modality")
        or risk_summary.get("mapping_risk_present")
        or issue_summary.get("overall_verdict") == "blocked_pending_mapping"
        or resolution_summary.get("overall_resolution_verdict") == "blocked_pending_mapping"
    )
    provenance_conflict_present = bool(
        risk_summary.get("patent_or_provenance_risk_present")
        or str(provenance_audit_preview.get("verdict") or "").strip()
        not in {"", "usable_with_caveats"}
        or provenance_summary.get("contract_status") not in {None, "report_only"}
    )

    summary = {
        "dataset_accession_count": dataset_accession_count,
        "overall_verdict": overall_verdict,
        "conflict_category_counts": conflict_category_counts,
        "top_conflict_categories": top_conflict_categories,
        "blocked_gate_count": blocked_gate_count,
        "mapping_conflict_present": mapping_conflict_present,
        "provenance_conflict_present": provenance_conflict_present,
        "non_mutating": True,
        "top_conflict_row_count": len(top_conflict_rows),
        "blocked_accession_count": int(risk_summary.get("blocked_accession_count") or 0),
        "caveated_accession_count": int(risk_summary.get("caveated_accession_count") or 0),
        "resolved_accession_count": int(risk_summary.get("resolved_accession_count") or 0),
    }

    source_artifacts = {
        "issue_matrix_preview": issue_matrix_preview.get("artifact_id") or "",
        "risk_register_preview": risk_register_preview.get("artifact_id") or "",
        "flaw_taxonomy_preview": flaw_taxonomy_preview.get("artifact_id") or "",
        "binding_audit_preview": binding_audit_preview.get("artifact_id") or "",
        "structure_audit_preview": structure_audit_preview.get("artifact_id") or "",
        "provenance_audit_preview": provenance_audit_preview.get("artifact_id") or "",
        "resolution_preview": resolution_preview.get("artifact_id") or "",
    }

    missing_inputs = sorted(
        [
            name
            for name, artifact_id in source_artifacts.items()
            if not str(artifact_id or "").strip()
        ],
        key=str.casefold,
    )
    if missing_inputs:
        summary["overall_verdict"] = _worst_verdict(
            summary["overall_verdict"],
            "blocked_pending_mapping",
        )

    return {
        "artifact_id": "external_dataset_conflict_register_preview",
        "schema_id": "proteosphere-external-dataset-conflict-register-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            issue_matrix_preview.get("generated_at")
            or risk_register_preview.get("generated_at")
            or flaw_taxonomy_preview.get("generated_at")
            or binding_audit_preview.get("generated_at")
            or structure_audit_preview.get("generated_at")
            or provenance_audit_preview.get("generated_at")
            or resolution_preview.get("generated_at")
            or ""
        ),
        "summary": summary,
        "top_conflict_rows": top_conflict_rows,
        "source_artifacts": source_artifacts,
        "truth_boundary": {
            "summary": (
                "This conflict register is advisory and fail-closed. It compacts "
                "existing issue, risk, flaw, and audit previews without mutating "
                "source truth or implying training-safe acceptance."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a fail-closed external dataset conflict register preview."
    )
    parser.add_argument("--issue-matrix-preview", type=Path, default=DEFAULT_ISSUE_MATRIX_PREVIEW)
    parser.add_argument("--risk-register-preview", type=Path, default=DEFAULT_RISK_REGISTER_PREVIEW)
    parser.add_argument(
        "--flaw-taxonomy-preview", type=Path, default=DEFAULT_FLAW_TAXONOMY_PREVIEW
    )
    parser.add_argument("--binding-audit-preview", type=Path, default=DEFAULT_BINDING_AUDIT_PREVIEW)
    parser.add_argument(
        "--structure-audit-preview", type=Path, default=DEFAULT_STRUCTURE_AUDIT_PREVIEW
    )
    parser.add_argument(
        "--provenance-audit-preview", type=Path, default=DEFAULT_PROVENANCE_AUDIT_PREVIEW
    )
    parser.add_argument("--resolution-preview", type=Path, default=DEFAULT_RESOLUTION_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_conflict_register_preview(
        _load_payload(args.issue_matrix_preview),
        _load_payload(args.risk_register_preview),
        _load_payload(args.flaw_taxonomy_preview),
        _load_payload(args.binding_audit_preview),
        _load_payload(args.structure_audit_preview),
        _load_payload(args.provenance_audit_preview),
        _load_payload(args.resolution_preview),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
