from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import ProteinSummaryRecord, SummaryLibrarySchema

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_export_protein_variant_summary_library_cli(tmp_path: Path) -> None:
    protein_library = SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="manifest:protein",
        records=(_protein_record("P04637"),),
    )
    protein_library_path = tmp_path / "protein_summary_library.json"
    protein_library_path.write_text(
        json.dumps(protein_library.to_dict(), indent=2),
        encoding="utf-8",
    )

    evidence_path = tmp_path / "variant_evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "support_scope": {
                    "supported_accessions": ["P04637"],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    uniprot_dir = tmp_path / "uniprot" / "P04637"
    uniprot_dir.mkdir(parents=True, exist_ok=True)
    (uniprot_dir / "P04637.json").write_text(
        json.dumps(
            {
                "features": [
                    {
                        "type": "Natural variant",
                        "featureId": "VAR_TEST",
                        "location": {
                            "start": {"value": 17, "modifier": "EXACT"},
                            "end": {"value": 17, "modifier": "EXACT"},
                        },
                        "alternativeSequence": {
                            "originalSequence": "E",
                            "alternativeSequences": ["K"],
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    mutation_path = tmp_path / "mutation.tsv"
    mutation_path.write_text(
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
                "",
            )
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "protein_variant_summary_library.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_protein_variant_summary_library.py"),
            "--protein-summary-library",
            str(protein_library_path),
            "--variant-evidence",
            str(evidence_path),
            "--uniprot-root",
            str(tmp_path / "uniprot"),
            "--intact-mutation-path",
            str(mutation_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["library_id"] == "summary-library:protein-variants:v1"
    assert payload["record_count"] == 1
    assert payload["records"][0]["variant_signature"] == "E17K"
    assert payload["records"][0]["join_reason"] == "uniprot_plus_intact_variant"
