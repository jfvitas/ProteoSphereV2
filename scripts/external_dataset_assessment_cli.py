from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


COMMAND_MAP = {
    "intake-contract": "export_external_dataset_intake_contract_preview.py",
    "assess": "export_external_dataset_assessment_preview.py",
    "admission-decision": "export_external_dataset_admission_decision_preview.py",
    "acceptance-path": "export_external_dataset_acceptance_path_preview.py",
    "remediation-readiness": "export_external_dataset_remediation_readiness_preview.py",
    "caveat-execution": "export_external_dataset_caveat_execution_preview.py",
    "blocked-acquisition-batch": "export_external_dataset_blocked_acquisition_batch_preview.py",
    "acquisition-unblock": "export_external_dataset_acquisition_unblock_preview.py",
    "advisory-followup-register": "export_external_dataset_advisory_followup_register_preview.py",
    "caveat-exit-criteria": "export_external_dataset_caveat_exit_criteria_preview.py",
    "caveat-review-batch": "export_external_dataset_caveat_review_batch_preview.py",
    "clearance-delta": "export_external_dataset_clearance_delta_preview.py",
    "flaw-taxonomy": "export_external_dataset_flaw_taxonomy_preview.py",
    "risk-register": "export_external_dataset_risk_register_preview.py",
    "conflict-register": "export_external_dataset_conflict_register_preview.py",
    "issue-matrix": "export_external_dataset_issue_matrix_preview.py",
    "manifest-lint": "export_external_dataset_manifest_lint_preview.py",
    "acceptance-gate": "export_external_dataset_acceptance_gate_preview.py",
    "resolution": "export_external_dataset_resolution_preview.py",
    "resolution-diff": "export_external_dataset_resolution_diff_preview.py",
    "remediation-template": "export_external_dataset_remediation_template_preview.py",
    "fixture-catalog": "export_external_dataset_fixture_catalog_preview.py",
    "remediation-queue": "export_external_dataset_remediation_queue_preview.py",
    "leakage-audit": "export_external_dataset_leakage_audit_preview.py",
    "modality-audit": "export_external_dataset_modality_audit_preview.py",
    "binding-audit": "export_external_dataset_binding_audit_preview.py",
    "structure-audit": "export_external_dataset_structure_audit_preview.py",
    "provenance-audit": "export_external_dataset_provenance_audit_preview.py",
    "sample-bundle": "export_sample_external_dataset_assessment_bundle.py",
    "sample-manifests": "generate_sample_external_dataset_manifest.py",
    "sample-manifest-dry-run": "generate_sample_external_dataset_manifest.py",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="External dataset assessment operator CLI.")
    parser.add_argument("command", choices=sorted(COMMAND_MAP))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = REPO_ROOT / "scripts" / COMMAND_MAP[args.command]
    result = subprocess.run([sys.executable, str(target)], cwd=REPO_ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
