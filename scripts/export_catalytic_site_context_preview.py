from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import read_json, write_json, write_text
DEFAULT_PROTEIN_ORIGIN_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "protein_origin_context_preview.json"
)
DEFAULT_KINETICS_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "catalytic_site_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "catalytic_site_context_preview.md"
)


def build_catalytic_site_context_preview(
    protein_origin_context_preview: dict[str, Any],
    kinetics_support_preview: dict[str, Any],
) -> dict[str, Any]:
    origin_rows = {
        str(row.get("accession") or "").strip(): row
        for row in (protein_origin_context_preview.get("rows") or [])
        if isinstance(row, dict) and str(row.get("accession") or "").strip()
    }
    rows = []
    for row in kinetics_support_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        support_sources = row.get("support_sources") or row.get("sources") or []
        if int(row.get("support_source_count") or len(support_sources) or 0) <= 0:
            continue
        origin = origin_rows.get(accession) or {}
        comment_flags = origin.get("comment_flags") or {}
        rows.append(
            {
                "accession": accession,
                "protein_name": origin.get("protein_name"),
                "kinetics_support_status": row.get("kinetics_support_status")
                or row.get("status")
                or row.get("support_status"),
                "ec_numbers": origin.get("ec_numbers") or [],
                "catalytic_activity_comment_present": bool(
                    comment_flags.get("catalytic_activity")
                ),
                "cofactor_comment_present": bool(comment_flags.get("cofactor")),
                "local_support_sources": support_sources,
                "residue_level_mcsa_harvest_status": "planned_pending_accession_specific_mapping",
                "default_ingest_status": "support-only",
                "source_urls": {
                    "uniprot": origin.get("source_url"),
                    "mcsa_candidate_query": (
                        f"https://www.ebi.ac.uk/thornton-srv/m-csa/api/entries/?uniprot_id={accession}"
                    ),
                },
            }
        )
    return {
        "artifact_id": "catalytic_site_context_preview",
        "schema_id": "proteosphere-catalytic-site-context-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accession_count": len(rows),
            "with_catalytic_comment_count": sum(
                1 for row in rows if row["catalytic_activity_comment_present"]
            ),
            "with_cofactor_comment_count": sum(
                1 for row in rows if row["cofactor_comment_present"]
            ),
        },
        "truth_boundary": {
            "summary": (
                "This surface captures enzyme/catalytic context only at the accession level. "
                "Residue-level M-CSA mapping remains planned and unvalidated."
            ),
            "report_only": True,
            "governing": False,
            "residue_level_site_claims": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Catalytic Site Context Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['accession']}` / catalytic comment "
            f"`{row['catalytic_activity_comment_present']}` / "
            f"cofactor `{row['cofactor_comment_present']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export accession-level catalytic context from local kinetics support "
            "and UniProt harvest."
        )
    )
    parser.add_argument(
        "--protein-origin-context",
        type=Path,
        default=DEFAULT_PROTEIN_ORIGIN_CONTEXT,
    )
    parser.add_argument(
        "--kinetics-support-preview",
        type=Path,
        default=DEFAULT_KINETICS_SUPPORT_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_catalytic_site_context_preview(
        read_json(args.protein_origin_context),
        read_json(args.kinetics_support_preview),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
