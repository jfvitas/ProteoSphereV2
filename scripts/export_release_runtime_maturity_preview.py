from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
DEFAULT_PROVENANCE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "provenance_table.json"
)
DEFAULT_RUNTIME_QUALIFICATION = (
    REPO_ROOT / "artifacts" / "status" / "release_runtime_qualification_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_runtime_maturity_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_runtime_maturity_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_runtime_maturity_preview(
    *, summary: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    runtime_qualification = _read_json(DEFAULT_RUNTIME_QUALIFICATION)
    qualification_summary = runtime_qualification.get("summary") or {}
    runtime = summary.get("runtime") or {}
    scope = summary.get("execution_scope") or {}
    run_context = provenance.get("run_context") or {}
    consistency = provenance.get("consistency_checks") or {}

    first_run = int(runtime.get("first_run_processed_examples") or 0)
    resumed_run = int(runtime.get("resumed_run_processed_examples") or 0)
    cohort_size = int(scope.get("cohort_size") or 0)
    completion_ratio = (resumed_run / cohort_size) if cohort_size else 0.0
    checkpoint_resumes = int(runtime.get("checkpoint_resumes") or 0)
    checkpoint_writes = int(runtime.get("checkpoint_writes") or 0)

    return {
        "artifact_id": "release_runtime_maturity_preview",
        "schema_id": "proteosphere-release-runtime-maturity-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "runtime_surface": scope.get("runtime_surface"),
            "cohort_size": cohort_size,
            "first_run_processed_examples": first_run,
            "resumed_run_processed_examples": resumed_run,
            "completion_ratio": round(completion_ratio, 4),
            "checkpoint_writes": checkpoint_writes,
            "checkpoint_resumes": checkpoint_resumes,
            "identity_safe_resume": consistency.get("checkpoint_identity_safe_resume"),
            "runtime_maturity_state": (
                qualification_summary.get("runtime_qualification_state")
                or (
                    "prototype_runtime_resumable"
                    if completion_ratio >= 1.0 and consistency.get("checkpoint_identity_safe_resume")
                    else "prototype_runtime_partial"
                )
            ),
            "next_action": (
                "none_frozen_v1_bar_closed"
                if qualification_summary.get("qualification_complete")
                else "promote benchmark runtime from prototype-only evidence"
            ),
            "qualification_complete": qualification_summary.get("qualification_complete", False),
        },
        "evidence": {
            "summary_path": str(DEFAULT_SUMMARY).replace("\\", "/"),
            "provenance_table_path": str(DEFAULT_PROVENANCE).replace("\\", "/"),
            "run_manifest_id": run_context.get("run_manifest_id"),
            "checkpoint_ref": run_context.get("checkpoint_ref"),
        },
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This preview summarizes prototype runtime evidence, including resume "
                "continuity, without upgrading the benchmark to release-grade runtime maturity."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    return "\n".join(
        [
            "# Release Runtime Maturity Preview",
            "",
            f"- Runtime surface: `{summary.get('runtime_surface')}`",
            f"- Cohort size: `{summary.get('cohort_size')}`",
            f"- First run processed: `{summary.get('first_run_processed_examples')}`",
            f"- Resumed run processed: `{summary.get('resumed_run_processed_examples')}`",
            f"- Identity-safe resume: `{str(summary.get('identity_safe_resume')).lower()}`",
            f"- Runtime maturity state: `{summary.get('runtime_maturity_state')}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the release runtime maturity preview.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--runtime-qualification", type=Path, default=DEFAULT_RUNTIME_QUALIFICATION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_runtime_maturity_preview(
        summary=_read_json(args.summary),
        provenance=_read_json(args.provenance),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
