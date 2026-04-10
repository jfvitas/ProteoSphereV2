from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_GROUNDING_CANDIDATE_PREVIEW = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_structure_grounding_candidate_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_future_structure_registry_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "bindingdb_future_structure_registry_preview.md"
)


def build_bindingdb_future_structure_registry_preview(
    grounding_candidate_preview: dict[str, Any],
    *,
    max_structures: int = 8,
) -> dict[str, Any]:
    structure_states: dict[str, dict[str, Any]] = {}
    for row in grounding_candidate_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        monomer_by_structure: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for monomer in row.get("top_candidate_monomers") or []:
            if not isinstance(monomer, dict):
                continue
            for structure_id in monomer.get("future_structure_ids") or []:
                structure_text = str(structure_id or "").strip().upper()
                if not structure_text:
                    continue
                monomer_by_structure[structure_text].append(monomer)

        for structure_id in row.get("top_future_structure_ids") or []:
            structure_text = str(structure_id or "").strip().upper()
            if not structure_text:
                continue
            state = structure_states.setdefault(
                structure_text,
                {
                    "structure_id": structure_text,
                    "source_accessions": set(),
                    "supporting_monomer_ids": set(),
                    "supporting_het_codes": set(),
                    "linked_measurement_count": 0,
                    "candidate_monomer_refs": [],
                },
            )
            state["source_accessions"].add(accession)
            for monomer in monomer_by_structure.get(structure_text, []):
                monomer_id = str(monomer.get("bindingdb_monomer_id") or "").strip()
                if monomer_id:
                    state["supporting_monomer_ids"].add(monomer_id)
                het_code = str(monomer.get("het_pdb") or "").strip()
                if het_code:
                    state["supporting_het_codes"].add(het_code)
                state["linked_measurement_count"] += int(
                    monomer.get("linked_measurement_count") or 0
                )
                state["candidate_monomer_refs"].append(
                    {
                        "bindingdb_monomer_id": monomer_id or None,
                        "display_name": monomer.get("display_name"),
                        "het_pdb": het_code or None,
                        "linked_measurement_count": int(
                            monomer.get("linked_measurement_count") or 0
                        ),
                        "source_accession": accession,
                    }
                )

    rows = sorted(
        structure_states.values(),
        key=lambda item: (
            len(item["source_accessions"]),
            item["linked_measurement_count"],
            len(item["supporting_het_codes"]),
            item["structure_id"],
        ),
        reverse=True,
    )[:max_structures]

    compact_rows = []
    for row in rows:
        compact_rows.append(
            {
                "structure_id": row["structure_id"],
                "source_accessions": sorted(row["source_accessions"]),
                "supporting_monomer_count": len(row["supporting_monomer_ids"]),
                "supporting_het_codes": sorted(row["supporting_het_codes"]),
                "linked_measurement_count": row["linked_measurement_count"],
                "candidate_monomer_refs": row["candidate_monomer_refs"][:6],
            }
        )

    return {
        "artifact_id": "bindingdb_future_structure_registry_preview",
        "schema_id": "proteosphere-bindingdb-future-structure-registry-preview-2026-04-03",
        "status": "report_only_live_candidate_registry",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(compact_rows),
        "rows": compact_rows,
        "summary": {
            "registered_future_structure_count": len(compact_rows),
            "source_accession_count": len(
                {
                    accession
                    for row in compact_rows
                    for accession in row.get("source_accessions") or []
                }
            ),
            "structures_with_supporting_het_codes": sum(
                1 for row in compact_rows if row.get("supporting_het_codes")
            ),
            "structure_ids": [row["structure_id"] for row in compact_rows],
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only registry of the strongest future BindingDB-linked "
                "PDB candidate structures. It does not widen the curated structure library."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Future Structure Registry Preview",
        "",
        f"- Registered structures: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / accessions `{len(row['source_accessions'])}` / "
            f"measurements `{row['linked_measurement_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a report-only registry of future BindingDB-linked structure candidates."
    )
    parser.add_argument(
        "--grounding-candidate-preview",
        type=Path,
        default=DEFAULT_GROUNDING_CANDIDATE_PREVIEW,
    )
    parser.add_argument("--max-structures", type=int, default=8)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_future_structure_registry_preview(
        read_json(args.grounding_candidate_preview),
        max_structures=args.max_structures,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
