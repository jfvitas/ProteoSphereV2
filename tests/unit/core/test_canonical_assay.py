from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "core" / "canonical" / "assay.py"
SPEC = importlib.util.spec_from_file_location("canonical_assay", MODULE_PATH)
assert SPEC and SPEC.loader
assay_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = assay_module
SPEC.loader.exec_module(assay_module)

CanonicalAssay = assay_module.CanonicalAssay
validate_assay_payload = assay_module.validate_assay_payload


def test_canonical_assay_normalizes_and_serializes():
    assay = CanonicalAssay(
        assay_id=" assay-0001 ",
        target_id=" p12345 ",
        ligand_id=" lig-0001 ",
        source="bindingdb",
        source_id=" BDBM12345 ",
        measurement_type=" ki ",
        measurement_value=7.25,
        measurement_unit=" nm ",
        relation=" <= ",
        assay_conditions=" pH 7.4 ",
        ph=7.4,
        temperature_celsius=25,
        references=(" PMID:1 ", "PMID:1", " DOI:10.1/abc "),
        provenance=(" bindingdb ", "bindingdb"),
    )

    assert assay.assay_id == "assay-0001"
    assert assay.target_id == "p12345"
    assert assay.ligand_id == "lig-0001"
    assert assay.source == "BINDINGDB"
    assert assay.source_id == "BDBM12345"
    assert assay.measurement_type == "ki"
    assert assay.measurement_value == 7.25
    assert assay.measurement_unit == "nm"
    assert assay.relation == "<="
    assert assay.assay_conditions == "pH 7.4"
    assert assay.ph == 7.4
    assert assay.temperature_celsius == 25.0
    assert assay.references == ("PMID:1", "DOI:10.1/abc")
    assert assay.provenance == ("bindingdb",)
    assert assay.canonical_id == "assay:BINDINGDB:BDBM12345"
    assert assay.canonical_assay_id == "assay:BINDINGDB:BDBM12345"
    assert assay.has_quantitative_measurement

    payload = assay.to_dict()
    assert payload["canonical_id"] == "assay:BINDINGDB:BDBM12345"
    assert payload["references"] == ["PMID:1", "DOI:10.1/abc"]
    assert payload["provenance"] == ["bindingdb"]


def test_validate_assay_payload_accepts_canonical_mapping():
    assay = validate_assay_payload(
        {
            "assay_id": "assay-0002",
            "target_id": "Q9XYZ1",
            "ligand_id": "lig-0002",
            "source": "pubchem",
            "source_id": "AID1234",
            "assay_type": "IC50",
            "value": 1.5,
            "unit": "uM",
            "inequality": ">=",
            "conditions": "pH 6.8",
            "pH": 6.8,
            "temperature": 37,
            "citations": ["PMID:2"],
            "evidence": ["pubchem"],
        }
    )

    assert isinstance(assay, CanonicalAssay)
    assert assay.source == "PUBCHEM"
    assert assay.measurement_type == "IC50"
    assert assay.measurement_value == 1.5
    assert assay.has_quantitative_measurement
    assert assay.references == ("PMID:2",)
    assert assay.provenance == ("pubchem",)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (
            {
                "assay_id": "",
                "target_id": "T",
                "ligand_id": "L",
                "source": "S",
                "source_id": "1",
                "measurement_type": "Ki",
            },
            "assay_id",
        ),
        (
            {
                "assay_id": "A",
                "target_id": "",
                "ligand_id": "L",
                "source": "S",
                "source_id": "1",
                "measurement_type": "Ki",
            },
            "target_id",
        ),
        (
            {
                "assay_id": "A",
                "target_id": "T",
                "ligand_id": "",
                "source": "S",
                "source_id": "1",
                "measurement_type": "Ki",
            },
            "ligand_id",
        ),
        (
            {
                "assay_id": "A",
                "target_id": "T",
                "ligand_id": "L",
                "source": "",
                "source_id": "1",
                "measurement_type": "Ki",
            },
            "source",
        ),
        (
            {
                "assay_id": "A",
                "target_id": "T",
                "ligand_id": "L",
                "source": "S",
                "source_id": "",
                "measurement_type": "Ki",
            },
            "source_id",
        ),
        (
            {
                "assay_id": "A",
                "target_id": "T",
                "ligand_id": "L",
                "source": "S",
                "source_id": "1",
                "measurement_type": "",
            },
            "measurement_type",
        ),
    ],
)
def test_canonical_assay_requires_core_fields(kwargs, message):
    with pytest.raises(ValueError, match=message):
        CanonicalAssay(**kwargs)


def test_canonical_assay_rejects_invalid_measurement_type():
    with pytest.raises(TypeError, match="measurement_value"):
        CanonicalAssay(
            assay_id="A1",
            target_id="T1",
            ligand_id="L1",
            source="B",
            source_id="1",
            measurement_type="Ki",
            measurement_value="not-a-number",
        )
