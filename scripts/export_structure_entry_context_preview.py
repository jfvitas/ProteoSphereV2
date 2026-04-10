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
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import (
        fetch_json,
        first,
        read_json,
        write_json,
        write_text,
    )
DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "pdb_enrichment_scrape_registry_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_entry_context_preview.md"
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
    mapped_chain_ids = sorted(
        {
            str(mapping.get("chain_id") or "").strip()
            for accession_payload in uniprot_map.values()
            if isinstance(accession_payload, dict)
            for mapping in accession_payload.get("mappings") or []
            if isinstance(mapping, dict) and str(mapping.get("chain_id") or "").strip()
        }
    )
    entry_info = rcsb.get("rcsb_entry_info") or {}
    accession_info = rcsb.get("rcsb_accession_info") or {}
    exptl = first(rcsb.get("exptl") or [])
    citation = first(rcsb.get("citation") or [])
    assemblies = (pdbe_row or {}).get("assemblies") or []
    preferred_assembly = first(assemblies) or {}
    return {
        "structure_id": structure_id,
        "seed_accessions": row.get("seed_accessions") or [],
        "mapped_uniprot_accessions": mapped_accessions,
        "mapped_chain_ids": mapped_chain_ids,
        "title": ((rcsb.get("struct") or {}).get("title") or (pdbe_row or {}).get("title")),
        "experimental_method": (exptl or {}).get("method")
        or (pdbe_row or {}).get("experimental_method"),
        "resolution_angstrom": first(entry_info.get("resolution_combined") or []),
        "deposit_date": accession_info.get("deposit_date")
        or (pdbe_row or {}).get("deposition_date"),
        "release_date": accession_info.get("initial_release_date")
        or (pdbe_row or {}).get("release_date"),
        "revision_date": accession_info.get("revision_date")
        or (pdbe_row or {}).get("revision_date"),
        "assembly_count": entry_info.get("assembly_count"),
        "preferred_assembly_id": preferred_assembly.get("assembly_id"),
        "preferred_assembly_name": preferred_assembly.get("name"),
        "polymer_composition": entry_info.get("polymer_composition"),
        "nonpolymer_bound_components": entry_info.get("nonpolymer_bound_components") or [],
        "citation_pubmed_id": (citation or {}).get("pdbx_database_id_pub_med"),
        "source_api_statuses": {
            "rcsb_core_entry": "ok",
            "pdbe_entry_summary": "ok",
            "sifts_uniprot_mapping": "ok",
        },
        "source_urls": {
            "rcsb_core_entry": f"https://data.rcsb.org/rest/v1/core/entry/{structure_id}",
            "pdbe_entry_summary": f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/summary/{structure_id_lower}",
            "sifts_uniprot_mapping": f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{structure_id_lower}",
        },
    }


def build_structure_entry_context_preview(
    pdb_enrichment_scrape_registry_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        _parse_structure_row(row)
        for row in (pdb_enrichment_scrape_registry_preview.get("rows") or [])
        if isinstance(row, dict)
    ]
    return {
        "artifact_id": "structure_entry_context_preview",
        "schema_id": "proteosphere-structure-entry-context-preview-2026-04-02",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structure_ids": [row["structure_id"] for row in rows],
            "harvested_structure_count": len(rows),
            "mapped_uniprot_accession_count": sum(
                len(row["mapped_uniprot_accessions"]) for row in rows
            ),
            "bound_component_count": sum(
                len(row["nonpolymer_bound_components"]) for row in rows
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a structured, provenance-tagged structure context harvest. It is "
                "report-only and does not alter curated structure families or governance."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Entry Context Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Harvested structures: `{payload['summary']['harvested_structure_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['structure_id']}` / `{row['experimental_method']}` / "
            f"mapped accessions `{len(row['mapped_uniprot_accessions'])}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Harvest structured structure-entry context for current seed PDB IDs."
    )
    parser.add_argument(
        "--pdb-enrichment-scrape-registry",
        type=Path,
        default=DEFAULT_PDB_ENRICHMENT_SCRAPE_REGISTRY,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_entry_context_preview(
        read_json(args.pdb_enrichment_scrape_registry),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
