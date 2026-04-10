from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.release_expansion_support import (
        DEFAULT_EXTERNAL_DRIVE_ROOT,
        build_procurement_expansion_storage_budget_payload,
        write_json_and_markdown,
    )
except ModuleNotFoundError:  # pragma: no cover
    from release_expansion_support import (
        DEFAULT_EXTERNAL_DRIVE_ROOT,
        build_procurement_expansion_storage_budget_payload,
        write_json_and_markdown,
    )
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "procurement_expansion_storage_budget_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "procurement_expansion_storage_budget_preview.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the expansion storage budget preview.")
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_DRIVE_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_procurement_expansion_storage_budget_payload(args.external_root)
    summary = payload.get("summary") or {}
    write_json_and_markdown(
        output_json=args.output_json,
        output_md=args.output_md,
        payload=payload,
        title="Procurement Expansion Storage Budget Preview",
        bullet_rows=[
            f"Baseline raw bytes: `{summary.get('baseline_raw_bytes')}`",
            f"Known additional bytes: `{summary.get('known_additional_bytes')}`",
            f"Projected v2 raw bytes: `{summary.get('projected_v2_raw_bytes')}`",
            f"External-drive mount state: `{summary.get('external_drive_mount_state')}`",
        ],
    )
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
