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
    SummaryRecordContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _protein_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:protein:test",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P1",
                protein_ref="protein:P1",
                protein_name="Protein 1",
                organism_name="Homo sapiens",
                taxon_id=9606,
                sequence_checksum="seq:p1",
                sequence_version="1",
                sequence_length=100,
                join_status="joined",
            ),
        ),
    )


def _variant_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:variant:test",
        schema_version=2,
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P1:A10V",
                protein_ref="protein:P1",
                variant_signature="A10V",
                variant_kind="point_mutation",
                mutation_list=("A10V",),
                sequence_delta_signature="A10V",
                organism_name="Homo sapiens",
                taxon_id=9606,
                join_status="joined",
                context=SummaryRecordContext(storage_tier="feature_cache"),
            ),
        ),
    )


def _structure_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:structure:test",
        schema_version=2,
        records=(
            StructureUnitSummaryRecord(
                summary_id="structure_unit:protein:P1:1ABC:A",
                protein_ref="protein:P1",
                structure_source="PDB",
                structure_id="1ABC",
                chain_id="A",
                structure_kind="experimental_chain",
                experimental_or_predicted="experimental",
                residue_span_start=1,
                residue_span_end=100,
                join_status="joined",
                context=SummaryRecordContext(storage_tier="feature_cache"),
            ),
        ),
    )


def test_export_entity_signature_preview(tmp_path: Path) -> None:
    protein_path = tmp_path / "protein_summary_library.json"
    variant_path = tmp_path / "protein_variant_summary_library.json"
    structure_path = tmp_path / "structure_unit_summary_library.json"
    output_json = tmp_path / "entity_signature_preview.json"
    output_md = tmp_path / "entity_signature_preview.md"

    protein_path.write_text(
        json.dumps(_protein_library().to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    variant_path.write_text(
        json.dumps(_variant_library().to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    structure_path.write_text(
        json.dumps(_structure_library().to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_entity_signature_preview.py"),
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
    assert payload["summary"]["entity_family_counts"] == {
        "protein": 1,
        "protein_variant": 1,
        "structure_unit": 1,
    }
    assert payload["summary"]["protein_spine_count"] == 1
    assert payload["summary"]["variant_delta_group_count"] == 1
    assert payload["summary"]["structure_chain_group_count"] == 1
    assert payload["truth_boundary"]["ligand_groups_materialized"] is False
    assert "Entity Signature Preview" in output_md.read_text(encoding="utf-8")
