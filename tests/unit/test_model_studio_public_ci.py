from __future__ import annotations

from api.model_studio.catalog import default_pipeline_spec
from api.model_studio.contracts import (
    compile_execution_graph,
    pipeline_spec_from_dict,
    validate_pipeline_spec,
)
from api.model_studio.runtime import MISSING_STRUCTURE_SENTINEL, _load_rows_from_csv
from api.model_studio.service import build_hardware_profile_payload


def test_default_pipeline_spec_validates_for_public_ci() -> None:
    spec = default_pipeline_spec()
    report = validate_pipeline_spec(spec)
    graph = compile_execution_graph(spec)

    assert not [item for item in report.items if item.level == "blocker"]
    assert not graph.blockers


def test_csv_loader_treats_dot_structure_path_as_missing(tmp_path) -> None:
    csv_path = tmp_path / "dot-structure.csv"
    csv_path.write_text(
        "\n".join(
            [
                "PDB,exp_dG,Source Data Set,Complex Type,Mapped Protein Accessions,Ligand Chains,Receptor Chains,Structure File,Resolution (A),Release Year,Label Temperature (K)",
                "5IIA,-11.9,governed_ppi_blended_subset_v2,protein_protein,P04552;Q8WR62,,,.,1.7,2017,298.15",
            ]
        ),
        encoding="utf-8",
    )

    rows = _load_rows_from_csv(csv_path, "test")

    assert len(rows) == 1
    assert rows[0].structure_file == MISSING_STRUCTURE_SENTINEL


def test_hardware_profile_payload_has_expected_keys() -> None:
    profile = build_hardware_profile_payload()

    assert "cpu_model" in profile
    assert "cpu_count" in profile
    assert "total_ram_gb" in profile
    assert "cuda_available" in profile
    assert "detected_gpus" in profile
    assert "recommended_preset" in profile


def test_sequence_embeddings_require_preprocess_lane() -> None:
    payload = default_pipeline_spec().to_dict()
    payload["feature_recipes"][0]["distributed_feature_sets"] = [
        *payload["feature_recipes"][0]["distributed_feature_sets"],
        "sequence_embeddings",
    ]

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]
    assert any("Sequence-embedding distributed features require" in message for message in blocker_messages)

    payload["preprocess_plan"]["modules"] = [
        *payload["preprocess_plan"]["modules"],
        "sequence embeddings",
    ]
    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))

    assert not [item for item in report.items if item.level == "blocker"]


def test_ligand_pilot_validation_reports_model_and_module_blockers() -> None:
    payload = default_pipeline_spec().to_dict()
    payload["data_strategy"]["task_type"] = "protein-ligand"
    payload["data_strategy"]["label_type"] = "delta_G"
    payload["data_strategy"]["split_strategy"] = "protein_ligand_component_grouped"
    payload["data_strategy"]["dataset_refs"] = ["governed_pl_bridge_pilot_subset_v1"]
    payload["training_set_request"]["task_type"] = "protein-ligand"
    payload["training_set_request"]["label_type"] = "delta_G"
    payload["training_set_request"]["source_families"] = ["governed_pl_bridge_pilot"]
    payload["training_set_request"]["dataset_refs"] = ["governed_pl_bridge_pilot_subset_v1"]
    payload["training_set_request"]["target_size"] = 48
    payload["graph_recipes"][0]["graph_kind"] = "whole_complex_graph"
    payload["graph_recipes"][0]["region_policy"] = "whole_molecule"
    payload["graph_recipes"][0]["partner_awareness"] = "role_conditioned"
    payload["split_plan"]["objective"] = "protein_ligand_component_grouped"
    payload["split_plan"]["grouping_policy"] = "protein_ligand_component_grouped"
    payload["training_plan"]["model_family"] = "gin"
    payload["training_plan"]["architecture"] = "gin_encoder"

    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    blocker_messages = [item.message for item in report.items if item.level == "blocker"]

    assert any("supports only `graphsage` and `multimodal_fusion`" in message for message in blocker_messages)
    assert any("requires the `ligand descriptors` preprocessing module" in message for message in blocker_messages)
