from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIGAND_IDENTITY_PILOT = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_pilot_preview.json"
)
DEFAULT_LIGAND_SUPPORT = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_P00387_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_validation_preview.json"
)
DEFAULT_Q9NZD4_VALIDATION = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_LOCAL_BRIDGE_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_core_materialization_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_identity_core_materialization_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _support_row_by_accession(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["accession"]: row for row in payload.get("rows", [])}


def _bridge_entry_by_accession(
    payload: dict[str, Any],
    accession: str,
) -> dict[str, Any] | None:
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("accession") or "").strip() == accession:
            return entry
    return None


def _build_row(
    row: dict[str, Any],
    support_row: dict[str, Any],
    p00387_validation: dict[str, Any],
    q9nzd4_validation: dict[str, Any],
    q9nzd4_bridge_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    accession = row["accession"]
    if accession == "P00387":
        materialization_status = "grounded_ready_identity_core_candidate"
        candidate_only = False
        validation_status = p00387_validation["status"]
    elif accession == "Q9NZD4":
        if (
            isinstance(q9nzd4_bridge_entry, dict)
            and str(q9nzd4_bridge_entry.get("status") or "").strip() == "resolved"
        ):
            materialization_status = "grounded_ready_identity_core_candidate"
            candidate_only = False
            validation_status = "aligned_bridge_payload_resolved"
        else:
            materialization_status = "candidate_bridge_ready_identity_core_candidate"
            candidate_only = True
            validation_status = q9nzd4_validation["status"]
    else:
        materialization_status = "held_support_only_identity_core_candidate"
        candidate_only = False
        validation_status = "support_only"

    grounded = row.get("grounded_evidence") is not None
    return {
        "rank": row["rank"],
        "accession": accession,
        "source_ref": row["source_ref"],
        "pilot_role": row["pilot_role"],
        "materialization_family": "ligand_identity_core",
        "materialization_status": materialization_status,
        "validation_status": validation_status,
        "grounded_evidence_kind": row["grounded_evidence_kind"],
        "grounded_now": grounded,
        "candidate_only": candidate_only,
        "current_blocker": support_row["current_blocker"],
        "next_truthful_stage": row["next_truthful_stage"],
    }


def build_ligand_identity_core_materialization_preview(
    ligand_identity_pilot: dict[str, Any],
    ligand_support: dict[str, Any],
    p00387_validation: dict[str, Any],
    q9nzd4_validation: dict[str, Any],
    local_bridge_payload: dict[str, Any],
) -> dict[str, Any]:
    support_rows = _support_row_by_accession(ligand_support)
    q9nzd4_bridge_entry = _bridge_entry_by_accession(local_bridge_payload, "Q9NZD4")
    rows = [
        _build_row(
            row,
            support_rows[row["accession"]],
            p00387_validation,
            q9nzd4_validation,
            q9nzd4_bridge_entry,
        )
        for row in ligand_identity_pilot.get("rows", [])
    ]
    grounded_accessions = [row["accession"] for row in rows if row["grounded_now"]]
    held_support_only_accessions = [
        row["accession"]
        for row in rows
        if row["materialization_status"] == "held_support_only_identity_core_candidate"
    ]
    candidate_only_accessions = [
        row["accession"] for row in rows if row["candidate_only"]
    ]
    return {
        "artifact_id": "ligand_identity_core_materialization_preview",
        "schema_id": "proteosphere-ligand-identity-core-materialization-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "ordered_accessions": [row["accession"] for row in rows],
            "grounded_accessions": grounded_accessions,
            "grounded_accession_count": len(grounded_accessions),
            "held_support_only_accessions": held_support_only_accessions,
            "candidate_only_accessions": candidate_only_accessions,
            "ready_for_bundle_preview": True,
        },
        "truth_boundary": {
            "summary": (
                "This is the first explicit identity-core ligand family candidate surface. "
                "It remains preview-only, does not materialize ligand rows, does not include "
                "bundle ligands, and does not change split, packet, or release claims."
            ),
            "report_only": True,
            "ligand_rows_materialized": False,
            "bundle_ligands_included": False,
            "canonical_ligand_materialization_claimed": False,
            "packet_promotion_claimed": False,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ligand Identity Core Materialization Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        f"- Grounded accessions: `{', '.join(payload['summary']['grounded_accessions'])}`",
        "",
        "## Candidate Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['accession']}` / `{row['materialization_status']}` / "
            f"next `{row['next_truthful_stage']}`"
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
        description="Export the first explicit ligand identity-core materialization preview."
    )
    parser.add_argument(
        "--ligand-identity-pilot",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_PILOT,
    )
    parser.add_argument(
        "--ligand-support",
        type=Path,
        default=DEFAULT_LIGAND_SUPPORT,
    )
    parser.add_argument(
        "--p00387-validation",
        type=Path,
        default=DEFAULT_P00387_VALIDATION,
    )
    parser.add_argument(
        "--q9nzd4-validation",
        type=Path,
        default=DEFAULT_Q9NZD4_VALIDATION,
    )
    parser.add_argument(
        "--local-bridge-payload",
        type=Path,
        default=DEFAULT_LOCAL_BRIDGE_PAYLOAD,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_identity_core_materialization_preview(
        _read_json(args.ligand_identity_pilot),
        _read_json(args.ligand_support),
        _read_json(args.p00387_validation),
        _read_json(args.q9nzd4_validation),
        _read_json(args.local_bridge_payload),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
