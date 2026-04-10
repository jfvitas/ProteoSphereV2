from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
DEFAULT_REPORTS_DIR = REPO_ROOT / "docs" / "reports"
DEFAULT_OPERATOR_RECIPES = REPO_ROOT / "scripts" / "operator_recipes.ps1"
DEFAULT_USER_SIM_REGRESSION = DEFAULT_RESULTS_DIR / "user_sim_regression.json"
DEFAULT_ACCEPTANCE_MATRIX = DEFAULT_REPORTS_DIR / "p20_acceptance_matrix.md"

ReviewState = Literal["promoted", "weak", "blocked"]
WorkspaceAction = Literal["promote", "continue", "stop"]

WORKFLOW_RECIPE_HINTS: dict[str, str] = {
    "recipe": "acceptance-review",
    "packet": "packet-triage",
    "benchmark": "benchmark-review",
    "review": "acceptance-review",
}


def _read_json(path: Path) -> tuple[bool, dict[str, Any] | None, str | None]:
    if not path.exists():
        return False, None, f"missing input: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive guard for malformed files
        return True, None, f"unreadable input: {path}: {exc}"
    if not isinstance(payload, dict):
        return True, None, f"expected JSON object: {path}"
    return True, payload, None


def _read_text(path: Path) -> tuple[bool, str | None, str | None]:
    if not path.exists():
        return False, None, f"missing input: {path}"
    try:
        return True, path.read_text(encoding="utf-8"), None
    except Exception as exc:  # pragma: no cover - defensive guard for malformed files
        return True, None, f"unreadable input: {path}: {exc}"


def _extract_recipe_ids(recipe_script: str) -> tuple[str, ...]:
    recipe_ids = tuple(dict.fromkeys(re.findall(r'recipe_id\s*=\s*"([^"]+)"', recipe_script)))
    return recipe_ids


def _coerce_text_tuple(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        return (values,)
    return tuple(str(item) for item in values if str(item).strip())


def _scenario_review_state(entry: dict[str, Any]) -> ReviewState:
    observed = str(entry.get("observed_state", "")).strip().casefold()
    if observed == "pass":
        return "promoted"
    if observed == "blocked":
        return "blocked"
    return "weak"


def _scenario_action(review_state: ReviewState) -> WorkspaceAction:
    if review_state == "promoted":
        return "promote"
    if review_state == "blocked":
        return "stop"
    return "continue"


def _recipe_hint(workflow: str, scenario_id: str, review_state: ReviewState) -> str:
    if review_state == "blocked" and "soak" in scenario_id.casefold():
        return "soak-readiness"
    return WORKFLOW_RECIPE_HINTS.get(workflow, "acceptance-review")


def _scenario_summary(
    scenario_id: str,
    persona: str,
    workflow: str,
    review_state: ReviewState,
    recipe_hint: str,
) -> str:
    if review_state == "promoted":
        return (
            f"{scenario_id} is promoted for {recipe_hint}; "
            f"{persona} / {workflow} evidence is strong enough for the front door."
        )
    if review_state == "blocked":
        return (
            f"{scenario_id} is blocked and must stop at {recipe_hint}; "
            "the evidence boundary remains explicit."
        )
    return (
        f"{scenario_id} stays weak for {recipe_hint}; "
        "continue triage without upgrading the claim."
    )


@dataclass(frozen=True, slots=True)
class ReviewScenario:
    scenario_id: str
    persona: str
    workflow: str
    expected_state: str
    observed_state: str
    review_state: ReviewState
    action: WorkspaceAction
    stop: bool
    recipe_hint: str
    promotion_target: str | None
    evidence_mode: str
    evidence_refs: tuple[str, ...]
    score: int | None
    actionability_score: int | None
    blocker_reason: str | None
    boundary_hits: tuple[str, ...]
    truth_boundary: dict[str, Any]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "persona": self.persona,
            "workflow": self.workflow,
            "expected_state": self.expected_state,
            "observed_state": self.observed_state,
            "review_state": self.review_state,
            "action": self.action,
            "stop": self.stop,
            "recipe_hint": self.recipe_hint,
            "promotion_target": self.promotion_target,
            "evidence_mode": self.evidence_mode,
            "evidence_refs": list(self.evidence_refs),
            "score": self.score,
            "actionability_score": self.actionability_score,
            "blocker_reason": self.blocker_reason,
            "boundary_hits": list(self.boundary_hits),
            "truth_boundary": self.truth_boundary,
            "summary": self.summary,
        }

    @classmethod
    def from_entry(cls, entry: dict[str, Any]) -> ReviewScenario:
        scenario_id = str(entry.get("plausibility", {}).get("scenario_id") or "").strip()
        persona = str(entry.get("persona", "")).strip()
        workflow = str(entry.get("workflow", "")).strip()
        if not workflow:
            workflow = "recipe"
        expected_state = str(entry.get("expected_state", "")).strip()
        observed_state = str(entry.get("observed_state", "")).strip()
        review_state = _scenario_review_state(entry)
        action = _scenario_action(review_state)
        recipe_hint = _recipe_hint(workflow, scenario_id, review_state)
        evidence_mode = str(entry.get("plausibility", {}).get("evidence_mode", "")).strip()
        evidence_refs = _coerce_text_tuple(entry.get("plausibility", {}).get("evidence_refs"))
        score = entry.get("plausibility", {}).get("score")
        actionability_score = entry.get("rubric", {}).get("actionability_score")
        blocker_reason = entry.get("rubric", {}).get("blocker_reason")
        boundary_hits = _coerce_text_tuple(entry.get("rubric", {}).get("boundary_hits"))
        truth_boundary = dict(entry.get("truth_boundary", {}))
        if review_state == "promoted":
            promotion_target = recipe_hint
        else:
            promotion_target = None
        summary = _scenario_summary(scenario_id, persona, workflow, review_state, recipe_hint)
        return cls(
            scenario_id=scenario_id,
            persona=persona,
            workflow=workflow,
            expected_state=expected_state,
            observed_state=observed_state,
            review_state=review_state,
            action=action,
            stop=action == "stop",
            recipe_hint=recipe_hint,
            promotion_target=promotion_target,
            evidence_mode=evidence_mode,
            evidence_refs=evidence_refs,
            score=int(score) if score is not None else None,
            actionability_score=(
                int(actionability_score) if actionability_score is not None else None
            ),
            blocker_reason=str(blocker_reason).strip() if blocker_reason else None,
            boundary_hits=boundary_hits,
            truth_boundary=truth_boundary,
            summary=summary,
        )


@dataclass(frozen=True, slots=True)
class ReviewWorkspace:
    workspace_id: str
    generated_at: str
    source_files: dict[str, str]
    operator_recipe_ids: tuple[str, ...]
    scenario_count: int
    promoted_count: int
    weak_count: int
    blocked_count: int
    stop_count: int
    batch_state: str
    batch_action: WorkspaceAction
    blockers: tuple[str, ...]
    scenarios: tuple[ReviewScenario, ...]

    def to_dict(self) -> dict[str, Any]:
        promoted = [
            scenario.to_dict()
            for scenario in self.scenarios
            if scenario.review_state == "promoted"
        ]
        weak = [
            scenario.to_dict()
            for scenario in self.scenarios
            if scenario.review_state == "weak"
        ]
        blocked = [
            scenario.to_dict()
            for scenario in self.scenarios
            if scenario.review_state == "blocked"
        ]
        return {
            "workspace_id": self.workspace_id,
            "generated_at": self.generated_at,
            "source_files": self.source_files,
            "operator_recipe_ids": list(self.operator_recipe_ids),
            "scenario_count": self.scenario_count,
            "promoted_count": self.promoted_count,
            "weak_count": self.weak_count,
            "blocked_count": self.blocked_count,
            "stop_count": self.stop_count,
            "batch_state": self.batch_state,
            "batch_action": self.batch_action,
            "blockers": list(self.blockers),
            "groups": {
                "promoted": promoted,
                "weak": weak,
                "blocked": blocked,
            },
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
        }


def build_review_workspace(
    *,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    operator_recipes_path: Path = DEFAULT_OPERATOR_RECIPES,
) -> ReviewWorkspace:
    regression_exists, regression_payload, regression_error = _read_json(
        results_dir / "user_sim_regression.json"
    )
    acceptance_exists, acceptance_text, acceptance_error = _read_text(
        reports_dir / "p20_acceptance_matrix.md"
    )
    recipes_exists, recipes_text, recipes_error = _read_text(operator_recipes_path)

    blockers = tuple(
        reason
        for reason in (regression_error, acceptance_error, recipes_error)
        if reason
    )
    recipe_ids = _extract_recipe_ids(recipes_text) if recipes_text else ()

    if not regression_exists or regression_payload is None:
        batch_state = "blocked"
        batch_action = "stop"
        return ReviewWorkspace(
            workspace_id="review-workspace:blocked",
            generated_at="",
            source_files={
                "user_sim_regression": str(results_dir / "user_sim_regression.json"),
                "acceptance_matrix": str(reports_dir / "p20_acceptance_matrix.md"),
                "operator_recipes": str(operator_recipes_path),
            },
            operator_recipe_ids=recipe_ids,
            scenario_count=0,
            promoted_count=0,
            weak_count=0,
            blocked_count=0,
            stop_count=0,
            batch_state=batch_state,
            batch_action=batch_action,
            blockers=blockers,
            scenarios=(),
        )

    entries = regression_payload.get("entries") or []
    scenarios = tuple(
        ReviewScenario.from_entry(entry)
        for entry in entries
        if isinstance(entry, dict)
    )
    promoted_count = sum(1 for scenario in scenarios if scenario.review_state == "promoted")
    weak_count = sum(1 for scenario in scenarios if scenario.review_state == "weak")
    blocked_count = sum(1 for scenario in scenarios if scenario.review_state == "blocked")
    stop_count = sum(1 for scenario in scenarios if scenario.stop)
    if blocked_count:
        batch_state = "blocked"
        batch_action = "stop"
    elif weak_count:
        batch_state = "weak"
        batch_action = "continue"
    else:
        batch_state = "promoted"
        batch_action = "promote"

    generated_at = str(regression_payload.get("generated_at", "")).strip()
    workspace_id = "review-workspace:user-sim-regression"
    if generated_at:
        workspace_id = f"{workspace_id}:{generated_at}"

    source_files = {
        "user_sim_regression": str(results_dir / "user_sim_regression.json"),
        "acceptance_matrix": str(reports_dir / "p20_acceptance_matrix.md"),
        "operator_recipes": str(operator_recipes_path),
    }
    if acceptance_exists and acceptance_text is not None:
        source_files["acceptance_matrix_status"] = "available"
    else:
        source_files["acceptance_matrix_status"] = "missing"

    return ReviewWorkspace(
        workspace_id=workspace_id,
        generated_at=generated_at,
        source_files=source_files,
        operator_recipe_ids=recipe_ids,
        scenario_count=len(scenarios),
        promoted_count=promoted_count,
        weak_count=weak_count,
        blocked_count=blocked_count,
        stop_count=stop_count,
        batch_state=batch_state,
        batch_action=batch_action,
        blockers=blockers,
        scenarios=scenarios,
    )


def render_workspace_text(workspace: ReviewWorkspace) -> str:
    lines = [
        f"Workspace: {workspace.workspace_id}",
        f"Batch state: {workspace.batch_state}",
        f"Batch action: {workspace.batch_action}",
        f"Scenarios: {workspace.scenario_count}",
        f"Promoted: {workspace.promoted_count}",
        f"Weak: {workspace.weak_count}",
        f"Blocked: {workspace.blocked_count}",
        f"Stops: {workspace.stop_count}",
        "Blockers:",
    ]
    if workspace.blockers:
        for blocker in workspace.blockers:
            lines.append(f"  - {blocker}")
    else:
        lines.append("  - none")
    lines.append("Scenario triage:")
    for scenario in workspace.scenarios:
        lines.append(
            f"  - {scenario.scenario_id} [{scenario.review_state}] -> {scenario.recipe_hint}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the operator review and triage workspace from user-sim evidence."
    )
    parser.add_argument(
        "--results-dir",
        default=str(DEFAULT_RESULTS_DIR),
        help="Path to the real benchmark full_results directory.",
    )
    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORTS_DIR),
        help="Path to the docs/reports directory.",
    )
    parser.add_argument(
        "--operator-recipes",
        default=str(DEFAULT_OPERATOR_RECIPES),
        help="Path to the operator recipe PowerShell surface.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a compact human-readable summary.",
    )
    args = parser.parse_args(argv)

    workspace = build_review_workspace(
        results_dir=Path(args.results_dir),
        reports_dir=Path(args.reports_dir),
        operator_recipes_path=Path(args.operator_recipes),
    )
    if args.json:
        print(json.dumps(workspace.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_workspace_text(workspace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
