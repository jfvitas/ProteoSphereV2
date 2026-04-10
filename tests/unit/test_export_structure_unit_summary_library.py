from __future__ import annotations

import json
from pathlib import Path

from core.library.summary_record import (
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
    SummaryReference,
)
from scripts.export_structure_unit_summary_library import main


def test_export_structure_unit_summary_library_writes_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "protein_summary_library.json"
    output_json = tmp_path / "structure_unit_summary_library.json"
    output_md = tmp_path / "structure_unit_summary_library.md"
    protein_library = SummaryLibrarySchema(
        library_id="summary-library:protein-materialized:v1",
        source_manifest_id="manifest:test",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P69905",
                protein_ref="protein:P69905",
                context=SummaryRecordContext(
                    domain_references=(
                        SummaryReference(
                            reference_kind="domain",
                            namespace="CATH",
                            identifier="1.10.490.10",
                            source_name="SIFTS",
                            source_record_id="4hhbA00",
                            span_start=2,
                            span_end=142,
                            notes=(
                                "pdb_id:4HHB",
                                "chain:A",
                                "domain_id:4hhbA00",
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    input_path.write_text(json.dumps(protein_library.to_dict(), indent=2), encoding="utf-8")

    exit_code = main(
        [
            "--input",
            str(input_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["record_count"] == 1
    assert payload["records"][0]["record_type"] == "structure_unit"
    assert "Structure Unit Summary Library" in output_md.read_text(encoding="utf-8")
