from __future__ import annotations

# ruff: noqa

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.seed_plus_neighbors_export_support import (
    build_seed_plus_neighbors_multimodal_sidecar_preview,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_multimodal_sidecar_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_multimodal_sidecar_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    visible = payload.get("all_visible_training_candidates_view") if isinstance(payload, dict) else None
    dataset_status = visible.get("status") if isinstance(visible, dict) else None
    lines = [
        "# Seed Plus Neighbors Multimodal Sidecar Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- All visible example count: `{summary.get('all_visible_training_candidates_view_count')}`",
        f"- Strict governing example count: `{summary.get('strict_governing_training_view_count')}`",
        f"- Dataset status: `{dataset_status}`",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the seed-plus-neighbors multimodal sidecar preview."
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_seed_plus_neighbors_multimodal_sidecar_preview()
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
