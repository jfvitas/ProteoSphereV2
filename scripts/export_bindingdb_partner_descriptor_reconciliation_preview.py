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

DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "bindingdb_partner_monomer_context_preview.json"
)
DEFAULT_STRUCTURE_LIGAND_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_partner_descriptor_reconciliation_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "bindingdb_partner_descriptor_reconciliation_preview.md"
)


def build_bindingdb_partner_descriptor_reconciliation_preview(
    bindingdb_partner_monomer_context_preview: dict[str, Any],
    structure_ligand_context_preview: dict[str, Any],
) -> dict[str, Any]:
    structure_ccd_ids: dict[str, set[str]] = {}
    for row in structure_ligand_context_preview.get("rows") or []:
        structure_id = str(row.get("structure_id") or "").strip()
        ccd_id = str(row.get("ccd_id") or "").strip()
        if structure_id and ccd_id:
            structure_ccd_ids.setdefault(structure_id, set()).add(ccd_id)

    status_counts: Counter[str] = Counter()
    rows = []
    for row in bindingdb_partner_monomer_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        pdb_ids_exact_sample = [
            str(pdb_id).strip()
            for pdb_id in row.get("pdb_ids_exact_sample") or []
            if str(pdb_id).strip()
        ]
        seed_structure_overlap_ids = sorted(
            structure_id
            for structure_id in pdb_ids_exact_sample
            if structure_id in structure_ccd_ids
        )
        overlap_ccd_ids = sorted(
            {
                ccd_id
                for structure_id in seed_structure_overlap_ids
                for ccd_id in structure_ccd_ids.get(structure_id, set())
            }
        )
        het_pdb = str(row.get("het_pdb") or "").strip()
        descriptor_richness = sum(
            1
            for present in (
                bool(row.get("chembl_id")),
                bool(het_pdb),
                bool(row.get("smiles_present")),
                bool(row.get("inchi_key_present")),
                bool(pdb_ids_exact_sample),
            )
            if present
        )
        if het_pdb and het_pdb in overlap_ccd_ids:
            reconciliation_status = "seed_structure_and_het_code_overlap"
        elif seed_structure_overlap_ids:
            reconciliation_status = "seed_structure_overlap_only"
        elif het_pdb:
            reconciliation_status = "het_code_present_no_seed_overlap"
        elif row.get("smiles_present") or row.get("inchi_key_present"):
            reconciliation_status = "descriptor_rich_no_seed_overlap"
        else:
            reconciliation_status = "sparse_descriptor_only"
        status_counts[reconciliation_status] += 1
        rows.append(
            {
                "bindingdb_monomer_id": row.get("bindingdb_monomer_id"),
                "display_name": row.get("display_name"),
                "chembl_id": row.get("chembl_id"),
                "het_pdb": het_pdb or None,
                "smiles_present": bool(row.get("smiles_present")),
                "inchi_key_present": bool(row.get("inchi_key_present")),
                "pdb_ids_exact_sample": pdb_ids_exact_sample,
                "seed_structure_overlap_ids": seed_structure_overlap_ids,
                "seed_structure_overlap_ccd_ids": overlap_ccd_ids,
                "linked_accessions": row.get("linked_accessions") or [],
                "linked_measurement_count": row.get("linked_measurement_count", 0),
                "descriptor_richness": descriptor_richness,
                "reconciliation_status": reconciliation_status,
            }
        )

    return {
        "artifact_id": "bindingdb_partner_descriptor_reconciliation_preview",
        "schema_id": "proteosphere-bindingdb-partner-descriptor-reconciliation-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "partner_monomer_count": len(rows),
            "reconciliation_status_counts": dict(sorted(status_counts.items())),
            "partners_with_seed_structure_overlap": sum(
                1 for row in rows if row.get("seed_structure_overlap_ids")
            ),
            "partners_with_chemistry_descriptors": sum(
                1
                for row in rows
                if row.get("smiles_present") or row.get("inchi_key_present") or row.get("chembl_id")
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only descriptor reconciliation view that compares BindingDB "
                "partner monomer metadata against current seeded structure ligand context."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Partner Descriptor Reconciliation Preview",
        "",
        f"- Partner monomers: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows")[:20]:
        lines.append(
            f"- `{row['bindingdb_monomer_id']}` / `{row['reconciliation_status']}` / "
            f"descriptors `{row['descriptor_richness']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB partner descriptor reconciliation preview."
    )
    parser.add_argument(
        "--bindingdb-partner-monomer-context",
        type=Path,
        default=DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT,
    )
    parser.add_argument(
        "--structure-ligand-context",
        type=Path,
        default=DEFAULT_STRUCTURE_LIGAND_CONTEXT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_partner_descriptor_reconciliation_preview(
        read_json(args.bindingdb_partner_monomer_context),
        read_json(args.structure_ligand_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
