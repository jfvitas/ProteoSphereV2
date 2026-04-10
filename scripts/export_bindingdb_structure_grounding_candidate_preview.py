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
DEFAULT_BINDINGDB_ACCESSION_PARTNER_IDENTITY_PROFILE = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_accession_partner_identity_profile_preview.json"
)
DEFAULT_BINDINGDB_STRUCTURE_MEASUREMENT_PROJECTION = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_structure_measurement_projection_preview.json"
)
DEFAULT_STRUCTURE_LIGAND_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "bindingdb_structure_grounding_candidate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "bindingdb_structure_grounding_candidate_preview.md"
)


def _candidate_class(row: dict[str, Any], future_structure_ids: list[str]) -> str:
    if future_structure_ids and row.get("het_pdb"):
        return "future_structure_and_het_code_candidate"
    if future_structure_ids:
        return "future_structure_candidate"
    if row.get("het_pdb"):
        return "het_code_candidate_only"
    return "descriptor_only"


def build_bindingdb_structure_grounding_candidate_preview(
    bindingdb_partner_monomer_context_preview: dict[str, Any],
    bindingdb_accession_partner_identity_profile_preview: dict[str, Any],
    bindingdb_structure_measurement_projection_preview: dict[str, Any],
    structure_ligand_context_preview: dict[str, Any],
) -> dict[str, Any]:
    seeded_structure_ids = {
        str(row.get("structure_id") or "").strip()
        for row in structure_ligand_context_preview.get("rows") or []
        if str(row.get("structure_id") or "").strip()
    }

    accession_profile_by_accession = {
        str(row.get("accession") or "").strip(): row
        for row in bindingdb_accession_partner_identity_profile_preview.get("rows") or []
        if isinstance(row, dict) and str(row.get("accession") or "").strip()
    }

    projection_state_by_accession: dict[str, dict[str, set[str]]] = {}
    for row in bindingdb_structure_measurement_projection_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "").strip()
        if not structure_id:
            continue
        mapped_accessions = {
            str(value).strip()
            for value in row.get("mapped_uniprot_accessions") or []
            if str(value).strip()
        }
        matched_accessions = {
            str(value).strip()
            for value in row.get("matched_accessions") or []
            if str(value).strip()
        }
        for accession in mapped_accessions | matched_accessions:
            projection_state = projection_state_by_accession.setdefault(
                accession,
                {
                    "mapped_seed_structures": set(),
                    "matched_seed_structures": set(),
                },
            )
            projection_state["mapped_seed_structures"].add(structure_id)
            if accession in matched_accessions:
                projection_state["matched_seed_structures"].add(structure_id)

    accession_states: dict[str, dict[str, Any]] = {}
    global_future_structure_counts: Counter[str] = Counter()
    for row in bindingdb_partner_monomer_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        linked_accessions = [
            str(value).strip()
            for value in row.get("linked_accessions") or []
            if str(value).strip()
        ]
        if not linked_accessions:
            continue

        exact_structure_ids = sorted(
            {
                str(value).strip()
                for value in row.get("pdb_ids_exact_sample") or []
                if str(value).strip()
            }
        )
        future_structure_ids = [
            structure_id
            for structure_id in exact_structure_ids
            if structure_id not in seeded_structure_ids
        ]
        seeded_exact_overlap_ids = [
            structure_id
            for structure_id in exact_structure_ids
            if structure_id in seeded_structure_ids
        ]
        candidate_class = _candidate_class(row, future_structure_ids)

        for accession in linked_accessions:
            state = accession_states.setdefault(
                accession,
                {
                    "candidate_monomer_count": 0,
                    "monomers_with_exact_pdb_sample_count": 0,
                    "monomers_with_het_code_count": 0,
                    "future_structure_ids": Counter(),
                    "top_candidate_monomers": [],
                    "measurement_count": 0,
                    "candidate_class_counts": Counter(),
                },
            )
            state["candidate_monomer_count"] += 1
            state["measurement_count"] += int(row.get("linked_measurement_count") or 0)
            state["candidate_class_counts"][candidate_class] += 1
            if exact_structure_ids:
                state["monomers_with_exact_pdb_sample_count"] += 1
            if row.get("het_pdb"):
                state["monomers_with_het_code_count"] += 1
            for structure_id in future_structure_ids:
                state["future_structure_ids"][structure_id] += 1
                global_future_structure_counts[structure_id] += 1

            monomer_payload = {
                "bindingdb_monomer_id": row.get("bindingdb_monomer_id"),
                "display_name": row.get("display_name"),
                "het_pdb": row.get("het_pdb") or None,
                "linked_measurement_count": int(row.get("linked_measurement_count") or 0),
                "future_structure_ids": future_structure_ids[:10],
                "seeded_exact_overlap_ids": seeded_exact_overlap_ids,
                "candidate_class": candidate_class,
            }
            state["top_candidate_monomers"].append(monomer_payload)
            state["top_candidate_monomers"].sort(
                key=lambda item: (
                    len(item.get("future_structure_ids") or []),
                    bool(item.get("het_pdb")),
                    int(item.get("linked_measurement_count") or 0),
                    str(item.get("bindingdb_monomer_id") or ""),
                ),
                reverse=True,
            )
            state["top_candidate_monomers"] = state["top_candidate_monomers"][:10]

    rows = []
    readiness_counts: Counter[str] = Counter()
    for accession, state in sorted(accession_states.items()):
        profile_row = accession_profile_by_accession.get(accession) or {}
        projection_state = projection_state_by_accession.get(accession) or {
            "mapped_seed_structures": set(),
            "matched_seed_structures": set(),
        }
        future_structure_ids = [
            structure_id
            for structure_id, _count in state["future_structure_ids"].most_common(25)
        ]
        if projection_state["matched_seed_structures"]:
            grounding_readiness_status = "seed_structure_supported"
            recommended_next_action = (
                "expand_current_seed_structure_assay_and_ligand_reconciliation"
            )
        elif future_structure_ids:
            grounding_readiness_status = "future_structure_candidate_available"
            recommended_next_action = "harvest_top_future_structure_candidates"
        elif state["monomers_with_het_code_count"] > 0:
            grounding_readiness_status = "het_code_candidate_only"
            recommended_next_action = "reconcile_partner_het_codes_to_external_ligand_registries"
        else:
            grounding_readiness_status = "descriptor_only_no_structure_cues"
            recommended_next_action = "keep_descriptor_rich_partner_set_for_later_ligand_grounding"
        readiness_counts[grounding_readiness_status] += 1

        rows.append(
            {
                "accession": accession,
                "grounding_readiness_status": grounding_readiness_status,
                "recommended_next_action": recommended_next_action,
                "matched_seed_structure_ids": sorted(projection_state["matched_seed_structures"]),
                "mapped_seed_structure_ids": sorted(projection_state["mapped_seed_structures"]),
                "candidate_monomer_count": state["candidate_monomer_count"],
                "monomers_with_exact_pdb_sample_count": state[
                    "monomers_with_exact_pdb_sample_count"
                ],
                "monomers_with_het_code_count": state["monomers_with_het_code_count"],
                "future_structure_candidate_count": len(future_structure_ids),
                "top_future_structure_ids": future_structure_ids[:15],
                "linked_measurement_count": state["measurement_count"],
                "descriptor_coverage_fraction": profile_row.get("descriptor_coverage_fraction"),
                "partners_with_seed_structure_overlap_count": profile_row.get(
                    "partners_with_seed_structure_overlap_count"
                ),
                "candidate_class_counts": dict(sorted(state["candidate_class_counts"].items())),
                "top_candidate_monomers": state["top_candidate_monomers"][:5],
            }
        )

    return {
        "artifact_id": "bindingdb_structure_grounding_candidate_preview",
        "schema_id": "proteosphere-bindingdb-structure-grounding-candidate-preview-2026-04-03",
        "status": "report_only_local_projection",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_seed_structure_support": sum(
                1
                for row in rows
                if row.get("grounding_readiness_status") == "seed_structure_supported"
            ),
            "accessions_with_future_structure_candidates": sum(
                1
                for row in rows
                if row.get("grounding_readiness_status") == "future_structure_candidate_available"
            ),
            "accessions_with_het_code_candidates": sum(
                1 for row in rows if row.get("monomers_with_het_code_count", 0) > 0
            ),
            "global_future_structure_candidate_count": len(global_future_structure_counts),
            "grounding_readiness_counts": dict(sorted(readiness_counts.items())),
            "top_global_future_structure_ids": [
                structure_id
                for structure_id, _count in global_future_structure_counts.most_common(20)
            ],
            "seeded_structure_ids": sorted(seeded_structure_ids),
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only BindingDB-to-structure grounding candidate view. "
                "It ranks current accession-level opportunities for seed-structure expansion "
                "and future PDB harvesting without changing any governing library state."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# BindingDB Structure Grounding Candidate Preview",
        "",
        f"- Accessions: `{payload['row_count']}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / `{row['grounding_readiness_status']}` / "
            f"future structures `{row['future_structure_candidate_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BindingDB structure grounding candidate preview."
    )
    parser.add_argument(
        "--bindingdb-partner-monomer-context",
        type=Path,
        default=DEFAULT_BINDINGDB_PARTNER_MONOMER_CONTEXT,
    )
    parser.add_argument(
        "--bindingdb-accession-partner-identity-profile",
        type=Path,
        default=DEFAULT_BINDINGDB_ACCESSION_PARTNER_IDENTITY_PROFILE,
    )
    parser.add_argument(
        "--bindingdb-structure-measurement-projection",
        type=Path,
        default=DEFAULT_BINDINGDB_STRUCTURE_MEASUREMENT_PROJECTION,
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
    payload = build_bindingdb_structure_grounding_candidate_preview(
        read_json(args.bindingdb_partner_monomer_context),
        read_json(args.bindingdb_accession_partner_identity_profile),
        read_json(args.bindingdb_structure_measurement_projection),
        read_json(args.structure_ligand_context),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
