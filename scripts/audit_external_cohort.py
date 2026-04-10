from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from scripts.modality_readiness_ladder import (
        LADDER_ABSENT,
        LADDER_CANDIDATE_ONLY,
        LADDER_GROUNDED_GOVERNING,
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_SUPPORT_ONLY,
        ladder_accession_buckets,
        ladder_counts,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from modality_readiness_ladder import (
        LADDER_ABSENT,
        LADDER_CANDIDATE_ONLY,
        LADDER_GROUNDED_GOVERNING,
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_SUPPORT_ONLY,
        ladder_accession_buckets,
        ladder_counts,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
DEFAULT_LIBRARY_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p50_training_set_creator_library_contract.json"
)
DEFAULT_PACKET_DEFICIT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "external_cohort_audit.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "external_cohort_audit.md"


class AuditInputError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise AuditInputError(f"{path} must contain a JSON object")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _repo_relative_text(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("/", "\\")


def _render_accession_list(values: list[str] | None) -> str:
    return ", ".join(values or []) or "none"


def _bucket_by_split(labels: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for label in labels:
        counts[str(label["split"])][str(label["bucket"])] += 1
    return {split: dict(counter) for split, counter in sorted(counts.items())}


def _missing_modalities_by_accession(packet_deficit: Mapping[str, Any]) -> dict[str, list[str]]:
    lookup: dict[str, list[str]] = {}
    for packet in packet_deficit.get("packets") or ():
        if not isinstance(packet, Mapping):
            continue
        accession = str(packet.get("accession") or "").strip()
        if accession:
            lookup[accession] = [
                str(item)
                for item in (packet.get("missing_modalities") or ())
                if str(item).strip()
            ]
    return lookup


def _eligibility_rows_by_accession(
    eligibility_matrix_payload: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if eligibility_matrix_payload is None:
        return {}
    rows = eligibility_matrix_payload.get("rows") or ()
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = dict(row)
    return indexed


def _ligand_follow_through(
    labels: list[dict[str, Any]],
    eligibility_matrix_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if eligibility_matrix_payload is None:
        return {
            "status": "not_assessed",
            "decision": "no_ligand_follow_through_surface",
            "grounded_accessions": [],
            "candidate_only_accessions": [],
            "blocked_accessions": [],
            "library_only_accessions": [],
            "audit_only_accessions": [],
            "split_status_counts": {},
            "notes": [
                "No eligibility matrix was provided, so ligand follow-through was not assessed.",
            ],
        }

    rows_by_accession = _eligibility_rows_by_accession(eligibility_matrix_payload)
    grounded_accessions: list[str] = []
    candidate_only_accessions: list[str] = []
    blocked_accessions: list[str] = []
    library_only_accessions: list[str] = []
    audit_only_accessions: list[str] = []
    split_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    readiness_ladder_values: list[str] = []

    for label in labels:
        accession = str(label.get("accession") or "").strip()
        split_name = str(label.get("split") or "").strip()
        row = rows_by_accession.get(accession)
        if row is None:
            split_status_counts[split_name]["missing_eligibility_row"] += 1
            continue
        status = str(
            (
                row.get("task_eligibility", {})
                .get("grounded_ligand_similarity_preview", {})
                .get("status")
            )
            or ""
        ).strip()
        split_status_counts[split_name][status or "missing_status"] += 1
        if status == "eligible_for_task":
            grounded_accessions.append(accession)
        elif status == "candidate_only_non_governing":
            candidate_only_accessions.append(accession)
        elif status == "blocked_pending_acquisition":
            blocked_accessions.append(accession)
        elif status == "library_only":
            library_only_accessions.append(accession)
        elif status == "audit_only":
            audit_only_accessions.append(accession)
        readiness_ladder = str(row.get("ligand_readiness_ladder") or LADDER_ABSENT).strip()
        readiness_ladder_values.append(readiness_ladder)

    notes: list[str] = []
    status = "ok"
    decision = "eligible_for_future_ligand_split_review"
    grounded_preview_safe_accessions = [
        accession
        for accession in grounded_accessions
        if rows_by_accession.get(accession, {}).get("ligand_readiness_ladder")
        == LADDER_GROUNDED_PREVIEW_SAFE
    ]
    grounded_governing_accessions = [
        accession
        for accession in grounded_accessions
        if rows_by_accession.get(accession, {}).get("ligand_readiness_ladder")
        == LADDER_GROUNDED_GOVERNING
    ]
    support_only_accessions = [
        accession
        for accession, row in rows_by_accession.items()
        if str(row.get("ligand_readiness_ladder") or "") == LADDER_SUPPORT_ONLY
    ]
    candidate_only_non_governing_accessions = [
        accession
        for accession, row in rows_by_accession.items()
        if str(row.get("ligand_readiness_ladder") or "") == LADDER_CANDIDATE_ONLY
    ]
    absent_accessions = [
        accession
        for accession, row in rows_by_accession.items()
        if str(row.get("ligand_readiness_ladder") or "") == LADDER_ABSENT
    ]
    readiness_ladder_buckets = ladder_accession_buckets(
        [
            {
                "accession": str(row.get("accession") or ""),
                "ligand_readiness_ladder": row.get("ligand_readiness_ladder"),
            }
            for row in rows_by_accession.values()
        ]
    )
    readiness_ladder_counts = ladder_counts(readiness_ladder_values)

    if len(grounded_preview_safe_accessions) + len(grounded_governing_accessions) < 2:
        status = "attention_needed"
        decision = "keep_ligand_split_non_governing"
        notes.append(
            "The audited cohort has fewer than two grounded ligand accessions, so ligand-aware "
            "split behavior would overclaim."
        )
    if candidate_only_non_governing_accessions:
        status = "attention_needed"
        decision = "keep_ligand_split_non_governing"
        notes.append(
            "Candidate-only ligand accessions are present and must remain non-governing in audit "
            "and split policy."
        )
    if support_only_accessions:
        notes.append(
            "Some accessions have support-only ligand readiness and should stay non-governing "
            "until grounded rows are explicitly materialized."
        )
    if absent_accessions:
        notes.append(
            "Some accessions remain absent in the ligand ladder and should stay outside any "
            "ligand-aware split rule."
        )
    blocked_accessions = sorted(absent_accessions)

    return {
        "status": status,
        "decision": decision,
        "grounded_accessions": sorted(grounded_accessions),
        "candidate_only_accessions": sorted(candidate_only_accessions),
        "blocked_accessions": blocked_accessions,
        "library_only_accessions": sorted(library_only_accessions),
        "audit_only_accessions": sorted(audit_only_accessions),
        "readiness_ladder": {
            "counts": readiness_ladder_counts,
            "by_ladder": readiness_ladder_buckets,
            "by_accession": {
                accession: str(row.get("ligand_readiness_ladder") or LADDER_ABSENT)
                for accession, row in sorted(rows_by_accession.items())
            },
            "grounded_preview_safe_accessions": sorted(grounded_preview_safe_accessions),
            "grounded_governing_accessions": sorted(grounded_governing_accessions),
            "candidate_only_non_governing_accessions": sorted(
                candidate_only_non_governing_accessions
            ),
            "support_only_accessions": sorted(support_only_accessions),
            "absent_accessions": sorted(absent_accessions),
        },
        "split_status_counts": {
            split_name: dict(counter)
            for split_name, counter in sorted(split_status_counts.items())
        },
        "notes": notes,
    }


def _modality_readiness_audit(
    labels: list[dict[str, Any]],
    eligibility_matrix_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if eligibility_matrix_payload is None:
        return {
            "status": "not_assessed",
            "modality_counts": {},
            "split_modality_counts": {},
            "notes": [
                "No eligibility matrix was provided, so modality readiness was not assessed.",
            ],
        }

    rows_by_accession = _eligibility_rows_by_accession(eligibility_matrix_payload)
    modality_counts: dict[str, Counter[str]] = defaultdict(Counter)
    split_modality_counts: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )

    for label in labels:
        accession = str(label.get("accession") or "").strip()
        split_name = str(label.get("split") or "").strip()
        row = rows_by_accession.get(accession)
        if row is None:
            continue
        modality_readiness = row.get("modality_readiness") or {}
        for modality_name, ladder_value in modality_readiness.items():
            label_value = str(ladder_value or LADDER_ABSENT).strip() or LADDER_ABSENT
            modality_counts[str(modality_name)][label_value] += 1
            split_modality_counts[split_name][str(modality_name)][label_value] += 1

    notes: list[str] = []
    status = "ok"
    if modality_counts.get("ligand", {}).get(LADDER_GROUNDED_GOVERNING, 0) == 0:
        status = "attention_needed"
        notes.append(
            "Ligand readiness does not yet reach grounded governing for any audited accession."
        )
    if modality_counts.get("interaction", {}).get(LADDER_CANDIDATE_ONLY, 0):
        status = "attention_needed"
        notes.append(
            "Interaction readiness remains candidate-only for part of the audited cohort."
        )

    return {
        "status": status,
        "modality_counts": {
            modality_name: dict(counter)
            for modality_name, counter in sorted(modality_counts.items())
        },
        "split_modality_counts": {
            split_name: {
                modality_name: dict(counter)
                for modality_name, counter in sorted(modality_map.items())
            }
            for split_name, modality_map in sorted(split_modality_counts.items())
        },
        "notes": notes,
    }


def build_external_cohort_audit(
    split_labels_payload: Mapping[str, Any],
    library_contract_payload: Mapping[str, Any],
    packet_deficit_payload: Mapping[str, Any] | None = None,
    eligibility_matrix_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    labels = [
        dict(item)
        for item in (split_labels_payload.get("labels") or ())
        if isinstance(item, Mapping)
    ]
    if not labels:
        raise AuditInputError("split labels must contain at least one label row")

    split_counts = dict(split_labels_payload.get("counts") or {})
    bucket_counts = dict(Counter(str(item["bucket"]) for item in labels))
    bucket_split_counts = _bucket_by_split(labels)

    accessions = [str(item["accession"]) for item in labels]
    accession_counts = Counter(accessions)
    duplicate_accessions = sorted(
        accession for accession, count in accession_counts.items() if count > 1
    )
    leakage_ready = dict(split_labels_payload.get("leakage_ready") or {})

    imbalance_status = "ok"
    imbalance_notes: list[str] = []
    if len(bucket_split_counts) > 1:
        non_empty_buckets_per_split = {
            split: sorted(bucket for bucket, count in buckets.items() if count > 0)
            for split, buckets in bucket_split_counts.items()
        }
        bucket_sets = {tuple(values) for values in non_empty_buckets_per_split.values()}
        if len(bucket_sets) > 1:
            imbalance_status = "attention_needed"
            imbalance_notes.append(
                "Split-level bucket placement is uneven even though overall bucket "
                "counts may be balanced."
            )

    missing_modality_lookup = (
        _missing_modalities_by_accession(packet_deficit_payload or {})
        if packet_deficit_payload is not None
        else {}
    )
    coverage_gaps = {
        accession: missing_modality_lookup.get(accession, [])
        for accession in accessions
        if missing_modality_lookup.get(accession)
    }
    ligand_follow_through = _ligand_follow_through(labels, eligibility_matrix_payload)
    modality_readiness = _modality_readiness_audit(labels, eligibility_matrix_payload)

    leakage_status = "ok"
    leakage_notes: list[str] = []
    if duplicate_accessions:
        leakage_status = "attention_needed"
        leakage_notes.append("Duplicate accessions detected across the audited split list.")
    if not leakage_ready.get("accession_level_only", False):
        leakage_status = "attention_needed"
        leakage_notes.append("Split guard is not accession-level only.")
    if leakage_ready.get("cross_split_duplicates"):
        leakage_status = "attention_needed"
        leakage_notes.append("Cross-split duplicates were reported in the leakage metadata.")

    overall_status = (
        "ok"
        if (
            imbalance_status == "ok"
            and leakage_status == "ok"
            and ligand_follow_through["status"] in {"ok", "not_assessed"}
        )
        else "attention_needed"
    )
    decision = (
        "usable_with_notes"
        if overall_status == "attention_needed"
        else "ready_for_read_only_audit"
    )

    return {
        "cli": {
            "command": "python scripts/audit_external_cohort.py",
            "mode": "report_only",
        },
        "inputs": {
            "split_labels": _repo_relative_text(DEFAULT_SPLIT_LABELS),
            "library_contract": _repo_relative_text(DEFAULT_LIBRARY_CONTRACT),
            "packet_deficit_dashboard": (
                _repo_relative_text(DEFAULT_PACKET_DEFICIT)
                if packet_deficit_payload is not None
                else None
            ),
        },
        "audited_split": {
            "manifest_id": split_labels_payload.get("manifest_id"),
            "split_policy": split_labels_payload.get("split_policy"),
            "split_counts": {
                key: split_counts.get(key)
                for key in ("total", "train", "val", "test", "resolved", "unresolved")
            },
            "bucket_counts": bucket_counts,
            "bucket_by_split": bucket_split_counts,
            "leakage_ready": leakage_ready,
        },
        "audit_results": {
            "imbalance": {
                "status": imbalance_status,
                "notes": imbalance_notes,
            },
            "leakage": {
                "status": leakage_status,
                "duplicate_accessions": duplicate_accessions,
                "notes": leakage_notes,
            },
            "coverage_gaps": {
                "status": "attention_needed" if coverage_gaps else "ok",
                "missing_modalities_by_accession": coverage_gaps,
            },
            "modality_readiness": modality_readiness,
            "ligand_follow_through": ligand_follow_through,
            "overall": {
                "status": overall_status,
                "decision": decision,
            },
        },
        "recommended_operator_actions": [
            "Keep the audited split read-only and do not silently widen or reshuffle it.",
            "Treat accession-level leakage as the hard floor for any external audit.",
            "Review sparse or coverage-skewed buckets before claiming broad generalization.",
            "Use packet deficit rows to explain missing-modality bias in the audited split.",
            (
                "Do not let ligand-aware split behavior govern this audited cohort while only one "
                "grounded ligand accession is present."
            ),
        ],
        "evidence_paths": {
            "split_labels": _repo_relative_text(DEFAULT_SPLIT_LABELS),
            "library_contract": _repo_relative_text(DEFAULT_LIBRARY_CONTRACT),
            "packet_deficit_dashboard": (
                _repo_relative_text(DEFAULT_PACKET_DEFICIT)
                if packet_deficit_payload is not None
                else None
            ),
            "training_set_eligibility_matrix_preview": (
                _repo_relative_text(DEFAULT_ELIGIBILITY_MATRIX)
                if eligibility_matrix_payload is not None
                else None
            ),
            "library_contract_id": library_contract_payload.get("contract_id")
            or library_contract_payload.get("artifact_id"),
        },
    }


def render_external_cohort_audit_markdown(payload: Mapping[str, Any]) -> str:
    audited_split = payload.get("audited_split") or {}
    audit_results = payload.get("audit_results") or {}
    ligand_follow_through = audit_results.get("ligand_follow_through", {})
    modality_readiness = audit_results.get("modality_readiness", {})
    readiness_ladder = ligand_follow_through.get("readiness_ladder", {})
    lines = [
        "# External Cohort Audit",
        "",
        "## What Was Audited",
        f"- Manifest id: `{audited_split.get('manifest_id')}`",
        f"- Split policy: `{audited_split.get('split_policy')}`",
        "- Split counts: "
        f"`{json.dumps(audited_split.get('split_counts') or {}, sort_keys=True)}`",
        "- Bucket counts: "
        f"`{json.dumps(audited_split.get('bucket_counts') or {}, sort_keys=True)}`",
        "",
        "## Audit Result",
        f"- Imbalance: `{audit_results.get('imbalance', {}).get('status')}`",
        f"- Leakage: `{audit_results.get('leakage', {}).get('status')}`",
        f"- Coverage gaps: `{audit_results.get('coverage_gaps', {}).get('status')}`",
        "- Ligand follow-through: "
        f"`{ligand_follow_through.get('status')}` / "
        f"`{ligand_follow_through.get('decision')}`",
        "- Modality readiness: "
        f"`{modality_readiness.get('status')}` / "
        f"`{json.dumps(modality_readiness.get('modality_counts') or {}, sort_keys=True)}`",
        "- Ligand readiness ladder counts: "
        f"`{json.dumps(readiness_ladder.get('counts') or {}, sort_keys=True)}`",
        "- Overall: "
        f"`{audit_results.get('overall', {}).get('status')}` / "
        f"`{audit_results.get('overall', {}).get('decision')}`",
        "",
        "## Ligand Follow-Through",
        "- Grounded accessions: "
        f"`{_render_accession_list(ligand_follow_through.get('grounded_accessions'))}`",
        "- Candidate-only accessions: "
        f"`{_render_accession_list(ligand_follow_through.get('candidate_only_accessions'))}`",
        "- Blocked accessions: "
        f"`{_render_accession_list(ligand_follow_through.get('blocked_accessions'))}`",
        "- Library-only accessions: "
        f"`{_render_accession_list(ligand_follow_through.get('library_only_accessions'))}`",
        "- Readiness ladder accessions:",
        (
            f"  - grounded preview-safe: "
            f"`{_render_accession_list(readiness_ladder.get('grounded_preview_safe_accessions'))}`"
        ),
        (
            f"  - grounded governing: "
            f"`{_render_accession_list(readiness_ladder.get('grounded_governing_accessions'))}`"
        ),
        (
            f"  - candidate-only non-governing: "
            f"`{_render_accession_list(readiness_ladder.get('candidate_only_non_governing_accessions'))}`"
        ),
        (
            f"  - support-only: "
            f"`{_render_accession_list(readiness_ladder.get('support_only_accessions'))}`"
        ),
        (
            f"  - absent: "
            f"`{_render_accession_list(readiness_ladder.get('absent_accessions'))}`"
        ),
        "",
        "## Recommended Next Action",
    ]
    for action in payload.get("recommended_operator_actions") or ():
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-labels", type=Path, default=DEFAULT_SPLIT_LABELS)
    parser.add_argument("--library-contract", type=Path, default=DEFAULT_LIBRARY_CONTRACT)
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT)
    parser.add_argument("--eligibility-matrix", type=Path, default=DEFAULT_ELIGIBILITY_MATRIX)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    split_labels_payload = _load_json(args.split_labels)
    library_contract_payload = _load_json(args.library_contract)
    packet_deficit_payload = (
        _load_json(args.packet_deficit) if args.packet_deficit.exists() else None
    )
    eligibility_matrix_payload = (
        _load_json(args.eligibility_matrix) if args.eligibility_matrix.exists() else None
    )
    payload = build_external_cohort_audit(
        split_labels_payload,
        library_contract_payload,
        packet_deficit_payload=packet_deficit_payload,
        eligibility_matrix_payload=eligibility_matrix_payload,
    )
    _write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_external_cohort_audit_markdown(payload),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditInputError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
