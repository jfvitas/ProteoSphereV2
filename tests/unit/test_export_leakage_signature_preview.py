from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import (
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_leakage_signature_preview(tmp_path: Path) -> None:
    protein_library = SummaryLibrarySchema(
        library_id="summary-library:protein:v1",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P04637",
                protein_ref="protein:P04637",
                protein_name="p53",
                organism_name="Homo sapiens",
                taxon_id=9606,
                sequence_checksum="seq-p53",
                sequence_version="1",
                sequence_length=393,
            ),
            ProteinSummaryRecord(
                summary_id="protein:P69905",
                protein_ref="protein:P69905",
                protein_name="HBA",
                organism_name="Homo sapiens",
                taxon_id=9606,
                sequence_checksum="seq-hba",
                sequence_version="1",
                sequence_length=142,
            ),
        ),
    )
    variant_library = SummaryLibrarySchema(
        library_id="summary-library:variant:v1",
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P04637:R175H",
                protein_ref="protein:P04637",
                variant_signature="R175H",
                variant_kind="point_mutation",
                mutation_list=("R175H",),
            ),
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P69905:A111D",
                protein_ref="protein:P69905",
                variant_signature="A111D",
                variant_kind="point_mutation",
                mutation_list=("A111D",),
            ),
        ),
    )
    structure_library = SummaryLibrarySchema(
        library_id="summary-library:structure:v1",
        records=(
            StructureUnitSummaryRecord(
                summary_id="structure_unit:protein:P69905:4HHB:A",
                protein_ref="protein:P69905",
                structure_source="PDB",
                structure_id="4HHB",
                chain_id="A",
                structure_kind="classification_anchored_chain",
                experimental_or_predicted="experimental",
            ),
        ),
    )
    candidate_map = {
        "candidate_rows": [
            {
                "protein_ref": "protein:P69905",
                "candidate_status": "candidate_only_no_variant_anchor",
            }
        ]
    }

    protein_path = tmp_path / "proteins.json"
    variant_path = tmp_path / "variants.json"
    structure_path = tmp_path / "structures.json"
    candidate_path = tmp_path / "candidate_map.json"
    protein_path.write_text(json.dumps(protein_library.to_dict(), indent=2), encoding="utf-8")
    variant_path.write_text(json.dumps(variant_library.to_dict(), indent=2), encoding="utf-8")
    structure_path.write_text(
        json.dumps(structure_library.to_dict(), indent=2),
        encoding="utf-8",
    )
    candidate_path.write_text(json.dumps(candidate_map, indent=2), encoding="utf-8")
    output_json = tmp_path / "preview.json"
    output_md = tmp_path / "preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_leakage_signature_preview.py"),
            "--protein-library",
            str(protein_path),
            "--variant-library",
            str(variant_path),
            "--structure-library",
            str(structure_path),
            "--candidate-map",
            str(candidate_path),
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
    assert payload["row_count"] == 2
    assert payload["summary"]["candidate_overlap_accessions"] == ["P69905"]
    assert payload["summary"]["structure_followup_accessions"] == ["P04637"]
    assert payload["summary"]["protein_only_accessions"] == []
