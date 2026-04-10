from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_CONTEXT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_alignment_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_future_structure_alignment_preview.md"
)


def build_bindingdb_future_structure_alignment_preview(
    context_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    alignment_counts: Counter[str] = Counter()
    for row in context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        source_accessions = sorted(
            {
                str(value).strip()
                for value in row.get("source_accessions") or []
                if str(value).strip()
            }
        )
        mapped_accessions = sorted(
            {
                str(value).strip()
                for value in row.get("mapped_uniprot_accessions") or []
                if str(value).strip()
            }
        )
        overlap = sorted(set(source_accessions) & set(mapped_accessions))
        if overlap:
            alignment_status = "aligned_to_source_accession"
        elif mapped_accessions:
            alignment_status = "mapped_to_different_accession"
        else:
            alignment_status = "mapping_absent"
        alignment_counts[alignment_status] += 1
        rows.append(
            {
                "structure_id": row.get("structure_id"),
                "source_accessions": source_accessions,
                "mapped_uniprot_accessions": mapped_accessions,
                "shared_accessions": overlap,
                "supporting_het_codes": row.get("supporting_het_codes") or [],
                "linked_measurement_count": row.get("linked_measurement_count"),
                "alignment_status": alignment_status,
            }
        )

    return {
        "artifact_id": "bindingdb_future_structure_alignment_preview",
        "schema_id": "proteosphere-bindingdb-future-structure-alignment-preview-2026-04-03",
        "status": "report_only_alignment_check",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "alignment_status_counts": dict(sorted(alignment_counts.items())),
            "aligned_structure_count": alignment_counts.get("aligned_to_source_accession", 0),
            "mismatched_structure_count": alignment_counts.get(
                "mapped_to_different_accession", 0
            ),
            "unmapped_structure_count": alignment_counts.get("mapping_absent", 0),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only alignment check that compares future BindingDB-linked "
                "structure candidates against their harvested UniProt mappings."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Future Structure Alignment Preview",
        "",
        f"- Structures checked: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / `{row['alignment_status']}` / "
            f"mapped `{','.join(row['mapped_uniprot_accessions']) or 'none'}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an alignment check for future BindingDB-linked structure candidates."
    )
    parser.add_argument("--context-json", type=Path, default=DEFAULT_CONTEXT_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_future_structure_alignment_preview(
        read_json(args.context_json)
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
