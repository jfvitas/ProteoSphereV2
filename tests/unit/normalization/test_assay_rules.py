from __future__ import annotations

from normalization.conflicts.assay_rules import merge_assay_records


def test_merge_assay_records_resolves_clean_merge() -> None:
    result = merge_assay_records(
        [
            {
                "target": "P12345",
                "ligand": "LIG-001",
                "value": 10.0,
                "type": "Ki",
                "unit": "nM",
                "confidence": 0.9,
                "source": "BindingDB",
                "source_id": "BDB-1",
                "provenance_refs": ["bindingdb:1"],
            },
            {
                "target": "P12345",
                "ligand": "LIG-001",
                "value": "10",
                "type": "Ki",
                "unit": "nm",
                "confidence": 0.8,
                "source": "curated",
                "source_id": "CUR-1",
                "provenance": ["curated:1"],
            },
        ]
    )

    assert result.status == "resolved"
    assert result.is_resolved
    assert result.resolved_assay is not None
    assert result.resolved_assay.target_id == "P12345"
    assert result.resolved_assay.ligand_id == "LIG-001"
    assert result.resolved_assay.measurement_type == "Ki"
    assert result.resolved_assay.measurement_value == 10.0
    assert result.resolved_assay.measurement_unit == "nM"
    assert result.provenance_refs == ("bindingdb:1", "curated:1")
    assert result.conflicts == ()


def test_merge_assay_records_normalizes_units_before_comparison() -> None:
    result = merge_assay_records(
        [
            {
                "target": "P12345",
                "ligand": "LIG-002",
                "value": 10.0,
                "type": "Ki",
                "unit": "nM",
                "provenance_refs": ["src:nm"],
            },
            {
                "target": "P12345",
                "ligand": "LIG-002",
                "value": 0.01,
                "type": "Ki",
                "unit": "uM",
                "provenance_refs": ["src:um"],
            },
        ]
    )

    assert result.status == "resolved"
    assert result.resolved_assay is not None
    assert result.resolved_assay.measurement_value == 10.0
    assert result.resolved_assay.measurement_unit == "nM"
    assert [assay.measurement_value for assay in result.evidence_assays] == [10.0, 10.0]
    assert [assay.measurement_unit for assay in result.evidence_assays] == ["nM", "nM"]


def test_merge_assay_records_preserves_provenance_rich_disagreement() -> None:
    result = merge_assay_records(
        [
            {
                "target": "P12345",
                "ligand": "LIG-003",
                "value": 10.0,
                "type": "Ki",
                "unit": "nM",
                "confidence": 0.95,
                "source": "BindingDB",
                "source_id": "BDB-10",
                "provenance_refs": ["bindingdb:10"],
            },
            {
                "target": "P12345",
                "ligand": "LIG-003",
                "value": 12.0,
                "type": "Ki",
                "unit": "nM",
                "confidence": 0.72,
                "source": "ChEMBL",
                "source_id": "CHEMBL-10",
                "provenance_refs": ["chembl:10"],
            },
        ]
    )

    assert result.status == "conflict"
    assert result.resolved_assay is None
    assert result.conflicts[0].kind == "measurement_value_disagreement"
    assert result.conflicts[0].observed_values == ("10 nM", "12 nM")
    assert result.provenance_refs == ("bindingdb:10", "chembl:10")
    assert [observation.measurement_value for observation in result.observations] == [
        10.0,
        12.0,
    ]


def test_merge_assay_records_preserves_unresolved_conflict_records() -> None:
    result = merge_assay_records(
        [
            {
                "target": "P12345",
                "ligand": "LIG-004",
                "value": 10.0,
                "type": "Ki",
                "unit": "nM",
                "provenance_refs": ["src:one"],
            },
            {
                "target": "P12345",
                "ligand": "LIG-004",
                "value": 80.0,
                "type": "Ki",
                "unit": "percent",
                "provenance_refs": ["src:two"],
            },
        ]
    )

    assert result.status == "unresolved"
    assert result.resolved_assay is None
    assert result.conflicts[0].kind == "unit_incompatible"
    assert result.observations[0].measurement_unit == "nM"
    assert result.observations[1].measurement_unit == "percent"
    assert result.provenance_refs == ("src:one", "src:two")
