from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = (
    REPO_ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "release_corpus_evidence_ledger.json"
)
DEFAULT_PROVENANCE = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "provenance_table.json"
)
DEFAULT_RELEASE_CARDS = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_cards_manifest.json"
)
DEFAULT_REPORTING_COMPLETENESS = (
    REPO_ROOT / "artifacts" / "status" / "release_reporting_completeness_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_provenance_depth_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_provenance_depth_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_provenance_depth_preview(
    *, ledger: dict[str, Any], provenance: dict[str, Any], release_cards: dict[str, Any]
) -> dict[str, Any]:
    reporting = _read_json(DEFAULT_REPORTING_COMPLETENESS)
    reporting_summary = reporting.get("summary") or {}
    ledger_summary = ledger.get("summary") or {}
    provenance_rows = (provenance.get("cohort_summary") or {}).get("rows") or []
    card_outputs = release_cards.get("card_outputs") or {}
    blocked = int(ledger_summary.get("blocked_count") or 0)
    entries = int(ledger_summary.get("entry_count") or 0)
    blocked_fraction = (blocked / entries) if entries else 0.0

    return {
        "artifact_id": "release_provenance_depth_preview",
        "schema_id": "proteosphere-release-provenance-depth-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "ledger_entry_count": entries,
            "ledger_blocked_count": blocked,
            "ledger_blocked_fraction": round(blocked_fraction, 4),
            "provenance_row_count": len(provenance_rows),
            "release_card_count": len(card_outputs),
            "provenance_depth_state": (
                "row_complete_evidence_pack_ready"
                if reporting_summary.get("reporting_completeness_complete")
                else ("ledger_present_but_blocked" if blocked > 0 else "ledger_release_ready")
            ),
            "next_action": (
                "deferred_to_v2_expansion_wave"
                if reporting_summary.get("reporting_completeness_complete")
                else "complete corpus-scale provenance and release evidence reporting"
            ),
            "reporting_completeness_complete": reporting_summary.get(
                "reporting_completeness_complete", False
            ),
        },
        "evidence": {
            "release_ledger_path": str(DEFAULT_LEDGER).replace("\\", "/"),
            "provenance_table_path": str(DEFAULT_PROVENANCE).replace("\\", "/"),
            "release_cards_manifest_path": str(DEFAULT_RELEASE_CARDS).replace("\\", "/"),
        },
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This preview summarizes corpus-wide provenance and reporting coverage "
                "without asserting that the release evidence bar has been cleared."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    return "\n".join(
        [
            "# Release Provenance Depth Preview",
            "",
            f"- Ledger entries: `{summary.get('ledger_entry_count')}`",
            f"- Ledger blocked count: `{summary.get('ledger_blocked_count')}`",
            f"- Provenance rows: `{summary.get('provenance_row_count')}`",
            f"- Release cards: `{summary.get('release_card_count')}`",
            f"- Provenance depth state: `{summary.get('provenance_depth_state')}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release provenance depth preview."
    )
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--release-cards", type=Path, default=DEFAULT_RELEASE_CARDS)
    parser.add_argument(
        "--reporting-completeness", type=Path, default=DEFAULT_REPORTING_COMPLETENESS
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_provenance_depth_preview(
        ledger=_read_json(args.ledger),
        provenance=_read_json(args.provenance),
        release_cards=_read_json(args.release_cards),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
