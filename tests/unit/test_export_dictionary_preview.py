from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import (
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_library(path: Path, library: SummaryLibrarySchema) -> None:
    path.write_text(json.dumps(library.to_dict(), indent=2), encoding="utf-8")


def test_export_dictionary_preview(tmp_path: Path) -> None:
    protein_library = SummaryLibrarySchema(
        library_id="summary-library:protein:v1",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P69905",
                protein_ref="protein:P69905",
                protein_name="Hemoglobin subunit alpha",
                organism_name="Homo sapiens",
                taxon_id=9606,
                sequence_checksum="abc",
                sequence_version="1",
                sequence_length=142,
                context=SummaryRecordContext(
                    motif_references=(
                        {
                            "reference_kind": "motif",
                            "namespace": "PROSITE",
                            "identifier": "PS01033",
                            "label": "GLOBIN",
                            "source_name": "PROSITE",
                            "join_status": "joined",
                        },
                    ),
                    domain_references=(
                        {
                            "reference_kind": "domain",
                            "namespace": "InterPro",
                            "identifier": "IPR000971",
                            "label": "Globin",
                            "source_name": "InterPro",
                            "join_status": "joined",
                        },
                    ),
                    pathway_references=(
                        {
                            "reference_kind": "pathway",
                            "namespace": "Reactome",
                            "identifier": "R-HSA-123",
                            "label": "Hemostasis",
                            "source_name": "Reactome",
                            "join_status": "joined",
                        },
                    ),
                ),
            ),
        ),
    )
    variant_library = SummaryLibrarySchema(library_id="summary-library:variant:v1", records=())
    structure_library = SummaryLibrarySchema(library_id="summary-library:structure:v1", records=())

    protein_path = tmp_path / "proteins.json"
    variant_path = tmp_path / "variants.json"
    structure_path = tmp_path / "structures.json"
    output_json = tmp_path / "dictionary_preview.json"
    output_md = tmp_path / "dictionary_preview.md"
    _write_library(protein_path, protein_library)
    _write_library(variant_path, variant_library)
    _write_library(structure_path, structure_library)

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_dictionary_preview.py"),
            "--protein-library",
            str(protein_path),
            "--variant-library",
            str(variant_path),
            "--structure-library",
            str(structure_path),
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
    assert payload["row_count"] == 3
    assert payload["summary"]["namespace_count"] == 3
    assert payload["summary"]["reference_kind_counts"] == {
        "domain": 1,
        "motif": 1,
        "pathway": 1,
    }
    assert payload["truth_boundary"]["ready_for_bundle_preview"] is True
    assert payload["truth_boundary"]["biological_content_family"] is False
    assert any(row["namespace"] == "InterPro" for row in payload["rows"])
