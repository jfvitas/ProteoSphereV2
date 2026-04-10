from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"
DEFAULT_SOURCE_MANIFEST = DEFAULT_RESULTS_DIR / "release_bundle_manifest.json"
DEFAULT_SUPPORT_MANIFEST = DEFAULT_RESULTS_DIR / "release_support_manifest.json"
DEFAULT_MODEL_PORTFOLIO = DEFAULT_RESULTS_DIR / "model_portfolio_benchmark.json"
DEFAULT_RELEASE_LEDGER = DEFAULT_RESULTS_DIR / "release_corpus_evidence_ledger.json"
DEFAULT_SOURCE_COVERAGE = DEFAULT_RESULTS_DIR / "source_coverage.json"
DEFAULT_METRICS_SUMMARY = DEFAULT_RESULTS_DIR / "metrics_summary.json"
DEFAULT_RUN_SUMMARY = DEFAULT_RESULTS_DIR / "run_summary.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "reports" / "release_cards"
DEFAULT_MANIFEST_OUTPUT = DEFAULT_RESULTS_DIR / "release_cards_manifest.json"
DEFAULT_BENCHMARK_CARD = DEFAULT_OUTPUT_DIR / "release_benchmark_card.md"
DEFAULT_MODEL_CARD = DEFAULT_OUTPUT_DIR / "release_model_card.md"
DEFAULT_DATA_CARD = DEFAULT_OUTPUT_DIR / "release_data_card.md"

_FORBIDDEN_OVERCLAIMS = [
    "production-equivalent runtime",
    "release-grade corpus validation",
    "full corpus success without pinned outputs",
    "silent cohort widening",
    "silent leakage across splits",
    "separate independent family sweeps",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"missing {label}: {path}")


def _format_code(value: Any) -> str:
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if value is None:
        return "`none`"
    if isinstance(value, (dict, list)):
        return f"`{json.dumps(value, sort_keys=True)}`"
    return f"`{value}`"


def _format_inline_list(items: list[Any] | tuple[Any, ...]) -> str:
    if not items:
        return "`none`"
    return ", ".join(f"`{item}`" for item in items)


def _escape_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|")


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(_escape_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_cell(cell) for cell in row) + " |")
    return lines


def _artifact_entry(path: Path, *, label: str, required: bool = False) -> dict[str, Any]:
    _assert_exists(path, label)
    return {
        "label": label,
        "path": str(path).replace("\\", "/"),
        "present": True,
        "required": required,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _validate_source_manifests(
    *,
    source_manifest: dict[str, Any],
    support_manifest: dict[str, Any],
    ledger: dict[str, Any],
    model_portfolio: dict[str, Any],
    coverage: dict[str, Any],
) -> None:
    bundle_id = str(source_manifest.get("bundle_id") or "").strip()
    if not bundle_id:
        raise ValueError("source bundle manifest missing bundle_id")
    if support_manifest.get("bundle_id") != bundle_id:
        raise ValueError("support manifest bundle_id does not match source bundle manifest")
    if support_manifest.get("release_status") != source_manifest.get("status"):
        raise ValueError("support manifest release_status does not match source bundle status")
    if support_manifest.get("truth_boundary") != source_manifest.get("truth_boundary"):
        raise ValueError("support manifest truth_boundary does not match source bundle manifest")

    truth_boundary = source_manifest.get("truth_boundary") or {}
    allowed_statuses = set(truth_boundary.get("allowed_statuses") or [])
    bundle_status = str(source_manifest.get("status") or "").strip()
    if bundle_status not in allowed_statuses:
        raise ValueError(
            f"source bundle status {bundle_status!r} is outside the allowed truth boundary"
        )

    release_artifacts = [
        item for item in source_manifest.get("release_artifacts") or [] if isinstance(item, dict)
    ]
    schema_entry = next((item for item in release_artifacts if item.get("role") == "schema"), None)
    if not schema_entry or not bool(schema_entry.get("present", False)):
        raise FileNotFoundError("missing required release artifact: schema")

    ledger_summary = ledger.get("summary") or {}
    if ledger_summary.get("release_ready_count") not in (0, "0"):
        raise ValueError("release corpus ledger claims release-ready rows, refusing to publish")
    rows = [row for row in ledger.get("rows") or [] if isinstance(row, dict)]
    if any(str(row.get("grade") or "").strip() != "blocked" for row in rows):
        raise ValueError("release corpus ledger contains non-blocked rows")
    if ledger_summary.get("blocked_count") not in (None, len(rows), str(len(rows))):
        raise ValueError("release corpus ledger blocked_count does not match row inventory")

    portfolio_boundary = model_portfolio.get("truth_boundary") or {}
    if not portfolio_boundary.get("coverage_not_validation", False):
        raise ValueError("model portfolio does not preserve coverage_not_validation truth boundary")
    release_readiness = model_portfolio.get("release_readiness") or {}
    if str(release_readiness.get("status") or "").strip() != "no_go":
        raise ValueError("model portfolio release readiness is not no_go")
    if release_readiness.get("release_ready_count") not in (0, "0"):
        raise ValueError("model portfolio claims release-ready rows, refusing to publish")

    coverage_semantics = coverage.get("semantics") or {}
    if not coverage_semantics.get("coverage_not_validation", False):
        raise ValueError("source coverage does not preserve coverage_not_validation truth boundary")
    if coverage_semantics.get("release_grade_corpus_validation", True):
        raise ValueError("source coverage claims release-grade corpus validation")


def _render_common_boundary_section(*, headline: str, supporting_artifacts: list[str]) -> list[str]:
    return [
        f"## {headline}",
        "",
        "- Status: `report-only`",
        "- Validation posture: `coverage_not_validation`",
        "- Publication stance: `fail-closed`",
        f"- Forbidden overclaims: {_format_code(_FORBIDDEN_OVERCLAIMS)}",
        f"- Supporting artifacts: {_format_inline_list(supporting_artifacts)}",
        "",
    ]


def _render_benchmark_card(
    *,
    source_manifest: dict[str, Any],
    support_manifest: dict[str, Any],
    model_portfolio: dict[str, Any],
    coverage: dict[str, Any],
    ledger: dict[str, Any],
    metrics_summary: dict[str, Any],
    run_summary: dict[str, Any],
) -> str:
    bundle_summary = source_manifest.get("bundle_summary") or {}
    coverage_summary = coverage.get("summary") or {}
    coverage_semantics = coverage.get("semantics") or {}
    ledger_summary = ledger.get("summary") or {}
    measurable = model_portfolio.get("measurable_results") or {}
    release_readiness = model_portfolio.get("release_readiness") or {}
    coverage_not_validation = _format_code(coverage_semantics.get("coverage_not_validation"))
    release_grade_validation = _format_code(
        coverage_semantics.get("release_grade_corpus_validation")
    )
    direct_live_smoke = _format_inline_list(
        measurable.get("direct_live_smoke_accessions") or []
    )
    probe_backed = _format_inline_list(measurable.get("probe_backed_accessions") or [])
    snapshot_backed = _format_inline_list(measurable.get("snapshot_backed_accessions") or [])
    verified_controls = _format_inline_list(measurable.get("verified_accession_controls") or [])
    validation_class_counts = _format_code(coverage_summary.get("validation_class_counts"))
    evidence_mode_counts = _format_code(coverage_summary.get("evidence_mode_counts"))
    lane_depth_counts = _format_code(coverage_summary.get("lane_depth_counts"))
    allowed_statuses = _format_code(
        (source_manifest.get("truth_boundary") or {}).get("allowed_statuses")
    )
    forbidden_overclaims = _format_code(
        (source_manifest.get("truth_boundary") or {}).get("forbidden_overclaims")
    )
    lines = [
        "# Release Benchmark Card",
        "",
        "- Status: `report-only`",
        f"- Bundle ID: {_format_code(source_manifest.get('bundle_id'))}",
        f"- Bundle status: {_format_code(source_manifest.get('status'))}",
        f"- Support bundle tag: {_format_code(support_manifest.get('bundle_tag'))}",
        f"- Runtime surface: {_format_code(bundle_summary.get('runtime_surface'))}",
        f"- Cohort size: {_format_code(bundle_summary.get('cohort_size'))}",
        f"- Split counts: {_format_code(bundle_summary.get('split_counts'))}",
        f"- Leakage free: {_format_code(bundle_summary.get('leakage_free'))}",
        f"- Coverage/validation boundary: {coverage_not_validation}",
        f"- Release-grade corpus validation: {release_grade_validation}",
        f"- Ledger release-ready count: {_format_code(ledger_summary.get('release_ready_count'))}",
        f"- Ledger blocked count: {_format_code(ledger_summary.get('blocked_count'))}",
        f"- Benchmark readiness: {_format_code(release_readiness.get('status'))}",
        "",
        "## Evidence Sources",
    ]
    for label, source in (
        ("release_bundle_manifest", source_manifest),
        ("release_support_manifest", support_manifest),
        ("source_coverage", coverage),
        ("release_corpus_evidence_ledger", ledger),
        ("model_portfolio_benchmark", model_portfolio),
        ("metrics_summary", metrics_summary),
        ("run_summary", run_summary),
    ):
        lines.append(f"- `{label}`: `{source.get('source_path')}`")
    lines.extend(
        [
            "",
            "## Observed Coverage",
            f"- Validation class counts: {validation_class_counts}",
            f"- Evidence mode counts: {evidence_mode_counts}",
            f"- Lane depth counts: {lane_depth_counts}",
            f"- Direct live smoke accessions: {direct_live_smoke}",
            f"- Probe-backed accessions: {probe_backed}",
            f"- Snapshot-backed accessions: {snapshot_backed}",
            f"- Verified accession controls: {verified_controls}",
            "",
            "## What This Card Supports",
            "- A report-only inventory of the frozen 12-accession benchmark cohort.",
            "- Accessions are tracked at accession granularity only; no silent cohort widening.",
            "- Coverage is described as evidence coverage, not corpus-scale validation.",
            "- Mixed evidence remains explicitly mixed evidence.",
            "",
            "## What This Card Does Not Claim",
        ]
    )
    for claim in _FORBIDDEN_OVERCLAIMS:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "",
            "## Blockers",
        ]
    )
    for blocker in source_manifest.get("blocker_categories") or []:
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            f"- Allowed statuses: {allowed_statuses}",
            f"- Forbidden overclaims: {forbidden_overclaims}",
            f"- Coverage not validation: {coverage_not_validation}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_model_card(
    *,
    source_manifest: dict[str, Any],
    support_manifest: dict[str, Any],
    model_portfolio: dict[str, Any],
    ledger: dict[str, Any],
    coverage: dict[str, Any],
) -> str:
    candidate_families = [
        row for row in model_portfolio.get("candidate_families") or [] if isinstance(row, dict)
    ]
    measurable = model_portfolio.get("measurable_results") or {}
    release_readiness = model_portfolio.get("release_readiness") or {}
    runtime_surface = _format_code(
        (model_portfolio.get("runtime_identities") or {}).get("runtime_surface")
    )
    benchmark_truth_boundary = _format_code(model_portfolio.get("truth_boundary"))
    direct_live_smoke = _format_inline_list(measurable.get("direct_live_smoke_accessions") or [])
    probe_backed = _format_inline_list(measurable.get("probe_backed_accessions") or [])
    snapshot_backed = _format_inline_list(measurable.get("snapshot_backed_accessions") or [])
    verified_controls = _format_inline_list(measurable.get("verified_accession_controls") or [])
    coverage_not_validation = _format_code(
        (coverage.get("semantics") or {}).get("coverage_not_validation")
    )
    release_ready_count = _format_code((ledger.get("summary") or {}).get("release_ready_count"))
    ledger_release_ready_line = f"- Ledger release-ready count: {release_ready_count}"
    lines = [
        "# Release Model Card",
        "",
        "- Status: `report-only`",
        f"- Benchmark kind: {_format_code(model_portfolio.get('benchmark_kind'))}",
        f"- Runtime surface: {runtime_surface}",
        f"- Benchmark truth boundary: {benchmark_truth_boundary}",
        f"- Release readiness: {_format_code(release_readiness.get('status'))}",
        f"- Release ready count: {_format_code(release_readiness.get('release_ready_count'))}",
        f"- Blocked count: {_format_code(release_readiness.get('blocked_count'))}",
        "",
        "## Evidence Sources",
        f"- `release_bundle_manifest`: `{source_manifest.get('source_path')}`",
        f"- `release_support_manifest`: `{support_manifest.get('source_path')}`",
        f"- `release_corpus_evidence_ledger`: `{ledger.get('source_path')}`",
        f"- `source_coverage`: `{coverage.get('source_path')}`",
        "",
        "## Candidate Families",
    ]
    candidate_rows = []
    for row in sorted(candidate_families, key=lambda item: int(item.get("rank") or 0)):
        candidate_rows.append(
            [
                row.get("rank"),
                row.get("name"),
                row.get("status"),
                row.get("observed_fit"),
                "; ".join(row.get("blockers") or []),
            ]
        )
    lines.extend(
        _markdown_table(
            ["Rank", "Family", "Status", "Observed fit", "Blockers"],
            candidate_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Ablation Order",
        ]
    )
    for step in model_portfolio.get("ablation_order") or []:
        if not isinstance(step, dict):
            continue
        lines.append(f"- Step {step.get('step')}: `{step.get('name')}`")
    lines.extend(
        [
            "",
            "## Measurable Results",
            f"- Direct live smoke accessions: {direct_live_smoke}",
            f"- Probe-backed accessions: {probe_backed}",
            f"- Snapshot-backed accessions: {snapshot_backed}",
            f"- Verified accession controls: {verified_controls}",
            "",
            "## Truth Boundary",
        ]
    )
    for claim in _FORBIDDEN_OVERCLAIMS:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "- The portfolio is proxy-derived, not production-equivalent.",
            "- The benchmark is an inventory over real artifacts, not corpus-scale validation.",
            "- The current recommendation is `no_go`.",
            "",
            "## Supporting Context",
            f"- Coverage not validation: {coverage_not_validation}",
            ledger_release_ready_line,
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_data_card(
    *,
    source_manifest: dict[str, Any],
    support_manifest: dict[str, Any],
    ledger: dict[str, Any],
    coverage: dict[str, Any],
    metrics_summary: dict[str, Any],
    run_summary: dict[str, Any],
) -> str:
    ledger_summary = ledger.get("summary") or {}
    coverage_summary = coverage.get("summary") or {}
    coverage_semantics = coverage.get("semantics") or {}
    thin_coverage = _format_inline_list(coverage_summary.get("thin_coverage_accessions") or [])
    mixed_evidence = _format_inline_list(coverage_summary.get("mixed_evidence_accessions") or [])
    verified_accessions = _format_inline_list(
        coverage_summary.get("verified_accession_accessions") or []
    )
    coverage_not_validation = _format_code(coverage_semantics.get("coverage_not_validation"))
    release_grade_validation = _format_code(
        coverage_semantics.get("release_grade_corpus_validation")
    )
    ledger_blocked_count = _format_code(ledger_summary.get("blocked_count"))
    ledger_release_ready_count = _format_code(ledger_summary.get("release_ready_count"))
    lines = [
        "# Release Data Card",
        "",
        "- Status: `report-only`",
        f"- Registry ID: {_format_code(ledger.get('registry_id'))}",
        f"- Release version: {_format_code(ledger.get('release_version'))}",
        f"- Freeze state: {_format_code(ledger.get('freeze_state'))}",
        f"- Ledger entry count: {_format_code(ledger_summary.get('entry_count'))}",
        f"- Included count: {_format_code(ledger_summary.get('included_count'))}",
        f"- Blocked count: {_format_code(ledger_summary.get('blocked_count'))}",
        f"- Release-ready count: {_format_code(ledger_summary.get('release_ready_count'))}",
        f"- Coverage not validation: {coverage_not_validation}",
        "",
        "## Evidence Sources",
        f"- `release bundle manifest`: `{source_manifest.get('source_path')}`",
        f"- `release support manifest`: `{support_manifest.get('source_path')}`",
        f"- `release corpus evidence ledger`: `{ledger.get('source_path')}`",
        f"- `source_coverage`: `{coverage.get('source_path')}`",
        f"- `metrics_summary`: `{metrics_summary.get('source_path')}`",
        f"- `run_summary`: `{run_summary.get('source_path')}`",
        "",
        "## Coverage Classes",
    ]
    rows = []
    for label, count in sorted((coverage_summary.get("validation_class_counts") or {}).items()):
        rows.append([label, count])
    lines.extend(_markdown_table(["Validation class", "Count"], rows))
    lines.extend(
        [
            "",
            "## Data Inventory",
            f"- Evidence mode counts: {_format_code(coverage_summary.get('evidence_mode_counts'))}",
            f"- Lane depth counts: {_format_code(coverage_summary.get('lane_depth_counts'))}",
            f"- Thin coverage accessions: {thin_coverage}",
            f"- Mixed evidence accessions: {mixed_evidence}",
            f"- Verified accession accessions: {verified_accessions}",
            "",
            "## What This Card Supports",
            "- A blocked-only evidence ledger for the frozen cohort.",
            "- Coverage accounting by validation class and lane depth.",
            "- Conservative provenance and reporting depth checks.",
            "",
            "## What This Card Does Not Claim",
        ]
    )
    for claim in _FORBIDDEN_OVERCLAIMS:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "- No row is promoted to release-ready in this ledger.",
            "- Coverage is intentionally not treated as validation.",
            "",
            "## Truth Boundary",
            f"- Release-grade corpus validation: {release_grade_validation}",
            f"- Ledger blocked count: {ledger_blocked_count}",
            f"- Ledger release-ready count: {ledger_release_ready_count}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_release_cards(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    support_manifest_path: Path = DEFAULT_SUPPORT_MANIFEST,
    model_portfolio_path: Path = DEFAULT_MODEL_PORTFOLIO,
    release_ledger_path: Path = DEFAULT_RELEASE_LEDGER,
    source_coverage_path: Path = DEFAULT_SOURCE_COVERAGE,
    metrics_summary_path: Path = DEFAULT_METRICS_SUMMARY,
    run_summary_path: Path = DEFAULT_RUN_SUMMARY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    manifest_output_path: Path = DEFAULT_MANIFEST_OUTPUT,
) -> dict[str, Any]:
    source_manifest_path = _resolve_path(source_manifest_path)
    support_manifest_path = _resolve_path(support_manifest_path)
    model_portfolio_path = _resolve_path(model_portfolio_path)
    release_ledger_path = _resolve_path(release_ledger_path)
    source_coverage_path = _resolve_path(source_coverage_path)
    metrics_summary_path = _resolve_path(metrics_summary_path)
    run_summary_path = _resolve_path(run_summary_path)
    output_dir = _resolve_path(output_dir)
    manifest_output_path = _resolve_path(manifest_output_path)

    for path, label in (
        (source_manifest_path, "source manifest"),
        (support_manifest_path, "support manifest"),
        (model_portfolio_path, "model portfolio benchmark"),
        (release_ledger_path, "release corpus evidence ledger"),
        (source_coverage_path, "source coverage"),
        (metrics_summary_path, "metrics summary"),
        (run_summary_path, "run summary"),
    ):
        _assert_exists(path, label)

    source_manifest = _read_json(source_manifest_path)
    support_manifest = _read_json(support_manifest_path)
    model_portfolio = _read_json(model_portfolio_path)
    ledger = _read_json(release_ledger_path)
    coverage = _read_json(source_coverage_path)
    metrics_summary = _read_json(metrics_summary_path)
    run_summary = _read_json(run_summary_path)

    _validate_source_manifests(
        source_manifest=source_manifest,
        support_manifest=support_manifest,
        ledger=ledger,
        model_portfolio=model_portfolio,
        coverage=coverage,
    )

    benchmark_card_path = output_dir / DEFAULT_BENCHMARK_CARD.name
    model_card_path = output_dir / DEFAULT_MODEL_CARD.name
    data_card_path = output_dir / DEFAULT_DATA_CARD.name

    source_path = str(source_manifest_path).replace("\\", "/")
    support_path = str(support_manifest_path).replace("\\", "/")
    model_path = str(model_portfolio_path).replace("\\", "/")
    ledger_path = str(release_ledger_path).replace("\\", "/")
    coverage_path = str(source_coverage_path).replace("\\", "/")
    metrics_path = str(metrics_summary_path).replace("\\", "/")
    run_path = str(run_summary_path).replace("\\", "/")

    benchmark_card = _render_benchmark_card(
        source_manifest={**source_manifest, "source_path": source_path},
        support_manifest={**support_manifest, "source_path": support_path},
        model_portfolio={**model_portfolio, "source_path": model_path},
        coverage={**coverage, "source_path": coverage_path},
        ledger={**ledger, "source_path": ledger_path},
        metrics_summary={**metrics_summary, "source_path": metrics_path},
        run_summary={**run_summary, "source_path": run_path},
    )
    model_card = _render_model_card(
        source_manifest={**source_manifest, "source_path": source_path},
        support_manifest={**support_manifest, "source_path": support_path},
        model_portfolio={**model_portfolio, "source_path": model_path},
        ledger={**ledger, "source_path": ledger_path},
        coverage={**coverage, "source_path": coverage_path},
    )
    data_card = _render_data_card(
        source_manifest={**source_manifest, "source_path": source_path},
        support_manifest={**support_manifest, "source_path": support_path},
        ledger={**ledger, "source_path": ledger_path},
        coverage={**coverage, "source_path": coverage_path},
        metrics_summary={**metrics_summary, "source_path": metrics_path},
        run_summary={**run_summary, "source_path": run_path},
    )

    _write_text(benchmark_card_path, benchmark_card)
    _write_text(model_card_path, model_card)
    _write_text(data_card_path, data_card)

    card_outputs = {
        "benchmark": _artifact_entry(benchmark_card_path, label="benchmark_card"),
        "model": _artifact_entry(model_card_path, label="model_card"),
        "data": _artifact_entry(data_card_path, label="data_card"),
    }

    manifest = {
        "artifact_id": "release_cards_manifest",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "report_only",
        "source_artifacts": {
            "release_bundle_manifest": _artifact_entry(
                source_manifest_path, label="release_bundle_manifest", required=True
            ),
            "release_support_manifest": _artifact_entry(
                support_manifest_path, label="release_support_manifest", required=True
            ),
            "model_portfolio_benchmark": _artifact_entry(
                model_portfolio_path, label="model_portfolio_benchmark", required=True
            ),
            "release_corpus_evidence_ledger": _artifact_entry(
                release_ledger_path, label="release_corpus_evidence_ledger", required=True
            ),
            "source_coverage": _artifact_entry(
                source_coverage_path, label="source_coverage", required=True
            ),
            "metrics_summary": _artifact_entry(
                metrics_summary_path, label="metrics_summary", required=True
            ),
            "run_summary": _artifact_entry(run_summary_path, label="run_summary", required=True),
        },
        "card_outputs": card_outputs,
        "paths": {
            "output_dir": str(output_dir).replace("\\", "/"),
            "benchmark_card": str(benchmark_card_path).replace("\\", "/"),
            "model_card": str(model_card_path).replace("\\", "/"),
            "data_card": str(data_card_path).replace("\\", "/"),
            "manifest_output": str(manifest_output_path).replace("\\", "/"),
        },
        "summary": {
            "bundle_id": source_manifest.get("bundle_id"),
            "bundle_status": source_manifest.get("status"),
            "bundle_tag": support_manifest.get("bundle_tag"),
            "cohort_size": (source_manifest.get("bundle_summary") or {}).get("cohort_size"),
            "split_counts": (source_manifest.get("bundle_summary") or {}).get("split_counts"),
            "validation_class_counts": (coverage.get("summary") or {}).get(
                "validation_class_counts"
            ),
            "evidence_mode_counts": (coverage.get("summary") or {}).get("evidence_mode_counts"),
            "candidate_family_count": len(model_portfolio.get("candidate_families") or []),
            "release_ready_count": (ledger.get("summary") or {}).get("release_ready_count"),
            "blocked_count": (ledger.get("summary") or {}).get("blocked_count"),
            "forbidden_overclaims": list(_FORBIDDEN_OVERCLAIMS),
        },
        "truth_boundary": {
            "report_only": True,
            "fail_closed": True,
            "coverage_not_validation": True,
            "no_production_equivalence": True,
            "no_corpus_validation_claim": True,
            "no_silent_cohort_widening": True,
            "no_silent_leakage_across_splits": True,
            "no_release_readiness_claim": True,
        },
        "source_checksums": {
            "release_bundle_manifest": _sha256(source_manifest_path),
            "release_support_manifest": _sha256(support_manifest_path),
            "model_portfolio_benchmark": _sha256(model_portfolio_path),
            "release_corpus_evidence_ledger": _sha256(release_ledger_path),
            "source_coverage": _sha256(source_coverage_path),
            "metrics_summary": _sha256(metrics_summary_path),
            "run_summary": _sha256(run_summary_path),
        },
    }

    _write_json(manifest_output_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish conservative benchmark, model, and data cards from release evidence."
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--support-manifest", type=Path, default=DEFAULT_SUPPORT_MANIFEST)
    parser.add_argument("--model-portfolio", type=Path, default=DEFAULT_MODEL_PORTFOLIO)
    parser.add_argument("--release-ledger", type=Path, default=DEFAULT_RELEASE_LEDGER)
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE)
    parser.add_argument("--metrics-summary", type=Path, default=DEFAULT_METRICS_SUMMARY)
    parser.add_argument("--run-summary", type=Path, default=DEFAULT_RUN_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-output", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_release_cards(
        source_manifest_path=args.source_manifest,
        support_manifest_path=args.support_manifest,
        model_portfolio_path=args.model_portfolio,
        release_ledger_path=args.release_ledger,
        source_coverage_path=args.source_coverage,
        metrics_summary_path=args.metrics_summary,
        run_summary_path=args.run_summary,
        output_dir=args.output_dir,
        manifest_output_path=args.manifest_output,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
