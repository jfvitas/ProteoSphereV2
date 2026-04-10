from connectors.rcsb.parsers import (
    RCSBParserError,
    parse_assembly,
    parse_entity,
    parse_entry,
    parse_structure_bundle,
)


def test_parse_entry_normalizes_and_extracts_core_fields():
    record = parse_entry(
        {
            "rcsb_id": "1abc",
            "struct": {"title": "Example structure"},
            "rcsb_entry_info": {
                "experimental_method": ["X-RAY DIFFRACTION", "X-RAY DIFFRACTION"],
                "resolution_combined": [1.85],
            },
            "rcsb_accession_info": {"initial_release_date": "2021-01-01"},
            "rcsb_entry_container_identifiers": {
                "assembly_ids": ["1", "2"],
                "polymer_entity_ids": ["1", "2"],
                "nonpolymer_entity_ids": ["3"],
            },
        }
    )

    assert record.pdb_id == "1ABC"
    assert record.title == "Example structure"
    assert record.experimental_methods == ("X-RAY DIFFRACTION",)
    assert record.resolution == 1.85
    assert record.release_date == "2021-01-01"
    assert record.assembly_ids == ("1", "2")
    assert record.polymer_entity_ids == ("1", "2")
    assert record.nonpolymer_entity_ids == ("3",)


def test_parse_entity_extracts_sequence_and_linked_identifiers():
    record = parse_entity(
        {
            "rcsb_id": "1ABC_1",
            "entity": {"id": "1", "pdbx_description": "Protein kinase"},
            "entity_poly": {
                "type": "polypeptide(L)",
                "pdbx_seq_one_letter_code_can": "MKT",
                "rcsb_sample_sequence_length": 3,
            },
            "rcsb_polymer_entity_container_identifiers": {
                "entry_id": "1ABC",
                "entity_id": "1",
                "auth_asym_ids": ["A", "B"],
                "uniprot_ids": ["P12345", "P12345", "Q9TEST"],
            },
            "rcsb_entity_source_organism": [
                {"scientific_name": "Homo sapiens", "ncbi_taxonomy_id": 9606}
            ],
        }
    )

    assert record.pdb_id == "1ABC"
    assert record.entity_id == "1"
    assert record.description == "Protein kinase"
    assert record.polymer_type == "polypeptide(L)"
    assert record.sequence == "MKT"
    assert record.sequence_length == 3
    assert record.chain_ids == ("A", "B")
    assert record.uniprot_ids == ("P12345", "Q9TEST")
    assert record.organism_names == ("Homo sapiens",)
    assert record.taxonomy_ids == ("9606",)


def test_parse_assembly_extracts_assembly_metadata():
    record = parse_assembly(
        {
            "rcsb_id": "1ABC-1",
            "id": "1",
            "details": "Biological assembly 1",
            "rcsb_assembly_container_identifiers": {
                "entry_id": "1ABC",
                "assembly_id": "1",
                "polymer_entity_ids": ["1"],
                "auth_asym_ids": ["A", "B"],
            },
            "rcsb_assembly_info": {
                "oligomeric_state": "dimer",
                "oligomeric_count": 2,
                "stoichiometry": "A2",
            },
        }
    )

    assert record.pdb_id == "1ABC"
    assert record.assembly_id == "1"
    assert record.method == "Biological assembly 1"
    assert record.oligomeric_state == "dimer"
    assert record.oligomeric_count == 2
    assert record.stoichiometry == "A2"
    assert record.chain_ids == ("A", "B")
    assert record.polymer_entity_ids == ("1",)


def test_parse_structure_bundle_combines_components():
    bundle = parse_structure_bundle(
        {
            "rcsb_id": "1ABC",
            "struct": {"title": "Example structure"},
            "rcsb_entry_info": {"experimental_method": ["X-RAY DIFFRACTION"]},
        },
        [
            {
                "rcsb_id": "1ABC",
                "entity": {"id": "1", "pdbx_description": "Protein kinase"},
                "entity_poly": {"type": "polypeptide(L)", "pdbx_seq_one_letter_code_can": "MKT"},
                "rcsb_polymer_entity_container_identifiers": {
                    "entity_id": "1",
                    "auth_asym_ids": ["A"],
                    "uniprot_ids": ["P12345"],
                },
                "rcsb_entity_source_organism": [
                    {"scientific_name": "Homo sapiens", "ncbi_taxonomy_id": 9606}
                ],
            }
        ],
        [
            {
                "rcsb_id": "1ABC",
                "id": "1",
                "rcsb_assembly_container_identifiers": {
                    "assembly_id": "1",
                    "polymer_entity_ids": ["1"],
                    "auth_asym_ids": ["A"],
                },
            }
        ],
    )

    assert bundle.pdb_id == "1ABC"
    assert bundle.entry.title == "Example structure"
    assert len(bundle.entities) == 1
    assert len(bundle.assemblies) == 1
    assert bundle.chain_to_entity_ids == {"A": ("1",)}


def test_parse_entity_prefers_entry_id_for_live_suffixed_payloads():
    record = parse_entity(
        {
            "rcsb_id": "1CBS_1",
            "rcsb_polymer_entity_container_identifiers": {
                "entry_id": "1CBS",
                "entity_id": "1",
                "auth_asym_ids": ["A"],
            },
        }
    )

    assert record.pdb_id == "1CBS"


def test_parse_assembly_prefers_entry_id_for_live_suffixed_payloads():
    record = parse_assembly(
        {
            "rcsb_id": "1CBS-1",
            "rcsb_assembly_container_identifiers": {
                "entry_id": "1CBS",
                "assembly_id": "1",
                "auth_asym_ids": ["A"],
                "polymer_entity_ids": ["1"],
            },
        }
    )

    assert record.pdb_id == "1CBS"


def test_parse_entry_rejects_bad_identifier():
    try:
        parse_entry({"rcsb_id": "bad"})
    except RCSBParserError as exc:
        assert "valid PDB identifier" in str(exc)
    else:
        raise AssertionError("expected RCSBParserError")
