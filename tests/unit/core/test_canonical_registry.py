from __future__ import annotations

import pytest

from core.canonical.assay import CanonicalAssay
from core.canonical.ligand import CanonicalLigand
from core.canonical.protein import CanonicalProtein
from core.canonical.registry import CanonicalEntityRegistry, UnresolvedCanonicalReference


def make_protein(accession: str = "P12345") -> CanonicalProtein:
    return CanonicalProtein(
        accession=accession,
        sequence="ACDEFGHIK",
        name="Kinase A",
        organism="Homo sapiens",
    )


def make_ligand(ligand_id: str = "LIG-001") -> CanonicalLigand:
    return CanonicalLigand(
        ligand_id=ligand_id,
        name="Ligand A",
        source="BindingDB",
        source_id="5001",
        smiles="CCO",
        inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
        synonyms=("Ligand Alias",),
    )


def make_assay(assay_id: str = "ASSAY-001") -> CanonicalAssay:
    return CanonicalAssay(
        assay_id=assay_id,
        target_id="protein:P12345",
        ligand_id="ligand:LIG-001",
        source="BindingDB",
        source_id="7001",
        measurement_type="IC50",
        measurement_value=42.0,
        measurement_unit="nM",
    )


def test_registry_resolves_canonical_and_stable_aliases() -> None:
    protein = make_protein()
    ligand = make_ligand()
    assay = make_assay()
    registry = CanonicalEntityRegistry(proteins=[protein], ligands=[ligand], assays=[assay])

    assert registry.resolve("protein:P12345") is protein
    assert registry.resolve("uniprot:p12345", entity_type="protein") is protein
    assert registry.resolve("ligand:LIG-001") is ligand
    assert registry.resolve("bindingdb:5001", entity_type="ligand") is ligand
    assert registry.resolve("assay:BINDINGDB:7001") is assay
    assert registry.resolve("bindingdb:7001", entity_type="assay") is assay


def test_registry_returns_explicit_unresolved_placeholder_for_missing_reference() -> None:
    registry = CanonicalEntityRegistry(proteins=[make_protein()])

    unresolved = registry.resolve("missing-protein", entity_type="protein")

    assert isinstance(unresolved, UnresolvedCanonicalReference)
    assert unresolved.reference == "missing-protein"
    assert unresolved.entity_type == "protein"
    assert unresolved.reason == "missing"
    assert unresolved.to_dict()["candidates"] == []


def test_registry_marks_cross_type_ambiguity_instead_of_guessing() -> None:
    protein = make_protein(accession="SHARED1")
    ligand = CanonicalLigand(
        ligand_id="SHARED1",
        name="Shared Identifier Ligand",
        source="BindingDB",
        source_id="801",
    )
    registry = CanonicalEntityRegistry(proteins=[protein], ligands=[ligand])

    resolved = registry.resolve("shared1")

    assert isinstance(resolved, UnresolvedCanonicalReference)
    assert resolved.reason == "ambiguous"
    assert resolved.candidates == ("protein:SHARED1", "ligand:SHARED1")
    assert registry.resolve("shared1", entity_type="protein") is protein
    assert registry.resolve("shared1", entity_type="ligand") is ligand


def test_registry_does_not_resolve_weak_name_aliases() -> None:
    ligand = make_ligand()
    registry = CanonicalEntityRegistry(ligands=[ligand])

    resolved_by_name = registry.resolve("Ligand A", entity_type="ligand")
    resolved_by_synonym = registry.resolve("Ligand Alias", entity_type="ligand")

    assert isinstance(resolved_by_name, UnresolvedCanonicalReference)
    assert resolved_by_name.reason == "missing"
    assert isinstance(resolved_by_synonym, UnresolvedCanonicalReference)
    assert resolved_by_synonym.reason == "missing"


def test_registry_rejects_conflicting_re_registration_for_same_canonical_id() -> None:
    registry = CanonicalEntityRegistry()
    registry.register(make_protein())

    with pytest.raises(ValueError, match="conflicting protein registration"):
        registry.register(
            CanonicalProtein(
                accession="P12345",
                sequence="ACDEFGHIKA",
                name="Kinase B",
                organism="Homo sapiens",
            )
        )


def test_registry_require_and_get_are_conservative() -> None:
    protein = make_protein()
    registry = CanonicalEntityRegistry(proteins=[protein])

    assert registry.get("protein", "P12345") is protein
    assert registry.get("protein", "unknown") is None
    assert registry.require("protein:P12345") is protein
    with pytest.raises(KeyError, match="could not resolve protein reference"):
        registry.require("unknown", entity_type="protein")
