from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLOSURE_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_closure_matrix_preview.json"
)
DEFAULT_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_readiness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_candidate_promotion_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_candidate_promotion_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_candidate_promotion_preview(
    *, closure_matrix: dict[str, Any], readiness: dict[str, Any]
) -> dict[str, Any]:
    matrix_rows = closure_matrix.get("rows") or []
    closest = [row for row in matrix_rows if row.get("closure_state") == "closest_to_release"]
    closest.sort(key=lambda row: (row.get("benchmark_priority") or 999, row["accession"]))
    release_grade_status = (readiness.get("summary") or {}).get("release_grade_status")
    promotion_blocked = release_grade_status != "frozen_v1_bar_closed"

    return {
        "artifact_id": "release_candidate_promotion_preview",
        "schema_id": "proteosphere-release-candidate-promotion-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "release_grade_status": release_grade_status,
            "candidate_count": len(closest),
            "top_candidate_accessions": [row["accession"] for row in closest[:3]],
            "promotion_blocked": promotion_blocked,
        },
        "rows": closest,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "These rows are closest to release promotion inside the current closure matrix, "
                "but they should only be promoted when the frozen v1 release bar "
                "is explicitly closed."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    return "\n".join(
        [
            "# Release Candidate Promotion Preview",
            "",
            f"- Candidate count: `{summary.get('candidate_count')}`",
            f"- Promotion blocked: `{str(summary.get('promotion_blocked')).lower()}`",
            f"- Top candidates: `{', '.join(summary.get('top_candidate_accessions') or [])}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release candidate promotion preview."
    )
    parser.add_argument("--closure-matrix", type=Path, default=DEFAULT_CLOSURE_MATRIX)
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_candidate_promotion_preview(
        closure_matrix=_read_json(args.closure_matrix),
        readiness=_read_json(args.readiness),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
