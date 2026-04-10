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

DEFAULT_ASSESSMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_FLAW_TAXONOMY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_flaw_taxonomy_preview.json"
)
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_PROVENANCE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_provenance_audit_preview.json"
)
DEFAULT_BINDING_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_binding_audit_preview.json"
)
DEFAULT_STRUCTURE_AUDIT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_structure_audit_preview.json"
)
DEFAULT_REMEDIATION_QUEUE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_queue_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_risk_register_preview.json"
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


def _count_from_rows(rows: Any, *, key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        value = str(row.get(key) or "").strip()
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def _normalize_risk_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "accession": str(row.get("accession") or "").strip(),
        "issue_category": str(row.get("issue_category") or row.get("category") or "").strip(),
        "priority_bucket": str(row.get("priority_bucket") or "").strip(),
        "blocking_gate": str(row.get("blocking_gate") or "").strip(),
        "worst_verdict": str(row.get("worst_verdict") or "").strip(),
        "remediation_action": str(row.get("remediation_action") or "").strip(),
        "supporting_artifacts": _sorted_unique(row.get("supporting_artifacts")),
    }


def _top_risk_rows(remediation_queue_preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = remediation_queue_preview.get("rows") or []
    compact_rows = [_normalize_risk_row(row) for row in rows if isinstance(row, dict)]
    compact_rows.sort(
        key=lambda row: (
            0 if row.get("priority_bucket") == "p0_blocker" else 1,
            -_rank_verdict(str(row.get("worst_verdict") or "")),
            str(row.get("issue_category") or "").casefold(),
            str(row.get("accession") or "").casefold(),
        )
    )
    return compact_rows[:8]


def _highest_risk_categories(
    *,
    flaw_taxonomy: dict[str, Any],
    remediation_queue: dict[str, Any],
) -> list[dict[str, Any]]:
    taxonomy_summary = dict(flaw_taxonomy.get("summary") or {})
    taxonomy_rows = [
        row for row in (flaw_taxonomy.get("category_rows") or []) if isinstance(row, dict)
    ]
    category_counts = dict(taxonomy_summary.get("category_counts") or {})
    if not category_counts:
        category_counts = _count_from_rows(taxonomy_rows, key="category")
    if not category_counts:
        category_counts = _count_from_rows(
            remediation_queue.get("rows") or [],
            key="issue_category",
        )

    top_rows = list(taxonomy_summary.get("top_blocking_categories") or [])
    if not top_rows:
        for category, count in sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0].casefold())
        ):
            top_rows.append(
                {
                    "category": category,
                    "affected_accession_count": count,
                    "resolution_state": "blocked" if count else "caveated",
                    "worst_verdict": (
                        "blocked_pending_acquisition" if count else "usable_with_caveats"
                    ),
                    "remediation_action": "review manually before training",
                }
            )

    return [
        {
            "category": str(row.get("category") or "").strip(),
            "affected_accession_count": int(row.get("affected_accession_count") or 0),
            "resolution_state": str(row.get("resolution_state") or "").strip(),
            "worst_verdict": str(row.get("worst_verdict") or "").strip(),
            "remediation_action": str(row.get("remediation_action") or "").strip(),
        }
        for row in sorted(
            top_rows,
            key=lambda item: (
                -int(item.get("affected_accession_count") or 0),
                str(item.get("category") or "").casefold(),
            ),
        )
    ][:5]


def build_external_dataset_risk_register_preview(
    assessment_preview: dict[str, Any],
    flaw_taxonomy_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    provenance_audit_preview: dict[str, Any],
    binding_audit_preview: dict[str, Any],
    structure_audit_preview: dict[str, Any],
    remediation_queue_preview: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = dict(assessment_preview.get("summary") or {})
    flaw_summary = dict(flaw_taxonomy_preview.get("summary") or {})
    acceptance_summary = dict(acceptance_gate_preview.get("summary") or {})
    provenance_summary = dict(provenance_audit_preview.get("summary") or {})
    structure_summary = dict(structure_audit_preview.get("summary") or {})
    remediation_summary = dict(remediation_queue_preview.get("summary") or {})

    source_artifacts = {
        "assessment_preview": assessment_preview.get("artifact_id") or "",
        "flaw_taxonomy_preview": flaw_taxonomy_preview.get("artifact_id") or "",
        "acceptance_gate_preview": acceptance_gate_preview.get("artifact_id") or "",
        "provenance_audit_preview": provenance_audit_preview.get("artifact_id") or "",
        "binding_audit_preview": binding_audit_preview.get("artifact_id") or "",
        "structure_audit_preview": structure_audit_preview.get("artifact_id") or "",
        "remediation_queue_preview": remediation_queue_preview.get("artifact_id") or "",
    }
    missing_inputs = sorted(
        name for name, artifact_id in source_artifacts.items() if not str(artifact_id or "").strip()
    )

    risk_category_counts = dict(flaw_summary.get("category_counts") or {})
    if not risk_category_counts:
        risk_category_counts = _count_from_rows(
            remediation_queue_preview.get("rows") or [],
            key="issue_category",
        )

    highest_risk_categories = _highest_risk_categories(
        flaw_taxonomy=flaw_taxonomy_preview,
        remediation_queue=remediation_queue_preview,
    )
    top_risk_rows = _top_risk_rows(remediation_queue_preview)

    blocked_gate_count = int(acceptance_summary.get("blocked_gate_count") or 0)
    patent_or_provenance_risk_present = bool(
        provenance_summary.get("binding_registry_source_counts")
    ) or str(provenance_audit_preview.get("verdict") or "").strip() != "usable_with_caveats"
    mapping_risk_present = bool(
        flaw_summary.get("blocking_category_counts")
        or flaw_summary.get("blocked_accession_count")
        or structure_summary.get("future_off_target_adjacent_context_only_count")
        or structure_summary.get("seed_structure_overlap_accession_count")
        or assessment_summary.get("missing_mapping_accession_count")
    )

    worst_verdict = _worst_verdict(
        str(assessment_summary.get("overall_verdict") or ""),
        str(flaw_summary.get("overall_verdict") or ""),
        str(acceptance_summary.get("overall_gate_verdict") or ""),
        str(remediation_summary.get("overall_queue_verdict") or ""),
        str(provenance_audit_preview.get("verdict") or ""),
        str(binding_audit_preview.get("verdict") or ""),
        str(structure_audit_preview.get("verdict") or ""),
        "blocked_pending_mapping" if missing_inputs else "",
    )
    if missing_inputs:
        worst_verdict = _worst_verdict(worst_verdict, "blocked_pending_mapping")

    if not risk_category_counts:
        risk_category_counts = {
            "provenance": 0,
            "binding": 0,
            "structure": 0,
        }

    summary = {
        "dataset_accession_count": int(assessment_summary.get("dataset_accession_count") or 0),
        "overall_verdict": worst_verdict,
        "risk_category_counts": risk_category_counts,
        "highest_risk_categories": highest_risk_categories,
        "blocked_gate_count": blocked_gate_count,
        "patent_or_provenance_risk_present": patent_or_provenance_risk_present,
        "mapping_risk_present": mapping_risk_present,
        "non_mutating": True,
        "top_risk_row_count": len(top_risk_rows),
        "blocked_accession_count": int(remediation_summary.get("blocked_accession_count") or 0),
        "caveated_accession_count": int(flaw_summary.get("caveated_accession_count") or 0),
        "resolved_accession_count": int(flaw_summary.get("resolved_accession_count") or 0),
    }

    return {
        "artifact_id": "external_dataset_risk_register_preview",
        "schema_id": "proteosphere-external-dataset-risk-register-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            assessment_preview.get("generated_at")
            or flaw_taxonomy_preview.get("generated_at")
            or acceptance_gate_preview.get("generated_at")
            or provenance_audit_preview.get("generated_at")
            or binding_audit_preview.get("generated_at")
            or structure_audit_preview.get("generated_at")
            or remediation_queue_preview.get("generated_at")
            or ""
        ),
        "summary": summary,
        "top_risk_rows": top_risk_rows,
        "source_artifacts": source_artifacts,
        "supporting_artifacts": {
            "assessment_verdict": assessment_summary.get("overall_verdict") or "",
            "flaw_taxonomy_verdict": flaw_summary.get("overall_verdict") or "",
            "acceptance_gate_verdict": acceptance_summary.get("overall_gate_verdict") or "",
            "provenance_verdict": provenance_audit_preview.get("verdict") or "",
            "binding_verdict": binding_audit_preview.get("verdict") or "",
            "structure_verdict": structure_audit_preview.get("verdict") or "",
            "remediation_queue_verdict": remediation_summary.get("overall_queue_verdict") or "",
        },
        "truth_boundary": {
            "summary": (
                "This risk register is advisory and fail-closed. It compacts existing "
                "external-assessment artifacts into operator-facing risk rows without "
                "mutating source truth or implying training-safe acceptance."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a fail-closed external dataset risk register preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument(
        "--flaw-taxonomy-preview", type=Path, default=DEFAULT_FLAW_TAXONOMY_PREVIEW
    )
    parser.add_argument(
        "--acceptance-gate-preview", type=Path, default=DEFAULT_ACCEPTANCE_GATE_PREVIEW
    )
    parser.add_argument(
        "--provenance-audit-preview", type=Path, default=DEFAULT_PROVENANCE_AUDIT_PREVIEW
    )
    parser.add_argument("--binding-audit-preview", type=Path, default=DEFAULT_BINDING_AUDIT_PREVIEW)
    parser.add_argument(
        "--structure-audit-preview", type=Path, default=DEFAULT_STRUCTURE_AUDIT_PREVIEW
    )
    parser.add_argument(
        "--remediation-queue-preview", type=Path, default=DEFAULT_REMEDIATION_QUEUE_PREVIEW
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_risk_register_preview(
        _load_payload(args.assessment_preview),
        _load_payload(args.flaw_taxonomy_preview),
        _load_payload(args.acceptance_gate_preview),
        _load_payload(args.provenance_audit_preview),
        _load_payload(args.binding_audit_preview),
        _load_payload(args.structure_audit_preview),
        _load_payload(args.remediation_queue_preview),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
