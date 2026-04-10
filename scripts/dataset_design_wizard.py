"""Dataset design wizard for PowerShell-first operator flow."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datasets.recipes.schema import (
    RecipeCompletenessPolicy,
    RecipeEvaluationContext,
    RecipeLeakagePolicy,
    RecipeRuleGroup,
    RecipeSelectionRule,
    TrainingRecipeSchema,
)
from datasets.recipes.split_simulator import (
    SplitSimulationCandidate,
    simulate_recipe_splits,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_REGISTRY_PATH = ROOT / "artifacts" / "status" / "release_cohort_registry.json"
DEFAULT_COHORT_SLICE_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "p15_upgraded_cohort_slice.json"
)
DEFAULT_SOURCE_COVERAGE_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)
DEFAULT_PACKET_AUDIT_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "training_packet_audit.json"
)
DEFAULT_USER_SIM_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "user_sim_regression.json"
)
DEFAULT_ACCEPTANCE_MATRIX_PATH = ROOT / "docs" / "reports" / "p20_acceptance_matrix.md"
DEFAULT_OPERATOR_PATH = ROOT / "scripts" / "powershell_interface.ps1"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        iterable = (values,)
    else:
        iterable = tuple(values)
    ordered: dict[str, str] = {}
    for value in iterable:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise TypeError("value must be an integer")
    return int(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise TypeError("value must be a bool")


def _unique_paths(*paths: Path | None) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for path in paths:
        if path is None:
            continue
        text = str(path)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _load_json_payload(path: Path) -> tuple[bool, Any, str | None]:
    if not path.exists():
        return False, None, f"missing input: {path}"
    try:
        return True, json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:  # pragma: no cover - defensive failure boundary
        return True, None, str(exc)


def _load_text_payload(path: Path) -> tuple[bool, str | None, str | None]:
    if not path.exists():
        return False, None, f"missing input: {path}"
    try:
        return True, path.read_text(encoding="utf-8"), None
    except Exception as exc:  # pragma: no cover - defensive failure boundary
        return True, None, str(exc)


def _scenario_accession(entry: Mapping[str, Any]) -> str | None:
    accession = _optional_text(entry.get("accession"))
    if accession:
        return accession

    trace = entry.get("trace")
    if isinstance(trace, Mapping):
        notes = trace.get("notes")
        if isinstance(notes, Sequence) and not isinstance(notes, (str, bytes)):
            for note in notes:
                text = _clean_text(note)
                if text.startswith("accession="):
                    return _optional_text(text.partition("=")[2])

    scenario_id = _optional_text(entry.get("scenario_id"))
    if not scenario_id:
        return None
    return _optional_text(scenario_id.rsplit("-", 1)[-1])


@dataclass(frozen=True, slots=True)
class TruthRow:
    accession: str
    canonical_id: str
    split: str
    leakage_key: str
    record_type: str
    bucket: str
    grade: str
    evidence_mode: str
    validation_class: str
    lane_depth: int
    present_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    source_lanes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blocker_ids: tuple[str, ...]
    source_manifest_ids: tuple[str, ...]
    thin_coverage: bool
    mixed_evidence: bool
    packet_ready: bool
    release_ready: bool
    release_state: str
    curated_ppi_state: str | None = None
    protein_depth_state: str | None = None
    bridge_state: str | None = None
    disprot_state: str | None = None
    assay_gap_state: str | None = None
    scenario_id: str | None = None
    scenario_state: str | None = None
    scenario_workflow: str | None = None
    scenario_persona: str | None = None
    scenario_rubric: str | None = None
    scenario_plausibility: str | None = None
    truth_boundary: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None

    def candidate_payload(self) -> dict[str, Any]:
        payload = {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "record_type": self.record_type,
            "split": self.split,
            "leakage_key": self.leakage_key,
            "validation_class": self.validation_class,
            "evidence_mode": self.evidence_mode,
            "lane_depth": self.lane_depth,
            "present_modalities": self.present_modalities,
            "missing_modalities": self.missing_modalities,
            "source_lanes": self.source_lanes,
            "thin_coverage": self.thin_coverage,
            "mixed_evidence": self.mixed_evidence,
            "packet_ready": self.packet_ready,
            "release_ready": self.release_ready,
            "freeze_state": "frozen",
            "inclusion_status": "included",
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def _row_from_payload(payload: Mapping[str, Any]) -> TruthRow:
    row = dict(payload)
    metadata = dict(row.get("metadata") or {})
    scenario = dict(row.get("scenario") or {})
    accession = (
        _optional_text(metadata.get("accession"))
        or _optional_text(row.get("accession"))
        or _optional_text(row.get("leakage_key"))
    )
    if not accession:
        raise ValueError("accession is required")
    canonical_id = _optional_text(row.get("canonical_id")) or f"protein:{accession}"
    tags = _clean_text_tuple(row.get("tags") or metadata.get("tags"))
    split = _optional_text(row.get("split")) or _optional_text(metadata.get("split"))
    if not split and tags:
        split = tags[0]
    split = split or "train"
    bucket = (
        _optional_text(row.get("bucket"))
        or _optional_text(metadata.get("bucket"))
        or _optional_text(row.get("coverage_bucket"))
        or _optional_text(row.get("grade"))
        or "unknown"
    )
    grade = _optional_text(row.get("grade")) or _optional_text(row.get("status")) or "unknown"
    evidence_mode = (
        _optional_text(row.get("evidence_mode"))
        or _optional_text(metadata.get("validation_class"))
        or _optional_text(row.get("validation_class"))
        or "unknown"
    )
    validation_class = (
        _optional_text(row.get("validation_class"))
        or _optional_text(metadata.get("validation_class"))
        or evidence_mode
    )
    lane_depth = _as_int(row.get("lane_depth", metadata.get("lane_depth")), 0)
    present_modalities = _clean_text_tuple(
        row.get("present_modalities") or metadata.get("present_modalities")
    )
    missing_modalities = _clean_text_tuple(
        row.get("missing_modalities") or metadata.get("missing_modalities")
    )
    source_lanes = _clean_text_tuple(row.get("source_lanes") or row.get("evidence_lanes"))
    evidence_refs = _clean_text_tuple(row.get("evidence_refs") or row.get("source_manifest_ids"))
    blocker_ids = _clean_text_tuple(row.get("blocker_ids") or metadata.get("blocker_ids"))
    source_manifest_ids = _clean_text_tuple(
        row.get("source_manifest_ids") or metadata.get("source_manifest_ids")
    )
    return TruthRow(
        accession=accession,
        canonical_id=canonical_id,
        split=split,
        leakage_key=_optional_text(row.get("leakage_key")) or accession,
        record_type=_optional_text(row.get("record_type")) or "protein",
        bucket=bucket,
        grade=grade,
        evidence_mode=evidence_mode,
        validation_class=validation_class,
        lane_depth=lane_depth,
        present_modalities=present_modalities,
        missing_modalities=missing_modalities,
        source_lanes=source_lanes,
        evidence_refs=_unique_paths(*(Path(item) for item in evidence_refs if item)),
        blocker_ids=blocker_ids,
        source_manifest_ids=source_manifest_ids,
        thin_coverage=_as_bool(row.get("thin_coverage", metadata.get("thin_coverage")), False),
        mixed_evidence=_as_bool(row.get("mixed_evidence", metadata.get("mixed_evidence")), False),
        packet_ready=_as_bool(row.get("packet_ready", metadata.get("packet_ready")), False),
        release_ready=_as_bool(row.get("release_ready", metadata.get("release_ready")), False),
        release_state=_optional_text(row.get("freeze_state"))
        or _optional_text(row.get("inclusion_status"))
        or "unknown",
        curated_ppi_state=_optional_text((row.get("curated_ppi") or {}).get("state"))
        or _optional_text(metadata.get("ppi_case_kind")),
        protein_depth_state=_optional_text((row.get("protein_depth") or {}).get("state")),
        bridge_state=_optional_text((row.get("bridge") or {}).get("state")),
        disprot_state=_optional_text((row.get("disprot") or {}).get("state")),
        assay_gap_state=_optional_text((row.get("assay_gap") or {}).get("state")),
        scenario_id=_optional_text(scenario.get("scenario_id")),
        scenario_state=_optional_text(scenario.get("state") or scenario.get("observed_state")),
        scenario_workflow=_optional_text(scenario.get("workflow")),
        scenario_persona=_optional_text(scenario.get("persona")),
        scenario_rubric=_optional_text(scenario.get("rubric")),
        scenario_plausibility=_optional_text(scenario.get("plausibility")),
        truth_boundary=_clean_text_tuple(
            row.get("truth_boundary") or scenario.get("truth_boundary")
        ),
        metadata=metadata,
    )


def _load_truth_bundle(
    *,
    release_registry_path: Path = DEFAULT_RELEASE_REGISTRY_PATH,
    cohort_slice_path: Path = DEFAULT_COHORT_SLICE_PATH,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE_PATH,
    packet_audit_path: Path = DEFAULT_PACKET_AUDIT_PATH,
    user_sim_path: Path = DEFAULT_USER_SIM_PATH,
    acceptance_matrix_path: Path = DEFAULT_ACCEPTANCE_MATRIX_PATH,
    operator_path: Path = DEFAULT_OPERATOR_PATH,
) -> tuple[list[TruthRow], dict[str, Any], tuple[str, ...]]:
    release_ok, release_data, release_error = _load_json_payload(release_registry_path)
    slice_ok, slice_data, slice_error = _load_json_payload(cohort_slice_path)
    coverage_ok, coverage_data, coverage_error = _load_json_payload(source_coverage_path)
    packet_ok, _packet_data, packet_error = _load_json_payload(packet_audit_path)
    user_ok, user_data, user_error = _load_json_payload(user_sim_path)
    acceptance_ok, _acceptance_data, acceptance_error = _load_text_payload(acceptance_matrix_path)
    operator_ok, _operator_data, operator_error = _load_text_payload(operator_path)

    slice_rows = {
        row.get("accession"): row
        for row in (slice_data or {}).get("rows", ())
        if isinstance(row, Mapping)
    }
    coverage_rows = {
        row.get("accession"): row
        for row in (coverage_data or {}).get("coverage_matrix", ())
        if isinstance(row, Mapping)
    }
    scenario_rows: dict[str, Mapping[str, Any]] = {}
    for row in (user_data or {}).get("entries", ()):
        if not isinstance(row, Mapping):
            continue
        accession = _scenario_accession(row)
        if accession:
            scenario_rows[accession] = row

    rows: list[TruthRow] = []
    release_rows = ()
    if release_ok:
        release_rows = (release_data or {}).get("entries") or (release_data or {}).get("rows") or ()
    for row in release_rows:
        if not isinstance(row, Mapping):
            continue
        metadata = dict(row.get("metadata") or {})
        accession = (
            _optional_text(metadata.get("accession"))
            or _optional_text(row.get("leakage_key"))
            or _optional_text(row.get("canonical_id"))
        )
        if not accession:
            continue
        merged = dict(row)
        merged["metadata"] = metadata
        if accession in slice_rows:
            merged.update(slice_rows[accession])
        if accession in coverage_rows:
            merged.update(coverage_rows[accession])
        if accession in scenario_rows:
            scenario = scenario_rows[accession]
            merged["scenario"] = {
                "scenario_id": scenario.get("scenario_id"),
                "state": scenario.get("observed_state"),
                "workflow": scenario.get("workflow"),
                "persona": scenario.get("persona"),
                "rubric": (scenario.get("rubric") or {}).get("judgment"),
                "plausibility": (scenario.get("plausibility") or {}).get("judgment"),
                "truth_boundary": scenario.get("truth_boundary"),
            }
        merged["evidence_refs"] = _unique_paths(
            release_registry_path,
            cohort_slice_path if slice_ok else None,
            source_coverage_path if coverage_ok else None,
            packet_audit_path if packet_ok else None,
            user_sim_path if user_ok else None,
            acceptance_matrix_path if acceptance_ok else None,
        )
        rows.append(_row_from_payload(merged))

    sources = {
        "release_registry": {
            "path": str(release_registry_path),
            "exists": release_ok,
            "error": release_error,
        },
        "cohort_slice": {"path": str(cohort_slice_path), "exists": slice_ok, "error": slice_error},
        "source_coverage": {
            "path": str(source_coverage_path),
            "exists": coverage_ok,
            "error": coverage_error,
        },
        "packet_audit": {
            "path": str(packet_audit_path),
            "exists": packet_ok,
            "error": packet_error,
        },
        "user_sim": {"path": str(user_sim_path), "exists": user_ok, "error": user_error},
        "acceptance_matrix": {
            "path": str(acceptance_matrix_path),
            "exists": acceptance_ok,
            "error": acceptance_error,
        },
        "operator_surface": {
            "path": str(operator_path),
            "exists": operator_ok,
            "error": operator_error,
        },
    }
    truth_boundary = (
        "prototype release planning surface only",
        "release registry remains conservative and blocked",
        "user-sim acceptance stays weak or blocked where evidence is thin",
    )
    return rows, sources, truth_boundary


def _build_default_recipe(rows: Sequence[TruthRow]) -> TrainingRecipeSchema:
    split_counts = Counter(row.split for row in rows if row.split)
    target_splits = {split: split_counts.get(split, 0) for split in ("train", "val", "test")}
    return TrainingRecipeSchema(
        recipe_id="recipe:dataset-design-balanced",
        title="Balanced dataset design",
        goal=(
            "Propose frozen cohort seeds that preserve leakage safety while surfacing "
            "supported, weak, and blocked evidence explicitly."
        ),
        requested_modalities=("sequence", "structure", "ligand", "ppi"),
        target_splits=target_splits,
        selection_rule=RecipeRuleGroup(
            mode="all",
            description="frozen release cohort entries",
            rules=(
                RecipeSelectionRule(
                    field_name="record_type",
                    operator="eq",
                    value="protein",
                    description="protein records only",
                ),
                RecipeSelectionRule(
                    field_name="freeze_state",
                    operator="eq",
                    value="frozen",
                    description="frozen rows only",
                ),
                RecipeSelectionRule(
                    field_name="inclusion_status",
                    operator="eq",
                    value="included",
                    description="included rows only",
                ),
            ),
        ),
        completeness_policy=RecipeCompletenessPolicy(
            requested_modalities=("sequence", "structure", "ligand", "ppi"),
            max_missing_modalities=2,
            min_lane_depth=1,
            allow_thin_coverage=False,
            allow_mixed_evidence=True,
            require_packet_ready=False,
        ),
        leakage_policy=RecipeLeakagePolicy(
            scope="accession",
            key_field="leakage_key",
            forbid_cross_split=True,
        ),
        tags=("powershell-first", "dataset-design", "cohort-proposal"),
        notes=("balanced current-cohort recipe",),
    )


def _proposal_bucket(row: TruthRow, status: str) -> str:
    if status == "supported":
        return "anchor_rich"
    if status == "weak":
        return "probe_backed"
    return row.bucket if row.bucket != "unknown" else "blocked_control"


def _status_from_row(
    row: TruthRow, evaluation: Any, recipe: TrainingRecipeSchema
) -> tuple[str, tuple[str, ...]]:
    if not evaluation.accepted:
        return "blocked", tuple(evaluation.reasons)
    notes: list[str] = []
    missing_count = len(row.missing_modalities)
    if row.evidence_mode == "direct_live_smoke" and row.lane_depth >= 5 and missing_count <= 2:
        notes.append("direct live smoke with rich lane depth supports the cohort proposal")
        return "supported", tuple(notes)
    if row.evidence_mode == "live_summary_library_probe" or row.mixed_evidence:
        notes.append("probe-backed or mixed evidence stays weak")
    if row.thin_coverage:
        notes.append("thin coverage is still explicit")
    if missing_count > recipe.completeness_policy.max_missing_modalities:
        notes.append("missing modalities sit beyond the design envelope")
    if row.packet_ready is False:
        notes.append("packet readiness remains false in the release registry")
    if row.release_ready is False:
        notes.append("release registry still marks this row as not release-ready")
    return "weak", tuple(notes)


def _score_row(row: TruthRow, status: str) -> int:
    score = 40
    score += min(row.lane_depth, 6) * 6
    score -= len(row.missing_modalities) * 8
    if row.thin_coverage:
        score -= 12
    if row.mixed_evidence:
        score -= 10
    if row.evidence_mode == "direct_live_smoke":
        score += 10
    elif row.evidence_mode == "live_summary_library_probe":
        score += 4
    if row.scenario_state == "pass":
        score += 5
    if status == "supported":
        score += 8
    elif status == "blocked":
        score -= 15
    return max(0, min(100, score))


def _build_completeness_payload(
    row: TruthRow,
    recipe: TrainingRecipeSchema,
) -> dict[str, Any]:
    completeness_ok, completeness_reasons = recipe.completeness_policy.evaluate(
        row.candidate_payload()
    )
    state = "blocked" if not completeness_ok else "degraded"
    if (
        completeness_ok
        and not row.missing_modalities
        and not row.thin_coverage
        and not row.mixed_evidence
    ):
        state = "complete"
    return {
        "status": state,
        "requested_modalities": list(recipe.completeness_policy.requested_modalities),
        "present_modalities": list(row.present_modalities),
        "missing_modalities": list(row.missing_modalities),
        "lane_depth": row.lane_depth,
        "thin_coverage": row.thin_coverage,
        "mixed_evidence": row.mixed_evidence,
        "packet_ready": row.packet_ready,
        "release_ready": row.release_ready,
        "max_missing_modalities": recipe.completeness_policy.max_missing_modalities,
        "min_lane_depth": recipe.completeness_policy.min_lane_depth,
        "reasons": list(completeness_reasons),
    }


def _build_leakage_payload(
    row: TruthRow,
    recipe: TrainingRecipeSchema,
    occupied_leakage_keys: tuple[str, ...],
    evaluation: Any,
) -> dict[str, Any]:
    leakage_ok, leakage_reasons = recipe.leakage_policy.evaluate(
        row.candidate_payload(), occupied_keys=occupied_leakage_keys
    )
    return {
        "status": "ok" if leakage_ok else "blocked",
        "scope": recipe.leakage_policy.scope,
        "key": row.leakage_key,
        "occupied_keys": list(occupied_leakage_keys),
        "forbidden_values": list(recipe.leakage_policy.blocked_key_values),
        "reasons": list(leakage_reasons),
        "accepted_by_recipe": evaluation.accepted,
    }


def _truth_payload(row: TruthRow) -> dict[str, Any]:
    return {
        "registry": {
            "grade": row.grade,
            "release_state": row.release_state,
            "packet_ready": row.packet_ready,
            "release_ready": row.release_ready,
            "blocker_ids": list(row.blocker_ids),
            "source_manifest_ids": list(row.source_manifest_ids),
        },
        "cohort_slice": {
            "curated_ppi_state": row.curated_ppi_state,
            "protein_depth_state": row.protein_depth_state,
            "bridge_state": row.bridge_state,
            "disprot_state": row.disprot_state,
            "assay_gap_state": row.assay_gap_state,
        },
        "coverage": {
            "bucket": row.bucket,
            "evidence_mode": row.evidence_mode,
            "validation_class": row.validation_class,
            "lane_depth": row.lane_depth,
            "source_lanes": list(row.source_lanes),
            "present_modalities": list(row.present_modalities),
            "missing_modalities": list(row.missing_modalities),
            "thin_coverage": row.thin_coverage,
            "mixed_evidence": row.mixed_evidence,
        },
        "scenario": {
            "scenario_id": row.scenario_id,
            "state": row.scenario_state,
            "workflow": row.scenario_workflow,
            "persona": row.scenario_persona,
            "rubric": row.scenario_rubric,
            "plausibility": row.scenario_plausibility,
            "truth_boundary": list(row.truth_boundary),
        },
    }


def build_dataset_design_report(
    recipe: TrainingRecipeSchema | None = None,
    rows: Sequence[TruthRow | Mapping[str, Any]] | None = None,
    *,
    release_registry_path: Path = DEFAULT_RELEASE_REGISTRY_PATH,
    cohort_slice_path: Path = DEFAULT_COHORT_SLICE_PATH,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE_PATH,
    packet_audit_path: Path = DEFAULT_PACKET_AUDIT_PATH,
    user_sim_path: Path = DEFAULT_USER_SIM_PATH,
    acceptance_matrix_path: Path = DEFAULT_ACCEPTANCE_MATRIX_PATH,
    operator_path: Path = DEFAULT_OPERATOR_PATH,
) -> dict[str, Any]:
    if rows is None:
        loaded_rows, sources, truth_boundary = _load_truth_bundle(
            release_registry_path=release_registry_path,
            cohort_slice_path=cohort_slice_path,
            source_coverage_path=source_coverage_path,
            packet_audit_path=packet_audit_path,
            user_sim_path=user_sim_path,
            acceptance_matrix_path=acceptance_matrix_path,
            operator_path=operator_path,
        )
    else:
        loaded_rows = [row if isinstance(row, TruthRow) else _row_from_payload(row) for row in rows]
        sources = {
            "release_registry": {"path": str(release_registry_path), "exists": True, "error": None},
            "cohort_slice": {"path": str(cohort_slice_path), "exists": True, "error": None},
            "source_coverage": {"path": str(source_coverage_path), "exists": True, "error": None},
            "packet_audit": {"path": str(packet_audit_path), "exists": True, "error": None},
            "user_sim": {"path": str(user_sim_path), "exists": True, "error": None},
            "acceptance_matrix": {
                "path": str(acceptance_matrix_path),
                "exists": True,
                "error": None,
            },
            "operator_surface": {"path": str(operator_path), "exists": True, "error": None},
        }
        truth_boundary = (
            "prototype release planning surface only",
            "release registry remains conservative and blocked",
            "user-sim acceptance stays weak or blocked where evidence is thin",
        )

    recipe = recipe or _build_default_recipe(loaded_rows)

    simulation = simulate_recipe_splits(
        recipe,
        (
            SplitSimulationCandidate(
                canonical_id=row.canonical_id,
                leakage_key=row.leakage_key,
                preferred_split=row.split,
                linked_group_id=row.canonical_id,
                lane_depth=row.lane_depth,
                bucket=row.bucket,
                validation_class=row.validation_class,
                evidence_lanes=row.source_lanes,
                blocker_ids=row.blocker_ids,
                payload=row.candidate_payload(),
            )
            for row in loaded_rows
        ),
    )
    simulated_split_by_id = {
        assignment.canonical_id: assignment.split_name for assignment in simulation.assignments
    }

    proposals: list[dict[str, Any]] = []
    occupied_leakage_keys: list[str] = []
    for row in loaded_rows:
        occupied_before = tuple(occupied_leakage_keys)
        evaluation = recipe.evaluate_candidate(
            row.candidate_payload(),
            context=RecipeEvaluationContext(occupied_leakage_keys=occupied_before),
        )
        leakage_payload = _build_leakage_payload(row, recipe, occupied_before, evaluation)
        if evaluation.accepted:
            occupied_leakage_keys.append(row.leakage_key)
        status, status_notes = _status_from_row(row, evaluation, recipe)
        if status != "blocked" and leakage_payload["status"] == "blocked":
            status = "blocked"
            status_notes = (
                *status_notes,
                "leakage diagnostics blocked this proposal",
            )
        notes = list(status_notes)
        preferred_split = simulated_split_by_id.get(row.canonical_id)
        if preferred_split != row.split:
            notes.append(f"simulated split preferred {preferred_split} instead of {row.split}")
        if row.release_ready is False:
            notes.append("release registry still marks this row as not release-ready")
        if row.packet_ready is False:
            notes.append("packet readiness remains false in the frozen registry")
        if row.scenario_id:
            notes.append(f"scenario={row.scenario_id}::{row.scenario_state or 'unknown'}")

        proposals.append(
            {
                "proposal_id": f"cohort:{row.accession}",
                "accession": row.accession,
                "canonical_id": row.canonical_id,
                "split": simulated_split_by_id.get(row.canonical_id, row.split),
                "cohort_bucket": _proposal_bucket(row, status),
                "status": status,
                "score": _score_row(row, status),
                "recipe_fit": {
                    "accepted": evaluation.accepted,
                    "reasons": list(evaluation.reasons),
                    "matched_rules": list(evaluation.matched_rules),
                },
                "leakage": leakage_payload,
                "completeness": _build_completeness_payload(row, recipe),
                "truth": _truth_payload(row),
                "evidence_refs": list(row.evidence_refs),
                "notes": notes,
            }
        )

    proposals.sort(
        key=lambda item: (
            {"supported": 0, "weak": 1, "blocked": 2}.get(item["status"], 3),
            -item["score"],
            item["accession"],
        )
    )
    summary = {
        "proposal_count": len(proposals),
        "status_counts": dict(Counter(item["status"] for item in proposals)),
        "split_counts": dict(Counter(item["split"] for item in proposals)),
        "cohort_bucket_counts": dict(Counter(item["cohort_bucket"] for item in proposals)),
        "leakage_blocked_count": sum(
            1 for item in proposals if item["leakage"]["status"] == "blocked"
        ),
        "completeness_blocked_count": sum(
            1 for item in proposals if item["completeness"]["status"] == "blocked"
        ),
        "scenario_covered_count": sum(
            1 for item in proposals if item["truth"]["scenario"]["scenario_id"]
        ),
        "simulation": {
            "linked_group_count": simulation.linked_group_count,
            "split_counts": dict(simulation.split_counts),
            "target_counts": dict(simulation.target_counts),
            "notes": list(simulation.notes),
            "leakage_collisions": list(simulation.leakage_collisions),
        },
    }
    return {
        "wizard_id": "dataset-design-wizard",
        "generated_at": datetime.now(UTC).isoformat(),
        "recipe": recipe.to_dict(),
        "sources": sources,
        "truth_boundary": list(truth_boundary),
        "summary": summary,
        "proposals": proposals,
    }


def render_report_text(report: Mapping[str, Any]) -> str:
    lines = [
        f"Wizard: {report['wizard_id']}",
        f"Recipe: {report['recipe']['recipe_id']} - {report['recipe']['title']}",
        f"Generated at: {report['generated_at']}",
        "Sources:",
    ]
    for name, info in report["sources"].items():
        state = "present" if info["exists"] else "missing"
        lines.append(f"  - {name}: {state} ({info['path']})")
        if info["error"]:
            lines.append(f"    error: {info['error']}")
    lines.append("Truth boundary:")
    for item in report["truth_boundary"]:
        lines.append(f"  - {item}")
    lines.append("Summary:")
    for key, value in report["summary"].items():
        if isinstance(value, Mapping):
            lines.append(f"  - {key}:")
            for inner_key, inner_value in value.items():
                lines.append(f"      {inner_key}: {inner_value}")
        else:
            lines.append(f"  - {key}: {value}")
    lines.append("Proposals:")
    for proposal in report["proposals"]:
        proposal_header = (
            f"  - {proposal['accession']} [{proposal['status']}] "
            f"split={proposal['split']} bucket={proposal['cohort_bucket']} "
            f"score={proposal['score']}"
        )
        completeness_line = (
            f"      completeness={proposal['completeness']['status']} "
            f"missing={proposal['completeness']['missing_modalities']} "
            f"lane_depth={proposal['completeness']['lane_depth']}"
        )
        leakage_line = (
            f"      leakage={proposal['leakage']['status']} "
            f"key={proposal['leakage']['key']} "
            f"reasons={proposal['leakage']['reasons']}"
        )
        scenario_line = (
            f"      scenario={proposal['truth']['scenario']['scenario_id'] or 'none'} / "
            f"{proposal['truth']['scenario']['state'] or 'unknown'}"
        )
        lines.append(proposal_header)
        lines.append(completeness_line)
        lines.append(leakage_line)
        lines.append(scenario_line)
        for note in proposal["notes"]:
            lines.append(f"      note: {note}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Design cohort proposals from frozen-truth artifacts and recipe constraints."
    )
    parser.add_argument(
        "--recipe-file",
        type=Path,
        default=None,
        help="Optional JSON file containing a training recipe schema.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the rendered report.",
    )
    parser.add_argument(
        "--as-json",
        action="store_true",
        help="Render JSON instead of text.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    recipe = None
    if args.recipe_file is not None:
        ok, data, error = _load_json_payload(args.recipe_file)
        if not ok or data is None:
            raise FileNotFoundError(error or f"missing recipe file: {args.recipe_file}")
        recipe = TrainingRecipeSchema.from_dict(data)
    report = build_dataset_design_report(recipe=recipe)
    output_text = json.dumps(report, indent=2) if args.as_json else render_report_text(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
    print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
