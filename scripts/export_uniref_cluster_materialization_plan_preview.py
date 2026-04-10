from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from web_enrichment_preview_support import (
        accession_rows,
        read_json,
        write_json,
        write_text,
    )
DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE = (
    REPO_ROOT / "artifacts" / "status" / "procurement_tail_freeze_gate_preview.json"
)
DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "uniref_cluster_materialization_plan_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "uniref_cluster_materialization_plan_preview.md"
)


def build_uniref_cluster_materialization_plan_preview(
    procurement_tail_freeze_gate: dict[str, Any],
    training_set_eligibility_matrix: dict[str, Any],
) -> dict[str, Any]:
    accessions = [row["accession"] for row in accession_rows(training_set_eligibility_matrix)]
    rows = [
        {
            "accession": accession,
            "planned_context_fields": [
                "cluster_id",
                "representative_member_accession",
                "member_count",
                "common_taxon",
                "identity_level",
                "cluster_breadth_metric",
                "representative_drift_flag",
            ],
            "planned_default_ingest_status": "support-only",
            "non_governing_for_split": True,
        }
        for accession in accessions
    ]
    return {
        "artifact_id": "uniref_cluster_materialization_plan_preview",
        "schema_id": "proteosphere-uniref-cluster-materialization-plan-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "mirror_completion_status": procurement_tail_freeze_gate.get("gate_status"),
        "supported_accession_count": len(accessions),
        "rows": rows,
        "summary": {
            "planned_family_id": "uniref_cluster_context_preview",
            "planned_guard_family_id": "sequence_redundancy_guard_preview",
            "family_origin_context_family_id": "family_origin_context_preview",
            "split_non_governing": True,
            "predicted_new_context_for_accession_count": len(accessions),
        },
        "forecast": {
            "post_tail_unlocks": [
                "cluster membership",
                "representative member lineage",
                "member count",
                "common taxon",
                "cluster breadth",
            ],
            "training_unit_collapse_disallowed": True,
        },
        "truth_boundary": {
            "summary": (
                "This is a UniRef100 cluster-context plan only. It does not materialize "
                "UniRef rows, does not alter split policy, and does not treat UniRef as "
                "complete before the procurement tail freeze gate clears."
            ),
            "report_only": True,
            "materialization_started": False,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# UniRef Cluster Materialization Plan Preview",
            "",
            f"- Status: `{payload['status']}`",
            f"- Mirror gate: `{payload['mirror_completion_status']}`",
            f"- Supported accessions: `{payload['supported_accession_count']}`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only UniRef cluster materialization plan preview."
    )
    parser.add_argument(
        "--procurement-tail-freeze-gate",
        type=Path,
        default=DEFAULT_PROCUREMENT_TAIL_FREEZE_GATE,
    )
    parser.add_argument(
        "--training-set-eligibility-matrix",
        type=Path,
        default=DEFAULT_TRAINING_SET_ELIGIBILITY_MATRIX,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_uniref_cluster_materialization_plan_preview(
        read_json(args.procurement_tail_freeze_gate),
        read_json(args.training_set_eligibility_matrix),
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
