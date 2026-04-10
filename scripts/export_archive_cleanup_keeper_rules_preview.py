from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DUPLICATE_CLEANUP_STATUS = (
    REPO_ROOT / "artifacts" / "status" / "duplicate_cleanup_status.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "archive_cleanup_keeper_rules_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "archive_cleanup_keeper_rules_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("/", "\\")


def _path_entry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": _relative(path),
            "exists": False,
            "kind": "missing",
            "size_bytes": 0,
        }
    if path.is_dir():
        return {
            "path": _relative(path),
            "exists": True,
            "kind": "directory",
            "child_count": len(list(path.iterdir())),
        }
    return {
        "path": _relative(path),
        "exists": True,
        "kind": "file",
        "size_bytes": path.stat().st_size,
    }


def build_archive_cleanup_keeper_rules_preview(
    duplicate_cleanup_status: dict[str, Any],
) -> dict[str, Any]:
    root_prefix_bytes = {
        str(row.get("root_prefix")): int(row.get("reclaimable_bytes") or 0)
        for row in (duplicate_cleanup_status.get("top_root_prefixes") or [])
        if isinstance(row, dict)
    }
    rows = [
        {
            "family_id": "chembl_archive_vs_extracted",
            "status": "blocked_pending_keeper_validation",
            "observed_layout": "archive_plus_extracted",
            "preferred_keeper_kind": "extracted_directory",
            "keeper_paths": [
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "chembl"
                    / "chembl_36_sqlite"
                )
            ],
            "candidate_removal_paths": [
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "chembl"
                    / "chembl_36_sqlite.tar.gz"
                )
            ],
            "estimated_reclaimable_bytes_hint": root_prefix_bytes.get(
                "data\\raw\\local_copies\\chembl", 0
            ),
            "blocking_rules": [
                "validate extracted sqlite tree completeness before any archive deletion",
                "confirm no manifest-backed consumer requires the tarball path",
                "confirm seed-vs-local keeper policy before mutating cross-location duplicates",
            ],
            "delete_ready_now": False,
        },
        {
            "family_id": "pdbbind_archive_vs_extracted",
            "status": "blocked_pending_keeper_validation",
            "observed_layout": "archive_plus_extracted",
            "preferred_keeper_kind": "extracted_directories",
            "keeper_paths": [
                _path_entry(REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "index"),
                _path_entry(REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "NA-L"),
                _path_entry(REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "P-NA"),
                _path_entry(REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "P-P"),
            ],
            "candidate_removal_paths": [
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "pdbbind"
                    / "index (1).tar.gz"
                ),
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "pdbbind"
                    / "NA-L.tar.gz"
                ),
                _path_entry(REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "P-L.tar.gz"),
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "pdbbind"
                    / "P-NA.tar.gz"
                ),
                _path_entry(REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "P-P.tar.gz"),
            ],
            "estimated_reclaimable_bytes_hint": root_prefix_bytes.get(
                "data\\raw\\local_copies\\pdbbind", 0
            ),
            "blocking_rules": [
                "validate extracted directory completeness across every archive family",
                (
                    "confirm dedicated pdbbind_pp and pdbbind_pl keepers do not rely on "
                    "archive-only content"
                ),
                (
                    "exclude partial or manifest-backed paths before any batch is "
                    "considered delete-ready"
                ),
            ],
            "delete_ready_now": False,
        },
        {
            "family_id": "alphafold_db_multi_copy_archive",
            "status": "blocked_pending_keeper_validation",
            "observed_layout": "multi_copy_archive_only",
            "preferred_keeper_kind": "protein_data_scope_seed_archive",
            "keeper_paths": [
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "protein_data_scope_seed"
                    / "alphafold_db"
                    / "swissprot_pdb_v6.tar"
                )
            ],
            "candidate_removal_paths": [
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "alphafold_db"
                    / "swissprot_pdb_v6.tar"
                ),
                _path_entry(
                    REPO_ROOT
                    / "data"
                    / "raw"
                    / "local_copies"
                    / "alphafold_db_v2"
                    / "swissprot_pdb_v6.tar"
                ),
            ],
            "estimated_reclaimable_bytes_hint": root_prefix_bytes.get(
                "data\\raw\\local_copies\\alphafold_db", 0
            ),
            "blocking_rules": [
                "verify checksum parity between seed and local archive copies",
                "confirm local copy paths are not the only provenance anchors for downstream jobs",
                "freeze the keeper path before considering multi-copy archive deletion",
            ],
            "delete_ready_now": False,
        },
    ]
    return {
        "artifact_id": "archive_cleanup_keeper_rules_preview",
        "schema_id": "proteosphere-archive-cleanup-keeper-rules-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "blocked_row_count": len(rows),
            "families": [row["family_id"] for row in rows],
            "delete_ready_now_count": 0,
        },
        "truth_boundary": {
            "summary": (
                "This is a keeper-rule preparation surface only. It documents preferred "
                "keepers and deletion blockers for archive-heavy families without authorizing "
                "or performing archive cleanup."
            ),
            "report_only": True,
            "archive_cleanup_executed": False,
            "requires_separate_keeper_validation": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Archive Cleanup Keeper Rules Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Family count: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['family_id']}` / `{row['observed_layout']}` / "
            f"keeper `{row['preferred_keeper_kind']}` / status `{row['status']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only archive cleanup keeper-rules preview."
    )
    parser.add_argument(
        "--duplicate-cleanup-status",
        type=Path,
        default=DEFAULT_DUPLICATE_CLEANUP_STATUS,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_archive_cleanup_keeper_rules_preview(
        _read_json(args.duplicate_cleanup_status)
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
