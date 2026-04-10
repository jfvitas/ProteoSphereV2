from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.final_structured_dataset_support import resolve_materialization_summary_path
    from scripts.pre_tail_dataset_support import (
        build_training_set_baseline_sidecar_preview,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from final_structured_dataset_support import resolve_materialization_summary_path
    from pre_tail_dataset_support import (
        build_training_set_baseline_sidecar_preview,
        read_json,
        write_json,
        write_text,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "seed_plus_neighbors_structured_corpus_preview.json"
)
DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_baseline_sidecar_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_baseline_sidecar_preview.md"
)


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Training Set Baseline Sidecar Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Examples: `{summary.get('example_count')}`",
        f"- Governing ready examples: `{summary.get('governing_ready_example_count')}`",
        f"- Blocked examples: `{summary.get('blocked_pending_acquisition_example_count')}`",
        "",
    ]
    for row in (payload.get("strict_governing_training_view") or []):
        lines.append(f"- `governing`: `{row.get('example_id')}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the training-set baseline sidecar preview."
    )
    parser.add_argument("--corpus-preview", type=Path, default=DEFAULT_CORPUS_PREVIEW)
    parser.add_argument("--materialization-summary", type=Path, default=None)
    parser.add_argument(
        "--training-set-readiness",
        type=Path,
        default=DEFAULT_TRAINING_SET_READINESS,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    materialization_summary = args.materialization_summary or resolve_materialization_summary_path()
    payload = build_training_set_baseline_sidecar_preview(
        read_json(args.corpus_preview),
        read_json(materialization_summary),
        read_json(args.training_set_readiness),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
