from __future__ import annotations

import pytest

from connectors.uniprot.parsers import (
    UniProtSequenceRecord,
    parse_uniprot_entry,
    parse_uniprot_fasta,
    parse_uniprot_text,
)


def test_parse_uniprot_entry_extracts_sequence_metadata():
    record = parse_uniprot_entry(
        {
            "primaryAccession": "P12345",
            "uniProtkbId": "ABC_HUMAN",
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Example protein"}},
            },
            "genes": [
                {
                    "geneName": {"value": "ABC"},
                    "synonyms": [{"value": "XYZ"}],
                }
            ],
            "organism": {"scientificName": "Homo sapiens"},
            "sequence": {"value": "MEEP QSDPSV", "length": 10},
        }
    )

    assert isinstance(record, UniProtSequenceRecord)
    assert record.accession == "P12345"
    assert record.entry_name == "ABC_HUMAN"
    assert record.protein_name == "Example protein"
    assert record.organism_name == "Homo sapiens"
    assert record.gene_names == ("ABC", "XYZ")
    assert record.reviewed is True
    assert record.sequence == "MEEPQSDPSV"
    assert record.sequence_length == 10
    assert record.source_format == "json"


def test_parse_uniprot_fasta_reads_header_and_sequence():
    record = parse_uniprot_fasta(
        ">sp|A0A024RBG1|A0A024RBG1_HUMAN Example protein [Homo sapiens]\n"
        "MEEPQSDP\n"
        "SV\n"
    )

    assert record.accession == "A0A024RBG1"
    assert record.entry_name == "A0A024RBG1_HUMAN"
    assert record.protein_name == "Example protein"
    assert record.organism_name == "Homo sapiens"
    assert record.reviewed is True
    assert record.sequence == "MEEPQSDPSV"
    assert record.sequence_length == 10
    assert record.source_format == "fasta"


def test_parse_uniprot_text_reads_flat_file_sections():
    record = parse_uniprot_text(
        "ID   A0A024RBG1_HUMAN Reviewed; 10 AA.\n"
        "AC   A0A024RBG1;\n"
        "DE   RecName: Full=Example protein;\n"
        "GN   Name=ABC; Synonyms=XYZ;\n"
        "OS   Homo sapiens (Human).\n"
        "SQ   SEQUENCE   10 AA;  1234 MW;  1234 CRC64;\n"
        "     MEEP QSDP SV\n"
        "//\n"
    )

    assert record.accession == "A0A024RBG1"
    assert record.entry_name == "A0A024RBG1_HUMAN"
    assert record.protein_name == "Example protein"
    assert record.organism_name == "Homo sapiens (Human)"
    assert record.gene_names == ("ABC", "XYZ")
    assert record.reviewed is True
    assert record.sequence == "MEEPQSDPSV"
    assert record.sequence_length == 10
    assert record.source_format == "text"


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        parse_uniprot_fasta("not a fasta payload")

    with pytest.raises(ValueError):
        parse_uniprot_text("ID   TEST_HUMAN Reviewed; 10 AA.\n//\n")
