from __future__ import annotations

import pytest

from core.canonical.ligand import CanonicalLigand
from models.multimodal.ligand_encoder import (
    DEFAULT_LIGAND_ENCODER_DIM,
    DEFAULT_LIGAND_ENCODER_MODEL,
    LigandEncoder,
    encode_ligand,
    encode_smiles,
)


def test_ligand_encoder_encodes_canonical_ligand_and_preserves_lineage() -> None:
    ligand = CanonicalLigand(
        ligand_id=" bindingdb:120095 ",
        name=" Example ligand ",
        source="BindingDB",
        source_id=" 120095 ",
        smiles="CCO",
        inchi="InChI=1S/C2H6O/c1-2-3/h2-3H,1H3",
        inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
        formula="C2H6O",
        charge=0,
        synonyms=(" ethanol ", "ethanol", "ethyl alcohol"),
        provenance=("raw/bindingdb/120095.json",),
    )

    result = encode_ligand(ligand, provenance={"run_id": "run-001"})

    assert result.canonical_id == "ligand:bindingdb:120095"
    assert result.ligand_id == "bindingdb:120095"
    assert result.model_name == DEFAULT_LIGAND_ENCODER_MODEL
    assert result.embedding_dim == DEFAULT_LIGAND_ENCODER_DIM
    assert result.source_kind == "ligand_baseline"
    assert result.frozen is True
    assert result.has_chemical_structure is True
    assert result.feature_count == len(result.token_ids)
    assert result.token_ids == (
        "ligand_id",
        "name",
        "source",
        "source_id",
        "smiles",
        "inchi",
        "inchikey",
        "formula",
        "charge",
        "synonyms",
    )
    assert len(result.token_embeddings) == len(result.token_ids)
    assert len(result.pooled_embedding) == DEFAULT_LIGAND_ENCODER_DIM
    assert result.provenance["run_id"] == "run-001"
    assert result.provenance["input_kind"] == "canonical_ligand"
    assert result.provenance["canonical_id"] == "ligand:bindingdb:120095"
    assert result.provenance["synonym_count"] == 2
    assert result.provenance["has_chemical_structure"] is True
    assert result.to_dict()["canonical_id"] == "ligand:bindingdb:120095"


def test_ligand_encoder_accepts_mapping_and_smiles_inputs() -> None:
    encoder = LigandEncoder(embedding_dim=4)

    mapping_result = encoder.encode_ligand(
        {
            "ligand_id": "chembl:CHEMBL25",
            "name": " Example mapping ",
            "source": "ChEMBL",
            "source_id": " CHEMBL25 ",
            "smiles": "c1ccccc1",
            "synonyms": ["benzene", "benzene", "cyclohexatriene"],
        },
        provenance={"request_id": "mapping"},
    )
    smiles_result = encode_smiles(
        " c1ccccc1 ",
        provenance={"request_id": "smiles"},
        name="Benzene",
    )

    assert mapping_result.canonical_id == "ligand:chembl:CHEMBL25"
    assert mapping_result.source == "CHEMBL"
    assert mapping_result.source_id == "CHEMBL25"
    assert mapping_result.token_ids == (
        "ligand_id",
        "name",
        "source",
        "source_id",
        "smiles",
        "synonyms",
    )
    assert len(mapping_result.pooled_embedding) == 4
    assert mapping_result.provenance["request_id"] == "mapping"
    assert mapping_result.provenance["input_kind"] == "mapping"
    assert smiles_result.canonical_id.startswith("ligand:smiles:")
    assert smiles_result.smiles == "c1ccccc1"
    assert smiles_result.source == "smiles"
    assert smiles_result.source_id == "c1ccccc1"
    assert smiles_result.provenance["request_id"] == "smiles"
    assert smiles_result.provenance["input_kind"] == "smiles"


def test_ligand_encoder_rejects_empty_smiles() -> None:
    encoder = LigandEncoder()

    with pytest.raises(ValueError, match="smiles must not be empty"):
        encoder.encode_smiles("   ")
