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

DEFAULT_TRIAGE_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_triage_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_off_target_adjacent_context_profile_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "bindingdb_off_target_adjacent_context_profile_preview.md"
)


def build_bindingdb_off_target_adjacent_context_profile_preview(
    triage_preview: dict[str, Any],
) -> dict[str, Any]:
    accession_states: dict[str, dict[str, Any]] = {}
    for row in triage_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("triage_status") or "").strip() != "off_target_adjacent_context_only":
            continue
        source_accessions = [
            str(value).strip()
            for value in row.get("source_accessions") or []
            if str(value).strip()
        ]
        if not source_accessions:
            continue
        mapped_accessions = [
            str(value).strip()
            for value in row.get("mapped_uniprot_accessions") or []
            if str(value).strip()
        ]
        structure_id = str(row.get("structure_id") or "").strip().upper()
        for accession in source_accessions:
            state = accession_states.setdefault(
                accession,
                {
                    "structure_ids": [],
                    "mapped_accessions": Counter(),
                    "het_codes": Counter(),
                    "linked_measurement_count": 0,
                    "experimental_methods": Counter(),
                    "titles": [],
                },
            )
            if structure_id and structure_id not in state["structure_ids"]:
                state["structure_ids"].append(structure_id)
            for mapped_accession in mapped_accessions:
                state["mapped_accessions"][mapped_accession] += 1
            for het_code in row.get("supporting_het_codes") or []:
                het_text = str(het_code).strip()
                if het_text:
                    state["het_codes"][het_text] += 1
            state["linked_measurement_count"] += int(row.get("linked_measurement_count") or 0)
            method = str(row.get("experimental_method") or "").strip()
            if method:
                state["experimental_methods"][method] += 1
            title = str(row.get("title") or "").strip()
            if title and title not in state["titles"]:
                state["titles"].append(title)

    rows = []
    for accession, state in sorted(accession_states.items()):
        rows.append(
            {
                "source_accession": accession,
                "off_target_structure_count": len(state["structure_ids"]),
                "off_target_structure_ids": state["structure_ids"][:20],
                "mapped_target_accessions": [
                    accession_id
                    for accession_id, _count in state["mapped_accessions"].most_common(10)
                ],
                "mapped_target_accession_counts": dict(sorted(state["mapped_accessions"].items())),
                "supporting_het_codes": [
                    het_code for het_code, _count in state["het_codes"].most_common(10)
                ],
                "linked_measurement_count": state["linked_measurement_count"],
                "experimental_method_counts": dict(sorted(state["experimental_methods"].items())),
                "title_samples": state["titles"][:8],
            }
        )

    return {
        "artifact_id": "bindingdb_off_target_adjacent_context_profile_preview",
        "schema_id": (
            "proteosphere-bindingdb-off-target-adjacent-context-profile-preview-2026-04-03"
        ),
        "status": "report_only_adjacent_context_summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "source_accession_count": len(rows),
            "off_target_structure_count": sum(
                row.get("off_target_structure_count", 0) for row in rows
            ),
            "unique_mapped_target_accession_count": len(
                {
                    mapped_accession
                    for row in rows
                    for mapped_accession in row.get("mapped_target_accessions") or []
                }
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only source-accession summary of off-target adjacent "
                "structure context discovered through BindingDB-linked future structures."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Off-Target Adjacent Context Profile Preview",
        "",
        f"- Source accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['source_accession']}` / structures `{row['off_target_structure_count']}` / "
            f"mapped targets `{','.join(row['mapped_target_accessions']) or 'none'}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a source-accession profile for off-target adjacent structure context."
    )
    parser.add_argument("--triage-json", type=Path, default=DEFAULT_TRIAGE_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_off_target_adjacent_context_profile_preview(
        read_json(args.triage_json)
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
