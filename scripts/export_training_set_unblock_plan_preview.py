from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_TRAINING_SET_REMEDIATION_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_COHORT_INCLUSION_RATIONALE = (
    REPO_ROOT / "artifacts" / "status" / "cohort_inclusion_rationale_preview.json"
)
DEFAULT_PACKET_DEFICIT_DASHBOARD = (
    REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_unblock_plan_preview.json"
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


def _selected_accessions(
    readiness: dict[str, Any],
    remediation: dict[str, Any],
    rationale: dict[str, Any],
) -> list[str]:
    for rows in (
        rationale.get("rows") or [],
        remediation.get("rows") or [],
        readiness.get("readiness_rows") or [],
    ):
        accessions = []
        for row in rows:
            if isinstance(row, dict):
                accession = _normalize_text(row.get("accession"))
                if accession:
                    accessions.append(accession)
        if accessions:
            return list(dict.fromkeys(accessions))

    selected = _listify((rationale.get("summary") or {}).get("selected_accessions"))
    if selected:
        return selected
    selected = _listify((readiness.get("summary") or {}).get("selected_accessions"))
    if selected:
        return selected
    selected = _listify((remediation.get("summary") or {}).get("selected_accessions"))
    if selected:
        return selected
    return []


def _packet_deficit_source_fix_refs(
    packet_deficit: dict[str, Any], accession: str
) -> list[str]:
    refs: list[str] = []
    for packet in packet_deficit.get("packets") or []:
        if not isinstance(packet, dict):
            continue
        if _normalize_text(packet.get("accession")) != accession:
            continue
        refs.extend(_listify(packet.get("deficit_source_refs")))
        missing_source_refs = packet.get("missing_source_refs") or {}
        if isinstance(missing_source_refs, dict):
            for value in missing_source_refs.values():
                refs.extend(_listify(value))

    for deficit in packet_deficit.get("modality_deficits") or []:
        if not isinstance(deficit, dict):
            continue
        if accession in _listify(deficit.get("packet_accessions")):
            refs.extend(_listify(deficit.get("top_source_fix_refs")))
            for candidate in deficit.get("top_source_fix_candidates") or []:
                if isinstance(candidate, dict):
                    refs.extend(_listify(candidate.get("source_ref")))

    for candidate in packet_deficit.get("source_fix_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if accession in _listify(candidate.get("packet_accessions")):
            refs.extend(_listify(candidate.get("source_ref")))

    return list(dict.fromkeys(refs))


def _top_source_fix_refs(packet_deficit: dict[str, Any]) -> list[dict[str, Any]]:
    summary = packet_deficit.get("summary") or {}
    top_fixes = summary.get("highest_leverage_source_fixes")
    if isinstance(top_fixes, list) and top_fixes:
        return [
            {
                "source_fix_ref": _normalize_text(row.get("source_ref")),
                "count": int(
                    row.get("affected_packet_count")
                    or row.get("missing_modality_count")
                    or 0
                ),
                "accessions": _listify(row.get("packet_accessions")),
            }
            for row in top_fixes
            if isinstance(row, dict) and _normalize_text(row.get("source_ref"))
        ]

    candidate_rows = []
    for candidate in packet_deficit.get("source_fix_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        source_ref = _normalize_text(candidate.get("source_ref"))
        if not source_ref:
            continue
        candidate_rows.append(
            {
                "source_fix_ref": source_ref,
                "count": int(
                    candidate.get("affected_packet_count")
                    or candidate.get("missing_modality_count")
                    or 0
                ),
                "accessions": _listify(candidate.get("packet_accessions")),
            }
        )
    return candidate_rows


def _collect_row_routes(
    *,
    accession: str,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
    rationale_row: dict[str, Any],
    packet_deficit: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    routes = []
    routes.extend(_listify(readiness_row.get("recommended_next_step")))
    routes.extend(_listify(remediation_row.get("recommended_actions")))
    routes.extend(_listify(rationale_row.get("next_actions")))
    routes.extend(_packet_deficit_source_fix_refs(packet_deficit, accession))
    routes = list(dict.fromkeys(routes))

    source_fix_refs = _listify(remediation_row.get("source_fix_refs"))
    source_fix_refs.extend(_listify(rationale_row.get("source_fix_refs")))
    source_fix_refs.extend(_packet_deficit_source_fix_refs(packet_deficit, accession))
    source_fix_refs = list(dict.fromkeys(source_fix_refs))

    blockers = []
    blockers.extend(_listify(remediation_row.get("issue_buckets")))
    blockers.extend(_listify(rationale_row.get("issue_buckets")))
    if _normalize_text(readiness_row.get("training_set_state")) == "blocked_pending_acquisition":
        blockers.append("blocked_pending_acquisition")
    if _normalize_text(rationale_row.get("inclusion_class")) == "gated":
        blockers.append("blocked_pending_acquisition")
    if _normalize_text(rationale_row.get("inclusion_class")) == "preview-only":
        blockers.append("preview_only_non_governing")
    blockers = list(dict.fromkeys(blockers))
    return routes, source_fix_refs, blockers


def build_training_set_unblock_plan_preview(
    training_set_readiness: dict[str, Any],
    package_readiness: dict[str, Any],
    training_set_remediation_plan: dict[str, Any],
    cohort_inclusion_rationale: dict[str, Any],
    packet_deficit_dashboard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet_deficit_dashboard = packet_deficit_dashboard or {}

    readiness_rows = _index_rows(training_set_readiness.get("readiness_rows") or [])
    remediation_rows = _index_rows(training_set_remediation_plan.get("rows") or [])
    rationale_rows = _index_rows(cohort_inclusion_rationale.get("rows") or [])
    packet_rows = _index_rows((packet_deficit_dashboard.get("packets") or []), key="accession")
    selected_accessions = _selected_accessions(
        training_set_readiness,
        training_set_remediation_plan,
        cohort_inclusion_rationale,
    )
    if not selected_accessions:
        raise ValueError("No accessions were found in the source artifacts")

    package_summary = package_readiness.get("summary") or {}
    package_blocked_reasons = _listify(package_summary.get("blocked_reasons"))
    package_ready = bool(package_summary.get("ready_for_package"))

    rows: list[dict[str, Any]] = []
    blocker_to_accessions: dict[str, set[str]] = defaultdict(set)
    route_to_accessions: dict[str, set[str]] = defaultdict(set)
    source_fix_to_accessions: dict[str, set[str]] = defaultdict(set)
    route_counts: Counter[str] = Counter()
    impacted_accessions: set[str] = set()

    for accession in selected_accessions:
        readiness_row = readiness_rows.get(accession, {})
        remediation_row = remediation_rows.get(accession, {})
        rationale_row = rationale_rows.get(accession, {})
        packet_row = packet_rows.get(accession, {})
        routes, source_fix_refs, blockers = _collect_row_routes(
            accession=accession,
            readiness_row=readiness_row,
            remediation_row=remediation_row,
            rationale_row=rationale_row,
            packet_deficit=packet_deficit_dashboard,
        )

        if not package_ready:
            blockers.append("package_gate_closed")
        if _normalize_text(packet_row.get("status")) in {"partial", "unresolved"}:
            blockers.append("packet_partial_or_missing")
        if _listify(packet_row.get("missing_modalities")):
            blockers.append("modality_gap")

        blockers = list(dict.fromkeys(blockers))
        impacted = bool(blockers)
        if impacted:
            impacted_accessions.add(accession)
        for blocker in blockers:
            blocker_to_accessions[blocker].add(accession)
        for route in routes:
            route_to_accessions[route].add(accession)
            route_counts[route] += 1
        for source_fix_ref in source_fix_refs:
            source_fix_to_accessions[source_fix_ref].add(accession)

        rows.append(
            {
                "accession": accession,
                "training_set_state": _normalize_text(
                    readiness_row.get("training_set_state")
                ),
                "inclusion_class": _normalize_text(rationale_row.get("inclusion_class")),
                "package_blockers": blockers,
                "direct_remediation_routes": routes,
                "source_fix_refs": source_fix_refs,
                "recommended_next_actions": routes,
                "impacted": impacted,
                "packet_status": _normalize_text(packet_row.get("status")),
            }
        )

    rows.sort(key=lambda row: (-len(row["package_blockers"]), row["accession"]))

    package_blockers = [
        {
            "blocker": blocker,
            "accession_count": len(accessions),
            "accessions": sorted(accessions),
        }
        for blocker, accessions in sorted(
            blocker_to_accessions.items(),
            key=lambda item: (-len(item[1]), item[0].casefold()),
        )
    ]
    direct_remediation_routes = [
        {
            "route": route,
            "accession_count": len(accessions),
            "accessions": sorted(accessions),
        }
        for route, accessions in sorted(
            route_to_accessions.items(),
            key=lambda item: (-len(item[1]), item[0].casefold()),
        )
    ]
    top_source_fix_refs = [
        {
            "source_fix_ref": source_fix_ref,
            "accession_count": len(accessions),
            "accessions": sorted(accessions),
        }
        for source_fix_ref, accessions in sorted(
            source_fix_to_accessions.items(),
            key=lambda item: (-len(item[1]), item[0].casefold()),
        )
    ]
    recommended_next_actions = [
        {"action": action, "count": count}
        for action, count in route_counts.most_common(10)
    ]

    row_blockers = Counter()
    for row in rows:
        row_blockers.update(row["package_blockers"])

    generated_at = (
        training_set_readiness.get("generated_at")
        or package_readiness.get("generated_at")
        or training_set_remediation_plan.get("generated_at")
        or cohort_inclusion_rationale.get("generated_at")
        or packet_deficit_dashboard.get("generated_at")
        or datetime.now(UTC).isoformat()
    )

    return {
        "artifact_id": "training_set_unblock_plan_preview",
        "schema_id": "proteosphere-training-set-unblock-plan-preview-2026-04-03",
        "status": "report_only",
        "generated_at": generated_at,
        "summary": {
            "selected_count": len(rows),
            "impacted_accession_count": len(impacted_accessions),
            "package_ready": package_ready,
            "package_blocked_reasons": package_blocked_reasons,
            "package_blockers": package_blockers,
            "direct_remediation_routes": direct_remediation_routes,
            "top_source_fix_refs": top_source_fix_refs
            or _top_source_fix_refs(packet_deficit_dashboard),
            "recommended_next_actions": recommended_next_actions,
            "row_blocker_counts": dict(row_blockers),
        },
        "rows": rows,
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
            "training_set_remediation_plan": str(
                DEFAULT_TRAINING_SET_REMEDIATION_PLAN
            ).replace("\\", "/"),
            "cohort_inclusion_rationale": str(
                DEFAULT_COHORT_INCLUSION_RATIONALE
            ).replace("\\", "/"),
            "packet_deficit_dashboard": str(DEFAULT_PACKET_DEFICIT_DASHBOARD).replace(
                "\\", "/"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This unblock plan is report-only and fail-closed. It summarizes what is "
                "blocking package readiness and suggests operator actions, but it does "
                "not mutate source artifacts or authorize packaging."
            ),
            "report_only": True,
            "non_governing": True,
            "non_mutating": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the training set unblock plan preview."
    )
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument(
        "--package-readiness",
        type=Path,
        default=DEFAULT_PACKAGE_READINESS,
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
        "--packet-deficit-dashboard",
        type=Path,
        default=DEFAULT_PACKET_DEFICIT_DASHBOARD,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_training_set_unblock_plan_preview(
        _read_json(
            args.training_set_readiness,
            label="training_set_readiness_preview",
            required=True,
        ),
        _read_json(args.package_readiness, label="package_readiness_preview", required=True),
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
