from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STALE_AFTER_DAYS = 21

DEFAULT_REQUIRED_REPORT_DOCS = (
    Path("runs/real_data_benchmark/full_results/release_bundle_manifest.json"),
    Path("runs/real_data_benchmark/full_results/release_notes.md"),
    Path("runs/real_data_benchmark/full_results/release_support_manifest.json"),
    Path("docs/reports/release_artifact_hardening.md"),
    Path("docs/reports/release_benchmark_bundle.md"),
    Path("docs/reports/release_grade_gap_analysis.md"),
    Path("docs/reports/release_program_master_plan.md"),
    Path("docs/reports/release_provenance_lineage_gap_analysis.md"),
    Path("docs/reports/release_stabilization_regression.md"),
    Path("docs/reports/p24_rc_signoff_plan.md"),
)

DEFAULT_REQUIRED_RUNBOOK_DOCS = (
    Path("docs/runbooks/autonomous_loop.md"),
    Path("docs/runbooks/canonical_materialization.md"),
    Path("docs/runbooks/data_inventory_audit.md"),
    Path("docs/runbooks/local_source_import.md"),
    Path("docs/runbooks/raw_data_bootstrap.md"),
    Path("docs/runbooks/support_simulation_pack.md"),
    Path("docs/runbooks/weeklong_codex_automation.md"),
)

_TIMESTAMP_KEYS = ("generated_at", "updated_at", "last_updated", "lastUpdated")
_MARKER_PATTERN = re.compile(
    r"^(?:[-*]\s*)?(?:generated at|updated at|last updated):\s*`?([^`]+)`?\s*$",
    re.IGNORECASE,
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _extract_timestamp_from_json(payload: dict[str, Any]) -> datetime | None:
    for key in _TIMESTAMP_KEYS:
        parsed = _parse_timestamp(payload.get(key))
        if parsed is not None:
            return parsed
    return None


def _extract_timestamp_from_text(text: str) -> datetime | None:
    for line in text.splitlines()[:30]:
        match = _MARKER_PATTERN.match(line.strip())
        if match:
            parsed = _parse_timestamp(match.group(1))
            if parsed is not None:
                return parsed
    return None


def _document_timestamp(path: Path) -> tuple[datetime, str]:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(_read_text(path))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            parsed = _extract_timestamp_from_json(payload)
            if parsed is not None:
                return parsed, "json-marker"

    try:
        text = _read_text(path)
    except UnicodeDecodeError:
        text = ""

    parsed = _extract_timestamp_from_text(text)
    if parsed is not None:
        return parsed, "text-marker"

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC), "mtime"


def _resolve_required_docs(repo_root: Path, docs: Sequence[Path]) -> list[Path]:
    resolved: list[Path] = []
    for item in docs:
        resolved.append(item if item.is_absolute() else repo_root / item)
    return resolved


def _check_doc(path: Path, *, as_of: datetime, stale_after: timedelta) -> dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path).replace("\\", "/"),
            "exists": False,
            "status": "missing",
            "age_days": None,
            "timestamp": None,
            "timestamp_source": None,
        }

    timestamp, timestamp_source = _document_timestamp(path)
    age = as_of - timestamp
    stale = age > stale_after
    return {
        "path": str(path).replace("\\", "/"),
        "exists": True,
        "status": "stale" if stale else "fresh",
        "age_days": round(age.total_seconds() / 86_400, 3),
        "timestamp": timestamp.isoformat(),
        "timestamp_source": timestamp_source,
    }


def _summarize_docs(doc_checks: Iterable[dict[str, Any]]) -> dict[str, Any]:
    checks = list(doc_checks)
    missing = [item["path"] for item in checks if item["status"] == "missing"]
    stale = [item["path"] for item in checks if item["status"] == "stale"]
    fresh = [item["path"] for item in checks if item["status"] == "fresh"]
    return {
        "required_count": len(checks),
        "present_count": len(checks) - len(missing),
        "fresh_count": len(fresh),
        "missing_count": len(missing),
        "stale_count": len(stale),
        "missing_docs": missing,
        "stale_docs": stale,
        "fresh_docs": fresh,
        "checks": checks,
    }


def build_release_docs_validation(
    *,
    repo_root: Path = REPO_ROOT,
    required_report_docs: Sequence[Path] = DEFAULT_REQUIRED_REPORT_DOCS,
    required_runbook_docs: Sequence[Path] = DEFAULT_REQUIRED_RUNBOOK_DOCS,
    stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    current_time = (as_of or datetime.now(UTC)).astimezone(UTC)
    stale_after = timedelta(days=stale_after_days)

    report_paths = _resolve_required_docs(repo_root, required_report_docs)
    runbook_paths = _resolve_required_docs(repo_root, required_runbook_docs)
    report_checks = [
        _check_doc(path, as_of=current_time, stale_after=stale_after)
        for path in report_paths
    ]
    runbook_checks = [
        _check_doc(path, as_of=current_time, stale_after=stale_after)
        for path in runbook_paths
    ]

    report_summary = _summarize_docs(report_checks)
    runbook_summary = _summarize_docs(runbook_checks)

    missing_docs = report_summary["missing_docs"] + runbook_summary["missing_docs"]
    stale_docs = report_summary["stale_docs"] + runbook_summary["stale_docs"]
    blocked_reasons = []
    if missing_docs:
        blocked_reasons.append("missing_release_docs")
    if stale_docs:
        blocked_reasons.append("stale_release_docs")

    status = "ok" if not blocked_reasons else "blocked"
    return {
        "artifact_id": "release_docs_validation",
        "schema_id": "proteosphere-release-docs-validation-2026-04-03",
        "generated_at": current_time.isoformat(),
        "status": status,
        "stale_after_days": stale_after_days,
        "required_sets": {
            "reports": [str(path).replace("\\", "/") for path in report_paths],
            "runbooks": [str(path).replace("\\", "/") for path in runbook_paths],
        },
        "report_validation": report_summary,
        "runbook_validation": runbook_summary,
        "overall_assessment": {
            "status": status,
            "blocked_reasons": blocked_reasons,
            "missing_doc_count": len(missing_docs),
            "stale_doc_count": len(stale_docs),
            "required_doc_count": len(report_paths) + len(runbook_paths),
            "present_doc_count": report_summary["present_count"] + runbook_summary["present_count"],
            "fresh_doc_count": report_summary["fresh_count"] + runbook_summary["fresh_count"],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    overall = payload["overall_assessment"]
    lines = [
        "# Release Docs Validation",
        "",
        f"- Status: `{overall['status']}`",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Stale after days: `{payload['stale_after_days']}`",
        "",
        "## Required Reports",
        "",
    ]
    for item in payload["report_validation"]["checks"]:
        lines.append(f"- `{item['path']}`: `{item['status']}`")
    lines.extend(["", "## Required Runbooks", ""])
    for item in payload["runbook_validation"]["checks"]:
        lines.append(f"- `{item['path']}`: `{item['status']}`")
    if overall["blocked_reasons"]:
        lines.extend(["", "## Blocked Reasons", ""])
        lines.extend(f"- `{reason}`" for reason in overall["blocked_reasons"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that release docs and runbooks are present and fresh."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--stale-after-days",
        type=int,
        default=DEFAULT_STALE_AFTER_DAYS,
        help="Fail closed when a required document is older than this many days.",
    )
    parser.add_argument(
        "--required-report",
        action="append",
        dest="required_reports",
        type=Path,
        help="Override the required report set. Repeat for multiple paths.",
    )
    parser.add_argument(
        "--required-runbook",
        action="append",
        dest="required_runbooks",
        type=Path,
        help="Override the required runbook set. Repeat for multiple paths.",
    )
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-md", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    required_reports = args.required_reports or list(DEFAULT_REQUIRED_REPORT_DOCS)
    required_runbooks = args.required_runbooks or list(DEFAULT_REQUIRED_RUNBOOK_DOCS)
    payload = build_release_docs_validation(
        repo_root=args.repo_root,
        required_report_docs=required_reports,
        required_runbook_docs=required_runbooks,
        stale_after_days=args.stale_after_days,
    )
    rendered_json = json.dumps(payload, indent=2)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered_json + "\n", encoding="utf-8")
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(rendered_json)
    raise SystemExit(0 if payload["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
