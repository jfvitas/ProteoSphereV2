from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.pre_tail_readiness_support import (
        build_external_dataset_resolution_diff_preview,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pre_tail_readiness_support import (
        build_external_dataset_resolution_diff_preview,
        read_json,
        write_json,
        write_text,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT_SIMULATION = (
    REPO_ROOT / "artifacts" / "status" / "split_simulation_preview.json"
)
DEFAULT_RESOLUTION = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_diff_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "external_dataset_resolution_diff_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# External Dataset Resolution Diff Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Unresolved or blocked: `{summary.get('unresolved_or_blocked_count')}`",
        f"- Conflicted: `{summary.get('conflicted_accession_count')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / claimed `{row['claimed_split']}` / "
            f"resolved `{row['resolved_state']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the external dataset resolution diff preview."
    )
    parser.add_argument("--split-simulation", type=Path, default=DEFAULT_SPLIT_SIMULATION)
    parser.add_argument("--resolution", type=Path, default=DEFAULT_RESOLUTION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_external_dataset_resolution_diff_preview(
        read_json(args.split_simulation),
        read_json(args.resolution),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
