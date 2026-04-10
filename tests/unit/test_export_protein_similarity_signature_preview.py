from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_protein_similarity_signature_preview(tmp_path: Path) -> None:
    entity_signature_preview = {
        "rows": [
            {
                "entity_family": "protein",
                "accession": "P04637",
                "protein_ref": "protein:P04637",
                "sequence_equivalence_group": "checksum:p53",
            },
            {
                "entity_family": "protein_variant",
                "accession": "P04637",
                "protein_ref": "protein:P04637",
                "sequence_equivalence_group": "protein:P04637",
            },
        ]
    }
    protein_library = {
        "records": [
            {
                "record_type": "protein",
                "summary_id": "protein:P04637",
                "protein_ref": "protein:P04637",
                "protein_name": "Cellular tumor antigen p53",
                "context": {
                    "provenance_pointers": [
                        {"provenance_id": "sequence:P04637", "source_name": "UniProt"}
                    ],
                    "domain_references": [
                        {"label": "P53_DNA_binding", "identifier": "IPR011615"}
                    ],
                    "motif_references": [],
                },
            }
        ]
    }

    entity_path = tmp_path / "entity_signature_preview.json"
    protein_path = tmp_path / "protein_summary_library.json"
    output_json = tmp_path / "protein_similarity_signature_preview.json"
    output_md = tmp_path / "protein_similarity_signature_preview.md"
    entity_path.write_text(json.dumps(entity_signature_preview), encoding="utf-8")
    protein_path.write_text(json.dumps(protein_library), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_protein_similarity_signature_preview.py"),
            "--entity-signature-preview",
            str(entity_path),
            "--protein-library",
            str(protein_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["row_count"] == 1
    assert payload["summary"]["protein_count"] == 1
    assert payload["rows"][0]["protein_similarity_group"] == "checksum:p53"
    assert payload["rows"][0]["family_label"] == "P53_DNA_binding"
    assert payload["truth_boundary"]["ready_for_bundle_preview"] is True
    assert "Protein Similarity Signature Preview" in output_md.read_text(encoding="utf-8")
