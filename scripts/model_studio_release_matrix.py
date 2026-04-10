from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.model_studio.catalog import default_pipeline_spec
from api.model_studio.contracts import pipeline_spec_from_dict
from api.model_studio.runtime import launch_run, load_run

MODELS = ("xgboost", "catboost", "mlp", "multimodal_fusion", "graphsage")
GRAPH_VARIANTS = {
    "interface_graph": {
        "region_policy": "interface_only",
        "include_waters": False,
        "include_salt_bridges": False,
        "include_contact_shell": False,
    },
    "residue_graph": {
        "region_policy": "interface_only",
        "include_waters": True,
        "include_salt_bridges": False,
        "include_contact_shell": False,
    },
    "hybrid_graph": {
        "region_policy": "interface_plus_shell",
        "include_waters": True,
        "include_salt_bridges": True,
        "include_contact_shell": True,
    },
}


def _build_payload(model_family: str, graph_kind: str) -> dict:
    payload = default_pipeline_spec().to_dict()
    payload["pipeline_id"] = f"pipeline:release-matrix-{model_family}-{graph_kind}"
    payload["study_title"] = f"Release Matrix {model_family} {graph_kind}"
    payload["data_strategy"]["dataset_refs"] = ["release_pp_alpha_benchmark_v1"]
    payload["training_plan"]["model_family"] = model_family
    payload["training_plan"]["epoch_budget"] = 10 if model_family in {"graphsage", "gin"} else 20
    payload["training_plan"]["architecture"] = (
        "graph_global_fusion"
        if model_family == "multimodal_fusion"
        else f"{model_family}_release_alpha"
    )
    graph = payload["graph_recipes"][0]
    graph["graph_kind"] = graph_kind
    graph.update(GRAPH_VARIANTS[graph_kind])
    payload["preprocess_plan"]["modules"] = [
        "PDB acquisition",
        "chain extraction and canonical mapping",
        "hydrogen-bond/contact summaries",
    ]
    if GRAPH_VARIANTS[graph_kind]["include_waters"]:
        payload["preprocess_plan"]["modules"].append("waters")
    if GRAPH_VARIANTS[graph_kind]["include_salt_bridges"]:
        payload["preprocess_plan"]["modules"].append("salt bridges")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Model Studio release matrix.")
    parser.add_argument(
        "--output",
        default=str(
            Path("artifacts")
            / "reviews"
            / "model_studio_internal_alpha"
            / "release_matrix_round_1.json"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max run count for smoke runs.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items = []
    for model_family in MODELS:
        for graph_kind in GRAPH_VARIANTS:
            if args.limit and len(items) >= args.limit:
                break
            payload = _build_payload(model_family, graph_kind)
            spec = pipeline_spec_from_dict(payload)
            manifest = launch_run(spec)
            run = load_run(manifest["run_id"])
            items.append(
                {
                    "model_family": model_family,
                    "graph_kind": graph_kind,
                    "run_id": manifest["run_id"],
                    "status": run["run_manifest"].get("status"),
                    "resolved_backend": run["metrics"].get("resolved_backend"),
                    "test_rmse": run["metrics"].get("test_rmse"),
                    "test_mae": run["metrics"].get("test_mae"),
                    "test_pearson": run["metrics"].get("test_pearson"),
                }
            )
        if args.limit and len(items) >= args.limit:
            break

    summary = {
        "run_count": len(items),
        "items": items,
        "all_completed": all(item["status"] == "completed" for item in items),
        "models_covered": sorted({item["model_family"] for item in items}),
        "graphs_covered": sorted({item["graph_kind"] for item in items}),
    }
    backend_families = {}
    for item in items:
        backend_families.setdefault(item["model_family"], set()).add(item["resolved_backend"])
    summary["backend_families"] = {
        key: sorted(value) for key, value in backend_families.items()
    }
    summary["release_gate"] = {
        "all_completed": summary["all_completed"],
        "all_models_covered": sorted(summary["models_covered"]) == sorted(MODELS),
        "distinct_backend_per_model": all(len(value) == 1 for value in backend_families.values()),
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(output_path)
    return 0 if all(summary["release_gate"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
