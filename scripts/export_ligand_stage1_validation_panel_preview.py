from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_P00387_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_validation_preview.json"
)
DEFAULT_Q9NZD4_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_stage1_validation_panel_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_stage1_validation_panel_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_ligand_stage1_validation_panel_preview(
    p00387_validation: dict[str, Any],
    q9nzd4_validation: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "rank": 1,
            "accession": "P00387",
            "lane_kind": "bulk_assay_anchor",
            "status": p00387_validation["status"],
            "evidence_kind": "local_chembl_bulk_assay_summary",
            "target_or_structure": p00387_validation["target_chembl_id"],
            "next_truthful_stage": "ingest_local_bulk_assay",
            "candidate_only": False,
        },
        {
            "rank": 2,
            "accession": "Q9NZD4",
            "lane_kind": "bridge_rescue_anchor",
            "status": q9nzd4_validation["status"],
            "evidence_kind": "local_structure_bridge_summary",
            "target_or_structure": q9nzd4_validation["best_pdb_id"],
            "next_truthful_stage": "ingest_local_structure_bridge_q9nzd4",
            "candidate_only": True,
        },
    ]
    return {
        "artifact_id": "ligand_stage1_validation_panel_preview",
        "schema_id": "proteosphere-ligand-stage1-validation-panel-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "validated_accessions": [row["accession"] for row in rows],
            "aligned_row_count": sum(1 for row in rows if row["status"] == "aligned"),
            "candidate_only_accessions": [
                row["accession"] for row in rows if row["candidate_only"]
            ],
            "operator_ready": all(
                preview["truth_boundary"]["ready_for_operator_preview"]
                for preview in (p00387_validation, q9nzd4_validation)
            ),
        },
        "truth_boundary": {
            "summary": (
                "This panel consolidates the two grounded ligand stage-one validation lanes "
                "for operator steering. It remains report-only and does not materialize "
                "ligand rows, unlock split behavior, or authorize packet promotion."
            ),
            "report_only": True,
            "ligand_rows_materialized": False,
            "bundle_ligands_included": False,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ligand Stage1 Validation Panel Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        "",
        "## Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['accession']}` / `{row['lane_kind']}` / "
            f"`{row['status']}` / next `{row['next_truthful_stage']}`"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact operator panel for grounded ligand stage-one validations."
    )
    parser.add_argument("--p00387-validation", type=Path, default=DEFAULT_P00387_VALIDATION)
    parser.add_argument("--q9nzd4-validation", type=Path, default=DEFAULT_Q9NZD4_VALIDATION)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_stage1_validation_panel_preview(
        _read_json(args.p00387_validation),
        _read_json(args.q9nzd4_validation),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
