from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE_PAYLOAD = (
    REPO_ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.real.json"
)
DEFAULT_EXECUTION_SLICE = (
    REPO_ROOT / "artifacts" / "status" / "p33_q9nzd4_ligand_execution_slice.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "q9nzd4_bridge_validation_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_bridge_entry(payload: dict[str, Any]) -> dict[str, Any] | None:
    for entry in payload.get("entries", []):
        if entry.get("accession") == "Q9NZD4":
            return entry
    return None


def _find_execution_entry(payload: dict[str, Any]) -> dict[str, Any] | None:
    for entry in payload.get("entries", []):
        if entry.get("accession") == "Q9NZD4":
            return entry
    return None


def build_q9nzd4_bridge_validation_preview(
    bridge_payload: dict[str, Any],
    execution_slice: dict[str, Any],
) -> dict[str, Any]:
    bridge_entry = _find_bridge_entry(bridge_payload) or {}
    execution_entry = _find_execution_entry(execution_slice) or {}
    selected_ligand = bridge_entry.get("selected_ligand") or {}
    structure_bridge = execution_entry.get("evidence", {}).get("structure_bridge", {})
    matched_pdb_ids = structure_bridge.get("matched_pdb_ids") or []
    best_source_path = structure_bridge.get("best_source_path")
    resolved = (
        bridge_entry.get("status") == "resolved"
        and bridge_entry.get("bridge_state") == "ready_now"
        and execution_entry.get("classification") == "rescuable_now"
    )
    status = "aligned" if resolved else "attention_needed"
    return {
        "artifact_id": "q9nzd4_bridge_validation_preview",
        "schema_id": "proteosphere-q9nzd4-bridge-validation-preview-2026-04-01",
        "status": status,
        "accession": "Q9NZD4",
        "classification": execution_entry.get("classification"),
        "best_next_action": execution_entry.get("best_next_action"),
        "best_pdb_id": bridge_entry.get("pdb_id") or structure_bridge.get("best_pdb_id"),
        "component_id": selected_ligand.get("component_id"),
        "component_name": selected_ligand.get("component_name"),
        "component_role": selected_ligand.get("component_role"),
        "chain_ids": selected_ligand.get("chain_ids") or [],
        "matched_pdb_id_count": len(matched_pdb_ids),
        "best_source_path": best_source_path,
        "validation_summary": {
            "bridge_payload_resolved": bridge_entry.get("status") == "resolved",
            "bridge_state_ready_now": bridge_entry.get("bridge_state") == "ready_now",
            "execution_classification_rescuable_now": (
                execution_entry.get("classification") == "rescuable_now"
            ),
            "ready_for_operator_preview": resolved,
        },
        "truth_boundary": {
            "summary": (
                "This is a bounded bridge-validation preview for Q9NZD4. It confirms the "
                "local structure-bridge evidence shape only and does not claim canonical "
                "ligand materialization, packet promotion, or direct structure-backed join "
                "certification."
            ),
            "report_only": True,
            "candidate_only": True,
            "canonical_ligand_materialization_claimed": False,
            "packet_promotion_claimed": False,
            "direct_structure_backed_join_certified": False,
            "ready_for_operator_preview": resolved,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Q9NZD4 Bridge Validation Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Accession: `{payload['accession']}`",
        f"- Classification: `{payload['classification']}`",
        f"- Best next action: `{payload['best_next_action']}`",
        f"- Best PDB ID: `{payload['best_pdb_id']}`",
        f"- Component ID: `{payload['component_id']}`",
        f"- Component role: `{payload['component_role']}`",
        f"- Matched PDB count: `{payload['matched_pdb_id_count']}`",
        "",
        "## Validation",
        "",
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
        description="Export the Q9NZD4 bridge validation preview."
    )
    parser.add_argument("--bridge-payload", type=Path, default=DEFAULT_BRIDGE_PAYLOAD)
    parser.add_argument("--execution-slice", type=Path, default=DEFAULT_EXECUTION_SLICE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_q9nzd4_bridge_validation_preview(
        _read_json(args.bridge_payload),
        _read_json(args.execution_slice),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
