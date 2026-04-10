from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ScenarioState = Literal["pass", "weak", "blocked"]
ScenarioWorkflow = Literal["recipe", "packet", "benchmark", "review"]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_P20_PERSONAS = REPO_ROOT / "docs" / "reports" / "p20_simulated_researcher_personas.md"
DEFAULT_RELEASE_PROGRAM = REPO_ROOT / "docs" / "reports" / "release_program_master_plan.md"
DEFAULT_SOURCE_JOIN_STRATEGIES = REPO_ROOT / "docs" / "reports" / "source_join_strategies.md"
DEFAULT_SOURCE_STORAGE_STRATEGY = REPO_ROOT / "docs" / "reports" / "source_storage_strategy.md"
DEFAULT_DATA_INVENTORY_AUDIT = REPO_ROOT / "artifacts" / "status" / "data_inventory_audit.json"
DEFAULT_PACKET_AUDIT = REPO_ROOT / "docs" / "reports" / "training_packet_audit.md"
DEFAULT_PACKET_AUDIT_JSON = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "training_packet_audit.json"
)
DEFAULT_PACKET_REBUILD = REPO_ROOT / "docs" / "reports" / "p18_packet_rebuild_determinism.md"
DEFAULT_PACKET_SOAK = REPO_ROOT / "docs" / "reports" / "p18_heavy_asset_packet_soak.md"
DEFAULT_BENCHMARK_BENCHMARK = REPO_ROOT / "docs" / "reports" / "p19_model_portfolio_benchmark.md"
DEFAULT_BENCHMARK_BENCHMARK_JSON = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "model_portfolio_benchmark.json"
)
DEFAULT_TRAINING_ENVELOPES = REPO_ROOT / "docs" / "reports" / "p19_training_envelopes.md"
DEFAULT_RUN_SUMMARY = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
)
DEFAULT_CHECKPOINT_SUMMARY = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "checkpoint_summary.json"
)
DEFAULT_WEEKLONG_SOAK = REPO_ROOT / "docs" / "reports" / "p22_weeklong_soak.md"
DEFAULT_OPERATOR_LIBRARY_REGRESSION = (
    REPO_ROOT / "docs" / "reports" / "operator_library_materialization_regression.md"
)
DEFAULT_USER_SIM_ACCEPTANCE_MATRIX = (
    REPO_ROOT / "docs" / "reports" / "p20_user_sim_acceptance_matrix.md"
)

_WORKFLOW_STATES: tuple[ScenarioState, ...] = ("pass", "weak", "blocked")
_WORKFLOW_KINDS: tuple[ScenarioWorkflow, ...] = ("recipe", "packet", "benchmark", "review")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (_clean_text(value),)
    if isinstance(value, Sequence):
        return tuple(_clean_text(item) for item in value if _clean_text(item))
    return (_clean_text(value),)


def _resolve_path(path: str | Path, *, repo_root: Path) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return repo_root / resolved


def _text_from_path(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _contains_any(text: str, markers: Sequence[str]) -> tuple[str, ...]:
    lowered = text.casefold()
    return tuple(marker for marker in markers if marker and marker.casefold() in lowered)


@dataclass(frozen=True, slots=True)
class ScenarioArtifactRef:
    label: str
    path: str
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", _clean_text(self.label))
        object.__setattr__(self, "path", _clean_text(self.path))
        object.__setattr__(self, "required", bool(self.required))
        if not self.label:
            raise ValueError("label must not be empty")
        if not self.path:
            raise ValueError("path must not be empty")

    def resolved_path(self, *, repo_root: Path = REPO_ROOT) -> Path:
        return _resolve_path(self.path, repo_root=repo_root)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path,
            "required": self.required,
        }


@dataclass(frozen=True, slots=True)
class ScenarioPlaybackCase:
    scenario_id: str
    persona: str
    workflow: ScenarioWorkflow
    expected_state: ScenarioState
    artifacts: tuple[ScenarioArtifactRef, ...]
    evidence_refs: tuple[str, ...] = ()
    pass_markers: tuple[str, ...] = ()
    weak_markers: tuple[str, ...] = ()
    blocked_markers: tuple[str, ...] = ()
    truth_boundary: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _clean_text(self.scenario_id))
        object.__setattr__(self, "persona", _clean_text(self.persona))
        object.__setattr__(self, "workflow", _clean_text(self.workflow))
        object.__setattr__(self, "expected_state", _clean_text(self.expected_state))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "evidence_refs", _as_tuple(self.evidence_refs))
        object.__setattr__(self, "pass_markers", _as_tuple(self.pass_markers))
        object.__setattr__(self, "weak_markers", _as_tuple(self.weak_markers))
        object.__setattr__(self, "blocked_markers", _as_tuple(self.blocked_markers))
        object.__setattr__(self, "truth_boundary", _as_tuple(self.truth_boundary))
        object.__setattr__(self, "notes", _as_tuple(self.notes))
        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty")
        if not self.persona:
            raise ValueError("persona must not be empty")
        if self.workflow not in _WORKFLOW_KINDS:
            raise ValueError("workflow must be recipe, packet, benchmark, or review")
        if self.expected_state not in _WORKFLOW_STATES:
            raise ValueError("expected_state must be pass, weak, or blocked")
        if not self.artifacts:
            raise ValueError("artifacts must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "persona": self.persona,
            "workflow": self.workflow,
            "expected_state": self.expected_state,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "evidence_refs": list(self.evidence_refs),
            "pass_markers": list(self.pass_markers),
            "weak_markers": list(self.weak_markers),
            "blocked_markers": list(self.blocked_markers),
            "truth_boundary": list(self.truth_boundary),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ScenarioArtifactCheck:
    label: str
    path: str
    required: bool
    exists: bool
    found_markers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path,
            "required": self.required,
            "exists": self.exists,
            "found_markers": list(self.found_markers),
        }


@dataclass(frozen=True, slots=True)
class ScenarioPlaybackTrace:
    scenario_id: str
    persona: str
    workflow: ScenarioWorkflow
    state: ScenarioState
    expected_state: ScenarioState
    artifact_checks: tuple[ScenarioArtifactCheck, ...]
    evidence_refs: tuple[str, ...]
    truth_boundary: tuple[str, ...]
    notes: tuple[str, ...]
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "persona": self.persona,
            "workflow": self.workflow,
            "state": self.state,
            "expected_state": self.expected_state,
            "artifact_checks": [artifact.to_dict() for artifact in self.artifact_checks],
            "evidence_refs": list(self.evidence_refs),
            "truth_boundary": list(self.truth_boundary),
            "notes": list(self.notes),
            "rationale": list(self.rationale),
        }


def _coerce_artifact(value: ScenarioArtifactRef | Mapping[str, Any]) -> ScenarioArtifactRef:
    if isinstance(value, ScenarioArtifactRef):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("artifact values must be ScenarioArtifactRef objects or mappings")
    return ScenarioArtifactRef(
        label=value.get("label") or value.get("name") or "",
        path=value.get("path") or "",
        required=bool(value.get("required", True)),
    )


def _coerce_case(value: ScenarioPlaybackCase | Mapping[str, Any]) -> ScenarioPlaybackCase:
    if isinstance(value, ScenarioPlaybackCase):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("scenario values must be ScenarioPlaybackCase objects or mappings")
    return ScenarioPlaybackCase(
        scenario_id=value.get("scenario_id") or value.get("id") or "",
        persona=value.get("persona") or "",
        workflow=value.get("workflow") or "",
        expected_state=value.get("expected_state") or value.get("state") or "weak",
        artifacts=tuple(_coerce_artifact(item) for item in value.get("artifacts") or ()),
        evidence_refs=value.get("evidence_refs") or (),
        pass_markers=value.get("pass_markers") or (),
        weak_markers=value.get("weak_markers") or (),
        blocked_markers=value.get("blocked_markers") or (),
        truth_boundary=value.get("truth_boundary") or (),
        notes=value.get("notes") or (),
    )


class ScenarioPlaybackHarness:
    def __init__(self, *, repo_root: Path = REPO_ROOT) -> None:
        self.repo_root = repo_root

    def replay(
        self,
        scenario: ScenarioPlaybackCase | Mapping[str, Any],
    ) -> ScenarioPlaybackTrace:
        case = _coerce_case(scenario)
        return self._replay_case(case)

    def replay_many(
        self,
        scenarios: Sequence[ScenarioPlaybackCase | Mapping[str, Any]],
    ) -> tuple[ScenarioPlaybackTrace, ...]:
        return tuple(self.replay(scenario) for scenario in scenarios)

    def _replay_case(self, case: ScenarioPlaybackCase) -> ScenarioPlaybackTrace:
        artifact_checks: list[ScenarioArtifactCheck] = []
        observed_bits: list[str] = []
        missing_artifacts: list[str] = []

        for artifact in case.artifacts:
            resolved = artifact.resolved_path(repo_root=self.repo_root)
            exists = resolved.exists()
            if not exists and artifact.required:
                missing_artifacts.append(artifact.label)
            artifact_text = _text_from_path(resolved)
            found_markers = _contains_any(
                artifact_text,
                (*case.pass_markers, *case.weak_markers, *case.blocked_markers),
            )
            if found_markers:
                observed_bits.extend(found_markers)
            observed_bits.append(artifact.label)
            observed_bits.append(artifact.path)
            artifact_checks.append(
                ScenarioArtifactCheck(
                    label=artifact.label,
                    path=artifact.path,
                    required=artifact.required,
                    exists=exists,
                    found_markers=found_markers,
                )
            )

        observed_text = "\n".join(
            (
                *observed_bits,
                *case.evidence_refs,
                *case.truth_boundary,
                *case.notes,
            )
        )
        blocked_hits = _contains_any(
            observed_text,
            case.blocked_markers,
        )
        weak_hits = _contains_any(
            observed_text,
            (*case.weak_markers, "partial", "prototype", "proxy-derived", "mixed evidence"),
        )
        pass_hits = _contains_any(observed_text, case.pass_markers)

        rationale: list[str] = []
        if missing_artifacts:
            rationale.append(
                "missing required artifact(s): " + ", ".join(sorted(missing_artifacts))
            )
        if blocked_hits:
            rationale.append("blocked markers detected: " + ", ".join(blocked_hits))
        if pass_hits:
            rationale.append("pass markers detected: " + ", ".join(pass_hits))
        if weak_hits:
            rationale.append("weak markers detected: " + ", ".join(weak_hits))
        if case.evidence_refs:
            rationale.append("evidence refs preserved explicitly")
        if case.truth_boundary:
            rationale.append("truth boundary preserved explicitly")

        state = case.expected_state
        if missing_artifacts or blocked_hits or state == "blocked":
            state = "blocked"
        elif state == "pass":
            if not pass_hits and weak_hits:
                state = "weak"
            elif not pass_hits:
                state = "weak"
        else:
            state = "weak"

        if not rationale:
            rationale.append("scenario replayed without contradictions")

        return ScenarioPlaybackTrace(
            scenario_id=case.scenario_id,
            persona=case.persona,
            workflow=case.workflow,
            state=state,  # conservative replay result
            expected_state=case.expected_state,
            artifact_checks=tuple(artifact_checks),
            evidence_refs=case.evidence_refs,
            truth_boundary=case.truth_boundary,
            notes=case.notes,
            rationale=tuple(rationale),
        )


def build_phase20_playback_cases(
    *, repo_root: Path = REPO_ROOT
) -> tuple[ScenarioPlaybackCase, ...]:
    return (
        ScenarioPlaybackCase(
            scenario_id="P20-S001",
            persona="Corpus Curator",
            workflow="recipe",
            expected_state="weak",
            artifacts=(
                ScenarioArtifactRef("persona brief", str(DEFAULT_P20_PERSONAS)),
                ScenarioArtifactRef("release program", str(DEFAULT_RELEASE_PROGRAM)),
                ScenarioArtifactRef("join strategies", str(DEFAULT_SOURCE_JOIN_STRATEGIES)),
                ScenarioArtifactRef("storage strategy", str(DEFAULT_SOURCE_STORAGE_STRATEGY)),
                ScenarioArtifactRef("data inventory audit", str(DEFAULT_DATA_INVENTORY_AUDIT)),
            ),
            evidence_refs=(
                str(DEFAULT_P20_PERSONAS),
                str(DEFAULT_RELEASE_PROGRAM),
                str(DEFAULT_SOURCE_JOIN_STRATEGIES),
                str(DEFAULT_SOURCE_STORAGE_STRATEGY),
                str(DEFAULT_DATA_INVENTORY_AUDIT),
            ),
            weak_markers=("prototype", "partial", "thin"),
            truth_boundary=("selective expansion", "truth before throughput"),
            notes=("recipe workflow should stay narrower than the corpus supports",),
        ),
        ScenarioPlaybackCase(
            scenario_id="P20-S002",
            persona="Packet Planner",
            workflow="packet",
            expected_state="weak",
            artifacts=(
                ScenarioArtifactRef("packet audit", str(DEFAULT_PACKET_AUDIT)),
                ScenarioArtifactRef("packet audit json", str(DEFAULT_PACKET_AUDIT_JSON)),
                ScenarioArtifactRef("packet rebuild report", str(DEFAULT_PACKET_REBUILD)),
                ScenarioArtifactRef("heavy asset soak", str(DEFAULT_PACKET_SOAK)),
            ),
            evidence_refs=(
                str(DEFAULT_PACKET_AUDIT),
                str(DEFAULT_PACKET_AUDIT_JSON),
                str(DEFAULT_PACKET_REBUILD),
                str(DEFAULT_PACKET_SOAK),
            ),
            weak_markers=("partial", "prototype", "thin"),
            truth_boundary=("deterministic rebuild", "partial packets remain partial"),
            notes=("packet workflow should surface completeness gaps explicitly",),
        ),
        ScenarioPlaybackCase(
            scenario_id="P20-S003",
            persona="Training Operator",
            workflow="benchmark",
            expected_state="weak",
            artifacts=(
                ScenarioArtifactRef("portfolio benchmark", str(DEFAULT_BENCHMARK_BENCHMARK)),
                ScenarioArtifactRef(
                    "portfolio benchmark json", str(DEFAULT_BENCHMARK_BENCHMARK_JSON)
                ),
                ScenarioArtifactRef("training envelopes", str(DEFAULT_TRAINING_ENVELOPES)),
                ScenarioArtifactRef("run summary", str(DEFAULT_RUN_SUMMARY)),
                ScenarioArtifactRef("checkpoint summary", str(DEFAULT_CHECKPOINT_SUMMARY)),
            ),
            evidence_refs=(
                str(DEFAULT_BENCHMARK_BENCHMARK),
                str(DEFAULT_BENCHMARK_BENCHMARK_JSON),
                str(DEFAULT_TRAINING_ENVELOPES),
                str(DEFAULT_RUN_SUMMARY),
                str(DEFAULT_CHECKPOINT_SUMMARY),
            ),
            weak_markers=("proxy-derived", "prototype", "partial"),
            truth_boundary=("identity-safe resume", "proxy-derived ranking"),
            notes=("benchmark workflow remains within the prototype boundary",),
        ),
        ScenarioPlaybackCase(
            scenario_id="P20-S004",
            persona="Operator Scientist",
            workflow="review",
            expected_state="blocked",
            artifacts=(
                ScenarioArtifactRef("weeklong soak note", str(DEFAULT_WEEKLONG_SOAK)),
                ScenarioArtifactRef(
                    "operator library regression",
                    str(DEFAULT_OPERATOR_LIBRARY_REGRESSION),
                ),
                ScenarioArtifactRef(
                    "user-sim acceptance matrix",
                    str(DEFAULT_USER_SIM_ACCEPTANCE_MATRIX),
                ),
            ),
            evidence_refs=(
                str(DEFAULT_WEEKLONG_SOAK),
                str(DEFAULT_OPERATOR_LIBRARY_REGRESSION),
            ),
            blocked_markers=("not yet", "not a claim", "blocked"),
            truth_boundary=("weeklong soak remains unproven",),
            notes=("review workflow blocks until the acceptance matrix is landed",),
        ),
    )


__all__ = [
    "REPO_ROOT",
    "ScenarioArtifactCheck",
    "ScenarioArtifactRef",
    "ScenarioPlaybackCase",
    "ScenarioPlaybackHarness",
    "ScenarioPlaybackTrace",
    "ScenarioState",
    "ScenarioWorkflow",
    "build_phase20_playback_cases",
]
