from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from training_set_builder_preview_support import (  # noqa: E402
    read_json,
    write_json,
    write_text,
)

DEFAULT_TRAINING_SET_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "training_set_readiness_preview.json"
)
DEFAULT_COHORT_COMPILER = REPO_ROOT / "artifacts" / "status" / "cohort_compiler_preview.json"
DEFAULT_PACKAGE_READINESS = REPO_ROOT / "artifacts" / "status" / "package_readiness_preview.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "training_set_candidate_package_manifest_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_candidate_package_manifest_preview.md"
)


def _index_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def _derive_package_role(row: dict[str, Any]) -> str:
    training_state = str(row.get("training_set_state") or "").strip()
    ligand_ladder = str(row.get("ligand_readiness_ladder") or "").strip()
    if training_state == "governing_ready":
        return "governing_preview_row"
    if training_state == "blocked_pending_acquisition":
        return "blocked_pending_acquisition"
    if ligand_ladder == "candidate-only non-governing":
        return "candidate_only_non_governing"
    if ligand_ladder == "support-only":
        return "support_only_non_governing"
    if ligand_ladder == "grounded preview-safe":
        return "grounded_preview_safe_non_governing"
    return "preview_visible_non_governing"


def build_training_set_candidate_package_manifest_preview(
    training_set_readiness: dict[str, Any],
    cohort_compiler: dict[str, Any],
    package_readiness: dict[str, Any],
) -> dict[str, Any]:
    readiness_rows = _index_by_accession(
        [row for row in training_set_readiness.get("readiness_rows") or [] if isinstance(row, dict)]
    )
    cohort_rows = [row for row in cohort_compiler.get("rows") or [] if isinstance(row, dict)]
    package_summary = package_readiness.get("summary") or {}
    rows: list[dict[str, Any]] = []

    for row in cohort_rows:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        readiness_row = readiness_rows.get(accession, {})
        merged = {
            "accession": accession,
            "split": row.get("split"),
            "bucket": row.get("bucket"),
            "packet_status": readiness_row.get("packet_status") or row.get("packet_status"),
            "training_set_state": readiness_row.get("training_set_state")
            or row.get("training_set_state"),
            "ligand_readiness_ladder": row.get("ligand_readiness_ladder"),
            "package_role": _derive_package_role(
                {
                    "training_set_state": readiness_row.get("training_set_state")
                    or row.get("training_set_state"),
                    "ligand_readiness_ladder": row.get("ligand_readiness_ladder"),
                }
            ),
            "recommended_next_step": readiness_row.get("recommended_next_step")
            or row.get("recommended_next_step"),
            "source_lanes": list(row.get("source_lanes") or []),
        }
        rows.append(merged)

    split_counts = Counter(str(row.get("split") or "unknown") for row in rows)
    package_role_counts = Counter(str(row.get("package_role") or "unknown") for row in rows)
    readiness_state_counts = Counter(
        str(row.get("training_set_state") or "unknown") for row in rows
    )
    ladder_counts = Counter(str(row.get("ligand_readiness_ladder") or "unknown") for row in rows)

    ready_for_package = bool(package_summary.get("ready_for_package"))
    blocked_reasons = list(package_summary.get("blocked_reasons") or [])

    payload = {
        "artifact_id": "training_set_candidate_package_manifest_preview",
        "schema_id": "proteosphere-training-set-candidate-package-manifest-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_status": (
            "candidate_package_ready_for_operator_review"
            if ready_for_package
            else "candidate_package_blocked_pending_readiness"
        ),
        "package_identity": {
            "package_kind": "training_set_candidate_package",
            "cohort_source": "cohort_compiler_preview",
            "readiness_source": "training_set_readiness_preview",
            "package_readiness_source": "package_readiness_preview",
            "package_ready": ready_for_package,
            "package_authorization_required": True,
        },
        "source_artifacts": {
            "training_set_readiness": str(DEFAULT_TRAINING_SET_READINESS).replace("\\", "/"),
            "cohort_compiler": str(DEFAULT_COHORT_COMPILER).replace("\\", "/"),
            "package_readiness": str(DEFAULT_PACKAGE_READINESS).replace("\\", "/"),
        },
        "summary": {
            "selected_count": len(rows),
            "selected_accessions": [row["accession"] for row in rows],
            "split_counts": dict(sorted(split_counts.items())),
            "training_set_state_counts": dict(sorted(readiness_state_counts.items())),
            "ligand_readiness_ladder_counts": dict(sorted(ladder_counts.items())),
            "package_role_counts": dict(sorted(package_role_counts.items())),
            "governing_preview_row_count": package_role_counts.get("governing_preview_row", 0),
            "candidate_only_non_governing_count": package_role_counts.get(
                "candidate_only_non_governing",
                0,
            ),
            "support_only_non_governing_count": package_role_counts.get(
                "support_only_non_governing",
                0,
            ),
            "blocked_pending_acquisition_count": package_role_counts.get(
                "blocked_pending_acquisition",
                0,
            ),
            "package_ready": ready_for_package,
            "blocked_reasons": blocked_reasons,
            "cohort_selected_count": int(cohort_compiler.get("row_count") or len(rows)),
            "training_set_readiness_count": int(
                training_set_readiness.get("summary", {}).get("selected_count") or len(rows)
            ),
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This manifest is report-only. It mirrors the current cohort and "
                "readiness surfaces, but it does not authorize packaging, mutate "
                "selection, or promote non-governing accessions into a bundle."
            ),
            "report_only": True,
            "non_mutating": True,
            "package_not_authorized": True,
            "candidate_only_rows_non_governing": True,
            "support_only_rows_non_governing": True,
            "grounded_preview_safe_rows_non_governing": True,
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Training Set Candidate Package Manifest Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Manifest status: `{payload.get('manifest_status')}`",
        f"- Selected count: `{summary.get('selected_count')}`",
        f"- Package ready: `{summary.get('package_ready')}`",
        f"- Blocked reasons: `{json.dumps(summary.get('blocked_reasons', []), sort_keys=True)}`",
        "",
        "## Selected Rows",
        "",
        "| Accession | Split | Package role | Training state | Ligand ladder |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            "| "
            + f"`{row['accession']}` | "
            + f"{row.get('split')} | "
            + f"{row.get('package_role')} | "
            + f"{row.get('training_set_state')} | "
            + f"{row.get('ligand_readiness_ladder')} |"
        )
    truth_boundary = payload.get("truth_boundary") or {}
    if truth_boundary.get("summary"):
        lines.extend(["", "## Truth Boundary", "", f"- {truth_boundary['summary']}"])
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only training set candidate package manifest preview."
    )
    parser.add_argument(
        "--training-set-readiness", type=Path, default=DEFAULT_TRAINING_SET_READINESS
    )
    parser.add_argument("--cohort-compiler", type=Path, default=DEFAULT_COHORT_COMPILER)
    parser.add_argument("--package-readiness", type=Path, default=DEFAULT_PACKAGE_READINESS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def _read_or_default(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {}


def main() -> None:
    args = parse_args()
    payload = build_training_set_candidate_package_manifest_preview(
        _read_or_default(args.training_set_readiness),
        _read_or_default(args.cohort_compiler),
        _read_or_default(args.package_readiness),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
