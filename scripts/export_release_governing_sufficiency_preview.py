from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.release_expansion_support import (
        build_release_governing_sufficiency_payload,
        load_release_context,
        write_json_and_markdown,
    )
except ModuleNotFoundError:  # pragma: no cover
    from release_expansion_support import (
        build_release_governing_sufficiency_payload,
        load_release_context,
        write_json_and_markdown,
    )
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_governing_sufficiency_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_governing_sufficiency_preview.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the release governing sufficiency preview.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_governing_sufficiency_payload(load_release_context())
    summary = payload.get("summary") or {}
    write_json_and_markdown(
        output_json=args.output_json,
        output_md=args.output_md,
        payload=payload,
        title="Release Governing Sufficiency Preview",
        bullet_rows=[
            f"Governing sufficiency state: `{summary.get('governing_sufficiency_state')}`",
            f"Strict governing allowed count: `{summary.get('strict_governing_allowed_count')}`",
            f"Support-only by design count: `{summary.get('non_governing_by_design_count')}`",
            f"Deferred to v2 source-fix count: `{summary.get('deferred_to_v2_source_fix_count')}`",
        ],
    )
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
