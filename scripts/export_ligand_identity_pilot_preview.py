from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PILOT_ORDER = (
    REPO_ROOT / "artifacts" / "status" / "p76_ligand_identity_pilot_accession_order.json"
)
DEFAULT_LIGAND_SUPPORT = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_P00387_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "p00387_local_chembl_ligand_payload.json"
)
DEFAULT_BRIDGE_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.real.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_pilot_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_identity_pilot_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_p00387_evidence_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    summary = payload.get("summary") or {}
    rows = payload.get("rows") or []
    first_row = rows[0] if rows else {}
    return {
        "grounded_evidence_kind": "local_chembl_bulk_assay_summary",
        "target_chembl_id": summary.get("target_chembl_id"),
        "target_pref_name": summary.get("target_pref_name"),
        "activity_count_total": summary.get("activity_count_total"),
        "rows_emitted": summary.get("rows_emitted"),
        "distinct_ligand_count_in_payload": summary.get("distinct_ligand_count_in_payload"),
        "top_ligand_chembl_id": first_row.get("ligand_chembl_id"),
        "top_standard_type": first_row.get("standard_type"),
        "top_standard_value": first_row.get("standard_value"),
        "top_standard_units": first_row.get("standard_units"),
    }


def _build_q9nzd4_evidence_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    for entry in payload.get("entries", []):
        if entry.get("accession") != "Q9NZD4":
            continue
        selected_ligand = entry.get("selected_ligand") or {}
        return {
            "grounded_evidence_kind": "local_structure_bridge_summary",
            "pdb_id": entry.get("pdb_id"),
            "bridge_state": entry.get("bridge_state"),
            "component_id": selected_ligand.get("component_id"),
            "component_name": selected_ligand.get("component_name"),
            "component_role": selected_ligand.get("component_role"),
            "chain_ids": selected_ligand.get("chain_ids") or [],
        }
    return None


def build_ligand_identity_pilot_preview(
    pilot_order: dict[str, Any],
    ligand_support: dict[str, Any],
    *,
    p00387_payload: dict[str, Any] | None = None,
    bridge_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ordering = pilot_order["ordering"]
    active_rows = [row for row in ordering if row["accession"] != "Q9UCM0"]
    deferred_row = next(row for row in ordering if row["accession"] == "Q9UCM0")
    support_rows = {row["accession"]: row for row in ligand_support["rows"]}
    grounded_evidence_map = {
        "P00387": _build_p00387_evidence_summary(p00387_payload),
        "Q9NZD4": _build_q9nzd4_evidence_summary(bridge_payload),
    }

    preview_rows = []
    for order_row in active_rows:
        support_row = support_rows[order_row["accession"]]
        grounded_evidence = grounded_evidence_map.get(order_row["accession"])
        preview_rows.append(
            {
                "rank": order_row["rank"],
                "accession": order_row["accession"],
                "source_ref": order_row["source_ref"],
                "pilot_role": order_row["pilot_role"],
                "pilot_lane_status": support_row["pilot_lane_status"],
                "current_blocker": support_row["current_blocker"],
                "next_truthful_stage": order_row["next_truthful_stage"],
                "grounded_evidence_kind": (
                    grounded_evidence.get("grounded_evidence_kind")
                    if grounded_evidence is not None
                    else "support_only_no_grounded_payload"
                ),
                "grounded_evidence": grounded_evidence,
            }
        )

    return {
        "artifact_id": "ligand_identity_pilot_preview",
        "schema_id": "proteosphere-ligand-identity-pilot-preview-2026-04-01",
        "status": "complete",
        "row_count": len(preview_rows),
        "rows": preview_rows,
        "deferred_accession": deferred_row["accession"],
        "deferred_reason": deferred_row["next_truthful_stage"],
        "grounded_accessions": [
            row["accession"] for row in preview_rows if row["grounded_evidence"] is not None
        ],
        "grounded_accession_count": sum(
            1 for row in preview_rows if row["grounded_evidence"] is not None
        ),
        "truth_boundary": {
            "summary": (
                "This is an execution-order preview for the narrow ligand identity pilot. "
                "It remains report-only, does not materialize ligand rows, and keeps "
                "Q9UCM0 deferred."
            ),
            "report_only": True,
            "ligand_rows_materialized": False,
            "bundle_ligands_included": False,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ligand Identity Pilot Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Active rows: `{payload['row_count']}`",
        f"- Deferred accession: `{payload['deferred_accession']}`",
        "",
        "## Pilot Order",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['accession']}` -> "
            f"`{row['pilot_lane_status']}` then `{row['next_truthful_stage']}`"
        )
        if row.get("grounded_evidence_kind"):
            lines.append(f"  evidence: `{row['grounded_evidence_kind']}`")
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
        description="Export the narrow ligand identity pilot preview."
    )
    parser.add_argument("--pilot-order", type=Path, default=DEFAULT_PILOT_ORDER)
    parser.add_argument("--ligand-support", type=Path, default=DEFAULT_LIGAND_SUPPORT)
    parser.add_argument("--p00387-payload", type=Path, default=DEFAULT_P00387_PAYLOAD)
    parser.add_argument("--bridge-payload", type=Path, default=DEFAULT_BRIDGE_PAYLOAD)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_identity_pilot_preview(
        _read_json(args.pilot_order),
        _read_json(args.ligand_support),
        p00387_payload=(
            _read_json(args.p00387_payload) if args.p00387_payload.exists() else None
        ),
        bridge_payload=(
            _read_json(args.bridge_payload) if args.bridge_payload.exists() else None
        ),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
