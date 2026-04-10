from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from training_set_builder_preview_support import (  # noqa: E402
    DEFAULT_BALANCED_DATASET_PLAN,
    DEFAULT_ELIGIBILITY_MATRIX,
    DEFAULT_EXTERNAL_COHORT_AUDIT,
    DEFAULT_MISSING_DATA_POLICY,
    DEFAULT_PACKET_DEFICIT,
    build_cohort_compiler_preview,
    read_json,
    render_markdown,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "cohort_compiler_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "cohort_compiler_preview.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export cohort compiler preview.")
    parser.add_argument("--eligibility-matrix", type=Path, default=DEFAULT_ELIGIBILITY_MATRIX)
    parser.add_argument("--missing-data-policy", type=Path, default=DEFAULT_MISSING_DATA_POLICY)
    parser.add_argument(
        "--balanced-dataset-plan",
        type=Path,
        default=DEFAULT_BALANCED_DATASET_PLAN,
    )
    parser.add_argument(
        "--external-cohort-audit",
        type=Path,
        default=DEFAULT_EXTERNAL_COHORT_AUDIT,
    )
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_cohort_compiler_preview(
        read_json(args.eligibility_matrix),
        read_json(args.missing_data_policy),
        read_json(args.balanced_dataset_plan),
        read_json(args.external_cohort_audit),
        read_json(args.packet_deficit),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown("Cohort Compiler Preview", payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
