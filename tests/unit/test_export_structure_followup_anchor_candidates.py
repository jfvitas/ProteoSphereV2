from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import (
    ProteinVariantSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _variant_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:protein-variants:test",
        schema_version=2,
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P04637:A119D",
                protein_ref="protein:P04637",
                variant_signature="A119D",
                variant_kind="point_mutation",
                mutation_list=("A119D",),
                join_status="joined",
                join_reason="test",
                organism_name="Homo sapiens",
                taxon_id=9606,
                context=SummaryRecordContext(storage_tier="feature_cache"),
            ),
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P04637:R248Q",
                protein_ref="protein:P04637",
                variant_signature="R248Q",
                variant_kind="point_mutation",
                mutation_list=("R248Q",),
                join_status="joined",
                join_reason="test",
                organism_name="Homo sapiens",
                taxon_id=9606,
                context=SummaryRecordContext(storage_tier="feature_cache"),
            ),
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P31749:E17K",
                protein_ref="protein:P31749",
                variant_signature="E17K",
                variant_kind="point_mutation",
                mutation_list=("E17K",),
                join_status="joined",
                join_reason="test",
                organism_name="Homo sapiens",
                taxon_id=9606,
                context=SummaryRecordContext(storage_tier="feature_cache"),
            ),
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P31749:bad",
                protein_ref="protein:P31749",
                variant_signature="fusion_variant",
                variant_kind="construct",
                mutation_list=("fusion_variant",),
                join_status="partial",
                join_reason="test",
                organism_name="Homo sapiens",
                taxon_id=9606,
                context=SummaryRecordContext(storage_tier="feature_cache"),
            ),
        ),
    )


def test_export_structure_followup_anchor_candidates(tmp_path: Path) -> None:
    variant_library_path = tmp_path / "protein_variant_summary_library.json"
    variant_library_path.write_text(
        json.dumps(_variant_library().to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )

    operator_matrix = {
        "summary": {
            "high_priority_accessions": ["P04637", "P31749"],
        },
        "rows": [],
    }
    operator_matrix_path = tmp_path / "summary_library_operator_accession_matrix.json"
    operator_matrix_path.write_text(json.dumps(operator_matrix), encoding="utf-8")

    rcsb_root = tmp_path / "rcsb_pdbe"
    alphafold_root = tmp_path / "alphafold"
    (rcsb_root / "20260401T000000Z" / "P04637").mkdir(parents=True)
    (rcsb_root / "20260401T000000Z" / "P31749").mkdir(parents=True)
    (alphafold_root / "20260401T000000Z" / "P04637").mkdir(parents=True)
    (alphafold_root / "20260401T000000Z" / "P31749").mkdir(parents=True)

    (rcsb_root / "20260401T000000Z" / "P04637" / "P04637.best_structures.json").write_text(
        json.dumps(
            [
                {
                    "pdb_id": "9r2q",
                    "chain_id": "K",
                    "experimental_method": "Electron Microscopy",
                    "resolution": 3.2,
                    "coverage": 1.0,
                    "unp_start": 1,
                    "unp_end": 393,
                }
            ]
        ),
        encoding="utf-8",
    )
    (rcsb_root / "20260401T000000Z" / "P31749" / "P31749.best_structures.json").write_text(
        json.dumps(
            [
                {
                    "pdb_id": "7nh5",
                    "chain_id": "A",
                    "experimental_method": "X-ray diffraction",
                    "resolution": 1.9,
                    "coverage": 0.927,
                    "unp_start": 2,
                    "unp_end": 446,
                }
            ]
        ),
        encoding="utf-8",
    )
    (alphafold_root / "20260401T000000Z" / "P04637" / "P04637.prediction.json").write_text(
        json.dumps(
            [
                {
                    "uniprotAccession": "P04637",
                    "entryId": "AF-P04637-F1",
                    "modelEntityId": "AF-P04637-F1",
                    "globalMetricValue": 75.06,
                    "latestVersion": 6,
                    "sequenceStart": 1,
                    "sequenceEnd": 393,
                    "cifUrl": "https://example/P04637.cif",
                }
            ]
        ),
        encoding="utf-8",
    )
    (alphafold_root / "20260401T000000Z" / "P31749" / "P31749.prediction.json").write_text(
        json.dumps(
            [
                {
                    "uniprotAccession": "P31749",
                    "entryId": "AF-P31749-F1",
                    "modelEntityId": "AF-P31749-F1",
                    "globalMetricValue": 83.06,
                    "latestVersion": 6,
                    "sequenceStart": 1,
                    "sequenceEnd": 480,
                    "cifUrl": "https://example/P31749.cif",
                }
            ]
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "structure_followup_anchor_candidates.json"
    output_md = tmp_path / "structure_followup_anchor_candidates.md"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_structure_followup_anchor_candidates.py"),
            "--variant-library",
            str(variant_library_path),
            "--operator-accession-matrix",
            str(operator_matrix_path),
            "--rcsb-root",
            str(rcsb_root),
            "--alphafold-root",
            str(alphafold_root),
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
    assert payload["row_count"] == 2
    assert payload["summary"]["candidate_accessions"] == ["P04637", "P31749"]
    p53 = next(row for row in payload["rows"] if row["accession"] == "P04637")
    akt1 = next(row for row in payload["rows"] if row["accession"] == "P31749")
    assert p53["recommended_experimental_anchor"]["pdb_id"] == "9R2Q"
    assert [row["variant_signature"] for row in p53["candidate_variant_anchors"]] == [
        "A119D",
        "R248Q",
    ]
    assert akt1["recommended_experimental_anchor"]["pdb_id"] == "7NH5"
    assert [row["variant_signature"] for row in akt1["candidate_variant_anchors"]] == [
        "E17K",
    ]
    assert akt1["variant_position_parse_failures"] == 1
    assert payload["truth_boundary"]["direct_structure_backed_join_materialized"] is False
    assert "structure-backed follow-up candidates" in output_md.read_text(encoding="utf-8")
