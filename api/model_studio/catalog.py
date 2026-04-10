from __future__ import annotations

from typing import Any

from api.model_studio.capabilities import (
    RELEASE_REVIEW_LANES,
    build_action_contract,
    build_capability_registry,
    build_field_help_registry,
    build_lab_catalog,
    build_stepper_definition,
    build_ui_option_registry,
)
from api.model_studio.capabilities import (
    build_design_catalog as build_capability_catalog,
)
from api.model_studio.contracts import (
    DataStrategySpec,
    EvaluationPlanSpec,
    ExampleMaterializationSpec,
    FeatureRecipeSpec,
    GraphRecipeSpec,
    ModelStudioPipelineSpec,
    PreprocessPlanSpec,
    SplitPlanSpec,
    TrainingPlanSpec,
    TrainingSetRequestSpec,
    compile_execution_graph,
    validate_pipeline_spec,
)

STUDIO_SCHEMA_VERSION = "model-studio:v2-study-builder"


def build_design_catalog(*, include_lab: bool = False) -> dict[str, Any]:
    catalog = build_capability_catalog(include_lab=include_lab)
    catalog["capability_registry"] = build_capability_registry()
    catalog["ui_option_registry"] = build_ui_option_registry()
    catalog["field_help_registry"] = build_field_help_registry()
    catalog["stepper_definition"] = build_stepper_definition()
    catalog["action_contract"] = build_action_contract()
    catalog["reviewer_lanes"] = list(RELEASE_REVIEW_LANES)
    catalog["catalog_mode"] = "lab" if include_lab else "release"
    return catalog


def build_release_catalog() -> dict[str, Any]:
    return build_design_catalog(include_lab=False)


def default_pipeline_spec() -> ModelStudioPipelineSpec:
    feature_recipe = FeatureRecipeSpec(
        recipe_id="feature:ppi-interface-v1",
        node_feature_policy="normalized_continuous",
        edge_feature_policy="normalized_continuous",
        global_feature_sets=("assay_globals", "structure_quality", "interface_chemistry"),
        distributed_feature_sets=(
            "residue_contacts",
            "interface_geometry",
            "water_context",
            "interface_chemistry_maps",
        ),
        notes=("Broadened beta protein-binding feature recipe.",),
    )
    graph_recipe = GraphRecipeSpec(
        recipe_id="graph:ppi-interface-shell-v1",
        graph_kind="hybrid_graph",
        region_policy="interface_plus_shell",
        node_granularity="residue",
        encoding_policy="normalized_continuous",
        feature_recipe_id=feature_recipe.recipe_id,
        partner_awareness="asymmetric",
        include_waters=True,
        include_salt_bridges=True,
        include_contact_shell=True,
        notes=("Released interface-plus-shell graph recipe.",),
    )
    return ModelStudioPipelineSpec(
        pipeline_id="pipeline:protein-binding-default-v1",
        schema_version=STUDIO_SCHEMA_VERSION,
        study_title="Protein Binding Studio Draft",
        data_strategy=DataStrategySpec(
            strategy_id="strategy:protein-binding-default-v1",
            task_type="protein-protein",
            label_type="delta_G",
            label_transform="identity",
            split_strategy="leakage_resistant_benchmark",
            structure_source_policy="experimental_only",
            graph_recipe_ids=(graph_recipe.recipe_id,),
            feature_recipe_ids=(feature_recipe.recipe_id,),
            dataset_refs=(
                "release_pp_alpha_benchmark_v1",
                "robust_pp_benchmark_v1",
                "expanded_pp_benchmark_v1",
            ),
            audit_requirements=("sequence_leakage", "partner_overlap", "state_reuse"),
            notes=("Broadened beta structure-backed protein-binding strategy.",),
        ),
        feature_recipes=(feature_recipe,),
        graph_recipes=(graph_recipe,),
        training_set_request=TrainingSetRequestSpec(
            request_id="training-set-request:protein-binding-default-v1",
            task_type="protein-protein",
            label_type="delta_G",
            structure_source_policy="experimental_only",
            source_families=("balanced_ppi_beta_pool", "release_frozen", "robust_structure_backed"),
            dataset_refs=(
                "release_pp_alpha_benchmark_v1",
                "robust_pp_benchmark_v1",
                "expanded_pp_benchmark_v1",
            ),
            target_size=192,
            acceptable_fidelity="pilot_ready",
            inclusion_filters={
                "max_resolution": 3.5,
                "min_release_year": 1990,
            },
            exclusion_filters={"exclude_pdb_ids": []},
            notes=("Default broadened beta request for the internal expert pilot.",),
        ),
        preprocess_plan=PreprocessPlanSpec(
            plan_id="preprocess:protein-binding-default-v1",
            modules=(
                "PDB acquisition",
                "chain extraction and canonical mapping",
                "waters",
                "salt bridges",
                "hydrogen-bond/contact summaries",
            ),
            cache_policy="prefer_cached_materializations",
            source_policy="experimental_only",
            shell_distance_angstroms=6.0,
            shell_strategy="interface_shell",
            options={"contact_cutoff_angstroms": 5.0, "neighbor_context_depth": 2},
        ),
        split_plan=SplitPlanSpec(
            plan_id="split:protein-binding-default-v1",
            objective="leakage_aware_component_balanced",
            grouping_policy="protein_accession_components",
            holdout_policy="explicit_test_holdout",
            train_fraction=0.7,
            val_fraction=0.1,
            test_fraction=0.2,
            hard_constraints=("no_direct_accession_overlap", "prefer_label_balance"),
            notes=("Released split compiler defaults for the internal expert pilot.",),
        ),
        example_materialization=ExampleMaterializationSpec(
            spec_id="materialization:protein-binding-default-v1",
            graph_recipe_ids=(graph_recipe.recipe_id,),
            feature_recipe_ids=(feature_recipe.recipe_id,),
            preprocess_modules=(
                "PDB acquisition",
                "chain extraction and canonical mapping",
                "waters",
                "salt bridges",
                "hydrogen-bond/contact summaries",
            ),
            region_policy="interface_plus_shell",
            cache_policy="prefer_cached_materializations",
            include_global_features=True,
            include_distributed_features=True,
            include_graph_payloads=True,
            notes=("Default example materialization bundle for the internal expert pilot.",),
        ),
        training_plan=TrainingPlanSpec(
            plan_id="training:protein-binding-default-v1",
            model_family="multimodal_fusion",
            architecture="graph_global_fusion",
            optimizer="adamw",
            scheduler="cosine_decay",
            loss_function="mse",
            epoch_budget=60,
            batch_policy="dynamic_by_graph_size",
            mixed_precision="bf16",
            uncertainty_head="heteroscedastic_regression",
            hyperparameters={"lr": 2e-4, "weight_decay": 1e-2, "dropout": 0.15},
            ablations=("graph_only", "global_only", "graph_plus_global"),
        ),
        evaluation_plan=EvaluationPlanSpec(
            plan_id="evaluation:protein-binding-default-v1",
            metric_families=("regression", "ranking", "calibration"),
            robustness_slices=("uniref_family_holdout", "interface_size_bucket", "partner_novelty"),
            outlier_policy="top_residuals_and_influence",
            attribution_policy="attention_and_feature_saliency",
            leakage_checks=("exact_sequence", "partner_overlap", "structure_state_reuse"),
        ),
        templates=("protein_binding_flagship",),
        tags=("web-first", "protein-first", "model-studio"),
    )


def build_workspace_preview() -> dict[str, Any]:
    spec = default_pipeline_spec()
    report = validate_pipeline_spec(spec)
    graph = compile_execution_graph(spec)
    return {
        "pipeline_spec": spec.to_dict(),
        "recommendation_report": report.to_dict(),
        "execution_graph": graph.to_dict(),
        "catalog": build_release_catalog(),
        "lab_catalog": build_lab_catalog(),
        "workspace_sections": [
            "Project Home",
            "Data Strategy Designer",
            "Representation Designer",
            "Pipeline Composer",
            "Execution Console",
            "Analysis and Review",
        ],
    }
