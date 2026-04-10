from __future__ import annotations

import pytest

import features.rdkit_descriptors as rdkit_descriptors


class _FakeMol:
    pass


class _FakeChem:
    @staticmethod
    def MolFromSmiles(smiles: str):
        if smiles == "invalid":
            return None
        return _FakeMol()

    @staticmethod
    def MolToSmiles(mol, canonical: bool = True):  # noqa: ARG004
        return "C1CCCCC1"


class _FakeDescriptors:
    @staticmethod
    def MolWt(mol):  # noqa: ARG004
        return 180.0

    @staticmethod
    def ExactMolWt(mol):  # noqa: ARG004
        return 180.123

    @staticmethod
    def HeavyAtomCount(mol):  # noqa: ARG004
        return 12

    @staticmethod
    def NumHeteroatoms(mol):  # noqa: ARG004
        return 4


class _FakeLipinski:
    @staticmethod
    def NumRotatableBonds(mol):  # noqa: ARG004
        return 3

    @staticmethod
    def NumHDonors(mol):  # noqa: ARG004
        return 1

    @staticmethod
    def NumHAcceptors(mol):  # noqa: ARG004
        return 2


class _FakeRDMolDescriptors:
    @staticmethod
    def CalcNumRings(mol):  # noqa: ARG004
        return 1

    @staticmethod
    def CalcNumAromaticRings(mol):  # noqa: ARG004
        return 1

    @staticmethod
    def CalcTPSA(mol):  # noqa: ARG004
        return 42.0

    @staticmethod
    def CalcFractionCSP3(mol):  # noqa: ARG004
        return 0.5


class _FakeCrippen:
    @staticmethod
    def MolLogP(mol):  # noqa: ARG004
        return 2.3


def _install_fake_rdkit(monkeypatch):
    fake_modules = rdkit_descriptors._RDKitModules(
        Chem=_FakeChem,
        Descriptors=_FakeDescriptors,
        Lipinski=_FakeLipinski,
        rdMolDescriptors=_FakeRDMolDescriptors,
        Crippen=_FakeCrippen,
    )
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_CACHE", fake_modules)
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_IMPORT_FAILED", False)


def test_describe_smiles_uses_rdkit_style_modules(monkeypatch):
    _install_fake_rdkit(monkeypatch)

    result = rdkit_descriptors.describe_smiles("CCO")

    assert result.smiles == "CCO"
    assert result.canonical_smiles == "C1CCCCC1"
    assert result.descriptors["molecular_weight"] == 180.0
    assert result.descriptors["exact_molecular_weight"] == 180.123
    assert result.descriptors["heavy_atom_count"] == 12
    assert result.descriptors["h_bond_acceptors"] == 2
    assert result.to_dict()["source"] == "rdkit"
    assert result.provenance["backend"] == "_RDKitModules"
    assert result.to_dict()["provenance"]["input_kind"] == "smiles"


def test_describe_smiles_rejects_invalid_smiles(monkeypatch):
    _install_fake_rdkit(monkeypatch)

    with pytest.raises(ValueError, match="Invalid SMILES"):
        rdkit_descriptors.describe_smiles("invalid")


def test_describe_smiles_raises_clear_blocker_when_rdkit_missing(monkeypatch):
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_CACHE", None)
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_IMPORT_FAILED", True)

    with pytest.raises(rdkit_descriptors.RdkitUnavailableError, match="RDKit is not available"):
        rdkit_descriptors.describe_smiles("CCO")


def test_rdkit_available_reflects_import_state(monkeypatch):
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_CACHE", None)
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_IMPORT_FAILED", True)

    assert rdkit_descriptors.rdkit_available() is False
