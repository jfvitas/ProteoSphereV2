from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
DEFAULT_METRICS_SUMMARY = DEFAULT_RESULTS_DIR / "metrics_summary.json"
DEFAULT_SOURCE_COVERAGE = DEFAULT_RESULTS_DIR / "source_coverage.json"
DEFAULT_PROVENANCE_TABLE = DEFAULT_RESULTS_DIR / "provenance_table.json"
DEFAULT_OUTPUT = DEFAULT_RESULTS_DIR / "real_example_review.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "real_example_usefulness_evaluation.md"
DEFAULT_LOCAL_IMPORT_VALIDATION = (
    REPO_ROOT / "docs" / "reports" / "local_source_import_validation.md"
)
DEFAULT_LOCAL_REUSE_STRATEGY = REPO_ROOT / "docs" / "reports" / "local_source_reuse_strategy.md"
DEFAULT_LOCAL_EVIDENCE_NOTE = (
    REPO_ROOT / "artifacts" / "reviews" / "p12_i008_local_evidence_join_2026_03_22.md"
)

_KNOWN_USEFUL_EVIDENCE = {"direct_live_smoke"}
_KNOWN_WEAK_EVIDENCE = {
    "direct_live_smoke",
    "in_tree_live_snapshot",
    "live_summary_library_probe",
    "live_verified_accession",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _to_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(item) for item in value)


def _path_string(path: Path) -> str:
    return str(path).replace("\\", "/")


def _format_pct(part: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def _find_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("coverage_matrix")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    rows = payload.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    nested_rows = payload.get("cohort_summary", {}).get("rows")
    if isinstance(nested_rows, list):
        return [row for row in nested_rows if isinstance(row, dict)]
    return []


def _runtime_context(
    metrics_summary: dict[str, Any],
    source_coverage: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_summary = metrics_summary.get("checkpoint_summary", {})
    resumed_checkpoint = checkpoint_summary.get("resumed_run", {})
    return {
        "backend": resumed_checkpoint.get("provenance", {}).get("backend"),
        "runtime_surface": source_coverage.get("run_context", {}).get("runtime_surface"),
        "truth_boundary_runtime_surface": metrics_summary.get("truth_boundary", {}).get(
            "runtime_surface"
        ),
        "resume_continuity": metrics_summary.get("runtime", {}).get("resume_continuity", {}),
        "checkpoint_writes": metrics_summary.get("runtime", {}).get("checkpoint_writes"),
        "checkpoint_resumes": metrics_summary.get("runtime", {}).get("checkpoint_resumes"),
        "first_run_processed_examples": metrics_summary.get("runtime", {}).get(
            "first_run_processed_examples"
        ),
        "resumed_run_processed_examples": metrics_summary.get("runtime", {}).get(
            "resumed_run_processed_examples"
        ),
        "selected_accession_count": metrics_summary.get("run", {}).get("selected_accession_count"),
    }


def _runtime_is_truthful(
    metrics_summary: dict[str, Any],
    source_coverage: dict[str, Any],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if metrics_summary.get("status") != "completed_on_prototype_runtime":
        reasons.append("metrics summary is not marked completed_on_prototype_runtime")
    if metrics_summary.get("run", {}).get("final_status") != "completed":
        reasons.append("run final status is not completed")

    resume_continuity = metrics_summary.get("runtime", {}).get("resume_continuity", {})
    if resume_continuity.get("declared") != "identity-safe":
        reasons.append("resume continuity is not identity-safe")
    if not resume_continuity.get("same_checkpoint_path"):
        reasons.append("checkpoint path continuity is broken")
    if not resume_continuity.get("same_checkpoint_ref"):
        reasons.append("checkpoint ref continuity is broken")
    if not resume_continuity.get("same_processed_example_ids"):
        reasons.append("processed-example continuity is broken")

    if source_coverage.get("semantics", {}).get("coverage_not_validation") is not True:
        reasons.append("source coverage is not explicitly conservative")
    if source_coverage.get("semantics", {}).get("release_grade_corpus_validation") is not False:
        reasons.append("release-grade corpus validation flag is not false")

    return not reasons, reasons


def _review_row(
    *,
    coverage_row: dict[str, Any] | None,
    provenance_row: dict[str, Any] | None,
    metrics_summary: dict[str, Any],
    source_coverage: dict[str, Any],
) -> dict[str, Any]:
    runtime_ok, runtime_reasons = _runtime_is_truthful(metrics_summary, source_coverage)
    row_index = None
    if coverage_row is not None:
        row_index = coverage_row.get("row_index")
    if row_index is None and provenance_row is not None:
        row_index = provenance_row.get("row_index")

    if coverage_row is None:
        accession = str(provenance_row.get("accession", ""))
        return {
            "accession": accession,
            "canonical_id": str(provenance_row.get("canonical_id", "")),
            "split": str(provenance_row.get("split", "")),
            "bucket": str(provenance_row.get("bucket", "")),
            "row_index": row_index,
            "leakage_key": str(provenance_row.get("leakage_key", "")),
            "evidence_mode": "",
            "validation_class": "",
            "lane_depth": 0,
            "mixed_evidence": False,
            "thin_coverage": False,
            "status": "blocked",
            "coverage_notes": (),
            "source_lanes": _to_tuple(provenance_row.get("source_lanes")),
            "evidence_refs": _to_tuple(provenance_row.get("evidence_refs")),
            "first_pass_visible": False,
            "resumed_visible": False,
            "completion_state": provenance_row.get("checkpoint_coverage", {}),
            "runtime_provenance": _runtime_context(metrics_summary, source_coverage),
            "judgment": "blocked",
            "rationale": (
                "missing source-coverage row for provenance entry",
                *runtime_reasons,
            ),
        }

    accession = str(coverage_row.get("accession", ""))
    provenance_ok = provenance_row is not None
    checkpoint_coverage = provenance_row.get("checkpoint_coverage", {}) if provenance_ok else {}
    evidence_mode = str(coverage_row.get("evidence_mode", "")).strip()
    lane_depth = int(coverage_row.get("lane_depth") or 0)
    mixed_evidence = bool(coverage_row.get("mixed_evidence"))
    thin_coverage = bool(coverage_row.get("thin_coverage"))
    row_status = str(coverage_row.get("status", ""))
    provenance_status = str(provenance_row.get("status", "")) if provenance_ok else ""
    first_pass_visible = bool(checkpoint_coverage.get("first_pass_visible"))
    resumed_visible = bool(checkpoint_coverage.get("resumed_visible"))
    coverage_notes = _to_tuple(coverage_row.get("coverage_notes"))
    leakage_key = str(coverage_row.get("leakage_key", ""))

    rationale = [
        f"evidence_mode={evidence_mode}",
        f"lane_depth={lane_depth}",
        f"mixed_evidence={mixed_evidence}",
        f"thin_coverage={thin_coverage}",
        f"validation_class={coverage_row.get('validation_class', '')}",
        f"checkpoint_visibility=first_pass:{first_pass_visible}, resumed:{resumed_visible}",
    ]

    if not runtime_ok:
        return {
            "accession": accession,
            "canonical_id": str(provenance_row.get("canonical_id", "")) if provenance_ok else "",
            "split": str(coverage_row.get("split", "")),
            "bucket": str(coverage_row.get("bucket", "")),
            "row_index": row_index,
            "leakage_key": leakage_key,
            "evidence_mode": evidence_mode,
            "validation_class": str(coverage_row.get("validation_class", "")),
            "lane_depth": lane_depth,
            "mixed_evidence": mixed_evidence,
            "thin_coverage": thin_coverage,
            "status": "blocked",
            "coverage_notes": coverage_notes,
            "source_lanes": _to_tuple(coverage_row.get("source_lanes")),
            "evidence_refs": _to_tuple(coverage_row.get("evidence_refs")),
            "first_pass_visible": first_pass_visible,
            "resumed_visible": resumed_visible,
            "completion_state": {
                "row_status": row_status,
                "provenance_status": provenance_status,
                "checkpoint_coverage": checkpoint_coverage,
            },
            "runtime_provenance": _runtime_context(metrics_summary, source_coverage),
            "judgment": "blocked",
            "rationale": (
                "benchmark runtime provenance is not truthful enough for scoring",
                *runtime_reasons,
            ),
        }

    if provenance_row is None:
        return {
            "accession": accession,
            "canonical_id": "",
            "split": str(coverage_row.get("split", "")),
            "bucket": str(coverage_row.get("bucket", "")),
            "row_index": row_index,
            "leakage_key": leakage_key,
            "evidence_mode": evidence_mode,
            "validation_class": str(coverage_row.get("validation_class", "")),
            "lane_depth": lane_depth,
            "mixed_evidence": mixed_evidence,
            "thin_coverage": thin_coverage,
            "status": "blocked",
            "coverage_notes": coverage_notes,
            "source_lanes": _to_tuple(coverage_row.get("source_lanes")),
            "evidence_refs": _to_tuple(coverage_row.get("evidence_refs")),
            "first_pass_visible": first_pass_visible,
            "resumed_visible": resumed_visible,
            "completion_state": {
                "row_status": row_status,
                "provenance_status": "missing",
                "checkpoint_coverage": {},
            },
            "runtime_provenance": _runtime_context(metrics_summary, source_coverage),
            "judgment": "blocked",
            "rationale": (
                "missing provenance row for accession",
                *rationale,
            ),
        }

    if row_status != "resolved" or provenance_status != "resolved":
        return {
            "accession": accession,
            "canonical_id": str(provenance_row.get("canonical_id", "")),
            "split": str(coverage_row.get("split", "")),
            "bucket": str(coverage_row.get("bucket", "")),
            "row_index": row_index,
            "leakage_key": leakage_key,
            "evidence_mode": evidence_mode,
            "validation_class": str(coverage_row.get("validation_class", "")),
            "lane_depth": lane_depth,
            "mixed_evidence": mixed_evidence,
            "thin_coverage": thin_coverage,
            "status": "blocked",
            "coverage_notes": coverage_notes,
            "source_lanes": _to_tuple(coverage_row.get("source_lanes")),
            "evidence_refs": _to_tuple(coverage_row.get("evidence_refs")),
            "first_pass_visible": first_pass_visible,
            "resumed_visible": resumed_visible,
            "completion_state": {
                "row_status": row_status,
                "provenance_status": provenance_status,
                "checkpoint_coverage": checkpoint_coverage,
            },
            "runtime_provenance": _runtime_context(metrics_summary, source_coverage),
            "judgment": "blocked",
            "rationale": (
                f"row/provenance not resolved ({row_status!r} / {provenance_status!r})",
                *rationale,
            ),
        }

    if (
        evidence_mode in _KNOWN_USEFUL_EVIDENCE
        and lane_depth >= 2
        and not mixed_evidence
        and not thin_coverage
        and (first_pass_visible or resumed_visible)
    ):
        judgment = "useful"
        rationale.insert(0, "direct live smoke with multilane, non-thin coverage")
    elif evidence_mode in _KNOWN_WEAK_EVIDENCE:
        judgment = "weak"
        if evidence_mode == "live_summary_library_probe":
            rationale.insert(0, "probe-backed and mixed evidence")
        elif thin_coverage:
            rationale.insert(0, "single-lane thin coverage")
        elif mixed_evidence:
            rationale.insert(0, "mixed evidence is conservatively weak")
        else:
            rationale.insert(0, "resolved but not strong enough for useful")
    else:
        judgment = "weak"
        rationale.insert(0, "unrecognized evidence mode treated conservatively")

    return {
        "accession": accession,
        "canonical_id": str(provenance_row.get("canonical_id", "")),
        "split": str(coverage_row.get("split", "")),
        "bucket": str(coverage_row.get("bucket", "")),
        "row_index": row_index,
        "leakage_key": leakage_key,
        "evidence_mode": evidence_mode,
        "validation_class": str(coverage_row.get("validation_class", "")),
        "lane_depth": lane_depth,
        "mixed_evidence": mixed_evidence,
        "thin_coverage": thin_coverage,
        "status": str(coverage_row.get("status", "")),
        "coverage_notes": coverage_notes,
        "source_lanes": _to_tuple(coverage_row.get("source_lanes")),
        "evidence_refs": _to_tuple(coverage_row.get("evidence_refs")),
        "first_pass_visible": first_pass_visible,
        "resumed_visible": resumed_visible,
        "completion_state": {
            "row_status": row_status,
            "provenance_status": provenance_status,
            "checkpoint_coverage": checkpoint_coverage,
        },
        "runtime_provenance": _runtime_context(metrics_summary, source_coverage),
        "judgment": judgment,
        "rationale": tuple(rationale),
    }


@dataclass(frozen=True, slots=True)
class RealExampleReviewReport:
    task_id: str
    metrics_summary_path: str
    source_coverage_path: str
    provenance_table_path: str
    runtime_provenance: dict[str, Any]
    coverage_semantics: dict[str, Any]
    examples: tuple[dict[str, Any], ...]
    source_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        examples = [dict(example) for example in self.examples]
        judgment_counts = Counter(example["judgment"] for example in examples)
        evidence_mode_counts = Counter(example["evidence_mode"] for example in examples)
        lane_depth_counts = Counter(str(example["lane_depth"]) for example in examples)
        return {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "task_id": self.task_id,
            "status": "completed",
            "runtime_provenance": dict(self.runtime_provenance),
            "coverage_semantics": dict(self.coverage_semantics),
            "summary": {
                "example_count": len(examples),
                "judgment_counts": dict(judgment_counts),
                "useful_accessions": [
                    example["accession"] for example in examples if example["judgment"] == "useful"
                ],
                "weak_accessions": [
                    example["accession"] for example in examples if example["judgment"] == "weak"
                ],
                "blocked_accessions": [
                    example["accession"] for example in examples if example["judgment"] == "blocked"
                ],
                "evidence_mode_counts": dict(evidence_mode_counts),
                "lane_depth_counts": dict(lane_depth_counts),
                "thin_coverage_count": sum(1 for example in examples if example["thin_coverage"]),
                "mixed_evidence_count": sum(1 for example in examples if example["mixed_evidence"]),
            },
            "example_reviews": examples,
            "source_files": dict(self.source_files),
        }


def review_real_examples(
    *,
    task_id: str = "P12-T007",
    metrics_summary_path: Path = DEFAULT_METRICS_SUMMARY,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE,
    provenance_table_path: Path = DEFAULT_PROVENANCE_TABLE,
) -> RealExampleReviewReport:
    metrics_summary = _read_json(metrics_summary_path)
    source_coverage = _read_json(source_coverage_path)
    provenance_table = _read_json(provenance_table_path)

    coverage_rows = _find_rows(source_coverage)
    provenance_rows = _find_rows(provenance_table)
    coverage_by_accession = {
        str(row.get("accession", "")): row for row in coverage_rows if row.get("accession")
    }
    provenance_by_accession = {
        str(row.get("accession", "")): row for row in provenance_rows if row.get("accession")
    }

    ordered_accessions = [
        str(row.get("accession", "")) for row in coverage_rows if row.get("accession")
    ]
    for accession in provenance_by_accession:
        if accession not in coverage_by_accession:
            ordered_accessions.append(accession)

    examples = []
    for accession in ordered_accessions:
        examples.append(
            _review_row(
                coverage_row=coverage_by_accession.get(accession),
                provenance_row=provenance_by_accession.get(accession),
                metrics_summary=metrics_summary,
                source_coverage=source_coverage,
            )
        )

    runtime_provenance = _runtime_context(metrics_summary, source_coverage)
    return RealExampleReviewReport(
        task_id=task_id,
        metrics_summary_path=_path_string(metrics_summary_path),
        source_coverage_path=_path_string(source_coverage_path),
        provenance_table_path=_path_string(provenance_table_path),
        runtime_provenance=runtime_provenance,
        coverage_semantics=dict(source_coverage.get("semantics", {})),
        examples=tuple(examples),
        source_files={
            "metrics_summary": _path_string(metrics_summary_path),
            "source_coverage": _path_string(source_coverage_path),
            "provenance_table": _path_string(provenance_table_path),
        },
    )


def write_real_example_review(
    output_path: Path = DEFAULT_OUTPUT,
    *,
    task_id: str = "P12-T007",
    metrics_summary_path: Path = DEFAULT_METRICS_SUMMARY,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE,
    provenance_table_path: Path = DEFAULT_PROVENANCE_TABLE,
) -> RealExampleReviewReport:
    report = review_real_examples(
        task_id=task_id,
        metrics_summary_path=metrics_summary_path,
        source_coverage_path=source_coverage_path,
        provenance_table_path=provenance_table_path,
    )
    _write_json(output_path, report.to_dict())
    return report


def render_real_example_markdown(
    report: RealExampleReviewReport,
    *,
    review_json_path: Path,
    local_import_validation_path: Path = DEFAULT_LOCAL_IMPORT_VALIDATION,
    local_reuse_strategy_path: Path = DEFAULT_LOCAL_REUSE_STRATEGY,
    local_evidence_note_path: Path = DEFAULT_LOCAL_EVIDENCE_NOTE,
) -> str:
    payload = report.to_dict()
    summary = payload["summary"]
    example_rows = payload["example_reviews"]
    useful_count = int(summary["judgment_counts"].get("useful", 0))
    weak_count = int(summary["judgment_counts"].get("weak", 0))
    blocked_count = int(summary["judgment_counts"].get("blocked", 0))
    total_count = int(summary.get("example_count", 0))
    thin_count = int(summary.get("thin_coverage_count", 0))
    mixed_count = int(summary.get("mixed_evidence_count", 0))
    runtime_surface = payload["runtime_provenance"].get("runtime_surface", "")
    resume = payload["runtime_provenance"].get("resume_continuity", {})
    backend = payload["runtime_provenance"].get("backend", "")
    selected_accession_count = payload["runtime_provenance"].get("selected_accession_count", "")
    checkpoint_writes = payload["runtime_provenance"].get("checkpoint_writes", "")
    checkpoint_resumes = payload["runtime_provenance"].get("checkpoint_resumes", "")
    useful_rate = _format_pct(useful_count, total_count)
    weak_rate = _format_pct(weak_count, total_count)
    blocked_rate = _format_pct(blocked_count, total_count)
    thin_rate = _format_pct(thin_count, total_count)
    mixed_rate = _format_pct(mixed_count, total_count)

    verdict = (
        "The real-example usefulness pass scored "
        f"{total_count} frozen benchmark examples from actual prototype-run artifacts. "
        f"{useful_count} example ({useful_rate}) is strong enough to call useful today, "
        "while the rest remain conservatively weak rather than promoted beyond the evidence."
    )
    if blocked_count:
        verdict += (
            f" {blocked_count} example(s) stayed blocked because their coverage or provenance "
            "could not be tied back cleanly."
        )

    prototype_boundary_line = (
        "This is a prototype-runtime usefulness readout, not a release-grade biological "
        "validation claim."
    )
    useful_line = f"- Useful examples: `{useful_count}/{total_count}` ({useful_rate})"
    weak_line = f"- Weak examples: `{weak_count}/{total_count}` ({weak_rate})"
    blocked_line = f"- Blocked examples: `{blocked_count}/{total_count}` ({blocked_rate})"
    thin_line = f"- Thin-coverage examples: `{thin_count}/{total_count}` ({thin_rate})"
    mixed_line = f"- Mixed-evidence examples: `{mixed_count}/{total_count}` ({mixed_rate})"
    selected_count_line = f"- Selected accession count: `{selected_accession_count}`"
    checkpoint_line = (
        f"- Checkpoint writes / resumes: `{checkpoint_writes}` / `{checkpoint_resumes}`"
    )
    local_evidence_line = (
        "Local-source bridge evidence supports statements about what was importable or "
        "joinable from the local bio-agent-lab mirrors, not about benchmark completeness:"
    )
    p69905_line = (
        "- `P69905` is the only example with direct live smoke plus multilane, non-thin "
        "support across UniProt, InterPro, Reactome, AlphaFold DB, and evolutionary evidence."
    )
    p68871_line = (
        "- `P68871` remains weak because its pair-aware support is probe-backed and mixed "
        "rather than direct assay-grade evidence."
    )
    thin_rows_line = (
        "- `P04637` and `P31749` are real direct-live rows, but each remains thin because "
        "they only carry one lane."
    )
    remainder_line = (
        "- The remaining rows are useful as traceable benchmark fixtures, but their current "
        "evidence depth is too narrow for a stronger judgment."
    )
    runtime_limit_line = (
        "- The runtime is still the local prototype surface with surrogate modality embeddings."
    )
    cohort_limit_line = (
        "- The usefulness report is frozen to the 12-accession benchmark cohort and does not "
        "widen the corpus."
    )
    import_limit_line = (
        "- Local import validation proves bridgeability on selected real files, not "
        "corpus-scale local completeness."
    )
    machine_artifact_line = (
        f"- Machine-readable review artifact: `{_path_string(review_json_path)}`"
    )

    lines = [
        "# Real Example Usefulness Evaluation",
        "",
        "Date: 2026-03-22",
        f"Task: `{report.task_id}`",
        "Status: `completed`",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        prototype_boundary_line,
        "",
        "## Aggregate Findings",
        "",
        useful_line,
        weak_line,
        blocked_line,
        thin_line,
        mixed_line,
        "",
        "## Runtime Boundary",
        "",
        f"- Runtime surface: `{runtime_surface}`",
        f"- Backend: `{backend}`",
        selected_count_line,
        checkpoint_line,
        f"- Resume continuity: `{resume.get('declared', '')}`",
        "",
        "## Per-Example Judgments",
        "",
        "| Accession | Split | Judgment | Evidence | Lanes | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for row in example_rows:
        note = str(row["rationale"][0]) if row.get("rationale") else ""
        lanes = f"{row.get('lane_depth', 0)} ({', '.join(row.get('source_lanes', []))})"
        row_line = (
            f"| `{row.get('accession', '')}` | `{row.get('split', '')}` | "
            f"`{row.get('judgment', '')}` | `{row.get('evidence_mode', '')}` | "
            f"{lanes} | {note} |"
        )
        lines.append(row_line)

    lines.extend(
        [
            "",
            "## Evidence Split",
            "",
            "Benchmark execution evidence supports statements about what actually ran and what the "
            "prototype runtime produced:",
            "",
            f"- `{_path_string(Path(report.metrics_summary_path))}`",
            f"- `{_path_string(Path(report.source_coverage_path))}`",
            f"- `{_path_string(Path(report.provenance_table_path))}`",
            "",
            local_evidence_line,
            "",
            f"- `{_path_string(local_import_validation_path)}`",
            f"- `{_path_string(local_reuse_strategy_path)}`",
            f"- `{_path_string(local_evidence_note_path)}`",
            "",
            "## What The Useful Result Actually Means",
            "",
            p69905_line,
            p68871_line,
            thin_rows_line,
            remainder_line,
            "",
            "## Limits",
            "",
            runtime_limit_line,
            cohort_limit_line,
            import_limit_line,
            machine_artifact_line,
        ]
    )
    return "\n".join(lines) + "\n"


def write_real_example_markdown(
    output_path: Path = DEFAULT_MARKDOWN_OUTPUT,
    *,
    report: RealExampleReviewReport,
    review_json_path: Path,
    local_import_validation_path: Path = DEFAULT_LOCAL_IMPORT_VALIDATION,
    local_reuse_strategy_path: Path = DEFAULT_LOCAL_REUSE_STRATEGY,
    local_evidence_note_path: Path = DEFAULT_LOCAL_EVIDENCE_NOTE,
) -> str:
    content = render_real_example_markdown(
        report,
        review_json_path=review_json_path,
        local_import_validation_path=local_import_validation_path,
        local_reuse_strategy_path=local_reuse_strategy_path,
        local_evidence_note_path=local_evidence_note_path,
    )
    _write_text(output_path, content)
    return content


__all__ = [
    "DEFAULT_METRICS_SUMMARY",
    "DEFAULT_MARKDOWN_OUTPUT",
    "DEFAULT_LOCAL_IMPORT_VALIDATION",
    "DEFAULT_LOCAL_REUSE_STRATEGY",
    "DEFAULT_LOCAL_EVIDENCE_NOTE",
    "DEFAULT_OUTPUT",
    "DEFAULT_PROVENANCE_TABLE",
    "DEFAULT_SOURCE_COVERAGE",
    "RealExampleReviewReport",
    "render_real_example_markdown",
    "review_real_examples",
    "write_real_example_markdown",
    "write_real_example_review",
]
