from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json

DEFAULT_BINDING_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
)
DEFAULT_STRUCTURE_AFFINITY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_binding_affinity_context_preview.json"
)
DEFAULT_STRUCTURE_ENTRY_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_entry_context_preview.json"
)
DEFAULT_STRUCTURE_LIGAND_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "structure_ligand_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_affinity_best_evidence_preview.json"
)

_RT_LN_10 = 0.00198720425864083 * 298.15 * math.log(10.0)
_UNIT_TO_MOLAR_FACTOR = {
    "m": 1.0,
    "mol/l": 1.0,
    "molar": 1.0,
    "nm": 1e-9,
    "um": 1e-6,
    "µm": 1e-6,
    "mm": 1e-3,
    "pm": 1e-12,
    "fm": 1e-15,
}


def _group_rows(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get(key) or "").strip().upper()
        if not value:
            continue
        grouped[value].append(row)
    return grouped


def _measurement_score(row: dict[str, Any]) -> float | None:
    if row.get("p_affinity") is not None:
        try:
            return float(row["p_affinity"])
        except (TypeError, ValueError):
            return None
    delta_g = row.get("delta_g_derived_298k_kcal_per_mol")
    if delta_g is not None:
        try:
            return -float(delta_g) / _RT_LN_10
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    value_molar = row.get("value_molar_normalized")
    if value_molar is not None:
        try:
            numeric = float(value_molar)
        except (TypeError, ValueError):
            return None
        if numeric > 0:
            return -math.log10(numeric)
    raw_value = row.get("raw_value")
    raw_unit = str(row.get("raw_unit") or "").strip().casefold()
    if raw_value is not None and raw_unit:
        factor = _UNIT_TO_MOLAR_FACTOR.get(raw_unit)
        if factor is None:
            factor = _UNIT_TO_MOLAR_FACTOR.get(raw_unit.replace("μ", "µ"))
        if factor is not None:
            try:
                numeric = float(raw_value) * factor
            except (TypeError, ValueError):
                return None
            if numeric > 0:
                return -math.log10(numeric)
    return None


def _measurement_kind(row: dict[str, Any]) -> str:
    if row.get("confidence_for_normalization") == "exact_relation_unit_converted" and row.get(
        "p_affinity"
    ) is not None:
        return "exact"
    if _measurement_score(row) is not None:
        return "derived"
    return "support_only"


def _summarize_measurement(row: dict[str, Any], *, evidence_kind: str) -> dict[str, Any]:
    payload = {
        "measurement_id": row.get("measurement_id"),
        "measurement_origin": row.get("measurement_origin"),
        "source_name": row.get("source_name"),
        "source_record_id": row.get("source_record_id"),
        "measurement_type": row.get("measurement_type"),
        "raw_affinity_string": row.get("raw_affinity_string"),
        "relation": row.get("relation"),
        "confidence_for_normalization": row.get("confidence_for_normalization"),
        "candidate_only": bool(row.get("candidate_only")),
        "evidence_kind": evidence_kind,
    }
    if row.get("p_affinity") is not None:
        payload["p_affinity"] = row.get("p_affinity")
    if row.get("value_molar_normalized") is not None:
        payload["value_molar_normalized"] = row.get("value_molar_normalized")
    if row.get("delta_g_derived_298k_kcal_per_mol") is not None:
        payload["delta_g_derived_298k_kcal_per_mol"] = row.get(
            "delta_g_derived_298k_kcal_per_mol"
        )
    score = _measurement_score(row)
    if score is not None:
        payload["derived_p_affinity"] = score
    return payload


def _best_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected: list[dict[str, Any]] = []
    for row in rows:
        kind = _measurement_kind(row)
        score = _measurement_score(row)
        if kind in {"exact", "derived"} and score is not None:
            selected.append(dict(row))
    if not selected:
        return None
    selected.sort(
        key=lambda row: (
            float(
                row.get("p_affinity")
                if row.get("p_affinity") is not None
                else _measurement_score(row) or -1e9
            ),
            str(row.get("measurement_id") or ""),
        ),
        reverse=True,
    )
    return selected[0]


def _best_exact(measurements: list[dict[str, Any]]) -> dict[str, Any] | None:
    comparable = [
        row
        for row in measurements
        if row.get("confidence_for_normalization") == "exact_relation_unit_converted"
        and row.get("p_affinity") is not None
    ]
    if not comparable:
        return None
    best = max(comparable, key=lambda row: float(row["p_affinity"]))
    return _summarize_measurement(best, evidence_kind="exact")


def _best_derived(measurements: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for row in measurements if _measurement_kind(row) == "derived"]
    best = _best_row(candidates)
    if best is None:
        return None
    return _summarize_measurement(best, evidence_kind="derived")


def _summarize_structure_surface_support(
    structure_entry_context_preview: dict[str, Any],
    structure_ligand_context_preview: dict[str, Any],
    binding_measurement_registry_preview: dict[str, Any],
) -> dict[str, Any]:
    entry_rows = []
    registry_rows = binding_measurement_registry_preview.get("rows") or []
    for row in structure_entry_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "").strip().upper()
        if not structure_id:
            continue
        accessions = [
            str(item).strip().upper()
            for item in row.get("mapped_uniprot_accessions") or []
            if str(item).strip()
        ]
        accession_support_rows = []
        for accession in accessions:
            accession_rows = [
                dict(measurement)
                for measurement in registry_rows
                if str(measurement.get("accession") or "").strip().upper() == accession
            ]
            if not accession_rows:
                continue
            origin_counts = Counter(
                str(measurement.get("measurement_origin") or "") for measurement in accession_rows
            )
            exact_count = sum(
                1 for measurement in accession_rows if _measurement_kind(measurement) == "exact"
            )
            derived_count = sum(
                1 for measurement in accession_rows if _measurement_kind(measurement) == "derived"
            )
            support_count = len(accession_rows) - exact_count - derived_count
            best_support = _best_row(accession_rows)
            accession_support_rows.append(
                {
                    "accession": accession,
                    "measurement_count": len(accession_rows),
                    "measurement_origin_counts": dict(sorted(origin_counts.items())),
                    "exact_measurement_count": exact_count,
                    "derived_measurement_count": derived_count,
                    "support_only_measurement_count": support_count,
                    "support_status": (
                        "grounded preview-safe"
                        if exact_count > 0 or derived_count > 0
                        else "candidate_only_non_governing"
                    ),
                    "best_measurement": (
                        _summarize_measurement(best_support, evidence_kind="support_only")
                        if best_support is not None
                        else None
                    ),
                }
            )
        entry_rows.append(
            {
                "structure_id": structure_id,
                "seed_accessions": [
                    str(item).strip().upper()
                    for item in row.get("seed_accessions") or []
                    if str(item).strip()
                ],
                "mapped_uniprot_accessions": accessions,
                "mapped_chain_ids": [
                    str(item).strip()
                    for item in row.get("mapped_chain_ids") or []
                    if str(item).strip()
                ],
                "nonpolymer_bound_components": [
                    str(item).strip()
                    for item in row.get("nonpolymer_bound_components") or []
                    if str(item).strip()
                ],
                "assembly_count": row.get("assembly_count"),
                "preferred_assembly_id": row.get("preferred_assembly_id"),
                "experimental_method": row.get("experimental_method"),
                "resolution_angstrom": row.get("resolution_angstrom"),
                "accession_support_rows": accession_support_rows,
            }
        )

    ligand_rows = []
    ligand_counts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in structure_ligand_context_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        structure_id = str(row.get("structure_id") or "").strip().upper()
        if structure_id:
            ligand_counts[structure_id].append(row)
    for structure_id, rows in sorted(ligand_counts.items()):
        ligand_rows.append(
            {
                "structure_id": structure_id,
                "ligand_count": len(rows),
                "ccd_ids": sorted(
                    {
                        str(row.get("ccd_id") or "").strip()
                        for row in rows
                        if str(row.get("ccd_id") or "").strip()
                    }
                ),
                "ligand_labels": sorted(
                    {
                        str(row.get("name") or "").strip()
                        for row in rows
                        if str(row.get("name") or "").strip()
                    }
                ),
            }
        )

    return {
        "entry_rows": sorted(entry_rows, key=lambda row: row["structure_id"]),
        "ligand_rows": ligand_rows,
    }


def build_structure_affinity_best_evidence_preview(
    binding_measurement_registry_preview: dict[str, Any],
    structure_binding_affinity_context_preview: dict[str, Any],
    structure_entry_context_preview: dict[str, Any],
    structure_ligand_context_preview: dict[str, Any],
) -> dict[str, Any]:
    registry_by_structure = _group_rows(
        binding_measurement_registry_preview.get("rows") or [],
        "pdb_id",
    )
    affinity_context_by_structure = {
        str(row.get("structure_id") or "").strip().upper(): dict(row)
        for row in structure_binding_affinity_context_preview.get("rows") or []
        if isinstance(row, dict) and str(row.get("structure_id") or "").strip()
    }

    rows: list[dict[str, Any]] = []
    exact_structure_count = 0
    derived_structure_count = 0
    support_only_structure_count = 0
    exact_measurement_count = 0
    derived_measurement_count = 0
    support_only_measurement_count = 0

    all_structure_ids = sorted(set(registry_by_structure) | set(affinity_context_by_structure))
    for structure_id in all_structure_ids:
        measurements = registry_by_structure.get(structure_id, [])
        affinity_row = affinity_context_by_structure.get(structure_id) or {}
        exact_measurements = [
            row for row in measurements if _measurement_kind(row) == "exact"
        ]
        derived_measurements = [
            row for row in measurements if _measurement_kind(row) == "derived"
        ]
        support_measurements = [
            row for row in measurements if _measurement_kind(row) == "support_only"
        ]
        best_exact = _best_exact(exact_measurements)
        best_derived = _best_derived(derived_measurements)
        if best_exact is not None:
            selected_kind = "exact"
            selected_rank = 0
            selected_evidence = best_exact
            exact_structure_count += 1
        elif best_derived is not None:
            selected_kind = "derived"
            selected_rank = 1
            selected_evidence = best_derived
            derived_structure_count += 1
        else:
            selected_kind = "support_only"
            selected_rank = 2
            selected_evidence = None
            support_only_structure_count += 1

        exact_measurement_count += len(exact_measurements)
        derived_measurement_count += len(derived_measurements)
        support_only_measurement_count += len(support_measurements)

        rows.append(
            {
                "structure_id": structure_id,
                "complex_type": affinity_row.get("complex_type")
                or (measurements[0].get("complex_type") if measurements else None),
                "chain_role_summary": affinity_row.get("chain_role_summary")
                or (measurements[0].get("parenthetical_tokens") if measurements else [])
                or [],
                "affinity_measurement_count": len(measurements),
                "exact_measurement_count": len(exact_measurements),
                "derived_measurement_count": len(derived_measurements),
                "support_only_measurement_count": len(support_measurements),
                "selected_evidence_kind": selected_kind,
                "selected_evidence_rank": selected_rank,
                "best_exact_affinity": best_exact,
                "best_derived_affinity": best_derived,
                "selected_evidence": selected_evidence,
                "thermodynamic_field_presence": bool(
                    affinity_row.get("thermodynamic_field_presence")
                    if affinity_row
                    else any(
                        row.get("delta_g_reported_kcal_per_mol") is not None
                        or row.get("delta_g_derived_298k_kcal_per_mol") is not None
                        for row in measurements
                    )
                ),
            }
        )

    rows.sort(key=lambda row: (row["selected_evidence_rank"], row["structure_id"]))

    supporting_surfaces = _summarize_structure_surface_support(
        structure_entry_context_preview,
        structure_ligand_context_preview,
        binding_measurement_registry_preview,
    )

    support_accession_count = sum(
        len(row.get("accession_support_rows") or []) for row in supporting_surfaces["entry_rows"]
    )

    return {
        "artifact_id": "structure_affinity_best_evidence_preview",
        "schema_id": "proteosphere-structure-affinity-best-evidence-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structure_count": len(rows),
            "exact_structure_count": exact_structure_count,
            "derived_structure_count": derived_structure_count,
            "support_only_structure_count": support_only_structure_count,
            "selected_evidence_kind_counts": {
                "exact": exact_structure_count,
                "derived": derived_structure_count,
                "support_only": support_only_structure_count,
            },
            "exact_measurement_count": exact_measurement_count,
            "derived_measurement_count": derived_measurement_count,
            "support_only_measurement_count": support_only_measurement_count,
            "structure_surface_support_count": len(supporting_surfaces["entry_rows"]),
            "structure_surface_ligand_count": len(supporting_surfaces["ligand_rows"]),
            "support_accession_count": support_accession_count,
            "measurement_origin_counts": dict(
                sorted(
                    Counter(
                        str(row.get("measurement_origin") or "")
                        for row in binding_measurement_registry_preview.get("rows") or []
                    ).items()
                )
            ),
        },
        "supporting_structure_surfaces": supporting_surfaces,
        "truth_boundary": {
            "summary": (
                "This surface is report-only. Exact PDBbind-derived structure "
                "affinity evidence is ranked ahead of derived or support-only "
                "evidence, and the structure surfaces are attached only as "
                "provenance context."
            ),
            "report_only": True,
            "governing": False,
            "exact_over_derived": True,
            "structure_surface_context_only": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only best-evidence structure affinity preview."
    )
    parser.add_argument("--binding-registry", type=Path, default=DEFAULT_BINDING_REGISTRY)
    parser.add_argument(
        "--structure-affinity-context",
        type=Path,
        default=DEFAULT_STRUCTURE_AFFINITY_CONTEXT,
    )
    parser.add_argument(
        "--structure-entry-context",
        type=Path,
        default=DEFAULT_STRUCTURE_ENTRY_CONTEXT,
    )
    parser.add_argument(
        "--structure-ligand-context",
        type=Path,
        default=DEFAULT_STRUCTURE_LIGAND_CONTEXT,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_affinity_best_evidence_preview(
        read_json(args.binding_registry),
        read_json(args.structure_affinity_context),
        read_json(args.structure_entry_context),
        read_json(args.structure_ligand_context),
    )
    write_json(args.output_json, payload)
    print(args.output_json)


if __name__ == "__main__":
    main()
