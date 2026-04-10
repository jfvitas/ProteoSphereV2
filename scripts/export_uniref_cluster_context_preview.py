from __future__ import annotations

import argparse
import gzip
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        read_json,
        write_json,
        write_text,
    )

DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_PROCUREMENT_GATE = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_PROCUREMENT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_IDMAPPING_SELECTED = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "uniprot" / "idmapping_selected.tab.gz"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "uniref_cluster_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "uniref_cluster_context_preview.md"

UNIREF_DATABASES = ("UniRef100", "UniRef90", "UniRef50")


def _cluster_id(entry: dict[str, Any], database_name: str) -> str | None:
    for xref in entry.get("uniProtKBCrossReferences") or []:
        if not isinstance(xref, dict):
            continue
        if str(xref.get("database") or "").strip() != database_name:
            continue
        cluster_id = str(xref.get("id") or "").strip()
        if cluster_id:
            return cluster_id
    return None


def _representative_candidate(cluster_id: str | None) -> str | None:
    text = str(cluster_id or "").strip()
    if "_" not in text:
        return None
    return text.split("_", 1)[1] or None


def _load_local_crossrefs(
    idmapping_selected_path: Path,
    accessions: set[str],
) -> dict[str, dict[str, Any]]:
    if not idmapping_selected_path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(idmapping_selected_path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            accession = parts[0].strip() if parts else ""
            if not accession or accession not in accessions or accession in rows:
                continue
            rows[accession] = {
                "uniref100_cluster_id": parts[7].strip() if len(parts) > 7 else None,
                "uniref90_cluster_id": parts[8].strip() if len(parts) > 8 else None,
                "uniref50_cluster_id": parts[9].strip() if len(parts) > 9 else None,
                "taxon_id": parts[12].strip() if len(parts) > 12 else None,
                "source_url": str(idmapping_selected_path).replace("\\", "/"),
                "materialization_basis": "local_idmapping_selected",
            }
            if len(rows) == len(accessions):
                break
    return rows


def build_uniref_cluster_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    procurement_tail_freeze_gate_preview: dict[str, Any],
    procurement_source_completion_preview: dict[str, Any],
    *,
    idmapping_selected_path: Path,
) -> dict[str, Any]:
    gate_status = str(procurement_tail_freeze_gate_preview.get("gate_status") or "").strip()
    uniprot_complete = bool(
        procurement_source_completion_preview.get("uniprot_completion_ready")
    )
    accessions = {
        row["accession"] for row in accession_rows(training_set_eligibility_matrix_preview)
    }
    local_crossrefs = (
        _load_local_crossrefs(idmapping_selected_path, accessions) if uniprot_complete else {}
    )
    rows = []
    for training_row in accession_rows(training_set_eligibility_matrix_preview):
        accession = training_row["accession"]
        local_entry = local_crossrefs.get(accession)
        if local_entry:
            uniref100 = str(local_entry.get("uniref100_cluster_id") or "").strip() or None
            uniref90 = str(local_entry.get("uniref90_cluster_id") or "").strip() or None
            uniref50 = str(local_entry.get("uniref50_cluster_id") or "").strip() or None
            source_url = str(local_entry.get("source_url") or "").strip()
            local_materialization_status = "materialized_from_local_uniprot_crossrefs"
            materialization_basis = "local_idmapping_selected"
        else:
            entry = fetch_json(f"https://rest.uniprot.org/uniprotkb/{accession}.json")
            uniref100 = _cluster_id(entry, "UniRef100")
            uniref90 = _cluster_id(entry, "UniRef90")
            uniref50 = _cluster_id(entry, "UniRef50")
            source_url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
            local_materialization_status = (
                "complete_but_missing_local_crossref_row"
                if uniprot_complete
                else "pending_tail_completion"
            )
            materialization_basis = "rest_fallback_crossrefs"
        rows.append(
            {
                "accession": accession,
                "uniref100_cluster_id": uniref100,
                "uniref90_cluster_id": uniref90,
                "uniref50_cluster_id": uniref50,
                "representative_member_candidate": _representative_candidate(uniref100),
                "identity_levels_present": [
                    level
                    for level, cluster_id in (
                        ("100", uniref100),
                        ("90", uniref90),
                        ("50", uniref50),
                    )
                    if cluster_id
                ],
                "local_materialization_status": local_materialization_status,
                "materialization_basis": materialization_basis,
                "source_url": source_url,
            }
        )
    return {
        "artifact_id": "uniref_cluster_context_preview",
        "schema_id": "proteosphere-uniref-cluster-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_uniref100_crossref": sum(
                1 for row in rows if row.get("uniref100_cluster_id")
            ),
            "accessions_with_all_identity_levels": sum(
                1 for row in rows if len(row["identity_levels_present"]) == len(UNIREF_DATABASES)
            ),
            "gate_status": gate_status,
            "uniprot_completion_ready": uniprot_complete,
            "local_crossref_row_count": len(local_crossrefs),
        },
        "truth_boundary": {
            "summary": (
                "UniRef cluster context prefers local UniProt cross-reference slices after "
                "tail completion and falls back to structured UniProt REST cross-references "
                "only when a local accession row is absent."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# UniRef Cluster Context Preview", ""]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / UniRef100 `{row.get('uniref100_cluster_id')}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build UniRef cluster context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument(
        "--procurement-tail-freeze-gate",
        type=Path,
        default=DEFAULT_PROCUREMENT_GATE,
    )
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
    )
    parser.add_argument(
        "--idmapping-selected",
        type=Path,
        default=DEFAULT_IDMAPPING_SELECTED,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_uniref_cluster_context_preview(
        read_json(args.training_set),
        read_json(args.procurement_tail_freeze_gate),
        read_json(args.procurement_source_completion),
        idmapping_selected_path=args.idmapping_selected,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
