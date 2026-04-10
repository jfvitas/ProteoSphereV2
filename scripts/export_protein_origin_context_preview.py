from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        first,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        first,
        read_json,
        write_json,
        write_text,
    )
DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "protein_origin_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "protein_origin_context_preview.md"
)


def _gene_name(entry: dict[str, Any]) -> str | None:
    genes = entry.get("genes") or []
    first_gene = first(genes) or {}
    gene_name = (first_gene.get("geneName") or {}).get("value")
    return str(gene_name).strip() if gene_name else None


def _protein_name(entry: dict[str, Any]) -> str | None:
    protein_description = entry.get("proteinDescription") or {}
    recommended = protein_description.get("recommendedName") or {}
    full_name = (recommended.get("fullName") or {}).get("value")
    return str(full_name).strip() if full_name else None


def _ec_numbers(entry: dict[str, Any]) -> list[str]:
    protein_description = entry.get("proteinDescription") or {}
    recommended = protein_description.get("recommendedName") or {}
    ec_rows = recommended.get("ecNumbers") or []
    return [
        str(item.get("value") or "").strip()
        for item in ec_rows
        if isinstance(item, dict) and str(item.get("value") or "").strip()
    ]


def _comment_types(entry: dict[str, Any]) -> set[str]:
    return {
        str(comment.get("commentType") or "").strip()
        for comment in (entry.get("comments") or [])
        if isinstance(comment, dict)
    }


def _protein_existence(entry: dict[str, Any]) -> str | None:
    value = entry.get("proteinExistence")
    if isinstance(value, dict):
        resolved = value.get("value")
        return str(resolved).strip() if resolved else None
    if isinstance(value, str):
        return value.strip() or None
    return None


def build_protein_origin_context_preview(
    training_set_eligibility_matrix: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for row in accession_rows(training_set_eligibility_matrix):
        accession = row["accession"]
        source_url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
        try:
            entry = fetch_json(source_url)
            comment_types = _comment_types(entry)
            organism = entry.get("organism") or {}
            lineage = organism.get("lineage") or []
            rows.append(
                {
                    "accession": accession,
                    "fetch_status": "ok",
                    "entry_type": entry.get("entryType"),
                    "reviewed": "reviewed" in str(entry.get("entryType") or "").lower(),
                    "annotation_score": entry.get("annotationScore"),
                    "protein_name": _protein_name(entry),
                    "primary_gene_name": _gene_name(entry),
                    "organism_scientific_name": organism.get("scientificName"),
                    "organism_common_name": organism.get("commonName"),
                    "taxon_id": organism.get("taxonId"),
                    "lineage_depth": len(lineage),
                    "lineage_terminal": lineage[-1] if lineage else None,
                    "protein_existence": _protein_existence(entry),
                    "ec_numbers": _ec_numbers(entry),
                    "comment_flags": {
                        "catalytic_activity": "CATALYTIC ACTIVITY" in comment_types,
                        "cofactor": "COFACTOR" in comment_types,
                        "disease": "DISEASE" in comment_types,
                        "subcellular_location": "SUBCELLULAR LOCATION" in comment_types,
                    },
                    "source_url": source_url,
                }
            )
        except Exception as exc:  # pragma: no cover - network safety fallback
            rows.append(
                {
                    "accession": accession,
                    "fetch_status": "error",
                    "error": str(exc),
                    "source_url": source_url,
                }
            )
    return {
        "artifact_id": "protein_origin_context_preview",
        "schema_id": "proteosphere-protein-origin-context-preview-2026-04-02",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "harvested_accession_count": sum(1 for row in rows if row["fetch_status"] == "ok"),
            "error_count": sum(1 for row in rows if row["fetch_status"] != "ok"),
            "reviewed_accession_count": sum(1 for row in rows if row.get("reviewed")),
        },
        "truth_boundary": {
            "summary": (
                "This is a structured UniProt-origin context harvest. It is report-only, "
                "non-governing, and does not overwrite curated protein truth."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Protein Origin Context Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Harvested accessions: `{payload['summary']['harvested_accession_count']}`",
        "",
    ]
    for row in payload["rows"][:10]:
        lines.append(
            f"- `{row['accession']}` / `{row['fetch_status']}` / "
            f"`{row.get('organism_scientific_name')}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Harvest structured UniProt origin context for current library accessions."
    )
    parser.add_argument(
        "--training-set-eligibility-matrix",
        type=Path,
        default=DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_protein_origin_context_preview(
        read_json(args.training_set_eligibility_matrix),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
