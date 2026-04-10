from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.release_expansion_support import (
        build_release_reporting_completeness_payload,
        load_release_context,
        write_json_and_markdown,
    )
except ModuleNotFoundError:  # pragma: no cover
    from release_expansion_support import (
        build_release_reporting_completeness_payload,
        load_release_context,
        write_json_and_markdown,
    )
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_reporting_completeness_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_reporting_completeness_preview.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the release reporting completeness preview.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_reporting_completeness_payload(load_release_context())
    summary = payload.get("summary") or {}
    write_json_and_markdown(
        output_json=args.output_json,
        output_md=args.output_md,
        payload=payload,
        title="Release Reporting Completeness Preview",
        bullet_rows=[
            f"Reporting completeness state: `{summary.get('reporting_completeness_state')}`",
            f"Row-complete count: `{summary.get('row_complete_count')}`",
            f"Provenance row count: `{summary.get('provenance_row_count')}`",
            f"Release card count: `{summary.get('release_card_count')}`",
        ],
    )
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
