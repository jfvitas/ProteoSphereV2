from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_contract.json"
)
DEFAULT_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "p00387_local_chembl_ligand_payload.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_validation_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "p00387_ligand_extraction_validation_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_p00387_ligand_extraction_validation_preview(
    contract: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    live_signal = contract.get("live_signal") or {}
    summary = payload.get("summary") or {}
    selected_target = live_signal.get("selected_target_hit") or {}
    rows = payload.get("rows") or []
    top_row = rows[0] if rows else {}
    contract_ready = contract.get("contract_status") == "ready_for_next_step"
    payload_resolved = payload.get("status") == "resolved"
    status = "aligned" if contract_ready and payload_resolved else "attention_needed"
    return {
        "artifact_id": "p00387_ligand_extraction_validation_preview",
        "schema_id": "proteosphere-p00387-ligand-extraction-validation-preview-2026-04-01",
        "status": status,
        "accession": "P00387",
        "target_chembl_id": summary.get("target_chembl_id") or selected_target.get("chembl_id"),
        "target_pref_name": summary.get("target_pref_name")
        or selected_target.get("pref_name"),
        "contract_status": contract.get("contract_status"),
        "payload_status": payload.get("status"),
        "activity_count_total": summary.get("activity_count_total", 0),
        "rows_emitted": summary.get("rows_emitted", 0),
        "distinct_assay_count_in_payload": summary.get("distinct_assay_count_in_payload", 0),
        "distinct_ligand_count_in_payload": summary.get(
            "distinct_ligand_count_in_payload",
            0,
        ),
        "top_ligand_chembl_id": summary.get("top_ligand_chembl_id")
        or top_row.get("ligand_chembl_id"),
        "top_standard_type": top_row.get("standard_type"),
        "top_standard_value": top_row.get("standard_value"),
        "top_standard_units": top_row.get("standard_units"),
        "validation_summary": {
            "contract_ready": contract_ready,
            "payload_resolved": payload_resolved,
            "selected_target_activity_count": selected_target.get("activity_count", 0),
            "ready_for_operator_preview": contract_ready and payload_resolved,
        },
        "truth_boundary": {
            "summary": (
                "This is a bounded validation preview for the P00387 local extraction lane. "
                "It validates fresh-run evidence shape only and does not claim canonical "
                "ligand materialization, assay reconciliation, or packet promotion."
            ),
            "report_only": True,
            "canonical_ligand_materialization_claimed": False,
            "canonical_assay_resolution_claimed": False,
            "packet_promotion_claimed": False,
            "ready_for_operator_preview": contract_ready and payload_resolved,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# P00387 Ligand Extraction Validation Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Accession: `{payload['accession']}`",
        f"- Target: `{payload['target_chembl_id']}` / `{payload['target_pref_name']}`",
        f"- Rows emitted: `{payload['rows_emitted']}`",
        f"- Total activities: `{payload['activity_count_total']}`",
        f"- Distinct assays: `{payload['distinct_assay_count_in_payload']}`",
        f"- Distinct ligands: `{payload['distinct_ligand_count_in_payload']}`",
        f"- Top ligand: `{payload['top_ligand_chembl_id']}`",
        "",
        "## Validation",
        "",
        f"- Contract ready: `{payload['validation_summary']['contract_ready']}`",
        f"- Payload resolved: `{payload['validation_summary']['payload_resolved']}`",
        (
            "- Ready for operator preview: "
            f"`{payload['validation_summary']['ready_for_operator_preview']}`"
        ),
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the P00387 ligand extraction validation preview."
    )
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_p00387_ligand_extraction_validation_preview(
        _read_json(args.contract),
        _read_json(args.payload),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
