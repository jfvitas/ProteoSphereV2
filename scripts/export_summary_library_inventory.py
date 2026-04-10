from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_LIBRARY_PATH = ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_OUTPUT_JSON = ROOT / "artifacts" / "status" / "summary_library_inventory.json"
DEFAULT_OUTPUT_MD = ROOT / "docs" / "reports" / "summary_library_inventory.md"


def _load_library(path: Path):
    from core.library.summary_record import SummaryLibrarySchema

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("summary library payload must be a mapping")
    return SummaryLibrarySchema.from_dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_summary_library_inventory(
    library: Any,
    *,
    source_path: str,
) -> dict[str, Any]:
    join_status_counts: Counter[str] = Counter()
    storage_tier_counts: Counter[str] = Counter()

    for record in library.records:
        join_status_counts[record.join_status] += 1
        storage_tier_counts[record.context.storage_tier] += 1

    record_type_counts = {
        "protein": len(library.protein_records),
        "protein_variant": len(library.variant_records),
        "structure_unit": len(library.structure_unit_records),
        "protein_protein": len(library.pair_records),
        "protein_ligand": len(library.ligand_records),
    }

    return {
        "inventory_id": "summary-library-inventory",
        "library_id": library.library_id,
        "schema_version": library.schema_version,
        "source_manifest_id": library.source_manifest_id,
        "source_path": source_path,
        "record_count": library.record_count,
        "record_type_counts": record_type_counts,
        "join_status_counts": dict(sorted(join_status_counts.items())),
        "storage_tier_counts": dict(sorted(storage_tier_counts.items())),
    }


def render_summary_library_inventory_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Summary Library Inventory",
        "",
        f"- Library id: `{payload.get('library_id')}`",
        f"- Schema version: `{payload.get('schema_version')}`",
        f"- Source manifest id: `{payload.get('source_manifest_id')}`",
        f"- Source path: `{payload.get('source_path')}`",
        f"- Record count: `{payload.get('record_count')}`",
        "",
        "## Record Types",
    ]
    for record_type, count in (payload.get("record_type_counts") or {}).items():
        lines.append(f"- `{record_type}`: `{count}`")
    lines.extend(["", "## Join Status Counts"])
    for join_status, count in (payload.get("join_status_counts") or {}).items():
        lines.append(f"- `{join_status}`: `{count}`")
    lines.extend(["", "## Storage Tier Counts"])
    for storage_tier, count in (payload.get("storage_tier_counts") or {}).items():
        lines.append(f"- `{storage_tier}`: `{count}`")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-json", type=Path, default=DEFAULT_LIBRARY_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    library = _load_library(args.library_json)
    try:
        source_path = str(args.library_json.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        source_path = str(args.library_json)
    payload = build_summary_library_inventory(library, source_path=source_path)
    _write_json(args.output_json, payload)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        render_summary_library_inventory_markdown(payload),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
