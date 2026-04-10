from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "core" / "canonical" / "ligand.py"
SPEC = importlib.util.spec_from_file_location("canonical_ligand", MODULE_PATH)
assert SPEC and SPEC.loader
ligand_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ligand_module
SPEC.loader.exec_module(ligand_module)

CanonicalLigand = ligand_module.CanonicalLigand
validate_ligand_payload = ligand_module.validate_ligand_payload


def test_canonical_ligand_normalizes_and_serializes():
    ligand = CanonicalLigand(
        ligand_id=" lig-0001 ",
        name=" ATP ",
        source="bindingdb",
        source_id=" BDBM12345 ",
        smiles=" C1=NC=NC2= ",
        inchikey="  ZZZ  ",
        charge=0,
        synonyms=("ATP", " ATP ", "adenosine triphosphate"),
        provenance=("bindingdb", " bindingdb "),
    )

    assert ligand.ligand_id == "lig-0001"
    assert ligand.name == "ATP"
    assert ligand.source == "BINDINGDB"
    assert ligand.source_id == "BDBM12345"
    assert ligand.has_chemical_structure
    assert ligand.synonyms == ("ATP", "adenosine triphosphate")
    assert ligand.provenance == ("bindingdb",)
    assert ligand.to_dict()["charge"] == 0


def test_validate_ligand_payload_accepts_canonical_mapping():
    ligand = validate_ligand_payload(
        {
            "ligand_id": "lig-0002",
            "name": "NAD+",
            "source": "pubchem",
            "source_id": "1234",
            "inchi": "InChI=1S/C10H14N5O7P2",
            "synonyms": ["NAD+", "nicotinamide adenine dinucleotide"],
            "provenance": ["pubchem"],
        }
    )

    assert isinstance(ligand, CanonicalLigand)
    assert ligand.source == "PUBCHEM"
    assert ligand.has_chemical_structure
    assert ligand.synonyms == ("NAD+", "nicotinamide adenine dinucleotide")


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"ligand_id": "", "name": "A", "source": "B", "source_id": "1"}, "ligand_id"),
        ({"ligand_id": "L1", "name": "", "source": "B", "source_id": "1"}, "name"),
        ({"ligand_id": "L1", "name": "A", "source": "", "source_id": "1"}, "source"),
        ({"ligand_id": "L1", "name": "A", "source": "B", "source_id": ""}, "source_id"),
    ],
)
def test_canonical_ligand_requires_core_fields(kwargs, message):
    with pytest.raises(ValueError, match=message):
        CanonicalLigand(**kwargs)


def test_canonical_ligand_rejects_invalid_charge_type():
    with pytest.raises(TypeError, match="charge"):
        CanonicalLigand(ligand_id="L1", name="A", source="B", source_id="1", charge="0")
