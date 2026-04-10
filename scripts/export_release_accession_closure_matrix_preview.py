from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_LEDGER = (
    REPO_ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "release_corpus_evidence_ledger.json"
)
DEFAULT_TRAINING_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_PACKET_SUMMARY = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_summary_preview.json"
)
DEFAULT_PACKET_QUEUE = (
    REPO_ROOT / "artifacts" / "status" / "training_packet_materialization_queue_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "release_accession_closure_matrix_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "release_accession_closure_matrix_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_release_accession_closure_matrix_preview(
    *,
    release_ledger: dict[str, Any],
    training_readiness: dict[str, Any],
    packet_summary: dict[str, Any],
    packet_queue: dict[str, Any],
) -> dict[str, Any]:
    readiness_by_accession = {
        row["accession"]: row for row in (training_readiness.get("readiness_rows") or [])
    }
    packet_summary_by_accession = {
        row["accession"]: row for row in (packet_summary.get("rows") or [])
    }
    packet_queue_by_accession = {
        row["accession"]: row for row in (packet_queue.get("rows") or [])
    }

    rows: list[dict[str, Any]] = []
    for ledger_row in release_ledger.get("rows") or []:
        accession = (ledger_row.get("metadata") or {}).get("accession")
        if not accession:
            continue
        readiness_row = readiness_by_accession.get(accession) or {}
        packet_row = packet_summary_by_accession.get(accession) or {}
        queue_row = packet_queue_by_accession.get(accession) or {}
        blocker_ids = list(ledger_row.get("blocker_ids") or [])
        missing_modalities = list(queue_row.get("missing_modalities") or [])
        closure_state = (
            "closest_to_release"
            if readiness_row.get("training_set_state") == "governing_ready"
            else (
                "blocked_pending_acquisition"
                if readiness_row.get("training_set_state") == "blocked_pending_acquisition"
                else "preview_only_non_governing"
            )
        )
        rows.append(
            {
                "accession": accession,
                "split": readiness_row.get("split"),
                "closure_state": closure_state,
                "training_set_state": readiness_row.get("training_set_state"),
                "package_state": readiness_row.get("package_state"),
                "release_grade": ledger_row.get("grade"),
                "benchmark_priority": ledger_row.get("benchmark_priority"),
                "blocker_ids": blocker_ids,
                "blocker_count": len(blocker_ids),
                "current_blocker": readiness_row.get("current_blocker"),
                "recommended_next_step": readiness_row.get("recommended_next_step"),
                "packet_lane": packet_row.get("packet_lane") or queue_row.get("packet_lane"),
                "packet_status": packet_row.get("packet_status"),
                "missing_modalities": missing_modalities,
            }
        )

    closure_order = {
        "closest_to_release": 0,
        "preview_only_non_governing": 1,
        "blocked_pending_acquisition": 2,
    }
    rows.sort(
        key=lambda row: (
            closure_order.get(row["closure_state"], 3),
            row.get("benchmark_priority") or 999,
            row["accession"],
        )
    )

    closure_counts: dict[str, int] = {}
    for row in rows:
        closure_counts[row["closure_state"]] = closure_counts.get(row["closure_state"], 0) + 1

    return {
        "artifact_id": "release_accession_closure_matrix_preview",
        "schema_id": "proteosphere-release-accession-closure-matrix-preview-2026-04-05",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "accession_count": len(rows),
            "closure_state_counts": closure_counts,
            "closest_to_release_count": closure_counts.get("closest_to_release", 0),
            "preview_only_non_governing_count": closure_counts.get(
                "preview_only_non_governing", 0
            ),
            "blocked_pending_acquisition_count": closure_counts.get(
                "blocked_pending_acquisition", 0
            ),
        },
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "This matrix translates the release-grade ledger into accession-level closure "
                "states without promoting any accession to release-ready."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    return "\n".join(
        [
            "# Release Accession Closure Matrix Preview",
            "",
            f"- Accession count: `{summary.get('accession_count')}`",
            f"- Closest to release: `{summary.get('closest_to_release_count')}`",
            f"- Preview-only non-governing: `{summary.get('preview_only_non_governing_count')}`",
            f"- Blocked pending acquisition: `{summary.get('blocked_pending_acquisition_count')}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the release accession closure matrix preview."
    )
    parser.add_argument("--release-ledger", type=Path, default=DEFAULT_RELEASE_LEDGER)
    parser.add_argument("--training-readiness", type=Path, default=DEFAULT_TRAINING_READINESS)
    parser.add_argument("--packet-summary", type=Path, default=DEFAULT_PACKET_SUMMARY)
    parser.add_argument("--packet-queue", type=Path, default=DEFAULT_PACKET_QUEUE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_release_accession_closure_matrix_preview(
        release_ledger=_read_json(args.release_ledger),
        training_readiness=_read_json(args.training_readiness),
        packet_summary=_read_json(args.packet_summary),
        packet_queue=_read_json(args.packet_queue),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
