from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "cohort_manifest.json"
)
DEFAULT_SPLIT_LABELS = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
)
DEFAULT_BENCHMARK_MANIFEST = REPO_ROOT / "runs" / "real_data_benchmark" / "manifest.json"
DEFAULT_RUN_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_manifest.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "leakage_audit.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _as_abs(path: Path) -> str:
    return str(path.resolve())


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(values))


def build_leakage_audit(
    cohort_manifest: dict[str, Any],
    split_labels: dict[str, Any],
    *,
    cohort_manifest_path: Path,
    split_labels_path: Path,
    benchmark_manifest_path: Path | None = None,
    run_manifest_path: Path | None = None,
) -> dict[str, Any]:
    split_label_rows = list(split_labels.get("labels", []))
    split_label_index: dict[str, list[str]] = defaultdict(list)
    split_label_counts: dict[str, int] = defaultdict(int)
    split_label_splits: dict[str, set[str]] = defaultdict(set)
    split_label_leakage_keys: dict[str, set[str]] = defaultdict(set)
    for item in split_label_rows:
        accession = str(item.get("accession", "")).strip()
        split = str(item.get("split", "")).strip()
        leakage_key = str(item.get("leakage_key", "")).strip()
        if accession:
            split_label_index[accession].append(split)
            split_label_counts[accession] += 1
            if split:
                split_label_splits[accession].add(split)
            if leakage_key:
                split_label_leakage_keys[accession].add(leakage_key)

    leakage_key_splits: dict[str, set[str]] = defaultdict(set)
    accession_splits: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    missing_split_labels: list[str] = []
    missing_leakage_keys: list[str] = []
    split_label_blockers: list[str] = []

    cohort_accessions = {
        str(row.get("accession", "")).strip()
        for row in cohort_manifest.get("cohort", [])
        if str(row.get("accession", "")).strip()
    }

    duplicate_split_label_accessions = _sorted_unique(
        accession
        for accession, count in split_label_counts.items()
        if count > 1
    )
    conflicting_split_label_accessions = _sorted_unique(
        accession
        for accession, splits in split_label_splits.items()
        if len(splits) > 1
    )
    out_of_cohort_split_label_accessions = _sorted_unique(
        accession for accession in split_label_counts if accession not in cohort_accessions
    )
    missing_cohort_split_label_accessions = _sorted_unique(
        accession for accession in cohort_accessions if accession not in split_label_counts
    )
    split_label_cross_split_keys = _sorted_unique(
        accession
        for accession, leakage_keys in split_label_leakage_keys.items()
        if len(leakage_keys) > 1
    )

    for accession in duplicate_split_label_accessions:
        split_label_blockers.append(
            f"duplicate split label rows for accession {accession}"
        )
    for accession in conflicting_split_label_accessions:
        split_label_blockers.append(
            f"conflicting split labels for accession {accession}"
        )
    for accession in out_of_cohort_split_label_accessions:
        split_label_blockers.append(
            f"split label accession {accession} is outside the frozen cohort"
        )
    for accession in missing_cohort_split_label_accessions:
        split_label_blockers.append(
            f"missing split label for frozen cohort accession {accession}"
        )
    for accession in split_label_cross_split_keys:
        split_label_blockers.append(
            f"split label leakage key changes across rows for accession {accession}"
        )

    for row in cohort_manifest.get("cohort", []):
        accession = str(row.get("accession", "")).strip()
        split_rows = split_label_index.get(accession, [])
        unique_splits = _sorted_unique(split_rows)
        split = unique_splits[0] if len(unique_splits) == 1 else ""
        leakage_key = str(row.get("leakage_key", "")).strip()
        split_label_issue: list[str] = []

        if not accession:
            blockers.append("cohort row is missing an accession")
            continue
        if not split_rows:
            missing_split_labels.append(accession)
            split_label_issue.append("missing split label")
        if len(split_rows) > 1:
            split_label_issue.append("duplicate split label rows")
        if len(unique_splits) > 1:
            split_label_issue.append("conflicting split labels")
        if not leakage_key:
            missing_leakage_keys.append(accession)
            split_label_issue.append("missing leakage key")

        accession_splits[accession].add(split)
        if leakage_key:
            leakage_key_splits[leakage_key].add(split)

        rows.append(
            {
                "accession": accession,
                "split": split,
                "leakage_key": leakage_key,
                "bucket": row.get("bucket"),
                "evidence_mode": row.get("evidence_mode"),
                "status": row.get("status"),
                "split_label_count": len(split_rows),
                "split_label_splits": unique_splits,
                "split_label_issues": split_label_issue,
                "cross_split": False,
            }
        )

    cross_split_accessions = _sorted_unique(
        accession
        for accession, splits in accession_splits.items()
        if len({split for split in splits if split}) > 1
    )
    cross_split_leakage_keys = _sorted_unique(
        leakage_key
        for leakage_key, splits in leakage_key_splits.items()
        if len({split for split in splits if split}) > 1
    )

    for row in rows:
        row["cross_split"] = (
            row["accession"] in cross_split_accessions
            or row["leakage_key"] in cross_split_leakage_keys
        )

    split_index: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row["split"]:
            split_index[row["split"]].append(row["accession"])

    leakage_key_index = {
        leakage_key: sorted({split for split in splits if split})
        for leakage_key, splits in sorted(leakage_key_splits.items())
    }

    accession_level_only = bool(
        cohort_manifest.get("split_leakage_metadata", {}).get(
            "accession_level_only", False
        )
    )
    leakage_free = (
        not cross_split_accessions
        and not cross_split_leakage_keys
        and not missing_split_labels
        and not missing_leakage_keys
        and not split_label_blockers
        and accession_level_only
    )

    benchmark_bundle = {
        "manifest_id": cohort_manifest.get("manifest_id"),
        "task_id": cohort_manifest.get("task_id"),
        "status": cohort_manifest.get("status"),
        "target_size": cohort_manifest.get("target_size"),
        "resolved_count": cohort_manifest.get("resolved_count"),
        "unresolved_count": cohort_manifest.get("unresolved_count"),
        "split_policy": cohort_manifest.get("split_policy"),
        "split_counts": cohort_manifest.get("split_counts", {}),
        "cohort_shape": cohort_manifest.get("cohort_shape", {}),
        "selection_rule": cohort_manifest.get("selection_rule"),
    }

    execution_context: dict[str, Any] = {
        "benchmark_manifest_path": (
            _as_abs(benchmark_manifest_path) if benchmark_manifest_path else None
        ),
        "cohort_manifest_path": _as_abs(cohort_manifest_path),
        "split_labels_path": _as_abs(split_labels_path),
    }
    if benchmark_manifest_path and benchmark_manifest_path.exists():
        execution_context["benchmark_manifest"] = _read_json(benchmark_manifest_path)
    if run_manifest_path and run_manifest_path.exists():
        execution_context["run_manifest_path"] = _as_abs(run_manifest_path)
        execution_context["run_manifest"] = _read_json(run_manifest_path)

    blockers.extend(
        f"missing split label for accession {accession}"
        for accession in missing_split_labels
    )
    blockers.extend(
        f"missing leakage key for accession {accession}"
        for accession in missing_leakage_keys
    )

    return {
        "task_id": "P6-T018",
        "audited_at": datetime.now(tz=UTC).isoformat(),
        "source_files": {
            "cohort_manifest": _as_abs(cohort_manifest_path),
            "split_labels": _as_abs(split_labels_path),
        },
        "bundle": benchmark_bundle,
        "execution_context": execution_context,
        "audit": {
            "accession_level_only": accession_level_only,
            "total_rows": len(rows),
            "unique_accessions": len(accession_splits),
            "unique_leakage_keys": len(leakage_key_splits),
            "split_index": {
                split: sorted(accessions)
                for split, accessions in sorted(split_index.items())
            },
            "leakage_key_index": leakage_key_index,
            "rows": rows,
            "cross_split_accessions": cross_split_accessions,
            "cross_split_leakage_keys": cross_split_leakage_keys,
        },
        "conclusion": {
            "leakage_free": leakage_free,
            "accession_cross_split": bool(cross_split_accessions),
            "leakage_key_cross_split": bool(cross_split_leakage_keys),
            "blockers": blockers + split_label_blockers,
            "notes": [
                (
                    "No accession appears in more than one split."
                    if not cross_split_accessions
                    else "At least one accession crosses splits."
                ),
                (
                    "No leakage key appears in more than one split."
                    if not cross_split_leakage_keys
                    else "At least one leakage key crosses splits."
                ),
            ],
        },
        "split_label_audit": {
            "total_rows": len(split_label_rows),
            "unique_accessions": len(split_label_counts),
            "duplicate_accession_rows": duplicate_split_label_accessions,
            "conflicting_split_accessions": conflicting_split_label_accessions,
            "out_of_cohort_accessions": out_of_cohort_split_label_accessions,
            "missing_cohort_accessions": missing_cohort_split_label_accessions,
            "cross_split_leakage_keys": split_label_cross_split_keys,
            "index": {
                accession: split_label_index[accession]
                for accession in sorted(split_label_index)
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit the frozen cohort split leakage audit.")
    parser.add_argument("--cohort-manifest", type=Path, default=DEFAULT_COHORT_MANIFEST)
    parser.add_argument("--split-labels", type=Path, default=DEFAULT_SPLIT_LABELS)
    parser.add_argument("--benchmark-manifest", type=Path, default=DEFAULT_BENCHMARK_MANIFEST)
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    cohort_manifest = _read_json(args.cohort_manifest)
    split_labels = _read_json(args.split_labels)
    audit = build_leakage_audit(
        cohort_manifest,
        split_labels,
        cohort_manifest_path=args.cohort_manifest,
        split_labels_path=args.split_labels,
        benchmark_manifest_path=args.benchmark_manifest,
        run_manifest_path=args.run_manifest,
    )
    _write_json(args.output, audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
