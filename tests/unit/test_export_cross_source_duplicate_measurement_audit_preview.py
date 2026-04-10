from __future__ import annotations

from scripts.export_cross_source_duplicate_measurement_audit_preview import (
    build_cross_source_duplicate_measurement_audit_preview,
)


def test_cross_source_duplicate_measurement_audit_groups_identical_measurements() -> None:
    payload = build_cross_source_duplicate_measurement_audit_preview(
        {
            "rows": [
                {
                    "accession": "P00387",
                    "measurement_type": "Kd",
                    "relation": "=",
                    "raw_value": 22.5,
                    "raw_unit": "nM",
                    "measurement_origin": "bindingdb",
                    "measurement_id": "bindingdb:1",
                    "complex_type": "protein_ligand",
                    "raw_binding_string": "Kd=22.5nM",
                },
                {
                    "accession": "P00387",
                    "measurement_type": "Kd",
                    "relation": "=",
                    "raw_value": 22.5,
                    "raw_unit": "nM",
                    "measurement_origin": "chembl_lightweight",
                    "measurement_id": "chembl:1",
                    "complex_type": "protein_ligand",
                    "raw_binding_string": "Kd=22.5nM",
                },
                {
                    "accession": "P00387",
                    "measurement_type": "Ki",
                    "relation": "=",
                    "raw_value": 11.0,
                    "raw_unit": "nM",
                    "measurement_origin": "bindingdb",
                    "measurement_id": "bindingdb:2",
                    "complex_type": "protein_ligand",
                    "raw_binding_string": "Ki=11nM",
                },
            ]
        }
    )

    assert payload["status"] == "report_only"
    assert payload["summary"]["cross_source_duplicate_group_count"] == 1
    group = payload["groups"][0]
    assert group["reference"] == "P00387"
    assert group["measurement_type"] == "Kd"
    assert group["distinct_sources"] == ["bindingdb", "chembl_lightweight"]
    assert group["row_count"] == 2


def test_cross_source_duplicate_measurement_audit_ignores_single_source_duplicates() -> None:
    payload = build_cross_source_duplicate_measurement_audit_preview(
        {
            "rows": [
                {
                    "pdb_id": "1Y01",
                    "measurement_type": "Kd",
                    "relation": "=",
                    "raw_value": 49.0,
                    "raw_unit": "uM",
                    "measurement_origin": "pdbbind",
                    "measurement_id": "pdbbind:1",
                    "complex_type": "protein_ligand",
                },
                {
                    "pdb_id": "1Y01",
                    "measurement_type": "Kd",
                    "relation": "=",
                    "raw_value": 49.0,
                    "raw_unit": "uM",
                    "measurement_origin": "pdbbind",
                    "measurement_id": "pdbbind:2",
                    "complex_type": "protein_ligand",
                },
            ]
        }
    )

    assert payload["summary"]["cross_source_duplicate_group_count"] == 0
    assert payload["groups"] == []
