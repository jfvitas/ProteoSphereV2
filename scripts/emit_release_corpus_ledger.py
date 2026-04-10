from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.release.cohort_registry import ReleaseCohortRegistry  # noqa: E402
from evaluation.release_corpus_completeness import (  # noqa: E402
    score_release_cohort_registry,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "artifacts" / "status" / "release_cohort_registry.json"
DEFAULT_OUTPUT_PATH = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_corpus_evidence_ledger.json"
)


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_release_corpus_ledger(
    registry: ReleaseCohortRegistry | dict[str, Any],
) -> dict[str, Any]:
    normalized_registry = (
        registry
        if isinstance(registry, ReleaseCohortRegistry)
        else ReleaseCohortRegistry.from_dict(registry)
    )
    report = score_release_cohort_registry(normalized_registry)
    score_by_id = {score.canonical_id: score for score in report.scores}

    rows: list[dict[str, Any]] = []
    for entry in normalized_registry.entries:
        score = score_by_id[entry.canonical_id]
        rows.append(
            {
                "canonical_id": entry.canonical_id,
                "record_type": entry.record_type,
                "inclusion_status": entry.inclusion_status,
                "freeze_state": entry.freeze_state,
                "inclusion_reason": entry.inclusion_reason,
                "exclusion_reason": entry.exclusion_reason,
                "blocker_ids": list(entry.blocker_ids),
                "evidence_lanes": list(entry.evidence_lanes),
                "source_manifest_ids": list(entry.source_manifest_ids),
                "packet_ready": entry.packet_ready,
                "benchmark_priority": entry.benchmark_priority,
                "leakage_key": entry.leakage_key,
                "tags": list(entry.tags),
                "metadata": dict(entry.metadata),
                "grade": score.grade,
                "score": score.score,
                "release_ready": score.release_ready,
                "rationale": list(score.rationale),
            }
        )

    return {
        "registry_id": normalized_registry.registry_id,
        "release_version": normalized_registry.release_version,
        "generated_at": _utc_now(),
        "freeze_state": normalized_registry.freeze_state,
        "notes": list(normalized_registry.notes),
        "summary": {
            "entry_count": len(normalized_registry.entries),
            "included_count": len(normalized_registry.included_entries),
            "excluded_count": len(normalized_registry.excluded_entries),
            "pending_count": len(normalized_registry.pending_entries),
            "blocked_count": len(normalized_registry.blocked_entries),
            "release_ready_count": len(normalized_registry.release_ready_entries),
            "grade_counts": dict(report.grade_counts),
        },
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a machine-readable release corpus evidence ledger "
            "from a release cohort registry."
        )
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to the release cohort registry JSON artifact.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Target JSON path for the emitted evidence ledger.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry_payload = _read_json(args.registry)
    ledger = build_release_corpus_ledger(registry_payload)
    _write_json(args.output, ledger)
    print(json.dumps(ledger, indent=2))


if __name__ == "__main__":
    main()
