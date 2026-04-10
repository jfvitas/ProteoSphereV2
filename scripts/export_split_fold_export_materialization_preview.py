from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLIT_LABELS = REPO_ROOT / "runs" / "real_data_benchmark" / "cohort" / "split_labels.json"
DEFAULT_ASSIGNMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_assignment_preview.json"
)
DEFAULT_DRY_RUN_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "split_engine_dry_run_validation.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "split_fold_export_materialization_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "split_fold_export_materialization_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_split_fold_export_materialization_preview(
    split_labels: dict[str, Any],
    assignment_preview: dict[str, Any],
    dry_run_validation: dict[str, Any],
) -> dict[str, Any]:
    labels = [
        row for row in split_labels.get("labels") or [] if isinstance(row, dict)
    ]
    group_rows = [
        row for row in assignment_preview.get("group_rows") or [] if isinstance(row, dict)
    ]
    validation = dry_run_validation.get("validation") or {}
    split_index = split_labels.get("split_index") or {}
    split_counts = (split_labels.get("counts") or {}).copy()
    status = "complete" if dry_run_validation.get("status") == "aligned" else "blocked_pending_alignment"

    folds = []
    for split_name in ("train", "val", "test"):
        accession_labels = [
            row for row in labels if str(row.get("split") or "").strip() == split_name
        ]
        linked_groups = [
            {
                "linked_group_id": row.get("linked_group_id"),
                "representative_accession": row.get("representative_accession"),
                "entity_count": row.get("entity_count"),
            }
            for row in group_rows
            if str(row.get("split_name") or "").strip() == split_name
        ]
        folds.append(
            {
                "fold_name": split_name,
                "accessions": [row.get("accession") for row in accession_labels],
                "bucket_counts": {
                    bucket: sum(
                        1
                        for row in accession_labels
                        if str(row.get("bucket") or "").strip() == bucket
                    )
                    for bucket in sorted(
                        {
                            str(row.get("bucket") or "").strip()
                            for row in accession_labels
                            if str(row.get("bucket") or "").strip()
                        }
                    )
                },
                "linked_groups": linked_groups,
                "entity_row_count": sum(int(row.get("entity_count") or 0) for row in linked_groups),
            }
        )

    return {
        "artifact_id": "split_fold_export_materialization_preview",
        "schema_id": "proteosphere-split-fold-export-materialization-preview-2026-04-05",
        "status": status,
        "summary": {
            "split_policy": split_labels.get("split_policy"),
            "accession_counts": {
                "train": split_counts.get("train"),
                "val": split_counts.get("val"),
                "test": split_counts.get("test"),
            },
            "linked_group_count": len(group_rows),
            "assignment_count": (assignment_preview.get("summary") or {}).get("assignment_count"),
            "candidate_row_count": (assignment_preview.get("summary") or {}).get("candidate_row_count"),
            "row_level_split_counts": validation.get("row_level_split_counts")
            or (assignment_preview.get("summary") or {}).get("row_level_split_counts"),
            "split_group_counts": validation.get("split_group_counts")
            or (assignment_preview.get("summary") or {}).get("split_group_counts"),
            "dry_run_validation_status": dry_run_validation.get("status"),
        },
        "folds": folds,
        "truth_boundary": {
            "summary": (
                "This is a run-scoped fold export materialization derived from the aligned dry-run "
                "assignment. It does not commit a release split or rewrite protected latest surfaces."
            ),
            "run_scoped_only": True,
            "cv_folds_materialized": status == "complete",
            "final_split_committed": False,
            "release_split_promoted": False,
        },
        "source_artifacts": {
            "split_labels": str(DEFAULT_SPLIT_LABELS).replace("\\", "/"),
            "assignment_preview": str(DEFAULT_ASSIGNMENT_PREVIEW).replace("\\", "/"),
            "dry_run_validation": str(DEFAULT_DRY_RUN_VALIDATION).replace("\\", "/"),
            "split_index": split_index,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Split Fold Export Materialization Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Dry-run validation status: `{summary.get('dry_run_validation_status')}`",
        f"- Linked groups: `{summary.get('linked_group_count')}`",
        f"- Assignment count: `{summary.get('assignment_count')}`",
        f"- Candidate row count: `{summary.get('candidate_row_count')}`",
        f"- Accession counts: `{json.dumps(summary.get('accession_counts'), sort_keys=True)}`",
        "",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the run-scoped split fold materialization preview."
    )
    parser.add_argument("--split-labels", type=Path, default=DEFAULT_SPLIT_LABELS)
    parser.add_argument("--assignment-preview", type=Path, default=DEFAULT_ASSIGNMENT_PREVIEW)
    parser.add_argument("--dry-run-validation", type=Path, default=DEFAULT_DRY_RUN_VALIDATION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_split_fold_export_materialization_preview(
        _read_json(args.split_labels),
        _read_json(args.assignment_preview),
        _read_json(args.dry_run_validation),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
