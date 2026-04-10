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
DEFAULT_BINDINGDB_PARTNER_DESCRIPTOR_RECONCILIATION = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_partner_descriptor_reconciliation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_accession_partner_identity_profile_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "bindingdb_accession_partner_identity_profile_preview.md"
)


def build_bindingdb_accession_partner_identity_profile_preview(
    bindingdb_partner_monomer_context_preview: dict[str, Any],
    bindingdb_partner_descriptor_reconciliation_preview: dict[str, Any],
) -> dict[str, Any]:
    reconciliation_by_monomer_id = {
        str(row.get("bindingdb_monomer_id") or "").strip(): row
        for row in bindingdb_partner_descriptor_reconciliation_preview.get("rows") or []
        if isinstance(row, dict) and str(row.get("bindingdb_monomer_id") or "").strip()
    }

    accession_states: dict[str, dict[str, Any]] = {}
    for row in bindingdb_partner_monomer_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        monomer_id = str(row.get("bindingdb_monomer_id") or "").strip()
        if not monomer_id:
            continue
        reconciliation = reconciliation_by_monomer_id.get(monomer_id) or {}
        linked_accessions = [str(value).strip() for value in row.get("linked_accessions") or []]
        for accession in linked_accessions:
            if not accession:
                continue
            state = accession_states.setdefault(
                accession,
                {
                    "partner_ids": set(),
                    "measurement_count": 0,
                    "partners_with_smiles": set(),
                    "partners_with_inchi_key": set(),
                    "partners_with_chembl_id": set(),
                    "partners_with_het_code": set(),
                    "partners_with_seed_overlap": set(),
                    "reconciliation_status_counts": Counter(),
                    "top_partner_names": [],
                },
            )
            state["partner_ids"].add(monomer_id)
            state["measurement_count"] += int(row.get("linked_measurement_count") or 0)
            if row.get("smiles_present"):
                state["partners_with_smiles"].add(monomer_id)
            if row.get("inchi_key_present"):
                state["partners_with_inchi_key"].add(monomer_id)
            if row.get("chembl_id"):
                state["partners_with_chembl_id"].add(monomer_id)
            if row.get("het_pdb"):
                state["partners_with_het_code"].add(monomer_id)
            if reconciliation.get("seed_structure_overlap_ids"):
                state["partners_with_seed_overlap"].add(monomer_id)
            reconciliation_status = str(reconciliation.get("reconciliation_status") or "").strip()
            if reconciliation_status:
                state["reconciliation_status_counts"][reconciliation_status] += 1
            display_name = str(row.get("display_name") or monomer_id).strip()
            if display_name and display_name not in state["top_partner_names"]:
                state["top_partner_names"].append(display_name)

    rows = []
    for accession, state in sorted(accession_states.items()):
        partner_count = len(state["partner_ids"])
        rows.append(
            {
                "accession": accession,
                "partner_monomer_count": partner_count,
                "linked_measurement_count": state["measurement_count"],
                "partners_with_smiles_count": len(state["partners_with_smiles"]),
                "partners_with_inchi_key_count": len(state["partners_with_inchi_key"]),
                "partners_with_chembl_id_count": len(state["partners_with_chembl_id"]),
                "partners_with_het_code_count": len(state["partners_with_het_code"]),
                "partners_with_seed_structure_overlap_count": len(
                    state["partners_with_seed_overlap"]
                ),
                "descriptor_coverage_fraction": (
                    round(
                        len(state["partners_with_smiles"] | state["partners_with_inchi_key"])
                        / partner_count,
                        4,
                    )
                    if partner_count
                    else 0.0
                ),
                "reconciliation_status_counts": dict(
                    sorted(state["reconciliation_status_counts"].items())
                ),
                "top_partner_names": state["top_partner_names"][:10],
            }
        )

    return {
        "artifact_id": "bindingdb_accession_partner_identity_profile_preview",
        "schema_id": "proteosphere-bindingdb-accession-partner-identity-profile-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_partner_identity_profile": len(rows),
            "accessions_with_seed_bridgeable_partners": sum(
                1
                for row in rows
                if row.get("partners_with_seed_structure_overlap_count", 0) > 0
            ),
            "accessions_with_descriptor_rich_partners": sum(
                1 for row in rows if row.get("descriptor_coverage_fraction", 0.0) > 0
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only accession-level summary of BindingDB partner monomer "
                "identity richness and seed-structure bridgeability."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Accession Partner Identity Profile Preview",
        "",
        f"- Accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / partners `{row['partner_monomer_count']}` / "
            f"descriptor coverage `{row['descriptor_coverage_fraction']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB accession partner identity profile preview."
    )
    parser.add_argument(
        "--bindingdb-partner-monomer-context",
        type=Path,
        default=DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT,
    )
    parser.add_argument(
        "--bindingdb-partner-descriptor-reconciliation",
        type=Path,
        default=DEFAULT_BINDINGDB_PARTNER_DESCRIPTOR_RECONCILIATION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_bindingdb_accession_partner_identity_profile_preview(
        read_json(args.bindingdb_partner_monomer_context),
        read_json(args.bindingdb_partner_descriptor_reconciliation),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
