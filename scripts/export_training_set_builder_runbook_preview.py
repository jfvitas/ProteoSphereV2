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
    REPO_ROOT / "artifacts" / "status" / "training_set_builder_runbook_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_builder_runbook_preview.md"
)


def _step(
    *,
    step_id: str,
    label: str,
    command: str,
    gate_status: str,
    output_artifact: str,
    notes: list[str],
    input_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "label": label,
        "command": command,
        "gate_status": gate_status,
        "output_artifact": output_artifact,
        "input_artifacts": input_artifacts or [],
        "notes": notes,
    }


def build_training_set_builder_runbook_preview(
    cohort_compiler: dict[str, Any],
    balance_diagnostics: dict[str, Any],
    split_simulation: dict[str, Any],
    readiness: dict[str, Any],
    package_readiness: dict[str, Any],
    session_preview: dict[str, Any],
) -> dict[str, Any]:
    readiness_summary = readiness.get("summary") or {}
    package_summary = package_readiness.get("summary") or {}
    session_summary = session_preview.get("summary") or {}
    blocked_reasons = list(readiness_summary.get("blocked_reasons") or [])
    split_counts = split_simulation.get("summary") or {}

    steps = [
        _step(
            step_id="compile-cohort",
            label="Compile leakage-aware cohort",
            command="python scripts/training_set_builder_cli.py compile-cohort",
            gate_status="ready",
            output_artifact="artifacts/status/cohort_compiler_preview.json",
            input_artifacts=[
                "artifacts/status/training_set_eligibility_matrix_preview.json",
                "runs/real_data_benchmark/full_results/balanced_dataset_plan.json",
            ],
            notes=[
                (
                    "Use this first to confirm the selected accessions, "
                    "packet state, and next-step recommendations."
                ),
                "This remains report-only and does not change manifests or split assignments.",
            ],
        ),
        _step(
            step_id="balance-diagnostics",
            label="Inspect balance and modality mix",
            command="python scripts/training_set_builder_cli.py balance-diagnostics",
            gate_status="ready",
            output_artifact="artifacts/status/balance_diagnostics_preview.json",
            input_artifacts=[
                "runs/real_data_benchmark/full_results/balanced_dataset_plan.json",
            ],
            notes=[
                (
                    "Check split balance, bucket spread, thin-coverage rows, "
                    "and mixed-evidence concentration before packaging."
                ),
            ],
        ),
        _step(
            step_id="split-simulation",
            label="Simulate split/export posture",
            command="python scripts/training_set_builder_cli.py split-simulation",
            gate_status=(
                "ready"
                if split_counts.get("dry_run_validation_status") in {"ok", "aligned"}
                else "attention_needed"
            ),
            output_artifact="artifacts/status/split_simulation_preview.json",
            input_artifacts=[
                "runs/real_data_benchmark/cohort/split_labels.json",
                "artifacts/status/split_fold_export_gate_preview.json",
            ],
            notes=[
                (
                    "This confirms current train/val/test counts and whether "
                    "fold export is still blocked."
                ),
                "It is the last safe check before interpreting package readiness blockers.",
            ],
        ),
        _step(
            step_id="assess-readiness",
            label="Assess overall training-set readiness",
            command="python scripts/training_set_builder_cli.py assess-readiness",
            gate_status="attention_needed" if blocked_reasons else "ready",
            output_artifact="artifacts/status/training_set_readiness_preview.json",
            input_artifacts=[
                "artifacts/status/training_set_eligibility_matrix_preview.json",
                "artifacts/status/missing_data_policy_preview.json",
                "artifacts/status/packet_deficit_dashboard.json",
            ],
            notes=[
                "Use the five-question block as the canonical operator summary.",
                "Any blocker here should be treated as fail-closed for overnight work.",
            ],
        ),
        _step(
            step_id="plan-package",
            label="Review package blockers",
            command="python scripts/training_set_builder_cli.py plan-package",
            gate_status="blocked" if blocked_reasons else "ready",
            output_artifact="artifacts/status/package_readiness_preview.json",
            input_artifacts=[
                "artifacts/status/packet_deficit_dashboard.json",
                "artifacts/status/split_fold_export_gate_preview.json",
                "artifacts/status/split_post_staging_gate_check_preview.json",
            ],
            notes=[
                (
                    "Package planning remains advisory until fold export "
                    "unlocks and post-staging gates open."
                ),
                *(
                    [f"Current blocker: {reason}" for reason in blocked_reasons]
                    or ["No current blockers."]
                ),
            ],
        ),
        _step(
            step_id="candidate-package",
            label="Emit candidate package manifest preview",
            command="python scripts/training_set_builder_cli.py candidate-package",
            gate_status="blocked" if not package_summary.get("ready_for_package") else "ready",
            output_artifact="artifacts/status/training_set_candidate_package_manifest_preview.json",
            input_artifacts=[
                "artifacts/status/package_readiness_preview.json",
                "artifacts/status/training_set_readiness_preview.json",
            ],
            notes=[
                "This keeps the package lane visible without mutating protected LATEST manifests.",
            ],
        ),
        _step(
            step_id="session",
            label="Refresh session snapshot",
            command="python scripts/training_set_builder_cli.py session",
            gate_status=session_summary.get("session_state") or "report_only",
            output_artifact="artifacts/status/training_set_builder_session_preview.json",
            input_artifacts=[
                "artifacts/status/cohort_compiler_preview.json",
                "artifacts/status/package_readiness_preview.json",
                "artifacts/status/training_set_readiness_preview.json",
            ],
            notes=[
                "This is the operator handoff surface for the builder lane.",
                "Keep it aligned with the runbook whenever new previews land.",
            ],
        ),
    ]

    return {
        "artifact_id": "training_set_builder_runbook_preview",
        "schema_id": "proteosphere-training-set-builder-runbook-preview-2026-04-03",
        "status": "report_only",
        "generated_at": session_preview.get("generated_at"),
        "summary": {
            "selected_count": session_summary.get("selected_count"),
            "package_ready": session_summary.get("package_ready"),
            "blocked_reason_count": len(blocked_reasons),
            "blocked_reasons": blocked_reasons,
            "split_counts": split_counts.get("split_counts"),
            "command_count": len(steps),
            "session_state": session_summary.get("session_state"),
        },
        "steps": steps,
        "truth_boundary": {
            "summary": (
                "This runbook is report-only. It orders the existing builder "
                "previews into a safe operator flow, "
                "but it does not commit splits, materialize packages, or authorize release."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export training-set builder runbook preview.")
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
    balance = build_balance_diagnostics_preview(
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
    session_preview = build_training_set_builder_session_preview(readiness, cohort, package)
    split_simulation = {
        "summary": {
            "split_counts": (readiness.get("summary") or {}).get("selected_split_counts", {}),
            "dry_run_validation_status": split_dry_run.get("status"),
        }
    }
    payload = build_training_set_builder_runbook_preview(
        cohort,
        balance,
        split_simulation,
        readiness,
        package,
        session_preview,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown("Training Set Builder Runbook Preview", payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
