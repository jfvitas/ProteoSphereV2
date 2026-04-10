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
    DEFAULT_SPLIT_DRY_RUN_VALIDATION,
    DEFAULT_SPLIT_ENGINE_INPUT,
    DEFAULT_SPLIT_FOLD_EXPORT_GATE,
    DEFAULT_SPLIT_POST_STAGING_GATE_CHECK,
    build_balance_diagnostics_preview,
    build_cohort_compiler_preview,
    build_package_readiness_preview,
    build_training_set_builder_session_preview,
    build_training_set_readiness_preview,
    read_json,
    render_markdown,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_builder_session_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "training_set_builder_session_preview.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export training set builder session preview.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    eligibility = read_json(DEFAULT_ELIGIBILITY_MATRIX)
    missing_data_policy = read_json(DEFAULT_MISSING_DATA_POLICY)
    balanced_plan = read_json(DEFAULT_BALANCED_DATASET_PLAN)
    external_audit = read_json(DEFAULT_EXTERNAL_COHORT_AUDIT)
    packet_deficit = read_json(DEFAULT_PACKET_DEFICIT)
    split_engine_input = read_json(DEFAULT_SPLIT_ENGINE_INPUT)
    split_dry_run = read_json(DEFAULT_SPLIT_DRY_RUN_VALIDATION)
    split_gate = read_json(DEFAULT_SPLIT_FOLD_EXPORT_GATE)
    split_post_stage = read_json(DEFAULT_SPLIT_POST_STAGING_GATE_CHECK)

    cohort = build_cohort_compiler_preview(
        eligibility,
        missing_data_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
    )
    build_balance_diagnostics_preview(
        eligibility,
        missing_data_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
    )
    package = build_package_readiness_preview(
        eligibility,
        missing_data_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
        split_engine_input,
        split_dry_run,
        split_gate,
        split_post_stage,
    )
    readiness = build_training_set_readiness_preview(
        eligibility,
        missing_data_policy,
        balanced_plan,
        external_audit,
        packet_deficit,
        split_engine_input,
        split_gate,
        package,
    )
    payload = build_training_set_builder_session_preview(readiness, cohort, package)
    write_json(args.output_json, payload)
    write_text(
        args.output_md,
        render_markdown("Training Set Builder Session Preview", payload),
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
