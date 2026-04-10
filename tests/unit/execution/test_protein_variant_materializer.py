from __future__ import annotations

import json
from pathlib import Path

from core.library.summary_record import ProteinSummaryRecord, SummaryLibrarySchema
from execution.library.protein_variant_materializer import (
    build_protein_variant_summary_library,
    materialize_protein_variant_records,
)


def _protein_record(accession: str) -> ProteinSummaryRecord:
    return ProteinSummaryRecord(
        summary_id=f"protein:{accession}",
        protein_ref=f"protein:{accession}",
        protein_name=f"Protein {accession}",
        organism_name="Homo sapiens",
        taxon_id=9606,
        sequence_checksum=f"checksum:{accession}",
        sequence_version="1",
        sequence_length=100,
        aliases=(accession,),
    )


def _write_uniprot_payload(root: Path, accession: str) -> None:
    payload = {
        "features": [
            {
                "type": "Natural variant",
                "featureId": "VAR_TEST",
                "location": {
                    "start": {"value": 17, "modifier": "EXACT"},
                    "end": {"value": 17, "modifier": "EXACT"},
                },
                "description": "example natural variant",
                "evidences": [{"source": "PubMed", "id": "12345"}],
                "alternativeSequence": {
                    "originalSequence": "E",
                    "alternativeSequences": ["K"],
                },
            },
            {
                "type": "Alternative sequence",
                "featureId": "VSP_TEST",
                "location": {
                    "start": {"value": 1, "modifier": "EXACT"},
                    "end": {"value": 4, "modifier": "EXACT"},
                },
                "description": "in isoform 2",
                "alternativeSequence": {
                    "originalSequence": "MPEP",
                    "alternativeSequences": ["AAAA"],
                },
            },
        ]
    }
    directory = root / accession
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{accession}.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_mutation_tsv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "\t".join(
                    [
                        "#Feature AC",
                        "Feature short label",
                        "Feature range(s)",
                        "Original sequence",
                        "Resulting sequence",
                        "Feature type",
                        "Feature annotation",
                        "Affected protein AC",
                        "Affected protein symbol",
                        "Affected protein full name",
                        "Affected protein organism",
                        "Interaction participants",
                        "PubMedID",
                        "Figure legend",
                        "Interaction AC",
                    ]
                ),
                "\t".join(
                    [
                        "EBI-1",
                        "P04637:p.Glu17Lys",
                        "17-17",
                        "E",
                        "K",
                        "mutation(MI:0118)",
                        "",
                        "uniprotkb:P04637",
                        "TP53",
                        "Tumor protein p53",
                        "9606 - Homo sapiens",
                        "",
                        "12345",
                        "",
                        "EBI-123",
                    ]
                ),
                "\t".join(
                    [
                        "EBI-2",
                        "P04637:p.[Arg273His;Pro309Ser]",
                        "273-273",
                        "R",
                        "H",
                        "mutation(MI:0118)",
                        "",
                        "uniprotkb:P04637",
                        "TP53",
                        "Tumor protein p53",
                        "9606 - Homo sapiens",
                        "",
                        "23456",
                        "",
                        "EBI-456",
                    ]
                ),
                "\t".join(
                    [
                        "EBI-3",
                        "P04637:p.[Arg273His;Pro309Ser]",
                        "309-309",
                        "P",
                        "S",
                        "mutation(MI:0118)",
                        "",
                        "uniprotkb:P04637",
                        "TP53",
                        "Tumor protein p53",
                        "9606 - Homo sapiens",
                        "",
                        "23456",
                        "",
                        "EBI-456",
                    ]
                ),
                "",
            )
        ),
        encoding="utf-8",
    )


def test_materialize_protein_variant_records_merges_uniprot_and_intact(tmp_path: Path) -> None:
    _write_uniprot_payload(tmp_path / "uniprot", "P04637")
    _write_mutation_tsv(tmp_path / "intact" / "mutation.tsv")
    library = SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="manifest:protein",
        records=(
            _protein_record("P04637"),
            _protein_record("Q99999"),
        ),
    )

    records = materialize_protein_variant_records(
        library,
        uniprot_root=tmp_path / "uniprot",
        intact_mutation_path=tmp_path / "intact" / "mutation.tsv",
        supported_accessions=("P04637",),
    )

    signatures = {record.variant_signature: record for record in records}
    assert "E17K" in signatures
    assert "R273H;P309S" in signatures
    assert "isoform:VSP_TEST:1-4" in signatures

    merged = signatures["E17K"]
    assert merged.join_reason == "uniprot_plus_intact_variant"
    assert {pointer.source_name for pointer in merged.context.provenance_pointers} == {
        "UniProt",
        "IntAct",
    }
    assert merged.variant_kind == "point_mutation"

    isoform = signatures["isoform:VSP_TEST:1-4"]
    assert isoform.variant_kind == "isoform_variant"
    assert isoform.is_partial is False


def test_build_protein_variant_summary_library_wraps_records(tmp_path: Path) -> None:
    _write_uniprot_payload(tmp_path / "uniprot", "P04637")
    _write_mutation_tsv(tmp_path / "intact" / "mutation.tsv")
    protein_library = SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="manifest:protein",
        records=(_protein_record("P04637"),),
    )

    variant_library = build_protein_variant_summary_library(
        protein_library,
        supported_accessions=("P04637",),
        uniprot_root=tmp_path / "uniprot",
        intact_mutation_path=tmp_path / "intact" / "mutation.tsv",
    )

    assert variant_library.schema_version == 2
    assert variant_library.record_count == 3
    assert variant_library.variant_records[0].record_type == "protein_variant"
    assert "IntActMutation" in (variant_library.source_manifest_id or "")


def test_materialize_protein_variant_records_discovers_timestamped_uniprot_roots(
    tmp_path: Path,
) -> None:
    _write_uniprot_payload(tmp_path / "uniprot" / "20260323T154140Z", "P69905")
    _write_mutation_tsv(tmp_path / "intact" / "mutation.tsv")
    library = SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="manifest:protein",
        records=(_protein_record("P69905"),),
    )

    records = materialize_protein_variant_records(
        library,
        uniprot_root=tmp_path / "uniprot",
        intact_mutation_path=tmp_path / "intact" / "mutation.tsv",
        supported_accessions=("P69905",),
    )

    assert len(records) == 2
    assert {record.variant_signature for record in records} == {"E17K", "isoform:VSP_TEST:1-4"}
