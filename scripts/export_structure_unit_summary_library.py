from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_INPUT = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "structure_unit_summary_library.md"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _render_markdown(library) -> str:
    example_records = library.structure_unit_records[:10]
    structure_ids = ", ".join(record.structure_id for record in example_records) or "none"
    protein_refs = ", ".join(record.protein_ref for record in example_records) or "none"
    return (
        "# Structure Unit Summary Library\n\n"
        f"- Library id: `{library.library_id}`\n"
        f"- Record count: `{library.record_count}`\n"
        f"- Example structure ids: `{structure_ids}`\n"
        f"- Example protein refs: `{protein_refs}`\n"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    from core.library.summary_record import SummaryLibrarySchema
    from execution.library.structure_unit_materializer import (
        build_structure_unit_summary_library,
    )

    args = parse_args(argv)
    protein_library = SummaryLibrarySchema.from_dict(
        json.loads(args.input.read_text(encoding="utf-8"))
    )
    structure_library = build_structure_unit_summary_library(
        protein_library,
        source_manifest_id=protein_library.source_manifest_id,
    )
    _write_json(args.output_json, structure_library.to_dict())
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(_render_markdown(structure_library), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
