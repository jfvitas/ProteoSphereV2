from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_COVERAGE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)
DEFAULT_GOVERNING_SUFFICIENCY = (
    REPO_ROOT / "artifacts" / "status" / "release_governing_sufficiency_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_source_coverage_depth_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_source_coverage_depth_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_source_coverage_depth_preview(
    *, source_coverage: dict[str, Any]
) -> dict[str, Any]:
    governing = _read_json(DEFAULT_GOVERNING_SUFFICIENCY)
    governing_summary = governing.get("summary") or {}
    summary = source_coverage.get("summary") or {}
    total = int(summary.get("total_accessions") or 0)
    thin = len(summary.get("thin_coverage_accessions") or [])
    direct = len(summary.get("direct_live_smoke_accessions") or [])
    probe = len(summary.get("probe_backed_accessions") or [])
    snapshot = len(summary.get("snapshot_backed_accessions") or [])
    verified = len(summary.get("verified_accession_accessions") or [])
    thin_fraction = (thin / total) if total else 0.0

    return {
        "artifact_id": "release_source_coverage_depth_preview",
        "schema_id": "proteosphere-release-source-coverage-depth-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_accessions": total,
            "thin_coverage_count": thin,
            "thin_coverage_fraction": round(thin_fraction, 4),
            "direct_live_smoke_count": direct,
            "probe_backed_count": probe,
            "snapshot_backed_count": snapshot,
            "verified_accession_count": verified,
            "coverage_depth_state": (
                "frozen_v1_governing_sufficient"
                if governing_summary.get("governing_sufficiency_complete")
                else ("thin_lane_heavy" if thin_fraction >= 0.5 else "moderate_depth")
            ),
            "next_action": (
                "deferred_to_v2_expansion_wave"
                if governing_summary.get("governing_sufficiency_complete")
                else "widen release-grade source coverage and close remaining thin lanes"
            ),
            "governing_sufficiency_complete": governing_summary.get("governing_sufficiency_complete", False),
        },
        "evidence": {
            "source_coverage_path": str(DEFAULT_SOURCE_COVERAGE).replace("\\", "/"),
            "validation_class_counts": summary.get("validation_class_counts"),
            "lane_depth_counts": summary.get("lane_depth_counts"),
        },
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This preview summarizes the frozen cohort's source-depth profile without "
                "claiming release-grade corpus coverage."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    return "\n".join(
        [
            "# Release Source Coverage Depth Preview",
            "",
            f"- Total accessions: `{summary.get('total_accessions')}`",
            f"- Thin coverage count: `{summary.get('thin_coverage_count')}`",
            f"- Direct live-smoke count: `{summary.get('direct_live_smoke_count')}`",
            f"- Snapshot-backed count: `{summary.get('snapshot_backed_count')}`",
            f"- Coverage depth state: `{summary.get('coverage_depth_state')}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release source coverage depth preview."
    )
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE)
    parser.add_argument("--governing-sufficiency", type=Path, default=DEFAULT_GOVERNING_SUFFICIENCY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_source_coverage_depth_preview(
        source_coverage=_read_json(args.source_coverage)
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
