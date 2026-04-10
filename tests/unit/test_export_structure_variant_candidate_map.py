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


def test_export_structure_variant_candidate_map(tmp_path: Path) -> None:
    variant_library = SummaryLibrarySchema(
        library_id="summary-library:protein-variants:v1",
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P68871:A11D",
                protein_ref="protein:P68871",
                variant_signature="A11D",
                variant_kind="point_mutation",
                mutation_list=("A11D",),
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
        library_id="summary-library:structure-units:v1",
        records=(
            StructureUnitSummaryRecord(
                summary_id="structure_unit:protein:P68871:4HHB:B",
                protein_ref="protein:P68871",
                structure_source="PDB",
                structure_id="4HHB",
                chain_id="B",
                structure_kind="classification_anchored_chain",
                experimental_or_predicted="experimental",
            ),
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
    variant_path = tmp_path / "variants.json"
    structure_path = tmp_path / "structures.json"
    variant_path.write_text(json.dumps(variant_library.to_dict(), indent=2), encoding="utf-8")
    structure_path.write_text(
        json.dumps(structure_library.to_dict(), indent=2),
        encoding="utf-8",
    )
    output_json = tmp_path / "candidate_map.json"
    output_md = tmp_path / "candidate_map.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_variant_candidate_map.py"),
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
    assert payload["candidate_count"] == 2
    assert payload["truth_boundary"]["direct_structure_backed_variant_join_materialized"] is False
    assert [row["protein_ref"] for row in payload["candidate_rows"]] == [
        "protein:P68871",
        "protein:P69905",
    ]
    assert all(
        row["candidate_status"] == "candidate_only_no_variant_anchor"
        for row in payload["candidate_rows"]
    )
