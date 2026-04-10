from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_P00387_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "p00387_local_chembl_ligand_payload.json"
)
DEFAULT_P00387_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_validation_preview.json"
)
DEFAULT_Q9NZD4_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_LOCAL_BRIDGE_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_row_materialization_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bridge_entry_by_accession(
    payload: dict[str, Any],
    accession: str,
) -> dict[str, Any] | None:
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("accession") or "").strip() == accession:
            return entry
    return None


def _as_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _representative_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    pchembl = _as_float(row.get("pchembl_value"))
    standard_value = _as_float(row.get("standard_value"))
    return (
        0 if pchembl is not None else 1,
        -(pchembl if pchembl is not None else -1.0),
        0 if row.get("standard_relation") == "=" else 1,
        standard_value if standard_value is not None else float("inf"),
        str(row.get("standard_type") or ""),
        int(row.get("activity_id") or 0),
    )


def _build_p00387_rows(
    payload: dict[str, Any],
    validation_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    if payload.get("status") != "resolved" or validation_preview.get("status") != "aligned":
        return []

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("rows", []):
        ligand_chembl_id = row.get("ligand_chembl_id")
        if ligand_chembl_id:
            groups[str(ligand_chembl_id)].append(row)

    materialized_rows: list[dict[str, Any]] = []
    ordered_group_ids = sorted(
        groups,
        key=lambda chembl_id: _representative_sort_key(
            min(groups[chembl_id], key=_representative_sort_key)
        ),
    )
    for rank, ligand_chembl_id in enumerate(ordered_group_ids, start=1):
        rows = groups[ligand_chembl_id]
        representative = min(rows, key=_representative_sort_key)
        distinct_assays = sorted(
            {int(row["assay_id"]) for row in rows if row.get("assay_id") is not None}
        )
        ligand_label = (
            representative.get("ligand_pref_name")
            or representative.get("ligand_chembl_id")
            or ligand_chembl_id
        )
        materialized_rows.append(
            {
                "rank": rank,
                "row_id": f"ligand_row:protein:P00387:chembl:{ligand_chembl_id}",
                "accession": "P00387",
                "protein_ref": "protein:P00387",
                "source_ref": "ligand:P00387",
                "ligand_ref": f"chembl:{ligand_chembl_id}",
                "ligand_namespace": "ChEMBL",
                "ligand_identifier": ligand_chembl_id,
                "ligand_label": ligand_label,
                "materialization_status": "grounded_lightweight_ligand_row",
                "evidence_kind": "local_chembl_bulk_assay_row",
                "candidate_only": False,
                "target_chembl_id": representative.get("target_chembl_id"),
                "target_pref_name": representative.get("target_pref_name"),
                "representative_activity_id": representative.get("activity_id"),
                "representative_assay_id": representative.get("assay_id"),
                "activity_count_for_ligand": len(rows),
                "distinct_assay_count_for_ligand": len(distinct_assays),
                "canonical_smiles": representative.get("canonical_smiles"),
                "standard_type": representative.get("standard_type"),
                "standard_relation": representative.get("standard_relation"),
                "standard_value": representative.get("standard_value"),
                "standard_units": representative.get("standard_units"),
                "pchembl_value": representative.get("pchembl_value"),
                "ligand_molecule_type": representative.get("ligand_molecule_type"),
                "full_mwt": representative.get("full_mwt"),
                "source_payload_status": payload.get("status"),
                "validation_status": validation_preview.get("status"),
            }
        )
    return materialized_rows


def _build_q9nzd4_row(
    validation_preview: dict[str, Any],
    bridge_payload: dict[str, Any],
    rank: int,
) -> dict[str, Any] | None:
    bridge_entry = _bridge_entry_by_accession(bridge_payload, "Q9NZD4")
    if (
        isinstance(bridge_entry, dict)
        and str(bridge_entry.get("status") or "").strip() == "resolved"
    ):
        selected_ligand = bridge_entry.get("selected_ligand") or {}
        return {
            "rank": rank,
            "row_id": "ligand_row:protein:Q9NZD4:pdb_ccd:CHK",
            "accession": "Q9NZD4",
            "protein_ref": "protein:Q9NZD4",
            "source_ref": "ligand:Q9NZD4",
            "ligand_ref": f"pdb_ccd:{selected_ligand.get('component_id') or 'CHK'}",
            "ligand_namespace": "PDB_CCD",
            "ligand_identifier": selected_ligand.get("component_id") or "CHK",
            "ligand_label": selected_ligand.get("component_name")
            or validation_preview.get("component_name")
            or "CHK",
            "materialization_status": "grounded_bridge_lightweight_ligand_row",
            "evidence_kind": "local_structure_bridge_payload",
            "candidate_only": False,
            "structure_ref": f"structure:{bridge_entry.get('pdb_id') or validation_preview.get('best_pdb_id')}",
            "best_pdb_id": bridge_entry.get("pdb_id") or validation_preview.get("best_pdb_id"),
            "chain_ids": selected_ligand.get("chain_ids") or validation_preview.get("chain_ids") or [],
            "component_role": selected_ligand.get("component_role")
            or validation_preview.get("component_role"),
            "matched_pdb_id_count": validation_preview.get("matched_pdb_id_count"),
            "canonical_smiles": selected_ligand.get("smiles") or None,
            "validation_status": "aligned_bridge_payload_resolved",
        }
    if validation_preview.get("status") != "aligned":
        return None
    return {
        "rank": rank,
        "row_id": "ligand_row:protein:Q9NZD4:pdb_ccd:CHK",
        "accession": "Q9NZD4",
        "protein_ref": "protein:Q9NZD4",
        "source_ref": "ligand:Q9NZD4",
        "ligand_ref": f"pdb_ccd:{validation_preview['component_id']}",
        "ligand_namespace": "PDB_CCD",
        "ligand_identifier": validation_preview["component_id"],
        "ligand_label": validation_preview.get("component_name")
        or validation_preview["component_id"],
        "materialization_status": "candidate_bridge_lightweight_ligand_row",
        "evidence_kind": "local_structure_bridge_component",
        "candidate_only": True,
        "structure_ref": f"structure:{validation_preview['best_pdb_id']}",
        "best_pdb_id": validation_preview["best_pdb_id"],
        "chain_ids": validation_preview.get("chain_ids") or [],
        "component_role": validation_preview.get("component_role"),
        "matched_pdb_id_count": validation_preview.get("matched_pdb_id_count"),
        "validation_status": validation_preview.get("status"),
    }


def build_ligand_row_materialization_preview(
    p00387_payload: dict[str, Any],
    p00387_validation: dict[str, Any],
    q9nzd4_validation: dict[str, Any],
    local_bridge_payload: dict[str, Any],
) -> dict[str, Any]:
    rows = _build_p00387_rows(p00387_payload, p00387_validation)
    q9nzd4_row = _build_q9nzd4_row(
        q9nzd4_validation,
        local_bridge_payload,
        rank=len(rows) + 1,
    )
    if q9nzd4_row is not None:
        rows.append(q9nzd4_row)

    namespace_counts: dict[str, int] = {}
    for row in rows:
        namespace = row["ligand_namespace"]
        namespace_counts[namespace] = namespace_counts.get(namespace, 0) + 1

    grounded_accessions = sorted(
        {
            row["accession"]
            for row in rows
            if not bool(row.get("candidate_only"))
        }
    )
    candidate_only_accessions = sorted(
        {
            row["accession"]
            for row in rows
            if bool(row.get("candidate_only"))
        }
    )
    materialized_accessions = sorted({row["accession"] for row in rows})
    grounded_row_count = sum(1 for row in rows if not bool(row.get("candidate_only")))
    candidate_only_row_count = sum(1 for row in rows if bool(row.get("candidate_only")))
    return {
        "artifact_id": "ligand_row_materialization_preview",
        "schema_id": "proteosphere-ligand-row-materialization-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "materialized_accessions": materialized_accessions,
            "grounded_accessions": grounded_accessions,
            "candidate_only_accessions": candidate_only_accessions,
            "grounded_row_count": grounded_row_count,
            "candidate_only_row_count": candidate_only_row_count,
            "ligand_namespace_counts": namespace_counts,
            "ready_for_bundle_preview": bool(rows),
        },
        "truth_boundary": {
            "summary": (
                "This is the first real lightweight ligand-row family. It materializes "
                "compact ligand identity rows from grounded local evidence, but it does "
                "not claim canonical ligand reconciliation across all sources, split "
                "changes, or packet promotion."
            ),
            "report_only": False,
            "ligand_rows_materialized": True,
            "bundle_ligands_included": True,
            "canonical_ligand_materialization_claimed": False,
            "ligand_similarity_signatures_materialized": False,
            "split_claims_changed": False,
            "packet_promotion_claimed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Ligand Row Materialization Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        f"- Materialized accessions: `{', '.join(summary['materialized_accessions'])}`",
        f"- Grounded row count: `{summary['grounded_row_count']}`",
        f"- Candidate-only row count: `{summary['candidate_only_row_count']}`",
        "",
        "## Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['accession']}` / `{row['ligand_ref']}` / "
            f"`{row['materialization_status']}`"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the first real lightweight ligand-row family."
    )
    parser.add_argument("--p00387-payload", type=Path, default=DEFAULT_P00387_PAYLOAD)
    parser.add_argument(
        "--p00387-validation",
        type=Path,
        default=DEFAULT_P00387_VALIDATION,
    )
    parser.add_argument(
        "--q9nzd4-validation",
        type=Path,
        default=DEFAULT_Q9NZD4_VALIDATION,
    )
    parser.add_argument(
        "--local-bridge-payload",
        type=Path,
        default=DEFAULT_LOCAL_BRIDGE_PAYLOAD,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_row_materialization_preview(
        _read_json(args.p00387_payload),
        _read_json(args.p00387_validation),
        _read_json(args.q9nzd4_validation),
        _read_json(args.local_bridge_payload),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
