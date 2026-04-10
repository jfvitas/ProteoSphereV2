from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.final_structured_dataset_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from final_structured_dataset_support import read_json, write_json, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = (
    REPO_ROOT / "artifacts" / "status" / "seed_plus_neighbors_structured_corpus_preview.json"
)
DEFAULT_ENTITY_RESOLUTION = (
    REPO_ROOT / "artifacts" / "status" / "seed_plus_neighbors_entity_resolution_preview.json"
)
DEFAULT_BASELINE = (
    REPO_ROOT / "artifacts" / "status" / "training_set_baseline_sidecar_preview.json"
)
DEFAULT_MULTIMODAL = (
    REPO_ROOT / "artifacts" / "status" / "training_set_multimodal_sidecar_preview.json"
)
DEFAULT_PACKET_SUMMARY = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_summary_preview.json"
)
DEFAULT_PACKAGE_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
)
DEFAULT_COMPLETION_SUMMARY = (
    REPO_ROOT / "artifacts" / "status" / "post_tail_completion_summary.json"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "reports" / "final_structured_datasets"
DEFAULT_LATEST = DEFAULT_OUTPUT_ROOT / "LATEST.json"
DEFAULT_PREVIEW_JSON = (
    REPO_ROOT / "artifacts" / "status" / "final_structured_dataset_bundle_preview.json"
)
DEFAULT_PREVIEW_MD = (
    REPO_ROOT / "docs" / "reports" / "final_structured_dataset_bundle_preview.md"
)


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Final Structured Dataset Bundle Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Bundle root: `{payload.get('bundle_root')}`",
        f"- Corpus rows: `{summary.get('corpus_row_count')}`",
        f"- Strict governing examples: `{summary.get('strict_governing_training_view_count')}`",
        f"- Visible examples: `{summary.get('all_visible_training_candidates_view_count')}`",
        f"- Packet count: `{summary.get('packet_count')}`",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a versioned final structured dataset bundle from the "
            "current post-tail artifacts."
        )
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--entity-resolution", type=Path, default=DEFAULT_ENTITY_RESOLUTION)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--multimodal", type=Path, default=DEFAULT_MULTIMODAL)
    parser.add_argument("--packet-summary", type=Path, default=DEFAULT_PACKET_SUMMARY)
    parser.add_argument("--package-readiness", type=Path, default=DEFAULT_PACKAGE_READINESS)
    parser.add_argument("--completion-summary", type=Path, default=DEFAULT_COMPLETION_SUMMARY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--latest-path", type=Path, default=DEFAULT_LATEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_PREVIEW_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_PREVIEW_MD)
    parser.add_argument("--run-id", type=str, default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus = read_json(args.corpus)
    entity_resolution = read_json(args.entity_resolution)
    baseline = read_json(args.baseline)
    multimodal = read_json(args.multimodal)
    packet_summary = read_json(args.packet_summary)
    package_readiness = read_json(args.package_readiness)
    completion_summary = read_json(args.completion_summary)

    run_id = args.run_id.strip() or f"final-structured-dataset-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    bundle_root = args.output_root / run_id
    bundle_root.mkdir(parents=True, exist_ok=True)

    outputs = {
        "seed_plus_neighbors_structured_corpus": (
            bundle_root / "seed_plus_neighbors_structured_corpus.json"
        ),
        "seed_plus_neighbors_entity_resolution": (
            bundle_root / "seed_plus_neighbors_entity_resolution.json"
        ),
        "training_set_baseline_sidecar": bundle_root / "training_set_baseline_sidecar.json",
        "training_set_multimodal_sidecar": bundle_root / "training_set_multimodal_sidecar.json",
        "training_packet_summary": bundle_root / "training_packet_summary.json",
        "bundle_manifest": bundle_root / "bundle_manifest.json",
    }

    write_json(outputs["seed_plus_neighbors_structured_corpus"], corpus)
    write_json(outputs["seed_plus_neighbors_entity_resolution"], entity_resolution)
    write_json(outputs["training_set_baseline_sidecar"], baseline)
    write_json(outputs["training_set_multimodal_sidecar"], multimodal)
    write_json(outputs["training_packet_summary"], packet_summary)

    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "bundle_root": str(bundle_root).replace("\\", "/"),
        "corpus_path": str(outputs["seed_plus_neighbors_structured_corpus"]).replace("\\", "/"),
        "entity_resolution_path": str(
            outputs["seed_plus_neighbors_entity_resolution"]
        ).replace("\\", "/"),
        "baseline_sidecar_path": str(outputs["training_set_baseline_sidecar"]).replace("\\", "/"),
        "multimodal_sidecar_path": str(outputs["training_set_multimodal_sidecar"]).replace(
            "\\", "/"
        ),
        "packet_summary_path": str(outputs["training_packet_summary"]).replace("\\", "/"),
        "corpus_row_count": (corpus.get("summary") or {}).get("row_count"),
        "strict_governing_training_view_count": (corpus.get("summary") or {}).get(
            "strict_governing_training_view_count"
        ),
        "visible_training_candidate_count": (baseline.get("summary") or {}).get(
            "all_visible_training_candidates_view_count"
        ),
        "packet_count": (packet_summary.get("summary") or {}).get("packet_count"),
        "package_readiness_state": (package_readiness.get("summary") or {}).get("readiness_state")
        or package_readiness.get("readiness_state"),
        "post_tail_completion_status": completion_summary.get("status"),
        "truth_boundary": {
            "summary": (
                "This versioned bundle captures the current one-hop seed-plus-neighbors corpus and "
                "training sidecars without mutating protected release/package manifests."
            ),
            "report_only_bundle": True,
            "non_mutating": True,
        },
    }
    write_json(outputs["bundle_manifest"], manifest)

    latest_payload = {
        "run_id": run_id,
        "bundle_root": str(bundle_root).replace("\\", "/"),
        "bundle_manifest_path": str(outputs["bundle_manifest"]).replace("\\", "/"),
        "status": "completed",
        "generated_at": manifest["generated_at"],
    }
    write_json(args.latest_path, latest_payload)

    preview = {
        "artifact_id": "final_structured_dataset_bundle_preview",
        "schema_id": "proteosphere-final-structured-dataset-bundle-preview-2026-04-05",
        "status": "completed",
        "generated_at": manifest["generated_at"],
        "bundle_root": latest_payload["bundle_root"],
        "bundle_manifest_path": latest_payload["bundle_manifest_path"],
        "summary": {
            "run_id": run_id,
            "corpus_row_count": manifest["corpus_row_count"],
            "strict_governing_training_view_count": manifest[
                "strict_governing_training_view_count"
            ],
            "all_visible_training_candidates_view_count": manifest[
                "visible_training_candidate_count"
            ],
            "packet_count": manifest["packet_count"],
            "package_readiness_state": manifest["package_readiness_state"],
        },
        "bundle_files": {
            name: str(path).replace("\\", "/")
            for name, path in outputs.items()
        },
        "truth_boundary": manifest["truth_boundary"],
    }
    write_json(args.output_json, preview)
    write_text(args.output_md, _render_markdown(preview))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
