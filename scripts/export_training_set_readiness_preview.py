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
    build_package_readiness_preview,
    build_training_set_readiness_preview,
    read_json,
    render_markdown,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "training_set_readiness_preview.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export training set readiness preview.")
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
    parser.add_argument(
        "--split-engine-input",
        type=Path,
        default=DEFAULT_SPLIT_ENGINE_INPUT,
    )
    parser.add_argument(
        "--split-fold-export-gate",
        type=Path,
        default=DEFAULT_SPLIT_FOLD_EXPORT_GATE,
    )
    parser.add_argument(
        "--split-dry-run-validation",
        type=Path,
        default=DEFAULT_SPLIT_DRY_RUN_VALIDATION,
    )
    parser.add_argument(
        "--split-post-staging-gate-check",
        type=Path,
        default=DEFAULT_SPLIT_POST_STAGING_GATE_CHECK,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    eligibility_matrix = read_json(args.eligibility_matrix)
    missing_data_policy = read_json(args.missing_data_policy)
    balanced_dataset_plan = read_json(args.balanced_dataset_plan)
    external_cohort_audit = read_json(args.external_cohort_audit)
    packet_deficit = read_json(args.packet_deficit)
    split_engine_input = read_json(args.split_engine_input)
    split_fold_export_gate = read_json(args.split_fold_export_gate)
    split_dry_run_validation = read_json(args.split_dry_run_validation)
    split_post_staging_gate_check = read_json(args.split_post_staging_gate_check)

    package_readiness = build_package_readiness_preview(
        eligibility_matrix,
        missing_data_policy,
        balanced_dataset_plan,
        external_cohort_audit,
        packet_deficit,
        split_engine_input,
        split_dry_run_validation,
        split_fold_export_gate,
        split_post_staging_gate_check,
    )
    payload = build_training_set_readiness_preview(
        eligibility_matrix,
        missing_data_policy,
        balanced_dataset_plan,
        external_cohort_audit,
        packet_deficit,
        split_engine_input,
        split_fold_export_gate,
        package_readiness,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown("Training Set Readiness Preview", payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
