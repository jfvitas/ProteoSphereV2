from __future__ import annotations
# ruff: noqa: E402, I001

import argparse
import gzip
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from execution.acquire.evolutionary_snapshot import (
    SOURCE_NAME,
    acquire_evolutionary_snapshot,
    build_evolutionary_snapshot_manifest,
)

try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_PACKAGE_LATEST = REPO_ROOT / "data" / "packages" / "LATEST.json"
DEFAULT_IDMAPPING_SELECTED = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "uniprot" / "idmapping_selected.tab.gz"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_RAW_RECORDS = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "sidecars"
    / "raw_registries"
    / "evolutionary_snapshot_records.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "evolutionary_snapshot_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "evolutionary_snapshot_preview.md"


def _seed_accessions(package_latest: dict[str, Any]) -> list[str]:
    accessions: list[str] = []
    for packet in package_latest.get("packets") or []:
        if not isinstance(packet, dict):
            continue
        accession = str(packet.get("accession") or "").strip()
        if accession:
            accessions.append(accession)
    return sorted(set(accessions))


def _authority_uniref_path(procurement_source_completion: dict[str, Any]) -> str | None:
    source_index = procurement_source_completion.get("source_completion_index") or {}
    uniprot = source_index.get("uniprot") or {}
    for row in uniprot.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("filename") or "").strip() != "uniref100.xml.gz":
            continue
        path = str(row.get("primary_location") or "").strip()
        if path:
            return path
    final_locations = uniprot.get("final_locations") or []
    if final_locations:
        return str((final_locations[0] or {}).get("path") or "").strip() or None
    path = str(uniprot.get("primary_live_path") or "").strip()
    return path or None


def _load_accession_rows(
    idmapping_selected_path: Path,
    accessions: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with gzip.open(idmapping_selected_path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            accession = parts[0].strip() if parts else ""
            if not accession or accession not in accessions or accession in seen:
                continue
            seen.add(accession)
            taxon_id = parts[12].strip() if len(parts) > 12 else ""
            row = {
                "accession": accession,
                "taxon_id": int(taxon_id) if taxon_id.isdigit() else None,
                "uniref_cluster_ids": [
                    value
                    for value in (
                        parts[7].strip() if len(parts) > 7 else "",
                        parts[8].strip() if len(parts) > 8 else "",
                        parts[9].strip() if len(parts) > 9 else "",
                    )
                    if value
                ],
                "source_refs": [str(idmapping_selected_path).replace("\\", "/")],
                "lazy_materialization_refs": [],
                "metadata": {
                    "uniprotkb_id": parts[1].strip() if len(parts) > 1 else None,
                    "go_terms": parts[6].strip() if len(parts) > 6 else None,
                    "uniparc_id": parts[10].strip() if len(parts) > 10 else None,
                    "local_crossref_slice": True,
                },
            }
            rows.append(row)
            if len(seen) == len(accessions):
                break
    return rows


def build_evolutionary_snapshot_preview(
    package_latest: dict[str, Any],
    procurement_source_completion: dict[str, Any],
    *,
    idmapping_selected_path: Path,
    raw_records_path: Path,
) -> dict[str, Any]:
    seed_accessions = _seed_accessions(package_latest)
    accession_rows = _load_accession_rows(idmapping_selected_path, set(seed_accessions))
    authority_uniref_path = _authority_uniref_path(procurement_source_completion)

    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(raw_records_path, {"records": accession_rows})

    manifest = build_evolutionary_snapshot_manifest(
        source_release={
            "source_name": SOURCE_NAME,
            "release_version": "post_tail_uniref_complete_2026_04_05",
            "retrieval_mode": "download",
            "source_locator": authority_uniref_path,
            "local_artifact_refs": [str(raw_records_path).replace("\\", "/")],
            "provenance": [str(idmapping_selected_path).replace("\\", "/")],
            "reproducibility_metadata": [
                "local_accession_scoped_uniref_crossref_slice",
                "seed_plus_neighbors_post_tail_completion",
            ],
        },
        corpus_snapshot_id="seed-plus-neighbors-post-tail",
        aligner_version="local_idmapping_crossref_v1",
        source_layers=("uniref100", "uniref90", "uniref50"),
        parameters={"seed_accession_count": len(seed_accessions)},
    )
    result = acquire_evolutionary_snapshot(manifest)

    snapshot_rows: list[dict[str, Any]] = []
    if result.snapshot is not None:
        for record in result.snapshot.records:
            snapshot_rows.append(record.to_dict())

    return {
        "artifact_id": "evolutionary_snapshot_preview",
        "schema_id": "proteosphere-evolutionary-snapshot-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "seed_accession_count": len(seed_accessions),
            "record_count": len(snapshot_rows),
            "records_with_uniref_cluster_ids": sum(
                1 for row in snapshot_rows if row.get("uniref_cluster_ids")
            ),
            "authority_uniref_path": authority_uniref_path,
            "acquisition_status": result.status,
        },
        "snapshot_result": result.to_dict(),
        "rows": snapshot_rows,
        "truth_boundary": {
            "summary": (
                "This evolutionary snapshot is accession-scoped and derived from local UniProt "
                "cross-reference slices after UniRef completion. It remains report-only and "
                "does not auto-promote training or release readiness."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Evolutionary Snapshot Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Acquisition status: `{payload.get('summary', {}).get('acquisition_status')}`",
        f"- Seed accession count: `{payload.get('summary', {}).get('seed_accession_count')}`",
        f"- Record count: `{payload.get('summary', {}).get('record_count')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row.get('accession')}` / `{len(row.get('uniref_cluster_ids') or [])}` cluster ids"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the post-tail evolutionary snapshot preview."
    )
    parser.add_argument("--package-latest", type=Path, default=DEFAULT_PACKAGE_LATEST)
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
    )
    parser.add_argument("--idmapping-selected", type=Path, default=DEFAULT_IDMAPPING_SELECTED)
    parser.add_argument("--raw-records", type=Path, default=DEFAULT_RAW_RECORDS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_evolutionary_snapshot_preview(
        read_json(args.package_latest),
        read_json(args.procurement_source_completion),
        idmapping_selected_path=args.idmapping_selected,
        raw_records_path=args.raw_records,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
