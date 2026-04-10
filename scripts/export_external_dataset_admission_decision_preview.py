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
DEFAULT_ACCEPTANCE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_acceptance_gate_preview.json"
)
DEFAULT_FLAW_TAXONOMY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_flaw_taxonomy_preview.json"
)
DEFAULT_RISK_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_risk_register_preview.json"
)
DEFAULT_CONFLICT_REGISTER_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_conflict_register_preview.json"
)
DEFAULT_RESOLUTION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_admission_decision_preview.json"
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


def _ordered_unique(*values: Any) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        for text in _listify(value):
            normalized.setdefault(text.casefold(), text)
    return list(normalized.values())


def _rank_verdict(verdict: str) -> int:
    return VERDICT_RANK.get(verdict, -1)


def _worst_verdict(*verdicts: str) -> str:
    ranked = [verdict for verdict in verdicts if verdict]
    if not ranked:
        return "audit_only"
    return max(ranked, key=_rank_verdict)


def _summary_int(summary: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 0


def _extract_remediations(*sources: Any) -> list[str]:
    remediations: list[str] = []
    for source in sources:
        if isinstance(source, dict):
            if source.get("remediation_action"):
                remediations.append(str(source.get("remediation_action") or "").strip())
            if source.get("top_required_remediations"):
                remediations.extend(_extract_remediations(source.get("top_required_remediations")))
            if source.get("rows") and isinstance(source.get("rows"), list):
                for row in source.get("rows") or []:
                    if isinstance(row, dict) and row.get("remediation_action"):
                        remediations.append(str(row.get("remediation_action") or "").strip())
            if source.get("top_blocking_categories") and isinstance(
                source.get("top_blocking_categories"), list
            ):
                for row in source.get("top_blocking_categories") or []:
                    if isinstance(row, dict) and row.get("remediation_action"):
                        remediations.append(str(row.get("remediation_action") or "").strip())
            if source.get("top_risk_rows") and isinstance(source.get("top_risk_rows"), list):
                for row in source.get("top_risk_rows") or []:
                    if isinstance(row, dict) and row.get("remediation_action"):
                        remediations.append(str(row.get("remediation_action") or "").strip())
            if source.get("top_conflict_rows") and isinstance(
                source.get("top_conflict_rows"), list
            ):
                for row in source.get("top_conflict_rows") or []:
                    if isinstance(row, dict) and row.get("remediation_action"):
                        remediations.append(str(row.get("remediation_action") or "").strip())
            continue
        remediations.extend(_listify(source))
    return _ordered_unique(remediations)


def _decision_reasons(
    *,
    overall_verdict: str,
    blocking_gate_count: int,
    missing_inputs: list[str],
    assessment_summary: dict[str, Any],
    acceptance_summary: dict[str, Any],
    flaw_summary: dict[str, Any],
    risk_summary: dict[str, Any],
    conflict_summary: dict[str, Any],
    resolution_summary: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if missing_inputs:
        reasons.append("missing source artifacts: " + ", ".join(missing_inputs))
    if blocking_gate_count:
        reasons.append(f"{blocking_gate_count} blocking gate(s) remain")
    if overall_verdict:
        reasons.append(f"overall verdict is {overall_verdict}")

    assessment_verdict = str(assessment_summary.get("overall_verdict") or "").strip()
    if assessment_verdict and assessment_verdict != overall_verdict:
        reasons.append(f"assessment preview reports {assessment_verdict}")

    gate_verdict = str(acceptance_summary.get("overall_gate_verdict") or "").strip()
    if gate_verdict:
        reasons.append(f"acceptance gate reports {gate_verdict}")

    blocking_categories = dict(flaw_summary.get("blocking_category_counts") or {})
    if blocking_categories:
        categories = ", ".join(sorted(blocking_categories, key=str.casefold))
        reasons.append("blocking flaw categories: " + categories)

    if risk_summary.get("patent_or_provenance_risk_present"):
        reasons.append("provenance risk present")
    if risk_summary.get("mapping_risk_present") or conflict_summary.get("mapping_conflict_present"):
        reasons.append("mapping conflict present")
    if conflict_summary.get("provenance_conflict_present"):
        reasons.append("provenance conflict present")

    resolution_verdict = str(resolution_summary.get("overall_resolution_verdict") or "").strip()
    if resolution_verdict:
        reasons.append(f"resolution preview reports {resolution_verdict}")

    if not reasons:
        reasons.append("preview remains advisory-only and non-mutating")

    return _ordered_unique(reasons)


def _overall_decision(
    overall_verdict: str,
    blocking_gate_count: int,
    missing_inputs: list[str],
) -> str:
    if blocking_gate_count or overall_verdict.startswith("blocked") or missing_inputs:
        return "blocked"
    return "advisory_only"


def build_external_dataset_admission_decision_preview(
    assessment_preview: dict[str, Any],
    acceptance_gate_preview: dict[str, Any],
    flaw_taxonomy_preview: dict[str, Any],
    risk_register_preview: dict[str, Any],
    conflict_register_preview: dict[str, Any],
    resolution_preview: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = dict(assessment_preview.get("summary") or {})
    acceptance_summary = dict(acceptance_gate_preview.get("summary") or {})
    flaw_summary = dict(flaw_taxonomy_preview.get("summary") or {})
    risk_summary = dict(risk_register_preview.get("summary") or {})
    conflict_summary = dict(conflict_register_preview.get("summary") or {})
    resolution_summary = dict(resolution_preview.get("summary") or {})

    source_artifacts = {
        "assessment_preview": assessment_preview.get("artifact_id") or "",
        "acceptance_gate_preview": acceptance_gate_preview.get("artifact_id") or "",
        "flaw_taxonomy_preview": flaw_taxonomy_preview.get("artifact_id") or "",
        "risk_register_preview": risk_register_preview.get("artifact_id") or "",
        "conflict_register_preview": conflict_register_preview.get("artifact_id") or "",
        "resolution_preview": resolution_preview.get("artifact_id") or "",
    }
    missing_inputs = sorted(
        name for name, artifact_id in source_artifacts.items() if not str(artifact_id or "").strip()
    )

    dataset_accession_count = 0
    for summary in (
        assessment_summary,
        acceptance_summary,
        flaw_summary,
        risk_summary,
        conflict_summary,
        resolution_summary,
    ):
        dataset_accession_count = _summary_int(
            summary,
            "dataset_accession_count",
            "accession_count",
            "row_count",
        )
        if dataset_accession_count:
            break

    blocking_gate_count = 0
    for summary in (acceptance_summary, risk_summary, resolution_summary):
        blocking_gate_count = _summary_int(
            summary,
            "blocking_gate_count",
            "blocked_gate_count",
        )
        if blocking_gate_count:
            break
    if missing_inputs:
        blocking_gate_count = max(blocking_gate_count, 1)

    verdict = _worst_verdict(
        str(assessment_summary.get("overall_verdict") or ""),
        str(acceptance_summary.get("overall_gate_verdict") or ""),
        str(flaw_summary.get("overall_verdict") or ""),
        str(risk_summary.get("overall_verdict") or ""),
        str(conflict_summary.get("overall_verdict") or ""),
        str(resolution_summary.get("overall_resolution_verdict") or ""),
    )
    if missing_inputs:
        verdict = _worst_verdict(verdict, "blocked_pending_mapping")

    decision = _overall_decision(verdict, blocking_gate_count, missing_inputs)
    decision_reasons = _decision_reasons(
        overall_verdict=verdict,
        blocking_gate_count=blocking_gate_count,
        missing_inputs=missing_inputs,
        assessment_summary=assessment_summary,
        acceptance_summary=acceptance_summary,
        flaw_summary=flaw_summary,
        risk_summary=risk_summary,
        conflict_summary=conflict_summary,
        resolution_summary=resolution_summary,
    )
    top_required_remediations = _extract_remediations(
        acceptance_summary,
        flaw_taxonomy_preview,
        risk_register_preview,
        conflict_register_preview,
        resolution_summary,
        resolution_preview,
    )
    if not top_required_remediations:
        top_required_remediations = [
            "review source artifacts before acceptance",
        ]

    return {
        "artifact_id": "external_dataset_admission_decision_preview",
        "schema_id": "proteosphere-external-dataset-admission-decision-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            assessment_preview.get("generated_at")
            or acceptance_gate_preview.get("generated_at")
            or flaw_taxonomy_preview.get("generated_at")
            or risk_register_preview.get("generated_at")
            or conflict_register_preview.get("generated_at")
            or resolution_preview.get("generated_at")
            or ""
        ),
        "summary": {
            "dataset_accession_count": dataset_accession_count,
            "overall_decision": decision,
            "overall_verdict": verdict,
            "blocking_gate_count": blocking_gate_count,
            "decision_reasons": decision_reasons,
            "top_required_remediations": top_required_remediations[:8],
            "advisory_only": True,
            "non_mutating": True,
        },
        "source_artifacts": source_artifacts,
        "supporting_artifacts": {
            "assessment_verdict": assessment_summary.get("overall_verdict") or "",
            "acceptance_gate_verdict": acceptance_summary.get("overall_gate_verdict") or "",
            "flaw_taxonomy_verdict": flaw_summary.get("overall_verdict") or "",
            "risk_register_verdict": risk_summary.get("overall_verdict") or "",
            "conflict_register_verdict": conflict_summary.get("overall_verdict") or "",
            "resolution_verdict": resolution_summary.get("overall_resolution_verdict") or "",
        },
        "truth_boundary": {
            "summary": (
                "This admission-decision preview is advisory and fail-closed. "
                "It compacts existing external-assessment artifacts without "
                "mutating source truth or implying training-safe acceptance."
            ),
            "report_only": True,
            "non_mutating": True,
            "fail_closed": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a fail-closed external dataset admission decision preview."
    )
    parser.add_argument("--assessment-preview", type=Path, default=DEFAULT_ASSESSMENT_PREVIEW)
    parser.add_argument(
        "--acceptance-gate-preview", type=Path, default=DEFAULT_ACCEPTANCE_GATE_PREVIEW
    )
    parser.add_argument(
        "--flaw-taxonomy-preview", type=Path, default=DEFAULT_FLAW_TAXONOMY_PREVIEW
    )
    parser.add_argument("--risk-register-preview", type=Path, default=DEFAULT_RISK_REGISTER_PREVIEW)
    parser.add_argument(
        "--conflict-register-preview", type=Path, default=DEFAULT_CONFLICT_REGISTER_PREVIEW
    )
    parser.add_argument("--resolution-preview", type=Path, default=DEFAULT_RESOLUTION_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_external_dataset_admission_decision_preview(
        _load_payload(args.assessment_preview),
        _load_payload(args.acceptance_gate_preview),
        _load_payload(args.flaw_taxonomy_preview),
        _load_payload(args.risk_register_preview),
        _load_payload(args.conflict_register_preview),
        _load_payload(args.resolution_preview),
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
