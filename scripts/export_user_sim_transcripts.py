from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation.user_sim.plausibility import PlausibilityCase, score_plausibility
from evaluation.user_sim.rubric_engine import (
    WorkflowRubricScenario,
    score_workflow_scenario,
)
from evaluation.user_sim.scenario_harness import (
    ScenarioPlaybackHarness,
    build_phase20_playback_cases,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_JSON_OUTPUT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "user_sim_transcript.json"
)
DEFAULT_TEXT_OUTPUT = REPO_ROOT / "docs" / "reports" / "p20_user_sim_transcript.md"
EXPORTER_ID = "phase20-user-sim-transcript:v1"


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _load_bundle(input_path: Path | None) -> dict[str, Any]:
    if input_path is None:
        return {"scenarios": [case.to_dict() for case in build_phase20_playback_cases()]}

    payload = _read_json(input_path)
    if isinstance(payload, list):
        return {"scenarios": payload}
    if not isinstance(payload, dict):
        raise TypeError("input bundle must be a JSON object or list")
    return payload


def _sequence_payload(bundle: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = bundle.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            raise TypeError(f"{key} must be a JSON list")
        return value
    return []


def _derive_rubric_scenario(trace: Any) -> WorkflowRubricScenario:
    if trace.state == "pass":
        judgment = "pass"
        evidence_mode = "rich"
    elif trace.state == "weak":
        judgment = "weak"
        evidence_mode = "mixed"
    else:
        judgment = "blocked"
        evidence_mode = "blocked"

    evidence_depth = len(trace.artifact_checks)
    if trace.state == "pass":
        evidence_depth += 2
    elif trace.state == "weak":
        evidence_depth += 1

    evidence_refs = trace.evidence_refs or tuple(check.path for check in trace.artifact_checks)
    action_items = tuple(trace.notes) or ("preserve explicit evidence citations",)
    claims = tuple(trace.truth_boundary) or ("prototype boundary preserved",)
    return WorkflowRubricScenario(
        scenario_id=trace.scenario_id,
        persona=trace.persona,
        judgment=judgment,
        evidence_mode=evidence_mode,
        evidence_depth=evidence_depth,
        evidence_refs=evidence_refs,
        action_items=action_items,
        claims=claims,
        blocker_reason=trace.rationale[0] if trace.state == "blocked" and trace.rationale else None,
        notes=trace.notes,
    )


def _derive_plausibility_case(trace: Any, transcript_text: str) -> PlausibilityCase:
    if trace.state == "pass":
        evidence_mode = "direct_live_smoke"
    elif trace.state == "weak":
        evidence_mode = "mixed_evidence"
    else:
        evidence_mode = "blocked"

    evidence_refs = trace.evidence_refs or tuple(check.path for check in trace.artifact_checks)
    claims = tuple(trace.truth_boundary) or tuple(trace.notes)
    return PlausibilityCase(
        scenario_id=trace.scenario_id,
        persona=trace.persona,
        artifact_kind=f"{trace.workflow}_transcript",
        output_text=transcript_text,
        evidence_mode=evidence_mode,
        truth_boundary={key: True for key in trace.truth_boundary} if trace.truth_boundary else {},
        evidence_refs=evidence_refs,
        claims=claims,
    )


def _artifact_citation(path: str, label: str, exists: bool) -> str:
    status = "present" if exists else "missing"
    return f"- {label}: {status} [{path}]({path})"


def _render_entry_text(
    *,
    trace: Any,
    rubric_score: Any,
    plausibility: Any | None,
) -> str:
    lines = [
        f"Scenario {trace.scenario_id} ({trace.persona}, {trace.workflow})",
        f"Observed state: {trace.state}",
        f"Expected state: {trace.expected_state}",
        (
            "Rubric: "
            f"{rubric_score.judgment} "
            f"(utility={rubric_score.utility_score}, "
            f"trust={rubric_score.trust_score}, "
            f"actionability={rubric_score.actionability_score})"
        ),
    ]
    if plausibility is None:
        lines.append("Plausibility: pending")
    else:
        lines.append(f"Plausibility: {plausibility.judgment} (score={plausibility.score})")
    lines.append("Evidence citations:")
    for artifact in trace.artifact_checks:
        lines.append(
            _artifact_citation(
                artifact.path,
                artifact.label,
                artifact.exists,
            )
        )
    if trace.evidence_refs:
        lines.append("Evidence refs:")
        for ref in trace.evidence_refs:
            lines.append(f"- {ref}")
    if trace.truth_boundary:
        lines.append("Truth boundary notes:")
        for note in trace.truth_boundary:
            lines.append(f"- {note}")
    if trace.rationale:
        lines.append("Harness rationale:")
        for reason in trace.rationale:
            lines.append(f"- {reason}")
    if getattr(rubric_score, "rationale", ()):
        lines.append("Rubric rationale:")
        for reason in rubric_score.rationale:
            lines.append(f"- {reason}")
    if getattr(plausibility, "reasons", ()):
        lines.append("Plausibility reasons:")
        for reason in plausibility.reasons:
            lines.append(f"- {reason}")
    return "\n".join(lines)


def _count(values: list[str], *, keys: tuple[str, ...]) -> dict[str, int]:
    counts = Counter(values)
    return {key: counts.get(key, 0) for key in keys}


def build_user_sim_transcript(
    *,
    input_path: Path | None = None,
) -> dict[str, Any]:
    bundle = _load_bundle(input_path)
    scenario_payloads = _sequence_payload(bundle, "scenarios", "scenario_payloads", "cases")
    rubric_payloads = _sequence_payload(
        bundle,
        "rubric_scenarios",
        "rubric_payloads",
        "rubric",
    )

    harness = ScenarioPlaybackHarness()
    traces = harness.replay_many(scenario_payloads)

    rubric_by_id: dict[str, WorkflowRubricScenario] = {}
    for payload in rubric_payloads:
        rubric_case = (
            payload
            if isinstance(payload, WorkflowRubricScenario)
            else WorkflowRubricScenario.from_dict(payload)
        )
        rubric_by_id.setdefault(rubric_case.scenario_id, rubric_case)

    entries: list[dict[str, Any]] = []
    for trace in traces:
        rubric_case = rubric_by_id.get(trace.scenario_id) or _derive_rubric_scenario(trace)
        rubric_score = score_workflow_scenario(rubric_case)
        draft_text = _render_entry_text(
            trace=trace,
            rubric_score=rubric_score,
            plausibility=None,
        )
        plausibility = score_plausibility(_derive_plausibility_case(trace, draft_text))
        entry_text = _render_entry_text(
            trace=trace,
            rubric_score=rubric_score,
            plausibility=plausibility,
        )
        entries.append(
            {
                "scenario_id": trace.scenario_id,
                "persona": trace.persona,
                "workflow": trace.workflow,
                "expected_state": trace.expected_state,
                "trace": trace.to_dict(),
                "rubric": rubric_score.to_dict(),
                "plausibility": plausibility.to_dict(),
                "transcript_text": entry_text,
            }
        )

    transcript = {
        "exporter_id": EXPORTER_ID,
        "scenario_count": len(entries),
        "summary": {
            "trace_states": _count(
                [entry["trace"]["state"] for entry in entries],
                keys=("pass", "weak", "blocked"),
            ),
            "rubric_judgments": _count(
                [entry["rubric"]["judgment"] for entry in entries],
                keys=("pass", "weak", "blocked"),
            ),
            "plausibility_judgments": _count(
                [entry["plausibility"]["judgment"] for entry in entries],
                keys=("conservative", "weak_usable", "unsupported"),
            ),
        },
        "entries": entries,
        "source_files": {
            "input": None if input_path is None else str(input_path).replace("\\", "/"),
        },
    }
    return transcript


def render_user_sim_transcript_markdown(transcript: dict[str, Any]) -> str:
    lines = [
        "# Phase 20 User-Sim Transcript",
        "",
        f"Exporter: `{transcript['exporter_id']}`",
        f"Scenario count: `{transcript['scenario_count']}`",
        (
            "Trace states: "
            f"{json.dumps(transcript['summary']['trace_states'], sort_keys=True)}"
        ),
        (
            "Rubric judgments: "
            f"{json.dumps(transcript['summary']['rubric_judgments'], sort_keys=True)}"
        ),
        (
            "Plausibility judgments: "
            f"{json.dumps(transcript['summary']['plausibility_judgments'], sort_keys=True)}"
        ),
        "",
    ]
    for entry in transcript["entries"]:
        lines.extend(
            [
                f"## {entry['scenario_id']} | {entry['persona']} | {entry['workflow']}",
                "",
                entry["transcript_text"],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def export_user_sim_transcripts(
    *,
    input_path: Path | None = None,
    json_output: Path = DEFAULT_JSON_OUTPUT,
    text_output: Path = DEFAULT_TEXT_OUTPUT,
) -> dict[str, Any]:
    transcript = build_user_sim_transcript(input_path=input_path)
    _write_json(json_output, transcript)
    _write_text(text_output, render_user_sim_transcript_markdown(transcript))
    return transcript


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export phase-20 user-sim transcripts as JSON and Markdown.",
    )
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--text-output", type=Path, default=DEFAULT_TEXT_OUTPUT)
    args = parser.parse_args(argv)

    export_user_sim_transcripts(
        input_path=args.input,
        json_output=args.json_output,
        text_output=args.text_output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
