from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SET_UNBLOCK_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
)
DEFAULT_TRAINING_SET_GATING_EVIDENCE = (
    REPO_ROOT / "artifacts" / "status" / "training_set_gating_evidence_preview.json"
)
DEFAULT_TRAINING_SET_REMEDIATION_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_PACKET_DEFICIT_DASHBOARD = (
    REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_action_queue_preview.json"
)

PRIORITY_BUCKET_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

ACTION_SORT_ORDER = {
    "wait_for_source_fix": 0,
    "fill_missing_modalities": 1,
    "do_not_package_until_readiness_unlocks": 2,
    "preserve_selected_cohort_membership": 3,
    "keep_visible_for_preview_compilation": 4,
    "keep_non_governing_preview_only": 5,
    "preserve_current_preview_state": 6,
}


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
            for nested_accession in _listify(row.get("packet_accessions")):
                if nested_accession and nested_accession not in seen:
                    seen.add(nested_accession)
                    ordered.append(nested_accession)
    return ordered


def _packet_context(
    packet_deficit_dashboard: dict[str, Any], accession: str
) -> tuple[list[str], list[str]]:
    source_fix_refs: list[str] = []
    affected_modalities: list[str] = []

    for packet in packet_deficit_dashboard.get("packets") or []:
        if not isinstance(packet, dict):
            continue
        if _normalize_text(packet.get("accession")) != accession:
            continue
        source_fix_refs.extend(_listify(packet.get("deficit_source_refs")))
        missing_source_refs = packet.get("missing_source_refs") or {}
        if isinstance(missing_source_refs, dict):
            for modality, value in missing_source_refs.items():
                if _normalize_text(modality):
                    affected_modalities.append(_normalize_text(modality))
                source_fix_refs.extend(_listify(value))
        affected_modalities.extend(_listify(packet.get("missing_modalities")))

    for deficit in packet_deficit_dashboard.get("modality_deficits") or []:
        if not isinstance(deficit, dict):
            continue
        if accession not in _listify(deficit.get("packet_accessions")):
            continue
        affected_modalities.extend(_listify(deficit.get("modality")))
        source_fix_refs.extend(_listify(deficit.get("top_source_fix_refs")))
        for candidate in deficit.get("top_source_fix_candidates") or []:
            if isinstance(candidate, dict):
                source_fix_refs.extend(_listify(candidate.get("source_ref")))

    for candidate in packet_deficit_dashboard.get("source_fix_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if accession not in _listify(candidate.get("packet_accessions")):
            continue
        source_fix_refs.extend(_listify(candidate.get("source_ref")))
        affected_modalities.extend(_listify(candidate.get("missing_modalities")))

    return list(dict.fromkeys(source_fix_refs)), list(dict.fromkeys(affected_modalities))


def _row_actions(
    *,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
    rationale_row: dict[str, Any],
    unblock_row: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    actions.extend(_listify(unblock_row.get("direct_remediation_routes")))
    actions.extend(_listify(unblock_row.get("recommended_next_actions")))
    actions.extend(_listify(remediation_row.get("recommended_actions")))
    actions.extend(_listify(rationale_row.get("next_actions")))
    actions.extend(_listify(readiness_row.get("recommended_next_step")))
    return list(dict.fromkeys(actions))


def _row_blockers(
    *,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
    rationale_row: dict[str, Any],
    unblock_row: dict[str, Any],
    package_ready: bool,
    package_blocked_reasons: list[str],
    affected_modalities: list[str],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(_listify(unblock_row.get("package_blockers")))
    blockers.extend(_listify(remediation_row.get("issue_buckets")))
    blockers.extend(_listify(rationale_row.get("issue_buckets")))
    blockers.extend(_listify(readiness_row.get("training_set_state")))
    if package_blocked_reasons:
        blockers.extend(package_blocked_reasons)
    if not package_ready:
        blockers.append("package_gate_closed")
    if affected_modalities:
        blockers.append("modality_gap")
    packet_status = _normalize_text(unblock_row.get("packet_status"))
    if packet_status in {"partial", "unresolved"}:
        blockers.append("packet_partial_or_missing")
    inclusion_class = _normalize_text(rationale_row.get("inclusion_class"))
    if inclusion_class == "preview-only":
        blockers.append("preview_only_non_governing")
    if inclusion_class == "gated":
        blockers.append("blocked_pending_acquisition")
    return list(dict.fromkeys(blockers))


def _priority_bucket(blockers: list[str]) -> str:
    blocker_set = set(blockers)
    critical_signals = {
        "blocked_pending_acquisition",
        "assignment_ready=false",
        "fold_export_ready=false",
        "cv_fold_export_unlocked=false",
        "split_dry_run_not_aligned",
        "split_post_staging_gate_closed",
    }
    high_signals = {
        "package_gate_closed",
        "modality_gap",
        "packet_partial_or_missing",
    }
    medium_signals = {
        "preview_only_non_governing",
        "candidate_only_non_governing",
        "governing_ready",
    }
    if blocker_set & critical_signals:
        return "critical"
    if blocker_set & high_signals:
        return "high"
    if blocker_set & medium_signals:
        return "medium"
    return "low"


def _action_sort_weight(action_ref: str) -> int:
    for prefix, weight in ACTION_SORT_ORDER.items():
        if action_ref == prefix or action_ref.startswith(f"{prefix}:"):
            return weight
    return 99


def _supporting_artifacts(
    *,
    package_ready: bool,
    package_blocked_reasons: list[str],
    source_fix_refs: list[str],
    affected_modalities: list[str],
    used_packet_deficit: bool,
) -> list[str]:
    artifacts = [
        "training_set_unblock_plan_preview",
        "training_set_gating_evidence_preview",
        "training_set_remediation_plan_preview",
    ]
    if used_packet_deficit or source_fix_refs or affected_modalities:
        artifacts.append("packet_deficit_dashboard")
    if package_blocked_reasons or not package_ready:
        artifacts.append("package_readiness_preview")
    return list(dict.fromkeys(artifacts))


def build_training_set_action_queue_preview(
    training_set_unblock_plan: dict[str, Any],
    training_set_gating_evidence: dict[str, Any],
    training_set_remediation_plan: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any],
    package_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package_readiness = package_readiness or {}

    unblock_rows = _index_rows(training_set_unblock_plan.get("rows") or [])
    gating_rows = _index_rows(training_set_gating_evidence.get("rows") or [])
    remediation_rows = _index_rows(training_set_remediation_plan.get("rows") or [])
    packet_rows = _index_rows(packet_deficit_dashboard.get("packets") or [])
    selected_accessions = _collect_accessions(
        training_set_unblock_plan.get("rows") or [],
        training_set_gating_evidence.get("rows") or [],
        training_set_remediation_plan.get("rows") or [],
        packet_deficit_dashboard.get("packets") or [],
        packet_deficit_dashboard.get("modality_deficits") or [],
        packet_deficit_dashboard.get("source_fix_candidates") or [],
    )
    if not selected_accessions:
        raise ValueError("No accessions were found in the source artifacts")

    package_summary = package_readiness.get("summary") or {}
    package_ready = bool(package_summary.get("ready_for_package"))
    package_blocked_reasons = _listify(package_summary.get("blocked_reasons"))

    rows: list[dict[str, Any]] = []
    priority_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    source_fix_counts: Counter[str] = Counter()
    impacted_accessions: set[str] = set()

    for accession in selected_accessions:
        unblock_row = unblock_rows.get(accession, {})
        gating_row = gating_rows.get(accession, {})
        remediation_row = remediation_rows.get(accession, {})
        packet_row = packet_rows.get(accession, {})
        source_fix_refs, affected_modalities = _packet_context(packet_deficit_dashboard, accession)
        actions = _row_actions(
            readiness_row=gating_row,
            remediation_row=remediation_row,
            rationale_row=gating_row,
            unblock_row=unblock_row,
        )
        if not actions:
            actions = [
                "do_not_package_until_readiness_unlocks"
                if not package_ready
                else "preserve_current_preview_state"
            ]

        blockers = _row_blockers(
            readiness_row=gating_row,
            remediation_row=remediation_row,
            rationale_row=gating_row,
            unblock_row=unblock_row,
            package_ready=package_ready,
            package_blocked_reasons=package_blocked_reasons,
            affected_modalities=affected_modalities,
        )
        if _normalize_text(packet_row.get("status")) in {"partial", "unresolved"}:
            blockers.append("packet_partial_or_missing")
        blockers = list(dict.fromkeys(blockers))
        priority_bucket = _priority_bucket(blockers)
        if blockers:
            impacted_accessions.add(accession)
        for blocker in blockers:
            blocker_counts[blocker] += 1
        for source_fix_ref in source_fix_refs:
            source_fix_counts[source_fix_ref] += 1

        supporting_artifacts = _supporting_artifacts(
            package_ready=package_ready,
            package_blocked_reasons=package_blocked_reasons,
            source_fix_refs=source_fix_refs,
            affected_modalities=affected_modalities,
            used_packet_deficit=bool(source_fix_refs or affected_modalities),
        )

        for action_ref in actions:
            action_counts[action_ref] += 1
            priority_counts[priority_bucket] += 1
            row = {
                "accession": accession,
                "action_ref": action_ref,
                "priority_bucket": priority_bucket,
                "blocker_context": blockers,
                "source_fix_refs": source_fix_refs,
                "supporting_artifacts": supporting_artifacts,
            }
            if affected_modalities:
                row["affected_modalities"] = affected_modalities
            rows.append(row)

    rows.sort(
        key=lambda row: (
            PRIORITY_BUCKET_ORDER.get(row["priority_bucket"], 99),
            _action_sort_weight(row["action_ref"]),
            row["accession"],
            row["action_ref"],
        )
    )

    generated_at = (
        training_set_unblock_plan.get("generated_at")
        or training_set_gating_evidence.get("generated_at")
        or training_set_remediation_plan.get("generated_at")
        or packet_deficit_dashboard.get("generated_at")
        or package_readiness.get("generated_at")
        or datetime.now(UTC).isoformat()
    )

    return {
        "artifact_id": "training_set_action_queue_preview",
        "schema_id": "proteosphere-training-set-action-queue-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "summary": {
            "selected_accession_count": len(selected_accessions),
            "queue_length": len(rows),
            "package_ready": package_ready,
            "package_blocked_reasons": package_blocked_reasons,
            "priority_bucket_counts": dict(priority_counts),
            "top_action_refs": [
                {"action_ref": action_ref, "count": count}
                for action_ref, count in action_counts.most_common(10)
            ],
            "top_blockers": [
                {"blocker": blocker, "count": count}
                for blocker, count in blocker_counts.most_common(10)
            ],
            "top_source_fix_refs": [
                {"source_fix_ref": source_fix_ref, "count": count}
                for source_fix_ref, count in source_fix_counts.most_common(10)
            ],
            "impacted_accession_count": len(impacted_accessions),
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_unblock_plan": str(DEFAULT_TRAINING_SET_UNBLOCK_PLAN).replace("\\", "/"),
            "training_set_gating_evidence": str(
                DEFAULT_TRAINING_SET_GATING_EVIDENCE
            ).replace("\\", "/"),
            "training_set_remediation_plan": str(
                DEFAULT_TRAINING_SET_REMEDIATION_PLAN
            ).replace("\\", "/"),
            "packet_deficit_dashboard": str(DEFAULT_PACKET_DEFICIT_DASHBOARD).replace(
                "\\", "/"
            ),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This action queue is report-only and fail-closed. It organizes the "
                "current planning previews for operator attention, but it does not "
                "mutate source artifacts or authorize packaging."
            ),
            "report_only": True,
            "non_governing": True,
            "non_mutating": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the training set action queue preview."
    )
    parser.add_argument(
        "--training-set-unblock-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_UNBLOCK_PLAN,
    )
    parser.add_argument(
        "--training-set-gating-evidence",
        type=Path,
        default=DEFAULT_TRAINING_SET_GATING_EVIDENCE,
    )
    parser.add_argument(
        "--training-set-remediation-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_REMEDIATION_PLAN,
    )
    parser.add_argument(
        "--packet-deficit-dashboard",
        type=Path,
        default=DEFAULT_PACKET_DEFICIT_DASHBOARD,
    )
    parser.add_argument(
        "--package-readiness",
        type=Path,
        default=DEFAULT_PACKAGE_READINESS,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_action_queue_preview(
        _read_json(
            args.training_set_unblock_plan,
            label="training_set_unblock_plan_preview",
            required=True,
        ),
        _read_json(
            args.training_set_gating_evidence,
            label="training_set_gating_evidence_preview",
            required=True,
        ),
        _read_json(
            args.training_set_remediation_plan,
            label="training_set_remediation_plan_preview",
            required=True,
        ),
        _read_json(
            args.packet_deficit_dashboard,
            label="packet_deficit_dashboard",
            required=True,
        ),
        _read_json(
            args.package_readiness,
            label="package_readiness_preview",
            required=False,
        ),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
