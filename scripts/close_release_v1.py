from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.release_expansion_support import (
        RELEASE_V1_MODE,
        RELEASE_V2_MODE,
        build_release_accession_evidence_pack_payload,
        build_release_blocker_resolution_board_payload,
        build_release_governing_sufficiency_payload,
        build_release_reporting_completeness_payload,
        build_release_runtime_qualification_payload,
        load_release_context,
        v1_release_bar_closed,
        write_json,
    )
except ModuleNotFoundError:  # pragma: no cover
    from release_expansion_support import (
        RELEASE_V1_MODE,
        RELEASE_V2_MODE,
        build_release_accession_evidence_pack_payload,
        build_release_blocker_resolution_board_payload,
        build_release_governing_sufficiency_payload,
        build_release_reporting_completeness_payload,
        build_release_runtime_qualification_payload,
        load_release_context,
        v1_release_bar_closed,
        write_json,
    )
SUMMARY_PATH = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
RELEASE_BUNDLE_MANIFEST_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
RELEASE_NOTES_SCRIPT = REPO_ROOT / "scripts" / "generate_release_notes.py"
RELEASE_BUNDLE_SCRIPT = REPO_ROOT / "scripts" / "build_release_bundle.py"
FOLLOW_ON_SCRIPTS = (
    "scripts/export_release_runtime_qualification_preview.py",
    "scripts/export_release_governing_sufficiency_preview.py",
    "scripts/export_release_accession_evidence_pack_preview.py",
    "scripts/export_release_reporting_completeness_preview.py",
    "scripts/export_release_blocker_resolution_board_preview.py",
    "scripts/export_release_runtime_maturity_preview.py",
    "scripts/export_release_source_coverage_depth_preview.py",
    "scripts/export_release_provenance_depth_preview.py",
    "scripts/export_release_grade_readiness_preview.py",
    "scripts/export_release_grade_closure_queue_preview.py",
    "scripts/export_release_accession_action_queue_preview.py",
    "scripts/export_release_candidate_promotion_preview.py",
    "scripts/export_release_promotion_gate_preview.py",
    "scripts/export_release_source_fix_followup_batch_preview.py",
    "scripts/export_operator_dashboard.py",
)


def _run_script(script_relative_path: str, *args: str) -> None:
    command = [sys.executable, str(REPO_ROOT / script_relative_path), *args]
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _refresh_new_surfaces() -> None:
    for script in FOLLOW_ON_SCRIPTS:
        _run_script(script)


def _write_summary(context: dict[str, object]) -> None:
    summary = dict(context["summary"])
    runtime = build_release_runtime_qualification_payload(context)
    sufficiency = build_release_governing_sufficiency_payload(context)
    evidence_pack = build_release_accession_evidence_pack_payload(context)
    reporting = build_release_reporting_completeness_payload(context)
    resolution_board = build_release_blocker_resolution_board_payload(context)

    summary["status"] = "completed"
    summary["blocker_categories"] = []
    summary["dataset_generation_mode"] = RELEASE_V1_MODE
    summary["release_target"] = {
        "version": RELEASE_V1_MODE,
        "state": "closed_for_frozen_candidate",
        "benchmark_release_bar_closed": True,
        "operator_release_ready": False,
    }
    summary["expansion_target"] = {
        "version": RELEASE_V2_MODE,
        "state": "deferred_until_external_drive",
        "external_drive_required": True,
    }
    runtime_summary = runtime.get("summary") or {}
    sufficiency_summary = sufficiency.get("summary") or {}
    evidence_summary = evidence_pack.get("summary") or {}
    reporting_summary = reporting.get("summary") or {}
    summary["release_grade_bar"] = {
        "runtime_qualification_complete": runtime_summary.get("qualification_complete"),
        "governing_sufficiency_complete": sufficiency_summary.get(
            "governing_sufficiency_complete"
        ),
        "reporting_completeness_complete": reporting_summary.get(
            "reporting_completeness_complete"
        ),
    }
    summary["release_candidate_snapshot"] = {
        "strict_governing_allowed_count": sufficiency_summary.get(
            "strict_governing_allowed_count"
        ),
        "row_complete_evidence_pack_count": evidence_summary.get("row_complete_count"),
        "deferred_to_v2_accession_count": evidence_summary.get("deferred_to_v2_count"),
    }
    summary["deferred_to_v2_blockers"] = [
        row.get("blocker")
        for row in (resolution_board.get("deferred_to_v2_blockers") or [])
        if row.get("blocker")
    ]
    write_json(SUMMARY_PATH, summary)


def _write_release_bundle_manifest(context: dict[str, object]) -> None:
    payload = dict(context["release_bundle_manifest"])
    payload["status"] = "assembled_release_candidate_v1"
    payload["bundle_version"] = RELEASE_V1_MODE
    payload["dataset_generation_mode"] = RELEASE_V1_MODE
    payload["blocker_categories"] = []
    payload["deferred_to_v2_blockers"] = [
        "expansion procurement wave",
        "mega_motif_base_backbone",
        "motivated_proteins_backbone",
        RELEASE_V2_MODE,
    ]
    truth_boundary = dict(payload.get("truth_boundary") or {})
    allowed_statuses = list(truth_boundary.get("allowed_statuses") or [])
    for status in ("assembled_with_blockers", "blocked", "assembled_release_candidate_v1"):
        if status not in allowed_statuses:
            allowed_statuses.append(status)
    truth_boundary["allowed_statuses"] = allowed_statuses
    payload["truth_boundary"] = truth_boundary
    notes = list(payload.get("notes") or [])
    notes.append(
        "Frozen v1 release candidate closed with explicit runtime qualification, "
        "governing sufficiency, and row-complete reporting."
    )
    notes.append(
        "Expanded v2 procurement and the two missing scrape families remain deferred "
        "until the external drive is mounted."
    )
    payload["notes"] = notes
    write_json(RELEASE_BUNDLE_MANIFEST_PATH, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Close the frozen v1 release candidate.")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = load_release_context()
    if not v1_release_bar_closed(context):
        raise SystemExit(
            "frozen v1 release bar is not closed; refusing to stamp summary/manifests"
        )
    if not args.execute:
        print(
            "v1 release bar is closed and ready to stamp; rerun with --execute "
            "to write artifacts."
        )
        return 0

    _refresh_new_surfaces()
    context = load_release_context()
    _write_summary(context)
    _write_release_bundle_manifest(context)
    _run_script("scripts/generate_release_notes.py", "--bundle-version", RELEASE_V1_MODE)
    _run_script("scripts/build_release_bundle.py", "--bundle-version", RELEASE_V1_MODE)
    _refresh_new_surfaces()
    print(SUMMARY_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
