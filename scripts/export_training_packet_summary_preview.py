from __future__ import annotations
# ruff: noqa: E402,I001

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.final_structured_dataset_support import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PACKAGE_LATEST,
    DEFAULT_PACKET_QUEUE,
    build_packet_summary_preview,
    read_json,
    render_markdown_summary,
    write_json,
    write_text,
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_summary_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_packet_summary_preview.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export training packet summary preview.")
    parser.add_argument("--package-latest", type=Path, default=DEFAULT_PACKAGE_LATEST)
    parser.add_argument("--packet-queue", type=Path, default=DEFAULT_PACKET_QUEUE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_packet_summary_preview(
        package_latest=read_json(args.package_latest),
        packet_queue=read_json(args.packet_queue),
        output_root=args.output_root,
    )
    write_json(args.output_json, payload)
    summary = payload.get("summary", {})
    write_text(
        args.output_md,
        render_markdown_summary(
            "Training Packet Summary Preview",
            [
                f"packet_count: `{summary.get('packet_count')}`",
                f"packet_lane_counts: `{summary.get('packet_lane_counts')}`",
            ],
        ),
    )
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
