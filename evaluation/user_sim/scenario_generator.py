from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from evaluation.user_sim.scenario_harness import (
    DEFAULT_BENCHMARK_BENCHMARK_JSON,
    DEFAULT_CHECKPOINT_SUMMARY,
    DEFAULT_OPERATOR_LIBRARY_REGRESSION,
    DEFAULT_P20_PERSONAS,
    DEFAULT_PACKET_AUDIT,
    DEFAULT_PACKET_AUDIT_JSON,
    DEFAULT_RELEASE_PROGRAM,
    DEFAULT_RUN_SUMMARY,
    DEFAULT_TRAINING_ENVELOPES,
    DEFAULT_USER_SIM_ACCEPTANCE_MATRIX,
    DEFAULT_WEEKLONG_SOAK,
    REPO_ROOT,
    ScenarioArtifactRef,
    ScenarioPlaybackCase,
)

ScenarioEvidenceClass = Literal["rich", "mixed", "thin", "blocked"]

DEFAULT_SCENARIO_GENERATOR_ID = "phase20-scenario-generator:v1"
DEFAULT_SOURCE_COVERAGE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)
DEFAULT_USEFULNESS_REVIEW_MD = (
    REPO_ROOT / "docs" / "reports" / "real_example_usefulness_evaluation.md"
)

_RICH_ACCESSION = "P69905"
_MIXED_ACCESSION = "P68871"
_THIN_PACKET_ACCESSION = "P04637"
_THIN_LIGAND_ACCESSION = "P31749"
_THIN_BENCHMARK_ACCESSION = "Q9NZD4"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (_clean_text(value),)
    if isinstance(value, Mapping):
        return tuple(_clean_text(item) for item in value.values() if _clean_text(item))
    try:
        return tuple(_clean_text(item) for item in value if _clean_text(item))
    except TypeError:
        return (_clean_text(value),)


def _path_string(path: Path) -> str:
    return str(path).replace("\\", "/")


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


_DEFAULT_ARTIFACT_LABELS: dict[Path, str] = {
    DEFAULT_P20_PERSONAS.resolve(): "persona brief",
    DEFAULT_RELEASE_PROGRAM.resolve(): "release program",
    DEFAULT_SOURCE_COVERAGE.resolve(): "source coverage",
    DEFAULT_PACKET_AUDIT.resolve(): "packet audit",
    DEFAULT_PACKET_AUDIT_JSON.resolve(): "packet audit json",
    DEFAULT_BENCHMARK_BENCHMARK_JSON.resolve(): "portfolio benchmark json",
    DEFAULT_TRAINING_ENVELOPES.resolve(): "training envelopes",
    DEFAULT_RUN_SUMMARY.resolve(): "run summary",
    DEFAULT_CHECKPOINT_SUMMARY.resolve(): "checkpoint summary",
    DEFAULT_WEEKLONG_SOAK.resolve(): "weeklong soak note",
    DEFAULT_OPERATOR_LIBRARY_REGRESSION.resolve(): "operator library regression",
    DEFAULT_USER_SIM_ACCEPTANCE_MATRIX.resolve(): "user-sim acceptance matrix",
    DEFAULT_USEFULNESS_REVIEW_MD.resolve(): "usefulness review",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_rows(payload: Mapping[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _row_by_accession(rows: list[dict[str, Any]], accession: str) -> dict[str, Any]:
    for row in rows:
        if _clean_text(row.get("accession")) == accession:
            return row
    raise ValueError(f"missing source row for accession {accession}")


def _packet_by_accession(rows: list[dict[str, Any]], accession: str) -> dict[str, Any]:
    for row in rows:
        if _clean_text(row.get("accession")) == accession:
            return row
    raise ValueError(f"missing packet row for accession {accession}")


def _artifact(
    path: Path,
    *,
    repo_root: Path,
    label: str | None = None,
) -> ScenarioArtifactRef:
    resolved = path.resolve()
    default_label = _DEFAULT_ARTIFACT_LABELS.get(resolved)
    if default_label is None:
        default_label = path.stem.replace("_", " ").replace("-", " ")
    return ScenarioArtifactRef(
        label=label or default_label,
        path=_repo_relative(path, repo_root=repo_root),
    )


def _source_ref(path: Path, *, repo_root: Path) -> str:
    return _repo_relative(path, repo_root=repo_root)


@dataclass(frozen=True, slots=True)
class ScenarioGenerationReport:
    generator_id: str
    scenarios: tuple[ScenarioPlaybackCase, ...]
    source_files: dict[str, str]
    truth_boundary: dict[str, Any] = field(default_factory=dict)

    @property
    def selected_accessions(self) -> tuple[str, ...]:
        accessions: list[str] = []
        for scenario in self.scenarios:
            for note in scenario.notes:
                if note.startswith("accession="):
                    accessions.append(note.split("=", 1)[1])
                    break
        return tuple(accessions)

    def to_dict(self) -> dict[str, Any]:
        scenarios = [scenario.to_dict() for scenario in self.scenarios]
        state_counts = Counter(scenario.expected_state for scenario in self.scenarios)
        workflow_counts = Counter(scenario.workflow for scenario in self.scenarios)
        return {
            "generator_id": self.generator_id,
            "scenario_count": len(self.scenarios),
            "selected_accessions": list(self.selected_accessions),
            "state_counts": dict(state_counts),
            "workflow_counts": dict(workflow_counts),
            "truth_boundary": dict(self.truth_boundary),
            "source_files": dict(self.source_files),
            "scenarios": scenarios,
        }


class Phase20ScenarioGenerator:
    def __init__(self, *, repo_root: Path = REPO_ROOT) -> None:
        self.repo_root = repo_root

    def generate(self) -> ScenarioGenerationReport:
        source_coverage = _read_json(DEFAULT_SOURCE_COVERAGE)
        packet_audit = _read_json(DEFAULT_PACKET_AUDIT_JSON)

        coverage_rows = _find_rows(source_coverage, "coverage_matrix", "rows")
        packet_rows = _find_rows(packet_audit, "packets")

        rich_row = _row_by_accession(coverage_rows, _RICH_ACCESSION)
        mixed_row = _row_by_accession(coverage_rows, _MIXED_ACCESSION)
        thin_packet_row = _row_by_accession(coverage_rows, _THIN_PACKET_ACCESSION)
        thin_ligand_row = _row_by_accession(coverage_rows, _THIN_LIGAND_ACCESSION)
        thin_benchmark_row = _row_by_accession(coverage_rows, _THIN_BENCHMARK_ACCESSION)

        rich_packet = _packet_by_accession(packet_rows, _RICH_ACCESSION)
        mixed_packet = _packet_by_accession(packet_rows, _MIXED_ACCESSION)
        thin_packet = _packet_by_accession(packet_rows, _THIN_PACKET_ACCESSION)
        thin_ligand_packet = _packet_by_accession(packet_rows, _THIN_LIGAND_ACCESSION)

        scenarios = (
            ScenarioPlaybackCase(
                scenario_id=f"P20-G001-{_RICH_ACCESSION}",
                persona="Corpus Curator",
                workflow="recipe",
                expected_state="pass",
                artifacts=(
                    _artifact(DEFAULT_P20_PERSONAS, repo_root=self.repo_root),
                    _artifact(DEFAULT_RELEASE_PROGRAM, repo_root=self.repo_root),
                    _artifact(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _artifact(
                        DEFAULT_BENCHMARK_BENCHMARK_JSON,
                        repo_root=self.repo_root,
                    ),
                ),
                evidence_refs=(
                    _source_ref(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _source_ref(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _source_ref(DEFAULT_BENCHMARK_BENCHMARK_JSON, repo_root=self.repo_root),
                ),
                pass_markers=("direct_live_smoke", "direct_multilane", "useful"),
                weak_markers=("partial", "prototype", "thin"),
                truth_boundary=("truth before throughput", "selective expansion"),
                notes=(
                    f"accession={_RICH_ACCESSION}",
                    f"validation_class={rich_row.get('validation_class', '')}",
                    f"packet_judgment={rich_packet.get('judgment', '')}",
                    f"missing_modalities={_as_tuple(rich_packet.get('missing_modalities'))}",
                ),
            ),
            ScenarioPlaybackCase(
                scenario_id=f"P20-G002-{_MIXED_ACCESSION}",
                persona="Evidence Reviewer",
                workflow="review",
                expected_state="weak",
                artifacts=(
                    _artifact(DEFAULT_P20_PERSONAS, repo_root=self.repo_root),
                    _artifact(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _artifact(DEFAULT_USEFULNESS_REVIEW_MD, repo_root=self.repo_root),
                ),
                evidence_refs=(
                    _source_ref(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _source_ref(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _source_ref(DEFAULT_USEFULNESS_REVIEW_MD, repo_root=self.repo_root),
                ),
                weak_markers=("probe_backed", "mixed_evidence", "summary-library probe"),
                truth_boundary=("mixed evidence stays weak", "truth before throughput"),
                notes=(
                    f"accession={_MIXED_ACCESSION}",
                    f"validation_class={mixed_row.get('validation_class', '')}",
                    f"packet_judgment={mixed_packet.get('judgment', '')}",
                    f"missing_modalities={_as_tuple(mixed_packet.get('missing_modalities'))}",
                ),
            ),
            ScenarioPlaybackCase(
                scenario_id=f"P20-G003-{_THIN_PACKET_ACCESSION}",
                persona="Packet Planner",
                workflow="packet",
                expected_state="weak",
                artifacts=(
                    _artifact(DEFAULT_P20_PERSONAS, repo_root=self.repo_root),
                    _artifact(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _artifact(DEFAULT_TRAINING_ENVELOPES, repo_root=self.repo_root),
                ),
                evidence_refs=(
                    _source_ref(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _source_ref(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _source_ref(DEFAULT_TRAINING_ENVELOPES, repo_root=self.repo_root),
                ),
                weak_markers=("single-lane coverage", "thin_coverage", "partial"),
                truth_boundary=("partial packets remain partial", "deterministic rebuild"),
                notes=(
                    f"accession={_THIN_PACKET_ACCESSION}",
                    f"validation_class={thin_packet_row.get('validation_class', '')}",
                    f"packet_judgment={thin_packet.get('judgment', '')}",
                    f"missing_modalities={_as_tuple(thin_packet.get('missing_modalities'))}",
                ),
            ),
            ScenarioPlaybackCase(
                scenario_id=f"P20-G004-{_THIN_LIGAND_ACCESSION}",
                persona="Packet Planner",
                workflow="packet",
                expected_state="weak",
                artifacts=(
                    _artifact(DEFAULT_P20_PERSONAS, repo_root=self.repo_root),
                    _artifact(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT, repo_root=self.repo_root),
                    _artifact(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _artifact(DEFAULT_RUN_SUMMARY, repo_root=self.repo_root),
                ),
                evidence_refs=(
                    _source_ref(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _source_ref(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
                    _source_ref(DEFAULT_RUN_SUMMARY, repo_root=self.repo_root),
                ),
                weak_markers=("single-lane coverage", "thin_coverage", "partial"),
                truth_boundary=("partial packets remain partial", "truth before throughput"),
                notes=(
                    f"accession={_THIN_LIGAND_ACCESSION}",
                    f"validation_class={thin_ligand_row.get('validation_class', '')}",
                    f"packet_judgment={thin_ligand_packet.get('judgment', '')}",
                    f"missing_modalities={_as_tuple(thin_ligand_packet.get('missing_modalities'))}",
                ),
            ),
            ScenarioPlaybackCase(
                scenario_id=f"P20-G005-{_THIN_BENCHMARK_ACCESSION}",
                persona="Training Operator",
                workflow="benchmark",
                expected_state="weak",
                artifacts=(
                    _artifact(DEFAULT_P20_PERSONAS, repo_root=self.repo_root),
                    _artifact(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _artifact(DEFAULT_RUN_SUMMARY, repo_root=self.repo_root),
                    _artifact(DEFAULT_CHECKPOINT_SUMMARY, repo_root=self.repo_root),
                    _artifact(DEFAULT_TRAINING_ENVELOPES, repo_root=self.repo_root),
                ),
                evidence_refs=(
                    _source_ref(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
                    _source_ref(DEFAULT_RUN_SUMMARY, repo_root=self.repo_root),
                    _source_ref(DEFAULT_CHECKPOINT_SUMMARY, repo_root=self.repo_root),
                    _source_ref(DEFAULT_TRAINING_ENVELOPES, repo_root=self.repo_root),
                ),
                weak_markers=("snapshot_backed", "single-lane coverage", "identity-safe resume"),
                truth_boundary=("identity-safe resume", "prototype boundary"),
                notes=(
                    f"accession={_THIN_BENCHMARK_ACCESSION}",
                    f"validation_class={thin_benchmark_row.get('validation_class', '')}",
                    "benchmark envelope stays inside the prototype boundary",
                ),
            ),
            ScenarioPlaybackCase(
                scenario_id="P20-G006-BLOCKED-SOAK",
                persona="Operator Scientist",
                workflow="review",
                expected_state="blocked",
                artifacts=(
                    _artifact(DEFAULT_WEEKLONG_SOAK, repo_root=self.repo_root),
                    _artifact(DEFAULT_OPERATOR_LIBRARY_REGRESSION, repo_root=self.repo_root),
                    _artifact(DEFAULT_USER_SIM_ACCEPTANCE_MATRIX, repo_root=self.repo_root),
                ),
                evidence_refs=(
                    _source_ref(DEFAULT_WEEKLONG_SOAK, repo_root=self.repo_root),
                    _source_ref(DEFAULT_OPERATOR_LIBRARY_REGRESSION, repo_root=self.repo_root),
                ),
                blocked_markers=("not yet", "not a claim", "blocked"),
                truth_boundary=("weeklong soak remains unproven",),
                notes=(
                    "review workflow remains blocked until the acceptance matrix is landed",
                    "missing acceptance matrix is an explicit release gap",
                ),
            ),
        )

        source_files = {
            "source_coverage": _source_ref(DEFAULT_SOURCE_COVERAGE, repo_root=self.repo_root),
            "packet_audit_json": _source_ref(DEFAULT_PACKET_AUDIT_JSON, repo_root=self.repo_root),
            "packet_audit_markdown": _source_ref(DEFAULT_PACKET_AUDIT, repo_root=self.repo_root),
            "benchmark_json": _source_ref(
                DEFAULT_BENCHMARK_BENCHMARK_JSON,
                repo_root=self.repo_root,
            ),
            "run_summary": _source_ref(DEFAULT_RUN_SUMMARY, repo_root=self.repo_root),
            "checkpoint_summary": _source_ref(DEFAULT_CHECKPOINT_SUMMARY, repo_root=self.repo_root),
            "training_envelopes": _source_ref(DEFAULT_TRAINING_ENVELOPES, repo_root=self.repo_root),
            "weeklong_soak": _source_ref(DEFAULT_WEEKLONG_SOAK, repo_root=self.repo_root),
            "operator_library_regression": _source_ref(
                DEFAULT_OPERATOR_LIBRARY_REGRESSION, repo_root=self.repo_root
            ),
            "acceptance_matrix": _source_ref(
                DEFAULT_USER_SIM_ACCEPTANCE_MATRIX, repo_root=self.repo_root
            ),
        }
        truth_boundary = {
            "prototype_runtime": True,
            "release_grade_corpus_validation": False,
            "weeklong_soak_claim_allowed": False,
            "production_release_claim_allowed": False,
            "full_corpus_validation_allowed": False,
            "partial_packets_allowed": True,
            "thin_lanes_visible": True,
            "power_shell_first": True,
        }
        return ScenarioGenerationReport(
            generator_id=DEFAULT_SCENARIO_GENERATOR_ID,
            scenarios=scenarios,
            source_files=source_files,
            truth_boundary=truth_boundary,
        )


def build_phase20_scenario_suite(*, repo_root: Path = REPO_ROOT) -> ScenarioGenerationReport:
    return Phase20ScenarioGenerator(repo_root=repo_root).generate()


def build_phase20_scenarios(*, repo_root: Path = REPO_ROOT) -> tuple[ScenarioPlaybackCase, ...]:
    return build_phase20_scenario_suite(repo_root=repo_root).scenarios


__all__ = [
    "DEFAULT_SCENARIO_GENERATOR_ID",
    "Phase20ScenarioGenerator",
    "ScenarioEvidenceClass",
    "ScenarioGenerationReport",
    "build_phase20_scenario_suite",
    "build_phase20_scenarios",
]
