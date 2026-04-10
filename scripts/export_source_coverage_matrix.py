from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.unified_source_catalog import build_unified_source_catalog

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP_SUMMARY = REPO_ROOT / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
DEFAULT_LOCAL_REGISTRY_SUMMARY = (
    REPO_ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "source_coverage_matrix.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "source_coverage_matrix.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _status_weight(status: str) -> int:
    return {"present": 3, "partial": 2, "missing": 0}.get(status, 0)


def _normalize_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    return int(value)


def _facet_summary(facet: dict[str, Any]) -> dict[str, Any]:
    detail = facet.get("detail") if isinstance(facet.get("detail"), dict) else {}
    facet_kind = str(facet.get("facet_kind") or "unknown")
    status = str(facet.get("status") or "missing")
    summary = {
        "facet_kind": facet_kind,
        "status": status,
        "is_available": status != "missing",
        "snapshot_state": str(facet.get("snapshot_state") or "unknown"),
        "drift_state": str(facet.get("drift_state") or "unknown"),
        "detail": dict(detail),
    }
    if facet_kind == "online_raw":
        summary.update(
            {
                "downloaded_file_count": _normalize_int(detail.get("downloaded_file_count")),
                "manifest_id": detail.get("manifest_id"),
                "release_version": detail.get("release_version"),
                "source_locator": detail.get("source_locator"),
            }
        )
    elif facet_kind == "local_registry":
        summary.update(
            {
                "present_root_count": _normalize_int(detail.get("present_root_count")),
                "present_file_count": _normalize_int(detail.get("present_file_count")),
                "present_total_bytes": _normalize_int(detail.get("present_total_bytes")),
                "load_hints": [str(item) for item in detail.get("load_hints") or ()],
                "manifest_path": detail.get("manifest_path"),
                "inventory_path": detail.get("inventory_path"),
            }
        )
    return summary


def _matrix_row(entry: Any) -> dict[str, Any]:
    facets = [_facet_summary(facet.to_dict()) for facet in entry.facets]
    available_facets = [facet["facet_kind"] for facet in facets if facet["status"] != "missing"]
    available_via = list(entry.available_via) or available_facets
    online_facet = next((facet for facet in facets if facet["facet_kind"] == "online_raw"), None)
    local_facet = next((facet for facet in facets if facet["facet_kind"] == "local_registry"), None)
    present_file_count = _normalize_int(local_facet.get("present_file_count")) if local_facet else 0
    present_total_bytes = (
        _normalize_int(local_facet.get("present_total_bytes")) if local_facet else 0
    )
    downloaded_file_count = (
        _normalize_int(online_facet.get("downloaded_file_count")) if online_facet else 0
    )
    present_facet_count = sum(1 for facet in facets if facet["status"] == "present")
    partial_facet_count = sum(1 for facet in facets if facet["status"] == "partial")
    missing_facet_count = sum(1 for facet in facets if facet["status"] == "missing")
    degraded_facet_count = sum(1 for facet in facets if facet["snapshot_state"] == "degraded")
    drifted_facet_count = sum(
        1 for facet in facets if facet["drift_state"] in {"drifted", "regressed"}
    )
    coverage_score = (
        _status_weight(entry.effective_status) * 100
        + present_facet_count * 10
        + partial_facet_count * 4
        + len(available_via)
        - degraded_facet_count * 12
        - drifted_facet_count * 8
    )
    coverage_score = max(0, coverage_score)
    return {
        "source_name": entry.source_name,
        "normalized_name": entry.normalized_name,
        "category": entry.category,
        "effective_status": entry.effective_status,
        "snapshot_state": entry.snapshot_state,
        "drift_state": entry.drift_state,
        "available_via": available_via,
        "notes": list(entry.notes),
        "coverage_score": coverage_score,
        "facet_counts": {
            "present": present_facet_count,
            "partial": partial_facet_count,
            "missing": missing_facet_count,
            "degraded": degraded_facet_count,
            "drifted": drifted_facet_count,
        },
        "counts": {
            "downloaded_file_count": downloaded_file_count,
            "present_file_count": present_file_count,
            "present_total_bytes": present_total_bytes,
        },
        "facets": facets,
        "planning_signals": {
            "status_weight": _status_weight(entry.effective_status),
            "available_facet_count": len(available_via),
            "source_facet_count": len(facets),
            "procurement_gap": entry.effective_status != "present",
            "local_registry_ready": bool(local_facet and local_facet["status"] == "present"),
            "online_raw_ready": bool(online_facet and online_facet["status"] == "present"),
            "snapshot_degraded": entry.snapshot_state == "degraded",
            "local_fingerprint_drift": any(
                facet["facet_kind"] == "local_registry"
                and facet["drift_state"] in {"drifted", "regressed"}
                for facet in facets
            ),
        },
    }


def build_source_coverage_matrix(
    *,
    bootstrap_summary_path: Path = DEFAULT_BOOTSTRAP_SUMMARY,
    local_registry_summary_path: Path = DEFAULT_LOCAL_REGISTRY_SUMMARY,
) -> dict[str, Any]:
    catalog = build_unified_source_catalog(
        bootstrap_summary_path=bootstrap_summary_path,
        local_registry_summary_path=local_registry_summary_path,
    )
    matrix = [_matrix_row(entry) for entry in catalog.entries]
    status_counts = Counter(row["effective_status"] for row in matrix)
    snapshot_state_counts = Counter(row["snapshot_state"] for row in matrix)
    drift_state_counts = Counter(row["drift_state"] for row in matrix)
    available_counts = Counter(via for row in matrix for via in row["available_via"])
    category_counts = Counter(str(row.get("category") or "unknown") for row in matrix)
    present_rows = [row for row in matrix if row["effective_status"] == "present"]
    partial_rows = [row for row in matrix if row["effective_status"] == "partial"]
    missing_rows = [row for row in matrix if row["effective_status"] == "missing"]
    total_downloaded_files = sum(row["counts"]["downloaded_file_count"] for row in matrix)
    total_present_files = sum(row["counts"]["present_file_count"] for row in matrix)
    total_present_bytes = sum(row["counts"]["present_total_bytes"] for row in matrix)

    return {
        "schema_id": "proteosphere-source-coverage-matrix-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "complete",
        "inputs": {
            "bootstrap_summary": str(bootstrap_summary_path).replace("\\", "/"),
            "local_registry_summary": str(local_registry_summary_path).replace("\\", "/"),
        },
        "source_catalog": catalog.to_dict(),
        "summary": {
            "source_count": len(matrix),
            "status_counts": dict(sorted(status_counts.items())),
            "snapshot_state_counts": dict(sorted(snapshot_state_counts.items())),
            "drift_state_counts": dict(sorted(drift_state_counts.items())),
            "available_via_counts": dict(sorted(available_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "present_source_count": len(present_rows),
            "partial_source_count": len(partial_rows),
            "missing_source_count": len(missing_rows),
            "total_downloaded_files": total_downloaded_files,
            "total_present_files": total_present_files,
            "total_present_bytes": total_present_bytes,
            "degraded_online_sources": catalog.summary.get("degraded_online_sources", []),
            "drifted_local_sources": catalog.summary.get("drifted_local_sources", []),
            "highest_coverage_sources": [row["source_name"] for row in sorted(
                matrix,
                key=lambda row: (
                    -int(row["coverage_score"]),
                    row["source_name"].casefold(),
                ),
            )[:10]],
            "procurement_priority_sources": [
                row["source_name"]
                for row in sorted(
                    matrix,
                    key=lambda row: (
                        row["effective_status"] != "missing",
                        row["effective_status"] != "partial",
                        -int(row["coverage_score"]),
                        row["source_name"].casefold(),
                    ),
                )
                if row["effective_status"] != "present"
            ][:15],
        },
        "matrix": sorted(
            matrix,
            key=lambda row: (
                row["effective_status"] != "missing",
                row["effective_status"] != "partial",
                row["source_name"].casefold(),
            ),
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    snapshot_state_counts = summary.get("snapshot_state_counts", {})
    drift_state_counts = summary.get("drift_state_counts", {})
    degraded_online_sources = summary.get("degraded_online_sources", [])
    drifted_local_sources = summary.get("drifted_local_sources", [])
    procurement_priority_sources = summary.get("procurement_priority_sources", [])
    highest_coverage_sources = summary.get("highest_coverage_sources", [])
    lines = [
        "# Source Coverage Matrix",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Source count: `{summary['source_count']}`",
        f"- Status counts: `{summary['status_counts']}`",
        f"- Snapshot state counts: `{snapshot_state_counts}`",
        f"- Drift state counts: `{drift_state_counts}`",
        f"- Available via counts: `{summary['available_via_counts']}`",
        f"- Total downloaded files: `{summary['total_downloaded_files']}`",
        f"- Total present files: `{summary['total_present_files']}`",
        f"- Total present bytes: `{summary['total_present_bytes']}`",
        "",
        "## Stability",
        "",
        (
            "- Degraded online snapshots: "
            + ", ".join(f"`{name}`" for name in degraded_online_sources[:10])
        )
        if degraded_online_sources
        else "- Degraded online snapshots: none",
        (
            "- Drifted local sources: "
            + ", ".join(f"`{name}`" for name in drifted_local_sources[:10])
        )
        if drifted_local_sources
        else "- Drifted local sources: none",
        "",
        "## Procurement Priority",
        "",
        (
            "- Priority sources: "
            + ", ".join(f"`{name}`" for name in procurement_priority_sources[:10])
        )
        if procurement_priority_sources
        else "- Priority sources: none",
        "",
        "## Top Coverage",
        "",
        (
            "- Highest coverage sources: "
            + ", ".join(f"`{name}`" for name in highest_coverage_sources[:10])
        )
        if highest_coverage_sources
        else "- Highest coverage sources: none",
        "",
        "## Matrix",
        "",
    ]
    for row in payload["matrix"]:
        lines.append(
            "- "
            + f"`{row['source_name']}` "
            + f"status=`{row['effective_status']}` "
            + f"snapshot=`{row.get('snapshot_state', 'unknown')}` "
            + f"drift=`{row.get('drift_state', 'unknown')}` "
            + f"via=`{','.join(row['available_via']) or 'none'}` "
            + f"score=`{row['coverage_score']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the source coverage matrix.")
    parser.add_argument("--bootstrap-summary", type=Path, default=DEFAULT_BOOTSTRAP_SUMMARY)
    parser.add_argument(
        "--local-registry-summary", type=Path, default=DEFAULT_LOCAL_REGISTRY_SUMMARY
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_source_coverage_matrix(
        bootstrap_summary_path=args.bootstrap_summary,
        local_registry_summary_path=args.local_registry_summary,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Source coverage matrix exported: "
            f"sources={payload['summary']['source_count']} "
            f"present={payload['summary']['present_source_count']} "
            f"partial={payload['summary']['partial_source_count']} "
            f"missing={payload['summary']['missing_source_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
