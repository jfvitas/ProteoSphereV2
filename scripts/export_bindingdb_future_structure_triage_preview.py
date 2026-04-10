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

DEFAULT_ALIGNMENT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_alignment_preview.json"
)
DEFAULT_CONTEXT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_triage_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_future_structure_triage_preview.md"
)


def build_bindingdb_future_structure_triage_preview(
    alignment_preview: dict[str, Any],
    context_preview: dict[str, Any],
) -> dict[str, Any]:
    context_by_structure = {
        str(row.get("structure_id") or "").strip().upper(): row
        for row in context_preview.get("rows") or []
        if isinstance(row, dict) and str(row.get("structure_id") or "").strip()
    }

    triage_counts: Counter[str] = Counter()
    rows = []
    for row in alignment_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "").strip().upper()
        if not structure_id:
            continue
        context_row = context_by_structure.get(structure_id) or {}
        alignment_status = str(row.get("alignment_status") or "").strip()
        supporting_het_codes = row.get("supporting_het_codes") or []

        if alignment_status == "aligned_to_source_accession":
            triage_status = "direct_grounding_candidate"
            recommended_action = (
                "consider_source_aligned_structure_harvest_for_structure_unit_expansion"
            )
        elif alignment_status == "mapped_to_different_accession" and supporting_het_codes:
            triage_status = "off_target_adjacent_context_only"
            recommended_action = "retain_as_adjacent_context_do_not_ground_to_source_accession"
        elif alignment_status == "mapped_to_different_accession":
            triage_status = "off_target_mapping_followup_needed"
            recommended_action = "review_mapping_before_any_grounding_claim"
        else:
            triage_status = "mapping_gap_followup_needed"
            recommended_action = "inspect_structure_mapping_and_ligand_identity_before_reuse"
        triage_counts[triage_status] += 1

        rows.append(
            {
                "structure_id": structure_id,
                "triage_status": triage_status,
                "recommended_action": recommended_action,
                "source_accessions": row.get("source_accessions") or [],
                "mapped_uniprot_accessions": row.get("mapped_uniprot_accessions") or [],
                "shared_accessions": row.get("shared_accessions") or [],
                "supporting_het_codes": supporting_het_codes,
                "linked_measurement_count": row.get("linked_measurement_count"),
                "experimental_method": context_row.get("experimental_method"),
                "resolution_angstrom": context_row.get("resolution_angstrom"),
                "title": context_row.get("title"),
            }
        )

    return {
        "artifact_id": "bindingdb_future_structure_triage_preview",
        "schema_id": "proteosphere-bindingdb-future-structure-triage-preview-2026-04-03",
        "status": "report_only_triage",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "triage_status_counts": dict(sorted(triage_counts.items())),
            "direct_grounding_candidate_count": triage_counts.get(
                "direct_grounding_candidate", 0
            ),
            "off_target_adjacent_context_only_count": triage_counts.get(
                "off_target_adjacent_context_only", 0
            ),
            "followup_needed_count": (
                triage_counts.get("off_target_mapping_followup_needed", 0)
                + triage_counts.get("mapping_gap_followup_needed", 0)
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only triage surface for future BindingDB-linked structures. "
                "It separates direct grounding candidates from off-target adjacent context."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Future Structure Triage Preview",
        "",
        f"- Structures triaged: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / `{row['triage_status']}` / "
            f"source `{','.join(row['source_accessions']) or 'none'}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a triage preview for future BindingDB-linked structure candidates."
    )
    parser.add_argument("--alignment-json", type=Path, default=DEFAULT_ALIGNMENT_JSON)
    parser.add_argument("--context-json", type=Path, default=DEFAULT_CONTEXT_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_future_structure_triage_preview(
        read_json(args.alignment_json),
        read_json(args.context_json),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
