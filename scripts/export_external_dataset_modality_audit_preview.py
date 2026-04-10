from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from external_dataset_assessment_support import (  # noqa: E402
    DEFAULT_ACCESSION_BINDING_SUPPORT,
    DEFAULT_BINDING_REGISTRY,
    DEFAULT_ELIGIBILITY_MATRIX,
    DEFAULT_EXTERNAL_COHORT_AUDIT,
    DEFAULT_FUTURE_STRUCTURE_TRIAGE,
    DEFAULT_INTERACTION_CONTEXT,
    DEFAULT_LIBRARY_CONTRACT,
    DEFAULT_OFF_TARGET_ADJACENT_PROFILE,
    DEFAULT_OPERATOR_ACCESSION_MATRIX,
    DEFAULT_SPLIT_LABELS,
    build_external_dataset_audits,
    read_json,
    render_markdown,
    write_json,
    write_text,
)

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "external_dataset_modality_audit_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "external_dataset_modality_audit_preview.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export external dataset modality audit preview.")
    parser.add_argument("--split-labels", type=Path, default=DEFAULT_SPLIT_LABELS)
    parser.add_argument("--library-contract", type=Path, default=DEFAULT_LIBRARY_CONTRACT)
    parser.add_argument(
        "--external-cohort-audit",
        type=Path,
        default=DEFAULT_EXTERNAL_COHORT_AUDIT,
    )
    parser.add_argument("--eligibility-matrix", type=Path, default=DEFAULT_ELIGIBILITY_MATRIX)
    parser.add_argument("--binding-registry", type=Path, default=DEFAULT_BINDING_REGISTRY)
    parser.add_argument(
        "--accession-binding-support",
        type=Path,
        default=DEFAULT_ACCESSION_BINDING_SUPPORT,
    )
    parser.add_argument(
        "--operator-accession-matrix",
        type=Path,
        default=DEFAULT_OPERATOR_ACCESSION_MATRIX,
    )
    parser.add_argument(
        "--future-structure-triage",
        type=Path,
        default=DEFAULT_FUTURE_STRUCTURE_TRIAGE,
    )
    parser.add_argument(
        "--off-target-adjacent-profile",
        type=Path,
        default=DEFAULT_OFF_TARGET_ADJACENT_PROFILE,
    )
    parser.add_argument("--interaction-context", type=Path, default=DEFAULT_INTERACTION_CONTEXT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def build_external_dataset_modality_audit_preview(
    *args: dict[str, Any],
) -> dict[str, Any]:
    return build_external_dataset_audits(*args)["modality"]


def main() -> None:
    args = parse_args()
    payloads = build_external_dataset_audits(
        read_json(args.split_labels),
        read_json(args.library_contract),
        read_json(args.external_cohort_audit),
        read_json(args.eligibility_matrix),
        read_json(args.binding_registry),
        read_json(args.accession_binding_support),
        read_json(args.operator_accession_matrix),
        read_json(args.future_structure_triage),
        read_json(args.off_target_adjacent_profile),
        read_json(args.interaction_context),
    )
    payload = payloads["modality"]
    write_json(args.output_json, payload)
    write_text(
        args.output_md,
        render_markdown("External Dataset Modality Audit Preview", payload),
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
