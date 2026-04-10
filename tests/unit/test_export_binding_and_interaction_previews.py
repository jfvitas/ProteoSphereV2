from __future__ import annotations

from pathlib import Path

from scripts.export_accession_binding_support_preview import (
    build_accession_binding_support_preview,
)
from scripts.export_binding_measurement_validation_preview import (
    build_binding_measurement_validation_preview,
)
from scripts.export_interaction_context_preview import build_interaction_context_preview


def test_build_binding_measurement_validation_preview_rejects_derived_delta_g_on_ic50() -> None:
    payload = build_binding_measurement_validation_preview(
        {
            "rows": [
                {
                    "measurement_origin": "pdbbind",
                    "complex_type": "protein_ligand",
                    "measurement_id": "m1",
                    "raw_binding_string": "Kd=49uM",
                    "measurement_type": "Kd",
                    "confidence_for_normalization": "exact_relation_unit_converted",
                },
                {
                    "measurement_origin": "pdbbind",
                    "complex_type": "protein_protein",
                    "measurement_id": "m2",
                    "raw_binding_string": "Kd=22.5nM",
                    "measurement_type": "Kd",
                    "confidence_for_normalization": "exact_relation_unit_converted",
                },
                {
                    "measurement_origin": "pdbbind",
                    "complex_type": "protein_nucleic_acid",
                    "measurement_id": "m3",
                    "raw_binding_string": "Kd=11uM",
                    "measurement_type": "Kd",
                    "confidence_for_normalization": "exact_relation_unit_converted",
                },
                {
                    "measurement_origin": "pdbbind",
                    "complex_type": "nucleic_acid_ligand",
                    "measurement_id": "m4",
                    "raw_binding_string": "Kd=1mM",
                    "measurement_type": "Kd",
                    "confidence_for_normalization": "exact_relation_unit_converted",
                },
                {
                    "measurement_origin": "chembl_lightweight",
                    "complex_type": "protein_ligand",
                    "measurement_id": "m5",
                    "measurement_type": "IC50",
                    "delta_g_derived_298k_kcal_per_mol": -4.0,
                },
            ]
        }
    )

    assert payload["status"] == "review_required"
    assert "delta_g may not be derived from IC50/EC50 rows" in payload["issues"]


def test_build_accession_binding_support_preview_summarizes_measurement_types() -> None:
    payload = build_accession_binding_support_preview(
        {"rows": [{"accession": "P00387", "protein_ref": "protein:P00387"}]},
        {
            "rows": [
                {
                    "accession": "P00387",
                    "measurement_type": "IC50",
                    "candidate_only": False,
                    "p_affinity": 4.9,
                    "delta_g_reported_kcal_per_mol": None,
                    "delta_g_derived_298k_kcal_per_mol": None,
                },
                {
                    "accession": "P00387",
                    "measurement_type": "Kd",
                    "candidate_only": False,
                    "p_affinity": 6.1,
                    "delta_g_reported_kcal_per_mol": None,
                    "delta_g_derived_298k_kcal_per_mol": -7.5,
                },
            ]
        },
    )

    row = payload["rows"][0]
    assert row["measurement_count"] == 2
    assert row["measurement_type_counts"] == {"IC50": 1, "Kd": 1}
    assert row["best_p_affinity"] == 6.1
    assert row["binding_support_status"] == "grounded preview-safe"


def test_build_interaction_context_preview_reads_latest_usable_snapshot(tmp_path: Path) -> None:
    old_snapshot = tmp_path / "20260323T154140Z" / "P09105"
    old_snapshot.mkdir(parents=True)
    (old_snapshot / "P09105.psicquic.tab25.txt").write_text(
        "\t".join(
            [
                "uniprotkb:P09105",
                "uniprotkb:P69905",
                "intact:EBI-1",
                "intact:EBI-2",
                "a",
                "b",
                'psi-mi:"MI:0397"(two hybrid array)',
                "Luck et al. (2017)",
                "pubmed:1",
                "taxid:9606(human)",
                "taxid:9606(human)",
                'psi-mi:"MI:0915"(physical association)',
                'psi-mi:"MI:0469"(IntAct)',
                "intact:EBI-23498192",
                "intact-miscore:0.56",
            ]
        ),
        encoding="utf-8",
    )
    newer_empty = tmp_path / "20260329T114112Z"
    newer_empty.mkdir()

    payload = build_interaction_context_preview(
        {"rows": [{"accession": "P09105", "protein_ref": "protein:P09105"}]},
        {
            "rows": [
                {
                    "accession": "P09105",
                    "biogrid_matched_row_count": 30,
                    "string_disk_state": "partial_on_disk",
                }
            ]
        },
        tmp_path,
    )

    row = payload["rows"][0]
    assert row["intact_row_count"] == 1
    assert row["biogrid_row_count"] == 30
    assert row["interaction_support_status"] == "support-only"
