from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_structure_similarity_signature_preview(tmp_path: Path) -> None:
    structure_library = {
        "records": [
            {
                "record_type": "structure_unit",
                "summary_id": "structure_unit:protein:P1:1ABC:A",
                "protein_ref": "protein:P1",
                "structure_source": "PDB",
                "structure_id": "1ABC",
                "chain_id": "A",
                "structure_kind": "classification_anchored_chain",
                "experimental_or_predicted": "experimental",
                "variant_ref": None,
                "residue_span_start": 10,
                "residue_span_end": 90,
                "context": {
                    "domain_references": [
                        {"namespace": "CATH", "identifier": "1.10.10.10"},
                        {"namespace": "SCOPe", "identifier": "a.1.1.1"},
                    ],
                    "source_connections": [
                        {"source_names": ["UniProt", "CATH"]},
                        {"source_names": ["UniProt", "SCOPe"]},
                    ],
                },
            }
        ]
    }
    input_path = tmp_path / "structure_unit_summary_library.json"
    output_json = tmp_path / "structure_similarity_signature_preview.json"
    output_md = tmp_path / "structure_similarity_signature_preview.md"
    input_path.write_text(json.dumps(structure_library), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_similarity_signature_preview.py"),
            "--structure-library",
            str(input_path),
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
    assert payload["summary"]["fold_signature_count"] == 1
    assert payload["summary"]["candidate_only_count"] == 1
    row = payload["rows"][0]
    assert row["structure_ref"] == "1ABC:A"
    assert row["variant_anchor_materialized"] is False
    assert "Structure Similarity Signature Preview" in output_md.read_text(
        encoding="utf-8"
    )
