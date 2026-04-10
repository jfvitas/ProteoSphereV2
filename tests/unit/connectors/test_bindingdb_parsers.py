from __future__ import annotations

from connectors.bindingdb.parsers import (
    BindingDBAssayRecord,
    parse_bindingdb_assay_row,
    parse_bindingdb_assays,
)


def test_parse_bindingdb_assays_normalizes_api_payload():
    payload = [
        {
            "BindingDB Reactant_set_id": "RS123",
            "BindingDB MonomerID": " 120095 ",
            "Ligand SMILES": " CCO ",
            "Ligand InChI Key": "InChIKey=ABCDEF",
            "Target Name": "Mitogen-activated protein kinase 1",
            "UniProtKB/SwissProt": "p28482;Q9XYZ1",
            "PDB": "1abc|2xyz",
            "Affinity Type": "Ki",
            "affinity_value_nM": "2.18E+4 nM",
            "Assay Description": "Competitive inhibition by fluorescence",
            "Publication Date": "2022-03-25",
            "BindingDB Curation Date": "2022-04-01",
        }
    ]

    records = parse_bindingdb_assays(payload, source="getLigandsByPDBs")

    assert len(records) == 1
    record = records[0]
    assert isinstance(record, BindingDBAssayRecord)
    assert record.reactant_set_id == "RS123"
    assert record.monomer_id == "120095"
    assert record.ligand_smiles == "CCO"
    assert record.ligand_inchi_key == "InChIKey=ABCDEF"
    assert record.target_name == "Mitogen-activated protein kinase 1"
    assert record.target_uniprot_ids == ("P28482", "Q9XYZ1")
    assert record.target_pdb_ids == ("1ABC", "2XYZ")
    assert record.affinity_type == "Ki"
    assert record.affinity_value_nM == 21800.0
    assert record.assay_description == "Competitive inhibition by fluorescence"
    assert record.publication_date == "2022-03-25"
    assert record.curation_date == "2022-04-01"
    assert record.source == "getLigandsByPDBs"
    assert record.raw["BindingDB MonomerID"] == " 120095 "


def test_parse_bindingdb_assay_row_preserves_empty_payload_as_none_value():
    record = parse_bindingdb_assay_row(
        {
            "monomerID": "42",
            "uniprot": "P35355",
            "smiles": "CCN",
            "measurement_value": "",
        },
        source="getLigandsByUniprot",
    )

    assert record.monomer_id == "42"
    assert record.target_uniprot_ids == ("P35355",)
    assert record.ligand_smiles == "CCN"
    assert record.affinity_value_nM is None
    assert record.source == "getLigandsByUniprot"


def test_parse_bindingdb_assays_handles_empty_service_payload():
    assert parse_bindingdb_assays("") == []
    assert parse_bindingdb_assays({"records": []}) == []


def test_parse_bindingdb_assays_flattens_live_uniprot_response_shape():
    payload = {
        "getLindsByUniprotResponse": {
            "bdb.hit": "2",
            "bdb.primary": "P31749",
            "bdb.alternative": ["P31749", "B2RAM5"],
            "bdb.affinities": [
                {
                    "bdb.monomerid": 2579,
                    "bdb.smile": "CCO",
                    "bdb.affinity_type": "IC50",
                    "bdb.affinity": " 3.8",
                },
                {
                    "bdb.monomerid": 8727,
                    "bdb.smile": "NCC",
                    "bdb.affinity_type": "Kd",
                    "bdb.affinity": " 20.0",
                },
            ],
        }
    }

    records = parse_bindingdb_assays(payload, source="getLigandsByUniprot")

    assert len(records) == 2
    first, second = records
    assert first.source == "getLigandsByUniprot"
    assert first.monomer_id == "2579"
    assert first.ligand_smiles == "CCO"
    assert first.affinity_type == "IC50"
    assert first.affinity_value_nM == 3.8
    assert first.target_uniprot_ids == ("P31749", "B2RAM5")
    assert first.raw["bdb.primary"] == "P31749"
    assert first.raw["bdb.monomerid"] == 2579
    assert second.monomer_id == "8727"
    assert second.affinity_type == "Kd"
    assert second.affinity_value_nM == 20.0
