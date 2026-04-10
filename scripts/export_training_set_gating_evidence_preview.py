from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_TRAINING_SET_REMEDIATION_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_COHORT_INCLUSION_RATIONALE = (
    REPO_ROOT / "artifacts" / "status" / "cohort_inclusion_rationale_preview.json"
)
DEFAULT_TRAINING_SET_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_PACKET_DEFICIT_DASHBOARD = (
    REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gating_evidence_preview.json"
)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _listify(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        values = [values]
    seen: dict[str, str] = {}
    for value in values:
        text = _normalize_text(value)
        if text:
            seen.setdefault(text.casefold(), text)
    return list(seen.values())


def _index_rows(rows: Any, *, key: str = "accession") -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        identifier = _normalize_text(row.get(key))
        if identifier:
            indexed[identifier] = dict(row)
    return indexed


def _read_json(path: Path, *, label: str, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required artifact: {label} ({path})")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {label}: {path}") from exc
    if not isinstance(payload, dict):
        if required:
            raise ValueError(f"Expected object JSON for {label}: {path}")
        return {}
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _collect_accessions(*sources: Any) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for row in source or []:
            if not isinstance(row, dict):
                continue
            accession = _normalize_text(row.get("accession"))
            if accession and accession not in seen:
                seen.add(accession)
                ordered.append(accession)
    return ordered


def _inclusion_class(
    *,
    readiness_row: dict[str, Any],
    rationale_row: dict[str, Any],
    remediation_row: dict[str, Any],
) -> str:
    rationale_class = _normalize_text(rationale_row.get("inclusion_class"))
    if rationale_class in {"selected", "gated", "preview-only"}:
        return rationale_class

    training_state = _normalize_text(readiness_row.get("training_set_state"))
    issue_buckets = set(_listify(remediation_row.get("issue_buckets")))
    if (
        training_state == "blocked_pending_acquisition"
        or "blocked_pending_acquisition" in issue_buckets
    ):
        return "gated"
    if training_state == "preview_visible_non_governing" or _normalize_text(
        readiness_row.get("ligand_readiness_ladder")
    ) in {"candidate-only non-governing", "support-only"}:
        return "preview-only"
    return "selected"


def _packet_deficit_source_fix_refs(
    packet_deficit_dashboard: dict[str, Any], accession: str
) -> list[str]:
    refs: list[str] = []
    for packet in packet_deficit_dashboard.get("packets") or []:
        if not isinstance(packet, dict):
            continue
        if _normalize_text(packet.get("accession")) != accession:
            continue
        refs.extend(_listify(packet.get("deficit_source_refs")))
        missing_source_refs = packet.get("missing_source_refs") or {}
        if isinstance(missing_source_refs, dict):
            for value in missing_source_refs.values():
                refs.extend(_listify(value))

    for deficit in packet_deficit_dashboard.get("modality_deficits") or []:
        if not isinstance(deficit, dict):
            continue
        if accession in _listify(deficit.get("packet_accessions")):
            refs.extend(_listify(deficit.get("top_source_fix_refs")))
            for candidate in deficit.get("top_source_fix_candidates") or []:
                if isinstance(candidate, dict):
                    refs.extend(_listify(candidate.get("source_ref")))

    for candidate in packet_deficit_dashboard.get("source_fix_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if accession in _listify(candidate.get("packet_accessions")):
            refs.extend(_listify(candidate.get("source_ref")))

    return list(dict.fromkeys(refs))


def _row_package_blockers(
    *,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
    unblock_row: dict[str, Any],
    inclusion_class: str,
) -> list[str]:
    blockers = _listify(unblock_row.get("package_blockers"))
    if blockers:
        return blockers

    blockers.extend(_listify(remediation_row.get("issue_buckets")))
    if _normalize_text(readiness_row.get("training_set_state")) == "blocked_pending_acquisition":
        blockers.append("blocked_pending_acquisition")
    if inclusion_class == "gated":
        blockers.append("blocked_pending_acquisition")
    if inclusion_class == "preview-only":
        blockers.append("preview_only_non_governing")
    return list(dict.fromkeys(blockers))


def _row_next_action_refs(
    *,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
    rationale_row: dict[str, Any],
    unblock_row: dict[str, Any],
) -> list[str]:
    refs: list[str] = []
    refs.extend(_listify(readiness_row.get("recommended_next_step")))
    refs.extend(_listify(remediation_row.get("recommended_actions")))
    refs.extend(_listify(rationale_row.get("next_actions")))
    refs.extend(_listify(unblock_row.get("direct_remediation_routes")))
    refs.extend(_listify(unblock_row.get("recommended_next_actions")))
    return list(dict.fromkeys(refs))


def _evidence_fields(
    *,
    accession: str,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
    rationale_row: dict[str, Any],
    unblock_row: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
) -> dict[str, Any]:
    packet_source_fix_refs = _packet_deficit_source_fix_refs(packet_deficit_dashboard, accession)
    return {
        "training_set_readiness.training_set_state": readiness_row.get("training_set_state"),
        "training_set_readiness.recommended_next_step": readiness_row.get(
            "recommended_next_step"
        ),
        "training_set_remediation_plan.issue_buckets": _listify(
            remediation_row.get("issue_buckets")
        ),
        "training_set_remediation_plan.recommended_actions": _listify(
            remediation_row.get("recommended_actions")
        ),
        "training_set_remediation_plan.source_fix_refs": _listify(
            remediation_row.get("source_fix_refs")
        ),
        "cohort_inclusion_rationale.inclusion_class": rationale_row.get("inclusion_class"),
        "cohort_inclusion_rationale.inclusion_reason": rationale_row.get("inclusion_reason"),
        "cohort_inclusion_rationale.next_actions": _listify(rationale_row.get("next_actions")),
        "training_set_unblock_plan.package_blockers": _listify(
            unblock_row.get("package_blockers")
        ),
        "training_set_unblock_plan.direct_remediation_routes": _listify(
            unblock_row.get("direct_remediation_routes")
        ),
        "training_set_unblock_plan.recommended_next_actions": _listify(
            unblock_row.get("recommended_next_actions")
        ),
        "training_set_unblock_plan.packet_status": _normalize_text(
            unblock_row.get("packet_status")
        ),
        "packet_deficit_dashboard.source_fix_refs": packet_source_fix_refs,
    }


def _evidence_snippets(evidence_fields: dict[str, Any]) -> list[str]:
    snippets: list[str] = []
    for key in (
        "training_set_readiness.training_set_state",
        "training_set_readiness.recommended_next_step",
        "cohort_inclusion_rationale.inclusion_class",
        "cohort_inclusion_rationale.inclusion_reason",
        "training_set_remediation_plan.issue_buckets",
        "training_set_unblock_plan.package_blockers",
        "training_set_unblock_plan.direct_remediation_routes",
        "packet_deficit_dashboard.source_fix_refs",
    ):
        value = evidence_fields.get(key)
        if value not in (None, "", [], {}):
            snippets.append(f"{key}={json.dumps(value, sort_keys=True)}")
    return snippets


def build_training_set_gating_evidence_preview(
    training_set_readiness: dict[str, Any],
    training_set_remediation_plan: dict[str, Any],
    cohort_inclusion_rationale: dict[str, Any],
    training_set_unblock_plan: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet_deficit_dashboard = packet_deficit_dashboard or {}

    readiness_rows = _index_rows(training_set_readiness.get("readiness_rows") or [])
    remediation_rows = _index_rows(training_set_remediation_plan.get("rows") or [])
    rationale_rows = _index_rows(cohort_inclusion_rationale.get("rows") or [])
    unblock_rows = _index_rows(training_set_unblock_plan.get("rows") or [])
    selected_accessions = _collect_accessions(
        cohort_inclusion_rationale.get("rows") or [],
        training_set_unblock_plan.get("rows") or [],
        training_set_remediation_plan.get("rows") or [],
        training_set_readiness.get("readiness_rows") or [],
        packet_deficit_dashboard.get("packets") or [],
    )
    if not selected_accessions:
        raise ValueError("No accessions were found in the source artifacts")

    root_source_artifacts = {
        "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
        "training_set_remediation_plan": str(
            DEFAULT_TRAINING_SET_REMEDIATION_PLAN
        ).replace("\\", "/"),
        "cohort_inclusion_rationale": str(
            DEFAULT_COHORT_INCLUSION_RATIONALE
        ).replace("\\", "/"),
        "training_set_unblock_plan": str(DEFAULT_TRAINING_SET_UNBLOCK_PLAN).replace(
            "\\", "/"
        ),
        "packet_deficit_dashboard": str(DEFAULT_PACKET_DEFICIT_DASHBOARD).replace("\\", "/"),
    }

    rows: list[dict[str, Any]] = []
    inclusion_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    next_action_counts: Counter[str] = Counter()
    source_fix_counts: Counter[str] = Counter()
    package_ready = bool((training_set_unblock_plan.get("summary") or {}).get("package_ready"))

    for accession in selected_accessions:
        readiness_row = readiness_rows.get(accession, {})
        remediation_row = remediation_rows.get(accession, {})
        rationale_row = rationale_rows.get(accession, {})
        unblock_row = unblock_rows.get(accession, {})
        inclusion_class = _inclusion_class(
            readiness_row=readiness_row,
            rationale_row=rationale_row,
            remediation_row=remediation_row,
        )
        training_state = _normalize_text(readiness_row.get("training_set_state"))
        package_blockers = _row_package_blockers(
            readiness_row=readiness_row,
            remediation_row=remediation_row,
            unblock_row=unblock_row,
            inclusion_class=inclusion_class,
        )
        next_action_refs = _row_next_action_refs(
            readiness_row=readiness_row,
            remediation_row=remediation_row,
            rationale_row=rationale_row,
            unblock_row=unblock_row,
        )
        evidence_fields = _evidence_fields(
            accession=accession,
            readiness_row=readiness_row,
            remediation_row=remediation_row,
            rationale_row=rationale_row,
            unblock_row=unblock_row,
            packet_deficit_dashboard=packet_deficit_dashboard,
        )
        evidence_snippets = _evidence_snippets(evidence_fields)
        row_source_artifacts = {
            "training_set_readiness": root_source_artifacts["training_set_readiness"],
            "training_set_remediation_plan": root_source_artifacts[
                "training_set_remediation_plan"
            ],
            "cohort_inclusion_rationale": root_source_artifacts[
                "cohort_inclusion_rationale"
            ],
            "training_set_unblock_plan": root_source_artifacts["training_set_unblock_plan"],
        }
        if packet_deficit_dashboard:
            row_source_artifacts["packet_deficit_dashboard"] = root_source_artifacts[
                "packet_deficit_dashboard"
            ]

        inclusion_counts[inclusion_class] += 1
        for blocker in package_blockers:
            blocker_counts[blocker] += 1
        for action_ref in next_action_refs:
            next_action_counts[action_ref] += 1
        for ref in _listify(
            remediation_row.get("source_fix_refs")
        ) + _packet_deficit_source_fix_refs(packet_deficit_dashboard, accession):
            source_fix_counts[ref] += 1

        rows.append(
            {
                "accession": accession,
                "inclusion_class": inclusion_class,
                "training_set_state": training_state,
                "package_blockers": package_blockers,
                "source_artifacts": row_source_artifacts,
                "evidence_snippets": evidence_snippets,
                "evidence_fields": evidence_fields,
                "next_action_refs": next_action_refs,
            }
        )

    rows.sort(key=lambda row: (row["inclusion_class"], row["accession"]))

    summary = {
        "selected_count": len(rows),
        "selected_accessions": [
            row["accession"]
            for row in rows
            if row["inclusion_class"] == "selected"
        ],
        "gated_count": sum(1 for row in rows if row["inclusion_class"] == "gated"),
        "preview_only_count": sum(
            1 for row in rows if row["inclusion_class"] == "preview-only"
        ),
        "package_ready": package_ready,
        "top_package_blockers": [
            {"blocker": blocker, "count": count}
            for blocker, count in blocker_counts.most_common(10)
        ],
        "top_next_action_refs": [
            {"next_action_ref": ref, "count": count}
            for ref, count in next_action_counts.most_common(10)
        ],
        "top_source_fix_refs": [
            {"source_fix_ref": ref, "count": count}
            for ref, count in source_fix_counts.most_common(10)
        ],
        "inclusion_class_counts": dict(inclusion_counts),
    }

    generated_at = (
        training_set_readiness.get("generated_at")
        or training_set_remediation_plan.get("generated_at")
        or cohort_inclusion_rationale.get("generated_at")
        or training_set_unblock_plan.get("generated_at")
        or packet_deficit_dashboard.get("generated_at")
        or datetime.now(UTC).isoformat()
    )

    return {
        "artifact_id": "training_set_gating_evidence_preview",
        "schema_id": "proteosphere-training-set-gating-evidence-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "summary": summary,
        "rows": rows,
        "source_artifacts": root_source_artifacts,
        "truth_boundary": {
            "summary": (
                "This gating evidence view is report-only and fail-closed. It explains "
                "which concrete preview fields support each accession's current state, "
                "but it does not mutate upstream artifacts or authorize packaging."
            ),
            "report_only": True,
            "non_governing": True,
            "non_mutating": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the training set gating evidence preview."
    )
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument(
        "--training-set-remediation-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_REMEDIATION_PLAN,
    )
    parser.add_argument(
        "--cohort-inclusion-rationale",
        type=Path,
        default=DEFAULT_COHORT_INCLUSION_RATIONALE,
    )
    parser.add_argument(
        "--training-set-unblock-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_UNBLOCK_PLAN,
    )
    parser.add_argument(
        "--packet-deficit-dashboard",
        type=Path,
        default=DEFAULT_PACKET_DEFICIT_DASHBOARD,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_gating_evidence_preview(
        _read_json(
            args.training_set_readiness,
            label="training_set_readiness_preview",
            required=True,
        ),
        _read_json(
            args.training_set_remediation_plan,
            label="training_set_remediation_plan_preview",
            required=True,
        ),
        _read_json(
            args.cohort_inclusion_rationale,
            label="cohort_inclusion_rationale_preview",
            required=True,
        ),
        _read_json(
            args.training_set_unblock_plan,
            label="training_set_unblock_plan_preview",
            required=True,
        ),
        _read_json(
            args.packet_deficit_dashboard,
            label="packet_deficit_dashboard",
            required=False,
        ),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
