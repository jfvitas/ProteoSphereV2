from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "summary.json"
DEFAULT_RUN_SUMMARY = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
)
DEFAULT_SOURCE_COVERAGE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
)
DEFAULT_PROVENANCE_TABLE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "provenance_table.json"
)
DEFAULT_RELEASE_LEDGER = (
    REPO_ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "release_corpus_evidence_ledger.json"
)
DEFAULT_RELEASE_CARDS_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_cards_manifest.json"
)
DEFAULT_FINAL_DATASET_BUNDLE = (
    REPO_ROOT / "artifacts" / "status" / "final_structured_dataset_bundle_preview.json"
)
DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD = (
    REPO_ROOT / "artifacts" / "status" / "release_blocker_resolution_board_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_grade_readiness_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_grade_readiness_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    blocker_rows = payload.get("blocker_rows") or []
    lines = [
        "# Release Grade Readiness Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Release-grade status: `{summary.get('release_grade_status')}`",
        f"- Final dataset bundle present: `{summary.get('final_dataset_bundle_present')}`",
        f"- Corpus rows: `{summary.get('corpus_row_count')}`",
        f"- Strict governing rows: `{summary.get('strict_governing_training_view_count')}`",
        f"- Blocker count: `{summary.get('blocker_count')}`",
        "",
        "## Ranked Blockers",
        "",
    ]
    for row in blocker_rows:
        lines.append(
            f"- `{row['rank']}` `{row['blocker']}`: {row['current_state']} "
            f"(next action: `{row['next_action']}`)"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            "- Report only: `true`",
            "- Release authority: `false`",
            "- Dataset creation complete for current procured scope: "
            f"`{str(summary.get('dataset_creation_complete_for_current_scope')).lower()}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_release_grade_readiness_preview(
    *,
    summary: dict[str, Any],
    run_summary: dict[str, Any],
    source_coverage: dict[str, Any],
    provenance_table: dict[str, Any],
    release_ledger: dict[str, Any],
    release_cards_manifest: dict[str, Any],
    final_dataset_bundle: dict[str, Any],
) -> dict[str, Any]:
    blocker_board = _read_json(DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD)
    board_summary = blocker_board.get("summary") or {}
    blocker_categories = list(summary.get("blocker_categories") or [])
    coverage_summary = source_coverage.get("summary") or {}
    ledger_summary = release_ledger.get("summary") or {}
    provenance_summary = (provenance_table.get("cohort_summary") or {}).get("rows") or []
    final_dataset_summary = final_dataset_bundle.get("summary") or {}
    card_outputs = release_cards_manifest.get("card_outputs") or {}

    blocker_details = {
        "runtime maturity": {
            "current_state": str(summary.get("execution_scope", {}).get("runtime_surface") or ""),
            "next_action": "promote benchmark runtime from prototype-only evidence",
        },
        "source coverage depth": {
            "current_state": (
                "validation_classes="
                + json.dumps(coverage_summary.get("validation_class_counts") or {}, sort_keys=True)
            ),
            "next_action": "widen release-grade source coverage and close remaining thin lanes",
        },
        "provenance/reporting depth": {
            "current_state": (
                f"ledger_blocked={ledger_summary.get('blocked_count')}, "
                f"cards_published={len(card_outputs)}"
            ),
            "next_action": "complete corpus-scale provenance and release evidence reporting",
        },
    }

    blocker_rows = []
    if board_summary.get("release_v1_bar_state") != "closed":
        blocker_rows = [
            {
                "rank": index + 1,
                "blocker": blocker,
                "current_state": blocker_details.get(blocker, {}).get("current_state", "unknown"),
                "next_action": blocker_details.get(blocker, {}).get("next_action", "investigate"),
            }
            for index, blocker in enumerate(blocker_categories)
        ]

    release_grade_status = (
        "frozen_v1_bar_closed"
        if board_summary.get("release_v1_bar_state") == "closed"
        else summary.get("status")
    )

    return {
        "artifact_id": "release_grade_readiness_preview",
        "schema_id": "proteosphere-release-grade-readiness-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "release_grade_status": release_grade_status,
            "blocker_count": len(blocker_rows),
            "blocker_categories": [row["blocker"] for row in blocker_rows],
            "dataset_creation_complete_for_current_scope": True,
            "final_dataset_bundle_present": final_dataset_bundle.get("status") == "completed",
            "corpus_row_count": final_dataset_summary.get("corpus_row_count"),
            "strict_governing_training_view_count": final_dataset_summary.get(
                "strict_governing_training_view_count"
            ),
            "visible_training_candidate_count": final_dataset_summary.get(
                "all_visible_training_candidates_view_count"
            ),
            "release_ledger_blocked_count": ledger_summary.get("blocked_count"),
            "provenance_row_count": len(provenance_summary),
            "release_card_count": len(card_outputs),
            "runtime_surface": summary.get("execution_scope", {}).get("runtime_surface"),
            "ready_for_next_wave": summary.get("ready_for_next_wave"),
            "dataset_generation_mode": summary.get(
                "dataset_generation_mode",
                "v1_frozen_release_candidate",
            ),
            "release_v1_bar_state": board_summary.get("release_v1_bar_state"),
            "deferred_to_v2_count": board_summary.get("deferred_to_v2_count"),
        },
        "blocker_rows": blocker_rows,
        "evidence_paths": {
            "summary": str(DEFAULT_SUMMARY).replace("\\", "/"),
            "run_summary": str(DEFAULT_RUN_SUMMARY).replace("\\", "/"),
            "source_coverage": str(DEFAULT_SOURCE_COVERAGE).replace("\\", "/"),
            "provenance_table": str(DEFAULT_PROVENANCE_TABLE).replace("\\", "/"),
            "release_corpus_evidence_ledger": str(DEFAULT_RELEASE_LEDGER).replace("\\", "/"),
            "release_cards_manifest": str(DEFAULT_RELEASE_CARDS_MANIFEST).replace("\\", "/"),
            "final_structured_dataset_bundle_preview": str(DEFAULT_FINAL_DATASET_BUNDLE).replace(
                "\\", "/"
            ),
            "release_blocker_resolution_board_preview": str(
                DEFAULT_RELEASE_BLOCKER_RESOLUTION_BOARD
            ).replace("\\", "/"),
        },
        "truth_boundary": {
            "summary": (
                "This preview separates completed structured-dataset creation from the "
                "remaining release-grade evidence bar. It is report-only and does not "
                "authorize a release claim."
            ),
            "report_only": True,
            "release_authority": False,
            "dataset_creation_complete_for_current_scope": True,
            "no_release_claim": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the release-grade readiness preview.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--run-summary", type=Path, default=DEFAULT_RUN_SUMMARY)
    parser.add_argument("--source-coverage", type=Path, default=DEFAULT_SOURCE_COVERAGE)
    parser.add_argument("--provenance-table", type=Path, default=DEFAULT_PROVENANCE_TABLE)
    parser.add_argument("--release-ledger", type=Path, default=DEFAULT_RELEASE_LEDGER)
    parser.add_argument(
        "--release-cards-manifest", type=Path, default=DEFAULT_RELEASE_CARDS_MANIFEST
    )
    parser.add_argument("--final-dataset-bundle", type=Path, default=DEFAULT_FINAL_DATASET_BUNDLE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_grade_readiness_preview(
        summary=_read_json(args.summary),
        run_summary=_read_json(args.run_summary),
        source_coverage=_read_json(args.source_coverage),
        provenance_table=_read_json(args.provenance_table),
        release_ledger=_read_json(args.release_ledger),
        release_cards_manifest=_read_json(args.release_cards_manifest),
        final_dataset_bundle=_read_json(args.final_dataset_bundle),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
