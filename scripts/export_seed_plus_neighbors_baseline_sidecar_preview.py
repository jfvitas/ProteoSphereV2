from __future__ import annotations

# ruff: noqa

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.seed_plus_neighbors_export_support import (
    build_seed_plus_neighbors_baseline_sidecar_preview,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_baseline_sidecar_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_baseline_sidecar_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    lines = [
        "# Seed Plus Neighbors Baseline Sidecar Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Example count: `{summary.get('example_count')}`",
        f"- Governing-ready example count: `{summary.get('governing_ready_example_count')}`",
        f"- All visible example count: `{summary.get('all_visible_training_candidates_view_count')}`",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the seed-plus-neighbors baseline sidecar preview."
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_seed_plus_neighbors_baseline_sidecar_preview()
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
