from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        fetch_json,
        first,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import (
        fetch_json,
        first,
        read_json,
        write_json,
        write_text,
    )

DEFAULT_REGISTRY_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_registry_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_future_structure_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "bindingdb_future_structure_context_preview.md"
)


def _parse_structure_row(row: dict[str, Any]) -> dict[str, Any]:
    structure_id = str(row.get("structure_id") or "").strip().upper()
    structure_id_lower = structure_id.lower()
    rcsb = fetch_json(f"https://data.rcsb.org/rest/v1/core/entry/{structure_id}")
    pdbe = fetch_json(
        f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{structure_id_lower}"
    )
    sifts = fetch_json(
        f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{structure_id_lower}"
    )

    pdbe_row = first(pdbe.get(structure_id_lower) or [])
    sifts_root = sifts.get(structure_id_lower) or {}
    uniprot_map = sifts_root.get("UniProt") or {}
    mapped_accessions = sorted(uniprot_map.keys())
    entry_info = rcsb.get("rcsb_entry_info") or {}
    accession_info = rcsb.get("rcsb_accession_info") or {}
    exptl = first(rcsb.get("exptl") or [])
    citation = first(rcsb.get("citation") or [])

    return {
        "structure_id": structure_id,
        "source_accessions": row.get("source_accessions") or [],
        "supporting_het_codes": row.get("supporting_het_codes") or [],
        "supporting_monomer_count": row.get("supporting_monomer_count"),
        "linked_measurement_count": row.get("linked_measurement_count"),
        "mapped_uniprot_accessions": mapped_accessions,
        "title": ((rcsb.get("struct") or {}).get("title") or (pdbe_row or {}).get("title")),
        "experimental_method": (exptl or {}).get("method")
        or (pdbe_row or {}).get("experimental_method"),
        "resolution_angstrom": first(entry_info.get("resolution_combined") or []),
        "deposit_date": accession_info.get("deposit_date")
        or (pdbe_row or {}).get("deposition_date"),
        "release_date": accession_info.get("initial_release_date")
        or (pdbe_row or {}).get("release_date"),
        "citation_pubmed_id": (citation or {}).get("pdbx_database_id_pub_med"),
        "polymer_entity_count": entry_info.get("polymer_entity_count"),
        "nonpolymer_bound_components": entry_info.get("nonpolymer_bound_components") or [],
        "source_api_statuses": {
            "rcsb_core_entry": "ok",
            "pdbe_entry_summary": "ok",
            "sifts_uniprot_mapping": "ok",
        },
    }


def build_bindingdb_future_structure_context_preview(
    registry_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        _parse_structure_row(row)
        for row in registry_preview.get("rows") or []
        if isinstance(row, dict)
    ]
    return {
        "artifact_id": "bindingdb_future_structure_context_preview",
        "schema_id": "proteosphere-bindingdb-future-structure-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "harvested_future_structure_count": len(rows),
            "structures_with_resolution": sum(
                1 for row in rows if row.get("resolution_angstrom") is not None
            ),
            "structures_with_bound_components": sum(
                1 for row in rows if row.get("nonpolymer_bound_components")
            ),
            "mapped_uniprot_accession_count": len(
                {
                    accession
                    for row in rows
                    for accession in row.get("mapped_uniprot_accessions") or []
                }
            ),
            "structure_ids": [row["structure_id"] for row in rows],
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only structured context harvest for future BindingDB-linked "
                "PDB candidates. It does not materialize new structure-unit rows."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Future Structure Context Preview",
        "",
        f"- Harvested structures: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['structure_id']}` / `{row['experimental_method']}` / "
            f"mapped accessions `{len(row['mapped_uniprot_accessions'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Harvest structured context for future BindingDB-linked structure candidates."
    )
    parser.add_argument(
        "--registry-json",
        type=Path,
        default=DEFAULT_REGISTRY_JSON,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_future_structure_context_preview(read_json(args.registry_json))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
