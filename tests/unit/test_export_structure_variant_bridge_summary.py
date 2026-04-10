from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import (
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_structure_variant_bridge_summary(tmp_path: Path) -> None:
    variant_library = SummaryLibrarySchema(
        library_id="summary-library:protein-variants:v1",
        schema_version=2,
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P68871:V2A",
                protein_ref="protein:P68871",
                parent_protein_ref="protein:P68871",
                variant_signature="V2A",
                variant_kind="point_mutation",
                mutation_list=("V2A",),
                sequence_delta_signature="V2A",
            ),
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P69905:V2E",
                protein_ref="protein:P69905",
                parent_protein_ref="protein:P69905",
                variant_signature="V2E",
                variant_kind="point_mutation",
                mutation_list=("V2E",),
                sequence_delta_signature="V2E",
            ),
        ),
    )
    structure_library = SummaryLibrarySchema(
        library_id="summary-library:structure-units:v1",
        schema_version=2,
        records=(
            StructureUnitSummaryRecord(
                summary_id="structure_unit:protein:P68871:4HHB:B",
                protein_ref="protein:P68871",
                structure_source="PDB",
                structure_id="4HHB",
                structure_kind="classification_anchored_chain",
                chain_id="B",
                experimental_or_predicted="experimental",
            ),
            StructureUnitSummaryRecord(
                summary_id="structure_unit:protein:P69905:4HHB:A",
                protein_ref="protein:P69905",
                structure_source="PDB",
                structure_id="4HHB",
                structure_kind="classification_anchored_chain",
                chain_id="A",
                experimental_or_predicted="experimental",
            ),
        ),
    )
    variant_path = tmp_path / "variant.json"
    structure_path = tmp_path / "structure.json"
    variant_path.write_text(json.dumps(variant_library.to_dict(), indent=2), encoding="utf-8")
    structure_path.write_text(
        json.dumps(structure_library.to_dict(), indent=2),
        encoding="utf-8",
    )
    output_json = tmp_path / "bridge.json"
    output_md = tmp_path / "bridge.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_variant_bridge_summary.py"),
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
    assert payload["overlap_protein_count"] == 2
    assert payload["overlap_rows"][0]["protein_ref"] == "protein:P68871"
    assert payload["overlap_rows"][1]["protein_ref"] == "protein:P69905"
