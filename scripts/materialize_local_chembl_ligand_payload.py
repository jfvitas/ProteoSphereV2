from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_chembl_ligand_payload import (  # noqa: E402
    DEFAULT_CHEMBL_PATH,
    build_local_chembl_ligand_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "p00387_local_chembl_ligand_payload.json"
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "p00387_local_chembl_ligand_payload.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    lines = [
        "# P00387 Local ChEMBL Ligand Payload",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Packet source ref: `{payload.get('packet_source_ref')}`",
        f"- Source DB: `{payload.get('source_db_path')}`",
        f"- Target: `{summary.get('target_chembl_id')}` / `{summary.get('target_pref_name')}`",
        f"- Total activities: `{summary.get('activity_count_total')}`",
        f"- Rows emitted: `{summary.get('rows_emitted')}`",
        f"- Distinct ligands in payload: `{summary.get('distinct_ligand_count_in_payload')}`",
        f"- Distinct assays in payload: `{summary.get('distinct_assay_count_in_payload')}`",
        "",
        "## Top Rows",
        "",
        "| Ligand | Name | Assay | Type | Value | Units | pChEMBL | Smiles |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows[:10]:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            + f"`{row.get('ligand_chembl_id')}` | "
            + f"{row.get('ligand_pref_name') or 'n/a'} | "
            + f"`{row.get('assay_id')}` | "
            + f"`{row.get('standard_type')}` | "
            + f"`{row.get('standard_value')}` | "
            + f"`{row.get('standard_units') or 'n/a'}` | "
            + f"`{row.get('pchembl_value')}` | "
            + f"`{(row.get('canonical_smiles') or '')[:48]}` |"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            *[
                f"- {note}"
                for note in ((payload.get("truth_boundary") or {}).get("notes") or [])
            ],
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize a fresh-run-only local ChEMBL ligand payload."
    )
    parser.add_argument("--accession", default="P00387")
    parser.add_argument("--chembl", type=Path, default=DEFAULT_CHEMBL_PATH)
    parser.add_argument("--max-rows", type=int, default=25)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_chembl_ligand_payload(
        accession=args.accession,
        chembl_path=args.chembl,
        max_rows=args.max_rows,
        output_path=args.output,
    )
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local ChEMBL ligand payload materialized: "
            f"status={payload['status']} rows={payload['summary']['rows_emitted']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
