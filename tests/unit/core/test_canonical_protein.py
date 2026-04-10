import pytest

from core.canonical.protein import CanonicalProtein


def test_canonical_protein_normalizes_identity_and_sequence():
    protein = CanonicalProtein(
        accession="  p12345 ",
        sequence="ac d\nEFg",
        name=" Example protein ",
        gene_names=("GeneA", "GeneA", " GeneB "),
        organism=" Homo sapiens ",
        description="",
        source=" UniProt ",
        aliases=("Alpha", " Alpha ", ""),
        annotations=(" reviewed ", "manual", "manual"),
    )

    assert protein.accession == "P12345"
    assert protein.sequence == "ACDEFG"
    assert protein.canonical_id == "protein:P12345"
    assert protein.canonical_protein_id == "protein:P12345"
    assert protein.sequence_length == 6
    assert protein.name == "Example protein"
    assert protein.gene_names == ("GeneA", "GeneB")
    assert protein.aliases == ("Alpha",)
    assert protein.annotations == ("reviewed", "manual")

    payload = protein.to_dict()
    assert payload["canonical_id"] == "protein:P12345"
    assert payload["canonical_protein_id"] == "protein:P12345"
    assert payload["gene_names"] == ["GeneA", "GeneB"]
    assert payload["aliases"] == ["Alpha"]
    assert payload["sequence_length"] == 6


def test_canonical_protein_from_dict_round_trips():
    protein = CanonicalProtein.from_dict(
        {
            "accession": "q9xyz1",
            "sequence": "MSTNPKPQR",
            "protein_name": "My protein",
            "genes": ["GENE1", "GENE1", "GENE2"],
            "species": "Mus musculus",
            "aliases": ["Alpha", "Beta"],
        }
    )

    assert protein.accession == "Q9XYZ1"
    assert protein.sequence == "MSTNPKPQR"
    assert protein.name == "My protein"
    assert protein.gene_names == ("GENE1", "GENE2")
    assert protein.organism == "Mus musculus"
    assert protein.aliases == ("Alpha", "Beta")
    assert protein.to_dict()["accession"] == "Q9XYZ1"


def test_canonical_protein_rejects_invalid_sequence():
    with pytest.raises(ValueError, match="invalid residue"):
        CanonicalProtein(accession="P12345", sequence="MST*NP")
