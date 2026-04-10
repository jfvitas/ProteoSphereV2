from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import read_json, write_json, write_text
DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_context_scrape_registry_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_context_scrape_registry_preview.md"
)


def _source_url(namespace: str, ref: str) -> str | None:
    if namespace == "PDB_CCD":
        return f"https://www.ebi.ac.uk/pdbe/entry/pdb/{ref.lower()}"
    if namespace == "CHEMBL":
        return f"https://www.ebi.ac.uk/chembl/compound_report_card/{ref}/"
    return None


def build_ligand_context_scrape_registry_preview(
    ligand_row_materialization_preview: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ligand_row_materialization_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession:
            grouped[accession].append(row)
    rows = []
    for accession, accession_rows in sorted(grouped.items()):
        ligand_refs = sorted(
            {
                str(
                    row.get("ligand_ref")
                    or row.get("ligand_id")
                    or row.get("source_id")
                    or ""
                ).strip()
                for row in accession_rows
            }
            - {""}
        )
        namespaces = sorted(
            {
                str(row.get("ligand_namespace") or row.get("namespace") or "").strip()
                for row in accession_rows
                if str(row.get("ligand_namespace") or row.get("namespace") or "").strip()
            }
        )
        rows.append(
            {
                "accession": accession,
                "ligand_refs": ligand_refs,
                "ligand_ref_count": len(ligand_refs),
                "namespaces": namespaces,
                "candidate_only": all(
                    "candidate"
                    in str(row.get("readiness") or row.get("status") or "").lower()
                    for row in accession_rows
                ),
                "default_ingest_status": "candidate_only_non_governing",
                "source_urls": [
                    url
                    for namespace in namespaces
                    for ligand_ref in ligand_refs
                    for url in [_source_url(namespace, ligand_ref)]
                    if url
                ],
            }
        )
    return {
        "artifact_id": "ligand_context_scrape_registry_preview",
        "schema_id": "proteosphere-ligand-context-scrape-registry-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_ligand_refs": [row["accession"] for row in rows],
            "candidate_only_accession_count": sum(1 for row in rows if row["candidate_only"]),
        },
        "truth_boundary": {
            "summary": (
                "This is a scrape registry for ligand-context enrichment only. It does not "
                "change grounded ligand identity materialization or governance."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ligand Context Scrape Registry Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Accessions with ligand refs: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['accession']}` / refs `{row['ligand_ref_count']}` / "
            f"candidate-only `{row['candidate_only']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a registry of ligand-context scrape targets from current ligand rows."
    )
    parser.add_argument(
        "--ligand-row-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_context_scrape_registry_preview(
        read_json(args.ligand_row_materialization_preview),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
