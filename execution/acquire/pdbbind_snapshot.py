from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.affinity_interaction_preview_support import PDBBIND_FILE_MAP, iter_pdbbind_rows

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "index"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "pdbbind_local_snapshot_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdbbind_local_snapshot_preview.md"


def build_pdbbind_local_snapshot_preview(index_dir: Path) -> dict[str, Any]:
    rows = iter_pdbbind_rows(index_dir)
    per_class_counts = Counter(str(row.get("complex_type") or "unknown") for row in rows)
    sample_rows: list[dict[str, Any]] = []
    sample_counts: dict[str, int] = {}
    for row in rows:
        complex_type = str(row.get("complex_type") or "unknown")
        if sample_counts.get(complex_type, 0) >= 2:
            continue
        sample_counts[complex_type] = sample_counts.get(complex_type, 0) + 1
        sample_rows.append(
            {
                "complex_type": complex_type,
                "pdb_id": row.get("pdb_id"),
                "raw_binding_string": row.get("raw_binding_string"),
                "measurement_type": row.get("measurement_type"),
                "source_comment": row.get("source_comment"),
                "parenthetical_tokens": row.get("parenthetical_tokens"),
            }
        )
    files_present = {
        short_type: (index_dir / filename).exists()
        for short_type, filename in PDBBIND_FILE_MAP.items()
    }
    return {
        "artifact_id": "pdbbind_local_snapshot_preview",
        "schema_id": "proteosphere-pdbbind-local-snapshot-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "index_dir": str(index_dir).replace("\\", "/"),
            "row_count": len(rows),
            "per_class_counts": dict(per_class_counts),
            "files_present": files_present,
        },
        "sample_rows": sample_rows,
        "truth_boundary": {
            "summary": (
                "This is a local-only PDBbind snapshot over manually acquired index files. It "
                "preserves raw binding strings and class-specific structure roles without "
                "changing governance state."
            ),
            "report_only": True,
            "non_governing": True,
            "local_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PDBbind Local Snapshot Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Row count: `{payload.get('summary', {}).get('row_count')}`",
        "",
    ]
    for row in payload.get("sample_rows") or []:
        lines.append(
            f"- `{row['complex_type']}` / `{row['pdb_id']}` / `{row['raw_binding_string']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a local PDBbind snapshot preview.")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdbbind_local_snapshot_preview(args.index_dir)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
