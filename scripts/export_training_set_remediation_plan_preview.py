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
DEFAULT_COHORT_COMPILER = (
    REPO_ROOT / "artifacts" / "status" / "cohort_compiler_preview.json"
)
DEFAULT_BALANCE_DIAGNOSTICS = (
    REPO_ROOT / "artifacts" / "status" / "balance_diagnostics_preview.json"
)
DEFAULT_PACKET_DEFICIT = (
    REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_remediation_plan_preview.json"
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


def _index_rows(
    rows: list[dict[str, Any]], key: str = "accession"
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        identifier = _normalize_text(row.get(key))
        if identifier:
            indexed[identifier] = dict(row)
    return indexed


def _source_fix_refs_from_packet_deficit(
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
    return list(dict.fromkeys(refs))


def _recommended_actions(
    *,
    accession: str,
    readiness_row: dict[str, Any],
    cohort_row: dict[str, Any],
    balance_row: dict[str, Any],
    packet_deficit: dict[str, Any],
    package_readiness: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    ladder = _normalize_text(readiness_row.get("ligand_readiness_ladder"))
    training_state = _normalize_text(readiness_row.get("training_set_state"))
    packet_status = _normalize_text(cohort_row.get("packet_status"))
    recommended_next_step = _normalize_text(cohort_row.get("recommended_next_step"))
    package_ready = bool((package_readiness.get("summary") or {}).get("ready_for_package"))
    missing_modalities = _listify(
        (balance_row.get("packet_expectation") or {}).get("missing_modalities")
    )

    if training_state == "blocked_pending_acquisition":
        if recommended_next_step.startswith("wait_for_source_fix:"):
            actions.append(recommended_next_step)
        else:
            actions.append(f"wait_for_source_fix:{accession}")
        actions.append("keep_row_non_governing_until_acquisition")
    elif ladder == "candidate-only non-governing":
        actions.append("keep_non_governing_until_real_ligand_rows_exist")
    elif ladder == "support-only":
        actions.append("keep_visible_as_support_only")
    elif ladder == "grounded preview-safe":
        actions.append("keep_visible_for_preview_compilation")
    else:
        actions.append("preserve_current_preview_state")

    if packet_status != "ready":
        actions.append("preserve_packet_partiality_and_fill_missing_modalities")
    if missing_modalities:
        actions.append(f"fill_missing_modalities:{','.join(missing_modalities)}")
    if not package_ready:
        actions.append("do_not_package_until_readiness_unlocks")
    if _source_fix_refs_from_packet_deficit(packet_deficit, accession):
        actions.append("prefer_source_fix_refs_from_packet_deficit")

    return list(dict.fromkeys(actions))


def _issue_buckets(
    *,
    readiness_row: dict[str, Any],
    cohort_row: dict[str, Any],
    balance_row: dict[str, Any],
    packet_deficit: dict[str, Any],
    package_readiness: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    ladder = _normalize_text(readiness_row.get("ligand_readiness_ladder"))
    training_state = _normalize_text(readiness_row.get("training_set_state"))
    packet_status = _normalize_text(cohort_row.get("packet_status"))
    missing_modalities = _listify(
        (balance_row.get("packet_expectation") or {}).get("missing_modalities")
    )
    thin_coverage = bool(balance_row.get("thin_coverage"))
    mixed_evidence = bool(balance_row.get("mixed_evidence"))
    blocked_reasons = _listify((package_readiness.get("summary") or {}).get("blocked_reasons"))

    if training_state == "blocked_pending_acquisition":
        issues.append("blocked_pending_acquisition")
    if ladder == "candidate-only non-governing":
        issues.append("candidate_only_non_governing")
    if ladder == "support-only":
        issues.append("support_only_non_governing")
    if ladder == "grounded preview-safe":
        issues.append("grounded_preview_safe")
    if packet_status != "ready":
        issues.append("packet_partial_or_missing")
    if missing_modalities:
        issues.append("modality_gap")
    if thin_coverage:
        issues.append("thin_coverage")
    if mixed_evidence:
        issues.append("mixed_evidence")
    if blocked_reasons:
        issues.append("package_gate_closed")
    accession = _normalize_text(cohort_row.get("accession"))
    if _source_fix_refs_from_packet_deficit(packet_deficit, accession):
        issues.append("source_fix_available")
    return list(dict.fromkeys(issues))


def build_training_set_remediation_plan_preview(
    readiness: dict[str, Any],
    cohort: dict[str, Any],
    balance: dict[str, Any],
    packet_deficit: dict[str, Any],
    package_readiness: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = _index_rows(readiness.get("readiness_rows") or [])
    cohort_rows = _index_rows(cohort.get("rows") or [])
    balance_rows = _index_rows(balance.get("rows") or [])
    selected_accessions = _listify(
        (cohort.get("summary") or {}).get("selected_accessions")
    )
    if not selected_accessions:
        selected_accessions = list(cohort_rows.keys())

    rows: list[dict[str, Any]] = []
    issue_bucket_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    fix_ref_counts: Counter[str] = Counter()
    bucket_to_accessions: dict[str, list[str]] = defaultdict(list)

    for accession in selected_accessions:
        cohort_row = cohort_rows.get(accession, {})
        readiness_row = readiness_rows.get(accession, {})
        balance_row = balance_rows.get(accession, {})
        issue_buckets = _issue_buckets(
            readiness_row=readiness_row,
            cohort_row=cohort_row,
            balance_row=balance_row,
            packet_deficit=packet_deficit,
            package_readiness=package_readiness,
        )
        source_fix_refs = _source_fix_refs_from_packet_deficit(packet_deficit, accession)
        recommended_actions = _recommended_actions(
            accession=accession,
            readiness_row=readiness_row,
            cohort_row=cohort_row,
            balance_row=balance_row,
            packet_deficit=packet_deficit,
            package_readiness=package_readiness,
        )
        for issue in issue_buckets:
            issue_bucket_counts[issue] += 1
            bucket_to_accessions[issue].append(accession)
        for action in recommended_actions:
            action_counts[action] += 1
        for ref in source_fix_refs:
            fix_ref_counts[ref] += 1

        rows.append(
            {
                "accession": accession,
                "split": cohort_row.get("split"),
                "bucket": cohort_row.get("bucket"),
                "training_set_state": readiness_row.get("training_set_state"),
                "ligand_readiness_ladder": readiness_row.get("ligand_readiness_ladder"),
                "package_role": cohort_row.get("package_role"),
                "issue_buckets": issue_buckets,
                "issue_count": len(issue_buckets),
                "recommended_actions": recommended_actions,
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

    package_summary = package_readiness.get("summary") or {}
    selected_split_counts = (cohort.get("summary") or {}).get("selected_split_counts") or {}
    issue_rows = sorted(rows, key=lambda row: (-int(row["issue_count"]), row["accession"]))
    issueful_count = sum(1 for row in issue_rows if row["issue_buckets"])

    top_recommended_actions = [
        {"action": action, "count": count}
        for action, count in action_counts.most_common(10)
    ]
    top_source_fix_refs = [
        {"source_fix_ref": ref, "count": count}
        for ref, count in fix_ref_counts.most_common(10)
    ]

    remediation_buckets = [
        {
            "bucket_id": bucket,
            "count": count,
            "accessions": sorted(dict.fromkeys(bucket_to_accessions[bucket])),
        }
        for bucket, count in issue_bucket_counts.most_common()
    ]

    summary = {
        "selected_count": len(rows),
        "issueful_count": issueful_count,
        "blocked_count": sum(
            1 for row in rows if "blocked_pending_acquisition" in row["issue_buckets"]
        ),
        "candidate_only_count": sum(
            1 for row in rows if "candidate_only_non_governing" in row["issue_buckets"]
        ),
        "support_only_count": sum(
            1 for row in rows if "support_only_non_governing" in row["issue_buckets"]
        ),
        "governing_preview_count": sum(
            1 for row in rows if "grounded_preview_safe" in row["issue_buckets"]
        ),
        "issue_bucket_counts": dict(issue_bucket_counts),
        "selected_split_counts": selected_split_counts,
        "package_ready": bool(package_summary.get("ready_for_package")),
        "package_blocked_reasons": _listify(package_summary.get("blocked_reasons")),
        "top_recommended_actions": top_recommended_actions,
        "top_source_fix_refs": top_source_fix_refs,
    }

    return {
        "artifact_id": "training_set_remediation_plan_preview",
        "schema_id": "proteosphere-training-set-remediation-plan-preview-2026-04-03",
        "status": "report_only",
        "generated_at": (
            readiness.get("generated_at")
            or cohort.get("generated_at")
            or package_readiness.get("generated_at")
            or ""
        ),
        "summary": summary,
        "remediation_buckets": remediation_buckets,
        "rows": issue_rows,
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "cohort_compiler": str(DEFAULT_COHORT_COMPILER).replace("\\", "/"),
            "balance_diagnostics": str(DEFAULT_BALANCE_DIAGNOSTICS).replace("\\", "/"),
            "packet_deficit": str(DEFAULT_PACKET_DEFICIT).replace("\\", "/"),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This remediation plan is report-only and operator-friendly. It surfaces "
                "per-accession issues, suggested next steps, and source-fix references, but "
                "it does not change cohort membership, package readiness, or governance state."
            ),
            "report_only": True,
            "non_governing": True,
            "package_not_authorized": True,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export training set remediation plan preview."
    )
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument("--cohort-compiler", type=Path, default=DEFAULT_COHORT_COMPILER)
    parser.add_argument(
        "--balance-diagnostics",
        type=Path,
        default=DEFAULT_BALANCE_DIAGNOSTICS,
    )
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT)
    parser.add_argument(
        "--package-readiness",
        type=Path,
        default=DEFAULT_PACKAGE_READINESS,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    payload = build_training_set_remediation_plan_preview(
        _read_json(args.training_set_readiness),
        _read_json(args.cohort_compiler),
        _read_json(args.balance_diagnostics),
        _read_json(args.packet_deficit),
        _read_json(args.package_readiness),
    )
    _write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
