from __future__ import annotations

from api.model_studio.catalog import default_pipeline_spec
from api.model_studio.contracts import (
    compile_execution_graph,
    pipeline_spec_from_dict,
    validate_pipeline_spec,
)


def test_default_pipeline_spec_validates_without_blockers() -> None:
    spec = default_pipeline_spec()
    report = validate_pipeline_spec(spec)
    assert report.status == "ok"
    assert any(item.category == "readiness" for item in report.items)


def test_compile_execution_graph_is_deterministic_shape() -> None:
    spec = default_pipeline_spec()
    graph = compile_execution_graph(spec)
    assert graph.graph_id == f"graph:{spec.pipeline_id}"
    assert "model_training" in graph.stages
    assert graph.dependencies["model_training"] == ("example_packaging",)


def test_lab_only_release_option_is_blocked() -> None:
    payload = default_pipeline_spec().to_dict()
    payload["training_plan"]["model_family"] = "cnn"
    report = validate_pipeline_spec(pipeline_spec_from_dict(payload))
    assert report.status == "blocked"
    assert any(item.category == "release_catalog" for item in report.items)
