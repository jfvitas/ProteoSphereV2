from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.post_tier1_packet_regression import (
    compare_packet_readiness,
    select_strongest_packet_baseline,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMOTION_PATH = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "promotions" / "LATEST.json"
)
DEFAULT_STATUS_PATH = REPO_ROOT / "artifacts" / "status" / "post_tier1_direct_pipeline.json"
DEFAULT_MARKDOWN_PATH = (
    REPO_ROOT / "docs" / "reports" / "post_tier1_direct_pipeline.md"
)
DEFAULT_SCOPE_ROOT = REPO_ROOT / "runs" / "tier1_direct_validation"
DEFAULT_PACKAGES_ROOT = REPO_ROOT / "data" / "packages"
DEFAULT_BASELINE_PACKET_SUMMARY_PATH = REPO_ROOT / "data" / "packages" / "LATEST.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp_path, path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    os.replace(temp_path, path)


def _clean_text(value: object | None) -> str:
    return str(value or "").strip()


def _tail_text(text: str, *, max_lines: int = 20) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:])


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _require_promoted_seed(promotion_path: Path) -> dict[str, Any]:
    if not promotion_path.exists():
        raise FileNotFoundError(f"missing Tier 1 promotion artifact: {promotion_path}")
    payload = _read_json(promotion_path)
    if _clean_text(payload.get("status")) != "promoted":
        raise ValueError("Tier 1 promotion artifact is not promoted")
    return payload


@dataclass(frozen=True, slots=True)
class PipelineStep:
    step_id: str
    label: str
    command: tuple[str, ...]
    expected_outputs: tuple[str, ...]


def _scope_paths(run_id: str) -> dict[str, Path]:
    scope_root = DEFAULT_SCOPE_ROOT / run_id
    return {
        "scope_root": scope_root,
        "canonical_root": scope_root / "canonical",
        "source_coverage_output": scope_root / "source_coverage_matrix.json",
        "source_coverage_markdown": scope_root / "source_coverage_matrix.md",
        "available_payloads_output": scope_root / "available_payloads.generated.json",
        "packages_root": scope_root / "packages",
        "selected_output": scope_root / "selected_cohort_materialization.json",
        "packet_deficit_output": scope_root / "packet_deficit_dashboard.json",
        "packet_deficit_markdown": scope_root / "packet_deficit_dashboard.md",
    }


def _default_steps(run_id: str) -> tuple[PipelineStep, ...]:
    scope = _scope_paths(run_id)
    return (
        PipelineStep(
            step_id="canonical",
            label="Canonical materialization",
            command=(
                "python",
                "scripts\\materialize_canonical_store.py",
                "--canonical-root",
                str(scope["canonical_root"]),
                "--run-id",
                f"tier1-direct-{run_id}",
            ),
            expected_outputs=(
                str(scope["canonical_root"] / "LATEST.json"),
            ),
        ),
        PipelineStep(
            step_id="source_coverage_matrix",
            label="Source coverage matrix refresh",
            command=(
                "python",
                "scripts\\export_source_coverage_matrix.py",
                "--output",
                str(scope["source_coverage_output"]),
                "--markdown-output",
                str(scope["source_coverage_markdown"]),
            ),
            expected_outputs=(
                str(scope["source_coverage_output"]),
                str(scope["source_coverage_markdown"]),
            ),
        ),
        PipelineStep(
            step_id="available_payload_registry",
            label="Available payload registry regeneration",
            command=(
                "python",
                "scripts\\generate_available_payload_registry.py",
                "--canonical-latest",
                str(scope["canonical_root"] / "LATEST.json"),
                "--output",
                str(scope["available_payloads_output"]),
            ),
            expected_outputs=(
                str(scope["available_payloads_output"]),
            ),
        ),
        PipelineStep(
            step_id="selected_packet_materialization",
            label="Selected packet cohort materialization",
            command=(
                "python",
                "scripts\\materialize_selected_packet_cohort.py",
                "--available-payloads",
                str(scope["available_payloads_output"]),
                "--output-root",
                str(scope["packages_root"]),
                "--output",
                str(scope["selected_output"]),
                "--run-id",
                f"tier1-direct-{run_id}",
            ),
            expected_outputs=(
                str(scope["selected_output"]),
                str(scope["packages_root"] / "LATEST.json"),
            ),
        ),
        PipelineStep(
            step_id="packet_deficit_dashboard",
            label="Packet deficit dashboard refresh",
            command=(
                "python",
                "scripts\\export_packet_deficit_dashboard.py",
                "--packages-root",
                str(scope["packages_root"]),
                "--output",
                str(scope["packet_deficit_output"]),
                "--markdown-output",
                str(scope["packet_deficit_markdown"]),
                "--latest-only",
            ),
            expected_outputs=(
                str(scope["packet_deficit_output"]),
                str(scope["packet_deficit_markdown"]),
            ),
        ),
    )


def _run_command(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_post_tier1_pipeline(
    *,
    promotion_path: Path,
    status_path: Path,
    markdown_path: Path,
) -> dict[str, Any]:
    promotion = _require_promoted_seed(promotion_path)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    step_results: list[dict[str, Any]] = []
    baseline_selection = select_strongest_packet_baseline(
        DEFAULT_PACKAGES_ROOT,
        current_latest_path=DEFAULT_BASELINE_PACKET_SUMMARY_PATH,
    )
    scope = _scope_paths(run_id)

    for step in _default_steps(run_id):
        completed = _run_command(step.command)
        expected_output_state = {
            path: (REPO_ROOT / Path(path)).exists() for path in step.expected_outputs
        }
        step_payload = {
            "step_id": step.step_id,
            "label": step.label,
            "command": list(step.command),
            "returncode": completed.returncode,
            "stdout_tail": _tail_text(completed.stdout),
            "stderr_tail": _tail_text(completed.stderr),
            "expected_outputs": dict(sorted(expected_output_state.items())),
            "status": "passed" if completed.returncode == 0 else "failed",
        }
        step_results.append(step_payload)
        if completed.returncode != 0:
            break

    canonical_traceability: dict[str, Any] = {}
    canonical_latest_path = scope["canonical_root"] / "LATEST.json"
    if canonical_latest_path.exists():
        canonical_payload = _read_json(canonical_latest_path)
        bindingdb_selection = canonical_payload.get("bindingdb_selection")
        if isinstance(bindingdb_selection, dict):
            canonical_traceability = {
                "canonical_latest_path": _repo_relative(canonical_latest_path),
                "bindingdb_selection": dict(bindingdb_selection),
            }

    regression_gate = compare_packet_readiness(
        baseline_selection.baseline_payload,
        _read_json(scope["selected_output"]) if scope["selected_output"].exists() else None,
        baseline_path=baseline_selection.baseline_path,
        candidate_path=_repo_relative(scope["selected_output"]),
    ).to_dict()
    regression_gate["baseline_selection"] = baseline_selection.to_dict()
    pipeline_status = "passed" if all(
        step["status"] == "passed" for step in step_results
    ) and regression_gate["status"] != "failed" else "failed"
    payload = {
        "schema_id": "proteosphere-post-tier1-direct-pipeline-2026-03-23",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": pipeline_status,
        "promotion_path": _repo_relative(promotion_path),
        "promotion_id": promotion.get("promotion_id"),
        "promotion_status": promotion.get("status"),
        "run_id": run_id,
        "scope_root": _repo_relative(scope["scope_root"]),
        "step_count": len(step_results),
        "steps": step_results,
        "canonical_traceability": canonical_traceability,
        "packet_regression_gate": regression_gate,
    }
    _write_json(status_path, payload)
    _write_text(markdown_path, render_post_tier1_pipeline_markdown(payload))
    return payload


def render_post_tier1_pipeline_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Post Tier1 Direct Pipeline",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Promotion path: `{payload['promotion_path']}`",
        f"- Promotion ID: `{payload['promotion_id']}`",
        f"- Run ID: `{payload['run_id']}`",
        f"- Scope root: `{payload['scope_root']}`",
        "",
    ]
    canonical_traceability = payload.get("canonical_traceability", {})
    if canonical_traceability:
        bindingdb_selection = canonical_traceability.get("bindingdb_selection") or {}
        lines.extend(
            [
                "## Canonical Traceability",
                "",
                "- Canonical latest path: "
                f"`{canonical_traceability.get('canonical_latest_path', '')}`",
                "- BindingDB selection path: "
                f"`{bindingdb_selection.get('selected_summary_path', '')}`",
                f"- BindingDB selection mode: `{bindingdb_selection.get('selection_mode', '')}`",
                f"- BindingDB local rows: `{bindingdb_selection.get('local_row_count', '')}`",
                "",
            ]
        )
    regression_gate = payload.get("packet_regression_gate", {})
    if regression_gate:
        lines.extend(
            [
                "## Packet Regression Gate",
                "",
                f"- Status: `{regression_gate.get('status', 'unknown')}`",
                f"- Baseline path: `{regression_gate.get('baseline_path', '')}`",
                f"- Candidate path: `{regression_gate.get('candidate_path', '')}`",
                "",
            ]
        )
        baseline_selection = regression_gate.get("baseline_selection") or {}
        if baseline_selection:
            lines.extend(
                [
                    "- Baseline selection: "
                    f"`{', '.join(baseline_selection.get('selection_notes', []))}`",
                    "- Current latest path: "
                    f"`{baseline_selection.get('current_latest_path', '')}`",
                    "- Current latest matches strongest baseline: "
                    f"`{baseline_selection.get('current_latest_matches_strongest')}`",
                    "",
                ]
            )
        baseline_metrics = regression_gate.get("baseline_metrics") or {}
        candidate_metrics = regression_gate.get("candidate_metrics") or {}
        if baseline_metrics and candidate_metrics:
            lines.extend(
                [
                    "- Complete count: "
                    f"`{baseline_metrics.get('complete_count')}` -> "
                    f"`{candidate_metrics.get('complete_count')}`",
                    "- Partial count: "
                    f"`{baseline_metrics.get('partial_count')}` -> "
                    f"`{candidate_metrics.get('partial_count')}`",
                    "- Unresolved count: "
                    f"`{baseline_metrics.get('unresolved_count')}` -> "
                    f"`{candidate_metrics.get('unresolved_count')}`",
                    "- Packet deficit count: "
                    f"`{baseline_metrics.get('packet_deficit_count')}` -> "
                    f"`{candidate_metrics.get('packet_deficit_count')}`",
                    "- Total missing modality count: "
                    f"`{baseline_metrics.get('total_missing_modality_count')}` -> "
                    f"`{candidate_metrics.get('total_missing_modality_count')}`",
                    "",
                ]
            )
        regressions = regression_gate.get("regressions") or []
        if regressions:
            lines.extend(["- Regressions:"] + [f"  - `{entry}`" for entry in regressions] + [""])
        improvements = regression_gate.get("improvements") or []
        if improvements:
            lines.extend(["- Improvements:"] + [f"  - `{entry}`" for entry in improvements] + [""])
        changed_packets = regression_gate.get("changed_packets") or []
        if changed_packets:
            lines.append("- Changed packets:")
            for change in changed_packets[:5]:
                lines.append(
                    "  - "
                    f"`{change.get('accession')}` "
                    f"`{change.get('before_status')}` -> `{change.get('after_status')}` "
                    f"missing `{change.get('before_missing_modalities')}` -> "
                    f"`{change.get('after_missing_modalities')}`"
                )
            lines.append("")
    for step in payload["steps"]:
        lines.extend(
            [
                f"## {step['step_id']}",
                "",
                f"- Label: `{step['label']}`",
                f"- Status: `{step['status']}`",
                f"- Return code: `{step['returncode']}`",
                f"- Command: `{' '.join(step['command'])}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the post-promotion Tier 1 direct rebuild pipeline."
    )
    parser.add_argument("--promotion", type=Path, default=DEFAULT_PROMOTION_PATH)
    parser.add_argument("--status-output", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = run_post_tier1_pipeline(
        promotion_path=args.promotion,
        status_path=args.status_output,
        markdown_path=args.markdown_output,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Post Tier1 direct pipeline: "
            f"status={payload['status']} steps={payload['step_count']}"
        )
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
