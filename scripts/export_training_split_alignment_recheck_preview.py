from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.pre_tail_readiness_support import (
        build_split_alignment_recheck_preview,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pre_tail_readiness_support import (
        build_split_alignment_recheck_preview,
        read_json,
        write_json,
        write_text,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BALANCED_DATASET_PLAN = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "balanced_dataset_plan.json"
)
DEFAULT_SPLIT_SIMULATION = (
    REPO_ROOT / "artifacts" / "status" / "split_simulation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_split_alignment_recheck_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_split_alignment_recheck_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Training Split Alignment Recheck Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Matched accessions: `{summary.get('matched_accession_count')}`",
        f"- Mismatches: `{summary.get('mismatch_count')}`",
        f"- Expected 8/2/2: `{summary.get('expected_8_2_2_layout')}`",
        "",
    ]
    for row in payload.get("mismatches") or []:
        lines.append(
            f"- `{row['accession']}` planned `{row['planned_split']}` vs simulated "
            f"`{row['simulated_split']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the current cohort split alignment recheck preview."
    )
    parser.add_argument("--balanced-dataset-plan", type=Path, default=DEFAULT_BALANCED_DATASET_PLAN)
    parser.add_argument("--split-simulation", type=Path, default=DEFAULT_SPLIT_SIMULATION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_alignment_recheck_preview(
        read_json(args.balanced_dataset_plan),
        read_json(args.split_simulation),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
