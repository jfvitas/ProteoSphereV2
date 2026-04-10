from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from execution.acquire.unified_source_catalog import build_unified_source_catalog  # noqa: E402

DEFAULT_BOOTSTRAP_SUMMARY = REPO_ROOT / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
DEFAULT_LOCAL_REGISTRY_SUMMARY = REPO_ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"
DEFAULT_CANONICAL_SUMMARY = REPO_ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "data_inventory_audit.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "data_inventory_audit.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _count_store_records_by_kind(canonical_summary: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in (canonical_summary.get("canonical_store") or {}).get("records") or ():
        entity_kind = str(record.get("entity_kind") or "unknown")
        counts[entity_kind] += 1
    return dict(sorted(counts.items()))


def _summarize_bootstrap(bootstrap_summary: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    total_files = 0
    ok_sources = 0
    for result in bootstrap_summary.get("results") or ():
        if not isinstance(result, dict):
            continue
        downloaded_files = [str(item) for item in result.get("downloaded_files") or ()]
        manifest = result.get("manifest") if isinstance(result.get("manifest"), dict) else {}
        status = str(result.get("status") or "unknown")
        if status == "ok":
            ok_sources += 1
        total_files += len(downloaded_files)
        sources.append(
            {
                "source": str(result.get("source") or "unknown"),
                "status": status,
                "downloaded_file_count": len(downloaded_files),
                "example_files": downloaded_files[:5],
                "manifest_id": manifest.get("manifest_id"),
                "release_version": manifest.get("release_version"),
                "retrieval_mode": manifest.get("retrieval_mode"),
                "source_locator": manifest.get("source_locator"),
            }
        )
    return {
        "generated_at": bootstrap_summary.get("generated_at"),
        "accessions": [str(item) for item in bootstrap_summary.get("accessions") or ()],
        "source_count": len(sources),
        "ok_source_count": ok_sources,
        "downloaded_file_count": total_files,
        "sources": sorted(sources, key=lambda item: item["source"]),
    }


def _summarize_local_registry(local_registry_summary: dict[str, Any]) -> dict[str, Any]:
    imported_sources = [
        item
        for item in local_registry_summary.get("imported_sources") or ()
        if isinstance(item, dict)
    ]
    status_counts = Counter(str(item.get("status") or "unknown") for item in imported_sources)
    category_counts = Counter(str(item.get("category") or "unknown") for item in imported_sources)
    total_bytes = sum(int(item.get("present_total_bytes") or 0) for item in imported_sources)
    present_sources = [item for item in imported_sources if str(item.get("status")) == "present"]
    largest_present = sorted(
        present_sources,
        key=lambda item: int(item.get("present_total_bytes") or 0),
        reverse=True,
    )[:10]
    return {
        "generated_at": local_registry_summary.get("generated_at"),
        "stamp": local_registry_summary.get("stamp"),
        "imported_source_count": local_registry_summary.get("imported_source_count"),
        "selected_source_count": local_registry_summary.get("selected_source_count"),
        "status_counts": dict(sorted(status_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "present_total_bytes": total_bytes,
        "largest_present_sources": [
            {
                "source_name": str(item.get("source_name") or "unknown"),
                "category": str(item.get("category") or "unknown"),
                "present_file_count": int(item.get("present_file_count") or 0),
                "present_total_bytes": int(item.get("present_total_bytes") or 0),
                "inventory_path": item.get("inventory_path"),
                "manifest_path": item.get("manifest_path"),
            }
            for item in largest_present
        ],
        "sources": [
            {
                "source_name": str(item.get("source_name") or "unknown"),
                "status": str(item.get("status") or "unknown"),
                "category": str(item.get("category") or "unknown"),
                "present_file_count": int(item.get("present_file_count") or 0),
                "present_total_bytes": int(item.get("present_total_bytes") or 0),
                "load_hints": [str(hint) for hint in item.get("load_hints") or ()],
                "join_keys": [str(key) for key in item.get("join_keys") or ()],
            }
            for item in imported_sources
        ],
    }


def _summarize_canonical(canonical_summary: dict[str, Any]) -> dict[str, Any]:
    sequence_result = canonical_summary.get("sequence_result") or {}
    structure_result = canonical_summary.get("structure_result") or {}
    assay_result = canonical_summary.get("assay_result") or {}
    top_record_counts = canonical_summary.get("record_counts") if isinstance(
        canonical_summary.get("record_counts"), dict
    ) else {}
    top_unresolved_counts = canonical_summary.get("unresolved_counts") if isinstance(
        canonical_summary.get("unresolved_counts"), dict
    ) else {}
    store_counts = _count_store_records_by_kind(canonical_summary)
    return {
        "created_at": canonical_summary.get("created_at"),
        "status": canonical_summary.get("status"),
        "reason": canonical_summary.get("reason"),
        "run_id": canonical_summary.get("run_id"),
        "record_counts": top_record_counts or {
            "protein": len(sequence_result.get("canonical_proteins") or ()),
            "ligand": store_counts.get("ligand", 0),
            "assay": len(assay_result.get("canonical_assays") or ()),
            "structure": store_counts.get("structure", 0),
            "store_total": sum(store_counts.values()),
        },
        "unresolved_counts": top_unresolved_counts or {
            "sequence_conflicts": len(sequence_result.get("conflicts") or ()),
            "sequence_unresolved_references": len(
                sequence_result.get("unresolved_references") or ()
            ),
            "structure_conflicts": len(structure_result.get("conflicts") or ()),
            "structure_unresolved_references": len(
                structure_result.get("unresolved_references") or ()
            ),
            "assay_conflicts": len(assay_result.get("conflicts") or ()),
            "assay_unresolved_cases": len(assay_result.get("unresolved_cases") or ()),
        },
        "lane_statuses": {
            "sequence": sequence_result.get("status"),
            "structure": structure_result.get("status"),
            "assay": assay_result.get("status"),
        },
        "store_counts_by_kind": store_counts,
        "output_paths": canonical_summary.get("output_paths") or {},
    }


def build_inventory_audit(
    bootstrap_summary_path: Path,
    local_registry_summary_path: Path,
    canonical_summary_path: Path,
) -> dict[str, Any]:
    bootstrap_summary = _read_json(bootstrap_summary_path)
    local_registry_summary = _read_json(local_registry_summary_path)
    canonical_summary = _read_json(canonical_summary_path)
    unified_catalog = build_unified_source_catalog(
        bootstrap_summary_path=bootstrap_summary_path,
        local_registry_summary_path=local_registry_summary_path,
    )

    return {
        "schema_id": "proteosphere-data-inventory-audit-2026-03-22",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "complete",
        "inputs": {
            "bootstrap_summary": _repo_relative(bootstrap_summary_path),
            "local_registry_summary": _repo_relative(local_registry_summary_path),
            "canonical_summary": _repo_relative(canonical_summary_path),
        },
        "storage_locations": {
            "raw_online_root": "data/raw",
            "raw_local_registry_root": "data/raw/local_registry",
            "canonical_root": "data/canonical",
            "packages_root": "data/packages",
            "planning_index_root": "data/planning_index",
        },
        "raw_online": _summarize_bootstrap(bootstrap_summary),
        "raw_local_registry": _summarize_local_registry(local_registry_summary),
        "effective_sources": unified_catalog.to_dict(),
        "canonical": _summarize_canonical(canonical_summary),
    }


def render_inventory_markdown(audit: dict[str, Any]) -> str:
    raw_online = audit["raw_online"]
    raw_local = audit["raw_local_registry"]
    effective_sources = audit["effective_sources"]["summary"]
    canonical = audit["canonical"]
    record_counts = canonical["record_counts"]
    unresolved_counts = canonical["unresolved_counts"]
    top_sources = raw_local["largest_present_sources"]
    lines = [
        "# Data Inventory Audit",
        "",
        f"- Generated at: `{audit['generated_at']}`",
        (
            "- Raw online sources mirrored: "
            + f"`{raw_online['ok_source_count']}/{raw_online['source_count']}`"
        ),
        f"- Raw online files mirrored: `{raw_online['downloaded_file_count']}`",
        f"- Local sources registered: `{raw_local['imported_source_count']}`",
        f"- Local registered bytes: `{raw_local['present_total_bytes']}`",
        f"- Canonical status: `{canonical['status']}`",
        f"- Canonical run id: `{canonical['run_id']}`",
        (
            "- Effective source availability: "
            + f"`{effective_sources['effective_status_counts']}`"
        ),
        (
            "- Snapshot health states: "
            + f"`{effective_sources.get('snapshot_state_counts', {})}`"
        ),
        (
            "- Drift states: "
            + f"`{effective_sources.get('drift_state_counts', {})}`"
        ),
        (
            "- Degraded online snapshots: "
            + ", ".join(
                f"`{name}`" for name in effective_sources.get("degraded_online_sources", [])[:10]
            )
        )
        if effective_sources.get("degraded_online_sources")
        else "- Degraded online snapshots: none",
        (
            "- Drifted local sources: "
            + ", ".join(
                f"`{name}`" for name in effective_sources.get("drifted_local_sources", [])[:10]
            )
        )
        if effective_sources.get("drifted_local_sources")
        else "- Drifted local sources: none",
        "",
        "## Storage",
        "",
        f"- Online snapshots: `{audit['storage_locations']['raw_online_root']}`",
        f"- Local mirror registry: `{audit['storage_locations']['raw_local_registry_root']}`",
        f"- Canonical records: `{audit['storage_locations']['canonical_root']}`",
        f"- Training packages: `{audit['storage_locations']['packages_root']}`",
        f"- Planning index: `{audit['storage_locations']['planning_index_root']}`",
        "",
        "## Canonical",
        "",
        f"- Proteins: `{record_counts.get('protein', 0)}`",
        f"- Ligands: `{record_counts.get('ligand', 0)}`",
        f"- Assays: `{record_counts.get('assay', 0)}`",
        f"- Structures: `{record_counts.get('structure', 0)}`",
        f"- Store total: `{record_counts.get('store_total', 0)}`",
        f"- Sequence lane: `{canonical['lane_statuses'].get('sequence')}`",
        f"- Structure lane: `{canonical['lane_statuses'].get('structure')}`",
        f"- Assay lane: `{canonical['lane_statuses'].get('assay')}`",
        f"- Assay unresolved cases: `{unresolved_counts.get('assay_unresolved_cases', 0)}`",
        "",
        "## Largest Local Sources",
        "",
    ]
    for item in top_sources:
        lines.append(
            "- "
            + f"`{item['source_name']}` "
            + (
                f"({item['category']}, {item['present_file_count']} files, "
                + f"{item['present_total_bytes']} bytes)"
            )
        )
    lines.extend(
        [
            "",
            "## Online Source Status",
            "",
        ]
    )
    for item in raw_online["sources"]:
        lines.append(
            "- "
            + f"`{item['source']}` "
            + f"status=`{item['status']}` "
            + f"files=`{item['downloaded_file_count']}` "
            + f"release=`{item['release_version']}`"
        )
    lines.extend(
        [
            "",
            "## Effective Availability",
            "",
            (
                "- Online-only sources: "
                + ", ".join(
                    f"`{name}`" for name in effective_sources["online_only_sources"][:10]
                )
            )
            if effective_sources["online_only_sources"]
            else "- Online-only sources: none",
            (
                "- Local-only sources: "
                + ", ".join(
                    f"`{name}`" for name in effective_sources["local_only_sources"][:10]
                )
            )
            if effective_sources["local_only_sources"]
            else "- Local-only sources: none",
            (
                "- Dual-available sources: "
                + ", ".join(
                    f"`{name}`" for name in effective_sources["dual_sources"][:10]
                )
            )
            if effective_sources["dual_sources"]
            else "- Dual-available sources: none",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit mirrored raw data, registered local sources, and canonical outputs."
    )
    parser.add_argument(
        "--bootstrap-summary",
        type=Path,
        default=DEFAULT_BOOTSTRAP_SUMMARY,
        help="Path to the online raw bootstrap summary JSON.",
    )
    parser.add_argument(
        "--local-registry-summary",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_SUMMARY,
        help="Path to the local source registry summary JSON.",
    )
    parser.add_argument(
        "--canonical-summary",
        type=Path,
        default=DEFAULT_CANONICAL_SUMMARY,
        help="Path to the canonical materialization summary JSON.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="Target JSON path for the inventory audit.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT,
        help="Target Markdown path for the human-readable inventory audit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_inventory_audit(
        bootstrap_summary_path=args.bootstrap_summary,
        local_registry_summary_path=args.local_registry_summary,
        canonical_summary_path=args.canonical_summary,
    )
    _write_json(args.json_output, audit)
    _write_text(args.markdown_output, render_inventory_markdown(audit))
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
