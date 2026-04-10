from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts.pre_tail_readiness_support import (
        build_external_dataset_remediation_template_preview,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pre_tail_readiness_support import (
        build_external_dataset_remediation_template_preview,
        read_json,
        write_json,
        write_text,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSESSMENT = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_assessment_preview.json"
)
DEFAULT_RESOLUTION = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_resolution_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_remediation_template_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "external_dataset_remediation_template_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# External Dataset Remediation Template Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['issue_category']}` / `{row.get('current_verdict')}` / "
            f"`{row['recommended_action']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the external dataset remediation template preview."
    )
    parser.add_argument("--assessment", type=Path, default=DEFAULT_ASSESSMENT)
    parser.add_argument("--resolution", type=Path, default=DEFAULT_RESOLUTION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_external_dataset_remediation_template_preview(
        read_json(args.assessment),
        read_json(args.resolution),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
