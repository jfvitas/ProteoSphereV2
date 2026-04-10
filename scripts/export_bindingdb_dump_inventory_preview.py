from __future__ import annotations

import argparse
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import bindingdb_zip_inventory
    from scripts.web_enrichment_preview_support import write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import bindingdb_zip_inventory
    from web_enrichment_preview_support import write_json, write_text

DEFAULT_BINDINGDB_ZIP = (
    REPO_ROOT / "data" / "raw" / "local_copies" / "bindingdb" / "BDB-mySQL_All_202603_dmp.zip"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_dump_inventory_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "bindingdb_dump_inventory_preview.md"

CREATE_TABLE_RE = re.compile(r"CREATE TABLE\s+`?([A-Za-z0-9_]+)`?", re.IGNORECASE)


def _sample_create_tables(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        dump_member = next(
            (
                entry
                for entry in archive.infolist()
                if str(entry.filename).lower().endswith(".dmp")
            ),
            None,
        )
        if dump_member is None:
            return []
        with archive.open(dump_member, "r") as handle:
            sample_text = handle.read(2_000_000).decode("latin-1", errors="replace")
    table_names = []
    seen: set[str] = set()
    for match in CREATE_TABLE_RE.finditer(sample_text):
        table_name = str(match.group(1) or "").strip()
        if not table_name or table_name in seen:
            continue
        seen.add(table_name)
        table_names.append(table_name)
        if len(table_names) >= 12:
            break
    return table_names


def build_bindingdb_dump_inventory_preview(bindingdb_zip_path: Path) -> dict[str, Any]:
    inventory = bindingdb_zip_inventory(bindingdb_zip_path)
    sampled_tables = _sample_create_tables(bindingdb_zip_path)
    dump_entry = next(
        (
            entry
            for entry in inventory.get("entries") or []
            if str(entry.get("full_name") or "").lower().endswith(".dmp")
        ),
        {},
    )
    return {
        "artifact_id": "bindingdb_dump_inventory_preview",
        "schema_id": "proteosphere-bindingdb-dump-inventory-preview-2026-04-03",
        "status": "report_only_local_inventory",
        "generated_at": datetime.now(UTC).isoformat(),
        "bindingdb_zip_path": inventory.get("zip_path"),
        "entry_count": inventory.get("entry_count"),
        "has_mysql_dump": inventory.get("has_mysql_dump"),
        "dump_entry": dump_entry,
        "sampled_create_tables": sampled_tables,
        "expected_measurement_fields": [
            "Ki",
            "Kd",
            "IC50",
            "EC50",
            "kon",
            "koff",
            "ΔG",
            "ΔH",
            "-TΔS",
            "pH",
            "temperature",
            "PMID",
            "PDB",
            "UniProt",
        ],
        "summary": {
            "dump_entry_name": dump_entry.get("full_name"),
            "sampled_table_count": len(sampled_tables),
            "uncompressed_dump_size_bytes": dump_entry.get("uncompressed_size"),
        },
        "truth_boundary": {
            "summary": (
                "This is an inventory-only BindingDB dump preview. It does not "
                "materialize dump rows yet and does not affect governing ligand state."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Dump Inventory Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Has MySQL dump: `{payload['has_mysql_dump']}`",
        f"- Sampled table count: `{payload['summary']['sampled_table_count']}`",
        "",
    ]
    for table_name in payload.get("sampled_create_tables") or []:
        lines.append(f"- `{table_name}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BindingDB dump inventory preview.")
    parser.add_argument("--bindingdb-zip", type=Path, default=DEFAULT_BINDINGDB_ZIP)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_dump_inventory_preview(args.bindingdb_zip)
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
