from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.affinity_interaction_preview_support import PDBBIND_FILE_MAP, iter_pdbbind_rows
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import PDBBIND_FILE_MAP, iter_pdbbind_rows

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "index"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "pdbbind_registry_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdbbind_registry_preview.md"


def build_pdbbind_registry_preview(index_dir: Path) -> dict[str, Any]:
    rows = iter_pdbbind_rows(index_dir)
    class_counts = Counter(str(row.get("complex_type") or "unknown") for row in rows)
    measurement_counts = Counter(str(row.get("measurement_type") or "unknown") for row in rows)
    exact_relation_count = sum(1 for row in rows if str(row.get("relation") or "") == "=")
    normalized_molar_count = sum(1 for row in rows if row.get("value_molar_normalized") is not None)
    files_present = {
        short_type: (index_dir / filename).exists()
        for short_type, filename in PDBBIND_FILE_MAP.items()
    }

    class_samples: list[dict[str, Any]] = []
    seen_classes: set[str] = set()
    for row in rows:
        complex_type = str(row.get("complex_type") or "unknown")
        if complex_type in seen_classes:
            continue
        seen_classes.add(complex_type)
        class_samples.append(
            {
                "complex_type": complex_type,
                "pdb_id": row.get("pdb_id"),
                "raw_binding_string": row.get("raw_binding_string"),
                "measurement_type": row.get("measurement_type"),
                "relation": row.get("relation"),
                "source_comment": row.get("source_comment"),
                "parenthetical_tokens": row.get("parenthetical_tokens"),
                "source_record_id": row.get("source_record_id"),
            }
        )

    return {
        "artifact_id": "pdbbind_registry_preview",
        "schema_id": "proteosphere-pdbbind-registry-preview-2026-04-05",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "index_dir": str(index_dir).replace("\\", "/"),
            "row_count": len(rows),
            "class_count": len(class_counts),
            "per_class_counts": dict(sorted(class_counts.items())),
            "measurement_type_counts": dict(sorted(measurement_counts.items())),
            "exact_relation_count": exact_relation_count,
            "normalized_molar_count": normalized_molar_count,
            "files_present": files_present,
            "local_only_acquisition": True,
        },
        "class_samples": class_samples,
        "truth_boundary": {
            "summary": (
                "This PDBbind registry is built from local index files already present on disk. "
                "It preserves class-specific row families and raw binding strings, but remains "
                "local/manual and non-governing."
            ),
            "report_only": True,
            "non_governing": True,
            "local_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# PDBbind Registry Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Row count: `{summary.get('row_count')}`",
        f"- Exact-relation rows: `{summary.get('exact_relation_count')}`",
        f"- Normalized molar rows: `{summary.get('normalized_molar_count')}`",
        "",
        "## Class Samples",
        "",
    ]
    for row in payload.get("class_samples") or []:
        lines.append(
            f"- `{row['complex_type']}` / `{row['pdb_id']}` / `{row['raw_binding_string']}` "
            f"/ `{row['source_record_id']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the local PDBbind registry preview.")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdbbind_registry_preview(args.index_dir)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
