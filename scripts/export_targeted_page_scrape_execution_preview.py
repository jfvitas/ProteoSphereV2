from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from scripts.export_targeted_page_scrape_registry_preview import (
        build_targeted_page_scrape_registry_preview,
    )
    from scripts.web_enrichment_preview_support import read_json, write_json
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from export_targeted_page_scrape_registry_preview import (
        build_targeted_page_scrape_registry_preview,
    )
    from web_enrichment_preview_support import read_json, write_json

DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
)
DEFAULT_COMPACT_ENRICHMENT_POLICY = (
    REPO_ROOT / "artifacts" / "status" / "compact_enrichment_policy_preview.json"
)
DEFAULT_MISSING_DATA_POLICY = (
    REPO_ROOT / "artifacts" / "status" / "missing_data_policy_preview.json"
)
DEFAULT_RAW_PAYLOAD_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_raw_payload_registry_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_execution_preview.json"
)

_FAMILY_PRIORITY_HINTS: tuple[tuple[str, str], ...] = (
    ("biogrid", "BioGRID guarded procurement first wave"),
    ("string", "STRING guarded procurement first wave"),
    ("intact", "IntAct authoritative mirror refresh or intake"),
    ("prosite", "PROSITE acquisition refresh"),
    ("elm", "ELM acquisition refresh"),
    ("sabio", "SABIO-RK acquisition"),
    ("kinetics", "SABIO-RK acquisition"),
)


def _load_targeted_page_scrape_registry(path: Path) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return build_targeted_page_scrape_registry_preview()


def _acquisition_priority_map(missing_data_policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = missing_data_policy.get("scrape_and_enrichment_priorities", {}).get(
        "top_next_acquisitions"
    ) or []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        target = str(row.get("target") or "").strip()
        if not target:
            continue
        result[target.casefold()] = {
            "rank": int(row.get("rank") or 0),
            "target": target,
            "why": str(row.get("why") or "").strip(),
        }
    return result


def _priority_anchor_for_family(
    target_family: str,
    acquisition_priority_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    family_key = target_family.casefold()
    for needle, target in _FAMILY_PRIORITY_HINTS:
        if needle in family_key:
            candidate = acquisition_priority_map.get(target.casefold())
            if candidate is not None:
                return dict(candidate)
    return {
        "rank": 999,
        "target": "unmapped_targeted_page_scrape_family",
        "why": (
            "No current scrape/acquisition priority anchor matched this targeted page "
            "family, so it stays behind known priority families."
        ),
    }


def _status_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def build_targeted_page_scrape_execution_preview(
    targeted_page_scrape_registry: dict[str, Any],
    compact_enrichment_policy: dict[str, Any],
    missing_data_policy: dict[str, Any],
    raw_payload_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    allowed_policy_labels = [
        str(label).strip()
        for label in (compact_enrichment_policy.get("allowed_policy_labels") or [])
        if str(label).strip()
    ]
    if "report_only_non_governing" not in allowed_policy_labels:
        raise ValueError("compact enrichment policy does not allow report_only_non_governing")

    acquisition_priority_map = _acquisition_priority_map(missing_data_policy)
    raw_payload_registry = raw_payload_registry if isinstance(raw_payload_registry, dict) else {}
    raw_payloads_by_accession: dict[str, list[dict[str, Any]]] = {}
    for raw_row in raw_payload_registry.get("rows") or []:
        if not isinstance(raw_row, dict):
            continue
        accession = str(raw_row.get("accession") or "").strip()
        if accession:
            raw_payloads_by_accession.setdefault(accession, []).append(dict(raw_row))

    registry_rows = targeted_page_scrape_registry.get("rows") or []
    unsorted_rows: list[dict[str, Any]] = []
    for source_index, row in enumerate(registry_rows, start=1):
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        target_family = str(row.get("target_family") or "").strip()
        if not accession or not target_family:
            continue
        anchor = _priority_anchor_for_family(target_family, acquisition_priority_map)
        candidate_pages = [
            str(page).strip()
            for page in (row.get("candidate_pages") or [])
            if str(page).strip()
        ]
        captured_payloads = raw_payloads_by_accession.get(accession, [])
        unsorted_rows.append(
            {
                "_source_index": source_index,
                "_family_anchor_rank": int(anchor["rank"]),
                "execution_slice_id": f"targeted_page_scrape:{accession}:{target_family}",
                "accession": accession,
                "target_family": target_family,
                "candidate_pages": candidate_pages,
                "page_count": len(candidate_pages),
                "default_ingest_status": str(row.get("default_ingest_status") or "").strip(),
                "policy_label": "report_only_non_governing",
                "execution_status": (
                    "captured_candidate_only_payloads"
                    if captured_payloads
                    else "ready_for_candidate_only_capture"
                ),
                "page_scraping_started": (
                    bool(row.get("page_scraping_started")) or bool(captured_payloads)
                ),
                "payload_capture_started": bool(captured_payloads),
                "captured_payload_count": len(captured_payloads),
                "priority_anchor_target": str(anchor["target"]),
                "priority_anchor_rank": int(anchor["rank"]),
                "priority_anchor_why": str(anchor["why"]),
                "next_truthful_stage": "capture_page_payloads_as_candidate_only_support",
                "governing_for_split_or_leakage": False,
                "bundle_safe_preview": False,
            }
        )

    ordered_rows = sorted(
        unsorted_rows,
        key=lambda row: (
            int(row["_family_anchor_rank"]),
            int(row["_source_index"]),
            str(row["accession"]).casefold(),
            str(row["target_family"]).casefold(),
        ),
    )
    rows: list[dict[str, Any]] = []
    for priority_rank, row in enumerate(ordered_rows, start=1):
        emitted = {key: value for key, value in row.items() if not key.startswith("_")}
        emitted["priority_rank"] = priority_rank
        rows.append(emitted)

    family_counts: dict[str, int] = {}
    for row in rows:
        target_family = str(row["target_family"])
        family_counts[target_family] = family_counts.get(target_family, 0) + 1

    ordered_accessions = [str(row["accession"]) for row in rows]
    ordered_slice_ids = [str(row["execution_slice_id"]) for row in rows]
    return {
        "artifact_id": "targeted_page_scrape_execution_preview",
        "schema_id": "proteosphere-targeted-page-scrape-execution-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "ordered_accessions": ordered_accessions,
            "ordered_execution_slice_ids": ordered_slice_ids,
            "target_family_counts": family_counts,
            "default_ingest_status_counts": _status_counts(rows, "default_ingest_status"),
            "policy_label_counts": _status_counts(rows, "policy_label"),
            "priority_anchor_targets": [
                row["priority_anchor_target"] for row in rows if row["priority_anchor_target"]
            ],
            "page_scraping_started": any(bool(row["page_scraping_started"]) for row in rows),
            "payload_capture_started": any(bool(row["payload_capture_started"]) for row in rows),
        },
        "truth_boundary": {
            "summary": (
                "This preview converts the targeted page scrape registry into ordered "
                "candidate-only execution slices. It does not perform scraping, does "
                "not normalize page payloads, and does not create governing bundle or "
                "split inputs."
            ),
            "report_only": True,
            "candidate_only_non_governing": True,
            "page_scraping_started": any(bool(row["page_scraping_started"]) for row in rows),
            "payload_capture_started": any(bool(row["payload_capture_started"]) for row in rows),
            "governing": False,
            "bundle_included": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a candidate-only targeted page scrape execution preview."
    )
    parser.add_argument(
        "--targeted-page-scrape-registry",
        type=Path,
        default=DEFAULT_TARGETED_PAGE_SCRAPE_REGISTRY,
    )
    parser.add_argument(
        "--compact-enrichment-policy",
        type=Path,
        default=DEFAULT_COMPACT_ENRICHMENT_POLICY,
    )
    parser.add_argument(
        "--missing-data-policy",
        type=Path,
        default=DEFAULT_MISSING_DATA_POLICY,
    )
    parser.add_argument(
        "--raw-payload-registry",
        type=Path,
        default=DEFAULT_RAW_PAYLOAD_REGISTRY,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_targeted_page_scrape_execution_preview(
        _load_targeted_page_scrape_registry(args.targeted_page_scrape_registry),
        read_json(args.compact_enrichment_policy),
        read_json(args.missing_data_policy),
        read_json(args.raw_payload_registry) if args.raw_payload_registry.exists() else {},
    )
    write_json(args.output_json, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
