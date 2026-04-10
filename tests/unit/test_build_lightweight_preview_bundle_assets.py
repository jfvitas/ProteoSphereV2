from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from core.library.summary_record import (
    ProteinSummaryRecord,
    ProteinVariantSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_library(path: Path, library: SummaryLibrarySchema) -> None:
    path.write_text(json.dumps(library.to_dict(), indent=2), encoding="utf-8")


def test_build_lightweight_preview_bundle_assets(tmp_path: Path) -> None:
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
            ),
        ),
    )
    variant_library = SummaryLibrarySchema(
        library_id="summary-library:variant:v1",
        records=(
            ProteinVariantSummaryRecord(
                summary_id="protein_variant:protein:P69905:A111D",
                protein_ref="protein:P69905",
                variant_signature="A111D",
                variant_kind="point_mutation",
                mutation_list=("A111D",),
                context=SummaryRecordContext(
                    provenance_pointers=(
                        {
                            "provenance_id": "prov-1",
                            "source_name": "UniProt",
                            "join_status": "joined",
                        },
                    ),
                ),
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
    protein_path = tmp_path / "proteins.json"
    variant_path = tmp_path / "variants.json"
    structure_path = tmp_path / "structures.json"
    protein_similarity_signature_preview_path = (
        tmp_path / "protein_similarity_signature_preview.json"
    )
    dictionary_preview_path = tmp_path / "dictionary_preview.json"
    structure_followup_payload_preview_path = (
        tmp_path / "structure_followup_payload_preview.json"
    )
    ligand_support_readiness_preview_path = (
        tmp_path / "ligand_support_readiness_preview.json"
    )
    ligand_identity_pilot_preview_path = tmp_path / "ligand_identity_pilot_preview.json"
    ligand_stage1_validation_panel_preview_path = (
        tmp_path / "ligand_stage1_validation_panel_preview.json"
    )
    ligand_identity_core_materialization_preview_path = (
        tmp_path / "ligand_identity_core_materialization_preview.json"
    )
    ligand_row_materialization_preview_path = (
        tmp_path / "ligand_row_materialization_preview.json"
    )
    ligand_similarity_signature_preview_path = (
        tmp_path / "ligand_similarity_signature_preview.json"
    )
    q9nzd4_bridge_validation_preview_path = (
        tmp_path / "q9nzd4_bridge_validation_preview.json"
    )
    motif_domain_compact_preview_family_path = (
        tmp_path / "motif_domain_compact_preview_family.json"
    )
    kinetics_support_preview_path = tmp_path / "kinetics_support_preview.json"
    structure_signature_preview_path = tmp_path / "structure_similarity_signature_preview.json"
    leakage_group_preview_path = tmp_path / "leakage_group_preview.json"
    _write_library(protein_path, protein_library)
    _write_library(variant_path, variant_library)
    _write_library(structure_path, structure_library)
    protein_similarity_signature_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "signature_id": "protein_similarity:protein:P69905",
                        "protein_ref": "protein:P69905",
                        "accession": "P69905",
                        "protein_similarity_group": "md5:abc",
                        "sequence_equivalence_group": "md5:abc",
                        "similarity_basis": "sequence_equivalence_group",
                        "provenance_ref": "prov-protein-1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    dictionary_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "dictionary_id": "dictionary:domain:InterPro:IPR000971",
                        "reference_kind": "domain",
                        "namespace": "InterPro",
                        "identifier": "IPR000971",
                        "label": "Globin",
                        "source_name": "InterPro",
                        "usage_count": 1,
                        "supporting_record_count": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    structure_followup_payload_preview_path.write_text(
        json.dumps(
            {
                "payload_row_count": 1,
                "payload_rows": [
                    {
                        "accession": "P69905",
                        "protein_ref": "protein:P69905",
                        "variant_ref": "protein_variant:protein:P69905:A111D",
                        "structure_id": "4HHB",
                        "chain_id": "A",
                        "coverage": 1.0,
                        "join_status": "candidate_only",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ligand_support_readiness_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "accession": "P69905",
                        "source_ref": "ligand:P69905",
                        "pilot_role": "lead_anchor",
                        "pilot_lane_status": "rescuable_now",
                        "packet_status": "partial",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ligand_identity_pilot_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "accession": "P69905",
                        "source_ref": "ligand:P69905",
                        "pilot_role": "lead_anchor",
                        "pilot_lane_status": "rescuable_now",
                        "grounded_evidence_kind": "local_chembl_bulk_assay_summary",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ligand_stage1_validation_panel_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "accession": "P69905",
                        "lane_kind": "bulk_assay_anchor",
                        "status": "aligned",
                        "evidence_kind": "local_chembl_bulk_assay_summary",
                        "target_or_structure": "CHEMBL1",
                        "next_truthful_stage": "ingest_local_bulk_assay",
                        "candidate_only": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ligand_identity_core_materialization_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "accession": "P69905",
                        "source_ref": "ligand:P69905",
                        "materialization_status": "grounded_ready_identity_core_candidate",
                        "grounded_evidence_kind": "local_chembl_bulk_assay_summary",
                        "next_truthful_stage": "ingest_local_bulk_assay",
                        "candidate_only": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ligand_row_materialization_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "row_id": "ligand_row:protein:P69905:chembl:CHEMBL1",
                        "accession": "P69905",
                        "protein_ref": "protein:P69905",
                        "source_ref": "ligand:P69905",
                        "ligand_ref": "chembl:CHEMBL1",
                        "ligand_namespace": "ChEMBL",
                        "materialization_status": "grounded_lightweight_ligand_row",
                        "evidence_kind": "local_chembl_bulk_assay_row",
                        "candidate_only": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ligand_similarity_signature_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "signature_id": "ligand_similarity:protein:P69905:CHEMBL1",
                        "entity_ref": "ligand_row:protein:P69905:chembl:CHEMBL1",
                        "protein_ref": "protein:P69905",
                        "accession": "P69905",
                        "ligand_ref": "chembl:CHEMBL1",
                        "exact_ligand_identity_group": "chembl:CHEMBL1",
                        "chemical_series_group": "smiles:abc",
                        "candidate_only": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    q9nzd4_bridge_validation_preview_path.write_text(
        json.dumps(
            {
                "status": "aligned",
                "accession": "Q9NZD4",
                "best_pdb_id": "1Y01",
                "component_id": "CHK",
                "component_role": "primary_binder",
                "matched_pdb_id_count": 3,
                "truth_boundary": {"candidate_only": True},
            }
        ),
        encoding="utf-8",
    )
    motif_domain_compact_preview_family_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "dictionary_id": "dictionary:motif:PROSITE:PS01033",
                        "reference_kind": "motif",
                        "namespace": "PROSITE",
                        "identifier": "PS01033",
                        "label": "GLOBIN",
                        "source_name": "PROSITE",
                        "usage_count": 1,
                        "supporting_record_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    kinetics_support_preview_path.write_text(
        json.dumps(
            {
                "status": "complete",
                "row_count": 1,
                "rows": [
                    {
                        "accession": "P69905",
                        "protein_ref": "protein:P69905",
                        "kinetics_support_status": "supported_now",
                        "support_source_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    structure_signature_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "entity_ref": "structure_unit:protein:P69905:4HHB:A",
                        "protein_ref": "protein:P69905",
                        "structure_ref": "4HHB:A",
                        "fold_signature_id": "foldsig-1",
                        "experimental_or_predicted": "experimental",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    leakage_group_preview_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "linked_group_id": "protein:P69905",
                        "protein_ref": "protein:P69905",
                        "accession": "P69905",
                        "split_name": "test",
                        "leakage_risk_class": "candidate_overlap",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "bundle"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_lightweight_preview_bundle_assets.py"),
            "--protein-library",
            str(protein_path),
            "--variant-library",
            str(variant_path),
            "--structure-library",
            str(structure_path),
            "--protein-similarity-signature-preview",
            str(protein_similarity_signature_preview_path),
            "--dictionary-preview",
            str(dictionary_preview_path),
            "--structure-followup-payload-preview",
            str(structure_followup_payload_preview_path),
            "--ligand-support-readiness-preview",
            str(ligand_support_readiness_preview_path),
            "--ligand-identity-pilot-preview",
            str(ligand_identity_pilot_preview_path),
            "--ligand-stage1-validation-panel-preview",
            str(ligand_stage1_validation_panel_preview_path),
            "--ligand-identity-core-materialization-preview",
            str(ligand_identity_core_materialization_preview_path),
            "--ligand-row-materialization-preview",
            str(ligand_row_materialization_preview_path),
            "--ligand-similarity-signature-preview",
            str(ligand_similarity_signature_preview_path),
            "--q9nzd4-bridge-validation-preview",
            str(q9nzd4_bridge_validation_preview_path),
            "--motif-domain-compact-preview-family",
            str(motif_domain_compact_preview_family_path),
            "--kinetics-support-preview",
            str(kinetics_support_preview_path),
            "--structure-signature-preview",
            str(structure_signature_preview_path),
            "--leakage-group-preview",
            str(leakage_group_preview_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    bundle_path = output_dir / "proteosphere-lite.sqlite.zst"
    manifest_path = output_dir / "proteosphere-lite.release_manifest.json"
    checksum_path = output_dir / "proteosphere-lite.sha256"

    assert bundle_path.exists()
    assert manifest_path.exists()
    assert checksum_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["record_counts"] == {
            "proteins": 1,
            "protein_variants": 1,
            "structures": 1,
            "ligands": 1,
            "ligand_similarity_signatures": 1,
            "dictionaries": 1,
            "structure_followup_payloads": 1,
            "ligand_support_readiness": 1,
            "ligand_identity_pilot": 1,
            "ligand_stage1_validation_panel": 1,
            "ligand_identity_core_materialization_preview": 1,
            "ligand_row_materialization_preview": 1,
            "q9nzd4_bridge_validation_preview": 1,
            "motif_domain_compact_preview_family": 1,
            "kinetics_support_preview": 1,
            "protein_similarity_signatures": 1,
            "structure_similarity_signatures": 1,
            "leakage_groups": 1,
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        sqlite_path = Path(temp_dir) / "bundle.sqlite"
        try:
            import compression.zstd as zstd
        except ModuleNotFoundError:  # pragma: no cover
            import zstandard as zstd  # type: ignore[no-redef]

        with bundle_path.open("rb") as src, sqlite_path.open("wb") as dst:
            if hasattr(zstd, "open"):
                with zstd.open(src, "rb") as reader:  # type: ignore[arg-type]
                    dst.write(reader.read())
            else:  # pragma: no cover
                decompressor = zstd.ZstdDecompressor()
                with decompressor.stream_reader(src) as reader:
                    dst.write(reader.read())

        connection = sqlite3.connect(sqlite_path)
        try:
            protein_count = connection.execute(
                "SELECT COUNT(*) FROM protein_records"
            ).fetchone()[0]
            variant_count = connection.execute(
                "SELECT COUNT(*) FROM protein_variant_records"
            ).fetchone()[0]
            structure_count = connection.execute(
                "SELECT COUNT(*) FROM structure_unit_records"
            ).fetchone()[0]
            ligand_count = connection.execute(
                "SELECT COUNT(*) FROM ligand_records"
            ).fetchone()[0]
            ligand_similarity_signature_count = connection.execute(
                "SELECT COUNT(*) FROM ligand_similarity_signature_records"
            ).fetchone()[0]
            protein_similarity_signature_count = connection.execute(
                "SELECT COUNT(*) FROM protein_similarity_signature_records"
            ).fetchone()[0]
            dictionary_count = connection.execute(
                "SELECT COUNT(*) FROM dictionary_records"
            ).fetchone()[0]
            structure_followup_payload_count = connection.execute(
                "SELECT COUNT(*) FROM structure_followup_payload_preview_records"
            ).fetchone()[0]
            ligand_support_readiness_count = connection.execute(
                "SELECT COUNT(*) FROM ligand_support_readiness_records"
            ).fetchone()[0]
            ligand_identity_pilot_count = connection.execute(
                "SELECT COUNT(*) FROM ligand_identity_pilot_records"
            ).fetchone()[0]
            ligand_stage1_validation_panel_count = connection.execute(
                "SELECT COUNT(*) FROM ligand_stage1_validation_panel_records"
            ).fetchone()[0]
            ligand_identity_core_materialization_count = connection.execute(
                "SELECT COUNT(*) FROM ligand_identity_core_materialization_preview_records"
            ).fetchone()[0]
            q9nzd4_bridge_validation_preview_count = connection.execute(
                "SELECT COUNT(*) FROM q9nzd4_bridge_validation_preview_records"
            ).fetchone()[0]
            motif_domain_compact_preview_count = connection.execute(
                "SELECT COUNT(*) FROM motif_domain_compact_preview_records"
            ).fetchone()[0]
            structure_signature_count = connection.execute(
                "SELECT COUNT(*) FROM structure_similarity_signature_records"
            ).fetchone()[0]
            leakage_group_count = connection.execute(
                "SELECT COUNT(*) FROM leakage_group_records"
            ).fetchone()[0]
        finally:
            connection.close()

    assert protein_count == 1
    assert variant_count == 1
    assert structure_count == 1
    assert ligand_count == 1
    assert ligand_similarity_signature_count == 1
    assert dictionary_count == 1
    assert structure_followup_payload_count == 1
    assert ligand_support_readiness_count == 1
    assert ligand_identity_pilot_count == 1
    assert ligand_stage1_validation_panel_count == 1
    assert ligand_identity_core_materialization_count == 1
    assert q9nzd4_bridge_validation_preview_count == 1
    assert motif_domain_compact_preview_count == 1
    assert protein_similarity_signature_count == 1
    assert structure_signature_count == 1
    assert leakage_group_count == 1
