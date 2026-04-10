from __future__ import annotations

from scripts.export_training_set_builder_runbook_preview import (
    build_training_set_builder_runbook_preview,
)


def test_runbook_preview_orders_builder_flow_and_carries_blockers() -> None:
    payload = build_training_set_builder_runbook_preview(
        cohort_compiler={"summary": {"selected_count": 12}},
        balance_diagnostics={"summary": {}},
        split_simulation={
            "summary": {
                "split_counts": {"train": 8, "val": 2, "test": 2},
                "dry_run_validation_status": "aligned",
            }
        },
        readiness={
            "summary": {
                "blocked_reasons": [
                    "fold_export_ready=false",
                    "cv_fold_export_unlocked=false",
                ]
            }
        },
        package_readiness={"summary": {"ready_for_package": False}},
        session_preview={
            "generated_at": "2026-04-03T00:00:00+00:00",
            "summary": {
                "selected_count": 12,
                "package_ready": False,
                "session_state": "ready_for_operator_review",
            },
        },
    )

    assert payload["summary"]["selected_count"] == 12
    assert payload["summary"]["blocked_reason_count"] == 2
    assert payload["summary"]["command_count"] == 7
    assert payload["steps"][0]["step_id"] == "compile-cohort"
    assert payload["steps"][3]["step_id"] == "assess-readiness"
    assert payload["steps"][4]["gate_status"] == "blocked"
    assert payload["steps"][5]["command"].endswith("candidate-package")


def test_runbook_preview_marks_package_lane_ready_without_blockers() -> None:
    payload = build_training_set_builder_runbook_preview(
        cohort_compiler={"summary": {"selected_count": 4}},
        balance_diagnostics={"summary": {}},
        split_simulation={
            "summary": {
                "split_counts": {"train": 4},
                "dry_run_validation_status": "ok",
            }
        },
        readiness={"summary": {"blocked_reasons": []}},
        package_readiness={"summary": {"ready_for_package": True}},
        session_preview={
            "generated_at": "2026-04-03T00:00:00+00:00",
            "summary": {
                "selected_count": 4,
                "package_ready": True,
                "session_state": "ready_for_operator_review",
            },
        },
    )

    step_ids = [step["step_id"] for step in payload["steps"]]
    assert "plan-package" in step_ids
    assert "candidate-package" in step_ids
    assert payload["steps"][4]["gate_status"] == "ready"
    assert payload["steps"][5]["gate_status"] == "ready"
