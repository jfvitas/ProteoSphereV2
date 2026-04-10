from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_COHORT_COMPILER = REPO_ROOT / "artifacts" / "status" / "cohort_compiler_preview.json"
DEFAULT_TRAINING_SET_REMEDIATION_PLAN = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
)
DEFAULT_BALANCE_DIAGNOSTICS = (
    REPO_ROOT / "artifacts" / "status" / "balance_diagnostics_preview.json"
)
DEFAULT_PACKET_DEFICIT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "cohort_inclusion_rationale_preview.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _index_rows(rows: list[dict[str, Any]], key: str = "accession") -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        identifier = _normalize_text(row.get(key))
        if identifier:
            indexed[identifier] = dict(row)
    return indexed


def _selected_accessions(cohort: dict[str, Any]) -> list[str]:
    summary = cohort.get("summary") or {}
    selected = _listify(summary.get("selected_accessions"))
    if selected:
        return selected
    return list(_index_rows(cohort.get("rows") or []).keys())


def _packet_source_fix_refs(packet_deficit: dict[str, Any], accession: str) -> list[str]:
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

    return list(dict.fromkeys(refs))


def _remediation_source_fix_refs(
    remediation_row: dict[str, Any], packet_deficit: dict[str, Any], accession: str
) -> list[str]:
    refs = _listify(remediation_row.get("source_fix_refs"))
    refs.extend(_packet_source_fix_refs(packet_deficit, accession))
    return list(dict.fromkeys(refs))


def _inclusion_class(
    *,
    readiness_row: dict[str, Any],
    remediation_row: dict[str, Any],
) -> tuple[str, str]:
    training_state = _normalize_text(readiness_row.get("training_set_state"))
    ladder = _normalize_text(readiness_row.get("ligand_readiness_ladder"))
    issue_buckets = set(_listify(remediation_row.get("issue_buckets")))

    if training_state == "blocked_pending_acquisition" or (
        "blocked_pending_acquisition" in issue_buckets
    ):
        return "gated", "blocked_pending_acquisition"
    if (
        ladder in {"candidate-only non-governing", "support-only"}
        or training_state == "preview_visible_non_governing"
    ):
        return "preview-only", ladder or training_state or "preview_visible_non_governing"
    return "selected", ladder or training_state or "selected_for_cohort"


def _rationale_tags(
    *,
    accession: str,
    cohort_row: dict[str, Any],
    readiness_row: dict[str, Any],
    balance_row: dict[str, Any],
    remediation_row: dict[str, Any],
    inclusion_class: str,
    source_fix_refs: list[str],
) -> list[str]:
    tags: list[str] = [
        "cohort_selected",
        f"split:{_normalize_text(cohort_row.get('split')) or 'unknown'}",
        f"bucket:{_normalize_text(cohort_row.get('bucket')) or 'unknown'}",
        f"training_state:{_normalize_text(readiness_row.get('training_set_state')) or 'unknown'}",
    ]
    ladder = _normalize_text(readiness_row.get("ligand_readiness_ladder"))
    if ladder:
        tags.append(f"ladder:{ladder}")
    tags.append(f"inclusion_class:{inclusion_class}")

    issue_buckets = _listify(remediation_row.get("issue_buckets"))
    tags.extend(issue_buckets)

    if _normalize_text(cohort_row.get("packet_status")) != "ready":
        tags.append("packet_partial_or_missing")
    if _listify((balance_row.get("packet_expectation") or {}).get("missing_modalities")):
        tags.append("modality_gap")
    if bool(balance_row.get("thin_coverage")):
        tags.append("thin_coverage")
    if bool(balance_row.get("mixed_evidence")):
        tags.append("mixed_evidence")
    if source_fix_refs:
        tags.append("source_fix_available")

    if inclusion_class == "gated":
        tags.append("gated_for_acquisition")
    elif inclusion_class == "preview-only":
        tags.append("preview_only_non_governing")
    else:
        tags.append("selected_for_cohort")

    return list(dict.fromkeys(tags))


def _next_actions(
    *,
    accession: str,
    cohort_row: dict[str, Any],
    remediation_row: dict[str, Any],
    source_fix_refs: list[str],
    inclusion_class: str,
) -> list[str]:
    actions: list[str] = []
    recommended = _listify(remediation_row.get("recommended_actions"))
    if inclusion_class == "gated":
        actions.append(f"wait_for_source_fix:{accession}")
        actions.append("keep_row_non_governing_until_acquisition")
    elif inclusion_class == "preview-only":
        actions.append("keep_non_governing_preview_only")
    else:
        actions.append("preserve_selected_cohort_membership")

    packet_status = _normalize_text(cohort_row.get("packet_status"))
    if packet_status != "ready":
        actions.append("preserve_packet_partiality_and_fill_missing_modalities")

    missing_modalities = _listify(
        (cohort_row.get("packet_expectation") or {}).get("missing_modalities")
    )
    if missing_modalities:
        actions.append(f"fill_missing_modalities:{','.join(missing_modalities)}")

    actions.extend(recommended)
    if source_fix_refs:
        actions.append("prefer_source_fix_refs_from_packet_deficit")

    return list(dict.fromkeys(actions))


def _rationale_summary(
    *,
    accession: str,
    inclusion_class: str,
    readiness_row: dict[str, Any],
    cohort_row: dict[str, Any],
    remediation_row: dict[str, Any],
    source_fix_refs: list[str],
) -> str:
    training_state = _normalize_text(readiness_row.get("training_set_state")) or "unknown"
    ladder = _normalize_text(readiness_row.get("ligand_readiness_ladder")) or "unknown"
    split = _normalize_text(cohort_row.get("split")) or "unknown"
    bucket = _normalize_text(cohort_row.get("bucket")) or "unknown"
    if inclusion_class == "gated":
        return (
            f"{accession} is gated because the readiness state is {training_state} "
            f"and the row still carries acquisition pressure; split={split}, bucket={bucket}."
        )
    if inclusion_class == "preview-only":
        return (
            f"{accession} remains preview-only because the readiness ladder is {ladder} "
            f"and the row is non-governing in the selected cohort; split={split}, bucket={bucket}."
        )
    issue_count = len(_listify(remediation_row.get("issue_buckets")))
    if issue_count:
        return (
            f"{accession} is selected for the cohort but still has {issue_count} "
            f"remediation signals; split={split}, bucket={bucket}."
        )
    if source_fix_refs:
        return (
            f"{accession} is selected and has source-fix references available; "
            f"split={split}, bucket={bucket}."
        )
    return f"{accession} is selected for the cohort; split={split}, bucket={bucket}."


def build_cohort_inclusion_rationale_preview(
    readiness: dict[str, Any],
    cohort: dict[str, Any],
    remediation: dict[str, Any],
    balance: dict[str, Any],
    packet_deficit: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = _index_rows(readiness.get("readiness_rows") or [])
    cohort_rows = _index_rows(cohort.get("rows") or [])
    remediation_rows = _index_rows(remediation.get("rows") or [])
    balance_rows = _index_rows(balance.get("rows") or [])
    selected_accessions = _selected_accessions(cohort)

    rows: list[dict[str, Any]] = []
    inclusion_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    source_fix_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    bucket_to_accessions: dict[str, set[str]] = defaultdict(set)
    state_to_accessions: dict[str, set[str]] = defaultdict(set)

    for accession in selected_accessions:
        cohort_row = cohort_rows.get(accession, {})
        readiness_row = readiness_rows.get(accession, {})
        remediation_row = remediation_rows.get(accession, {})
        balance_row = balance_rows.get(accession, {})
        inclusion_class, inclusion_reason = _inclusion_class(
            readiness_row=readiness_row,
            remediation_row=remediation_row,
        )
        source_fix_refs = _remediation_source_fix_refs(
            remediation_row, packet_deficit, accession
        )
        rationale_tags = _rationale_tags(
            accession=accession,
            cohort_row=cohort_row,
            readiness_row=readiness_row,
            balance_row=balance_row,
            remediation_row=remediation_row,
            inclusion_class=inclusion_class,
            source_fix_refs=source_fix_refs,
        )
        next_actions = _next_actions(
            accession=accession,
            cohort_row=cohort_row,
            remediation_row=remediation_row,
            source_fix_refs=source_fix_refs,
            inclusion_class=inclusion_class,
        )
        rationale_summary = _rationale_summary(
            accession=accession,
            inclusion_class=inclusion_class,
            readiness_row=readiness_row,
            cohort_row=cohort_row,
            remediation_row=remediation_row,
            source_fix_refs=source_fix_refs,
        )
        split = _normalize_text(cohort_row.get("split")) or "unknown"
        bucket = _normalize_text(cohort_row.get("bucket")) or "unknown"
        split_counts[split] += 1
        inclusion_counts[inclusion_class] += 1
        state_to_accessions[inclusion_class].add(accession)
        bucket_to_accessions[bucket].add(accession)

        for tag in rationale_tags:
            tag_counts[tag] += 1
        for action in next_actions:
            action_counts[action] += 1
        for ref in source_fix_refs:
            source_fix_counts[ref] += 1

        rows.append(
            {
                "accession": accession,
                "split": split,
                "bucket": bucket,
                "training_set_state": readiness_row.get("training_set_state"),
                "ligand_readiness_ladder": readiness_row.get("ligand_readiness_ladder"),
                "packet_status": cohort_row.get("packet_status"),
                "package_role": cohort_row.get("package_role"),
                "inclusion_class": inclusion_class,
                "inclusion_reason": inclusion_reason,
                "issue_buckets": _listify(remediation_row.get("issue_buckets")),
                "rationale_tags": rationale_tags,
                "rationale_summary": rationale_summary,
                "next_actions": next_actions,
                "source_fix_refs": source_fix_refs,
                "missing_modalities": _listify(
                    (balance_row.get("packet_expectation") or {}).get("missing_modalities")
                ),
                "present_modalities": _listify(
                    (balance_row.get("packet_expectation") or {}).get("present_modalities")
                ),
                "coverage_notes": _listify(balance_row.get("coverage_notes")),
            }
        )

    issueful_count = sum(1 for row in rows if row["issue_buckets"])
    selected_count = sum(1 for row in rows if row["inclusion_class"] == "selected")
    gated_count = sum(1 for row in rows if row["inclusion_class"] == "gated")
    preview_only_count = sum(
        1 for row in rows if row["inclusion_class"] == "preview-only"
    )
    issue_bucket_counts = Counter()
    for row in rows:
        issue_bucket_counts.update(row["issue_buckets"])

    summary = {
        "selected_count": selected_count,
        "gated_count": gated_count,
        "preview_only_count": preview_only_count,
        "issueful_count": issueful_count,
        "selected_split_counts": dict(split_counts),
        "inclusion_class_counts": dict(inclusion_counts),
        "issue_bucket_counts": dict(issue_bucket_counts),
        "top_rationale_tags": [
            {"tag": tag, "count": count}
            for tag, count in tag_counts.most_common(10)
        ],
        "top_next_actions": [
            {"action": action, "count": count}
            for action, count in action_counts.most_common(10)
        ],
        "top_source_fix_refs": [
            {"source_fix_ref": ref, "count": count}
            for ref, count in source_fix_counts.most_common(10)
        ],
        "selected_accessions": [
            row["accession"] for row in rows if row["inclusion_class"] == "selected"
        ],
        "gated_accessions": [
            row["accession"] for row in rows if row["inclusion_class"] == "gated"
        ],
        "preview_only_accessions": [
            row["accession"] for row in rows if row["inclusion_class"] == "preview-only"
        ],
        "bucket_coverage": {
            bucket: sorted(accessions) for bucket, accessions in bucket_to_accessions.items()
        },
        "package_ready": bool((readiness.get("summary") or {}).get("package_ready")),
    }

    return {
        "artifact_id": "cohort_inclusion_rationale_preview",
        "schema_id": "proteosphere-cohort-inclusion-rationale-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            readiness.get("generated_at")
            or cohort.get("generated_at")
            or remediation.get("generated_at")
            or balance.get("generated_at")
            or ""
        ),
        "summary": summary,
        "rows": sorted(rows, key=lambda row: (row["inclusion_class"], row["accession"])),
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "cohort_compiler": str(DEFAULT_COHORT_COMPILER).replace("\\", "/"),
            "training_set_remediation_plan": str(
                DEFAULT_TRAINING_SET_REMEDIATION_PLAN
            ).replace("\\", "/"),
            "balance_diagnostics": str(DEFAULT_BALANCE_DIAGNOSTICS).replace("\\", "/"),
            "packet_deficit": str(DEFAULT_PACKET_DEFICIT).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This rationale preview is report-only and operator-friendly. It explains "
                "why each accession is selected, gated, or preview-only, but it does not "
                "change cohort membership, readiness state, or package authorization."
            ),
            "report_only": True,
            "non_governing": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export cohort inclusion rationale preview."
    )
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument(
        "--cohort-compiler",
        type=Path,
        default=DEFAULT_COHORT_COMPILER,
    )
    parser.add_argument(
        "--training-set-remediation-plan",
        type=Path,
        default=DEFAULT_TRAINING_SET_REMEDIATION_PLAN,
    )
    parser.add_argument(
        "--balance-diagnostics",
        type=Path,
        default=DEFAULT_BALANCE_DIAGNOSTICS,
    )
    parser.add_argument(
        "--packet-deficit",
        type=Path,
        default=DEFAULT_PACKET_DEFICIT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    payload = build_cohort_inclusion_rationale_preview(
        _read_json(args.training_set_readiness),
        _read_json(args.cohort_compiler),
        _read_json(args.training_set_remediation_plan),
        _read_json(args.balance_diagnostics),
        _read_json(args.packet_deficit),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
