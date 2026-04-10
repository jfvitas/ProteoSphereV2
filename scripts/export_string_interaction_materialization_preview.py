from __future__ import annotations
# ruff: noqa: E402,I001

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.final_structured_dataset_support import (
    DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PACKAGE_LATEST,
    build_string_interaction_materialization,
    read_json,
    render_markdown_summary,
    write_json,
    write_text,
)

DEFAULT_PROCUREMENT_SOURCE_COMPLETION = (
    REPO_ROOT / "artifacts" / "status" / "procurement_source_completion_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "string_interaction_materialization_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "string_interaction_materialization_preview.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export STRING interaction materialization preview."
    )
    parser.add_argument(
        "--download-location-audit",
        type=Path,
        default=DEFAULT_DOWNLOAD_LOCATION_AUDIT,
    )
    parser.add_argument(
        "--procurement-source-completion",
        type=Path,
        default=DEFAULT_PROCUREMENT_SOURCE_COMPLETION,
    )
    parser.add_argument("--package-latest", type=Path, default=DEFAULT_PACKAGE_LATEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_string_interaction_materialization(
        download_location_audit=read_json(args.download_location_audit),
        procurement_source_completion=read_json(args.procurement_source_completion),
        package_latest=read_json(args.package_latest),
        output_root=args.output_root,
    )
    write_json(args.output_json, payload)
    summary = payload.get("summary", {})
    write_text(
        args.output_md,
        render_markdown_summary(
            "STRING Interaction Materialization Preview",
            [
                f"status: `{payload.get('status')}`",
                f"materialization_state: `{summary.get('materialization_state')}`",
                f"seed_accession_count: `{summary.get('seed_accession_count')}`",
                f"normalized_row_count: `{summary.get('normalized_row_count')}`",
            ],
        ),
    )
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
