from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATION_CONTRACT = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "p88_next_real_ligand_row_accession_validation_contract.json"
)
DEFAULT_LOCAL_SOURCE_MAP = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.refresh.json"
)
DEFAULT_LOCAL_GAP_PROBE = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_gap_probe.json"
)
DEFAULT_LIGAND_ROW_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "next_real_ligand_row_gate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "next_real_ligand_row_gate_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _index_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def _grounded_accessions(ligand_row_preview: dict[str, Any]) -> list[str]:
    summary = (
        ligand_row_preview.get("summary")
        if isinstance(ligand_row_preview.get("summary"), dict)
        else {}
    )
    return [
        str(value).strip()
        for value in summary.get("grounded_accessions") or []
        if str(value).strip()
    ]


def _gate_status(
    *,
    accession: str,
    local_source_map_row: dict[str, Any] | None,
    local_gap_probe_row: dict[str, Any] | None,
) -> tuple[str, str]:
    if local_source_map_row is None and local_gap_probe_row is None:
        return (
            "blocked_pending_acquisition",
            "no accession-scoped local source-map or gap-probe evidence is present",
        )

    source_classification = str(
        (local_source_map_row or {}).get("classification") or ""
    ).strip()
    gap_classification = str((local_gap_probe_row or {}).get("classification") or "").strip()
    recommended_next_action = str(
        (local_source_map_row or {}).get("recommended_next_action")
        or (local_gap_probe_row or {}).get("best_next_action")
        or ""
    ).strip()

    if source_classification == "structure_bridge_actionable":
        return (
            "ready_for_grounded_row_attempt",
            "a concrete structure bridge is present in the local source map",
        )
    if source_classification == "grounded_bulk_assay_actionable":
        return (
            "ready_for_grounded_row_attempt",
            "a grounded bulk-assay lane is present in the local source map",
        )
    if source_classification == "candidate_only_non_governing":
        return (
            "candidate_only_non_governing",
            "only candidate-only evidence is available, so it must remain non-governing",
        )
    if source_classification in {"structure_companion_only", "support_only_no_grounded_payload"}:
        return (
            "blocked_pending_acquisition",
            recommended_next_action
            or "only structure-companion or support-only evidence is present",
        )
    if gap_classification in {"requires_extraction", "not_found"}:
        return (
            "blocked_pending_acquisition",
            recommended_next_action or "the current gap probe still shows no grounded ligand lane",
        )
    if gap_classification == "rescuable_now":
        return (
            "candidate_only_non_governing",
            "the gap probe is rescuable now, but this remains candidate-only until grounded",
        )
    return (
        "blocked_pending_acquisition",
        recommended_next_action or "no grounded ligand evidence is present yet",
    )


def build_next_real_ligand_row_gate_preview(
    validation_contract: dict[str, Any],
    local_source_map: dict[str, Any],
    local_gap_probe: dict[str, Any],
    ligand_row_preview: dict[str, Any],
) -> dict[str, Any]:
    selected = validation_contract["selected_accession"]["accession"]
    fallback = validation_contract["selected_accession"][
        "fallback_accession_if_p09105_stays_blocked"
    ]
    source_map_rows = _index_by_accession(local_source_map.get("entries") or [])
    gap_probe_rows = _index_by_accession(local_gap_probe.get("entries") or [])
    grounded_accessions = sorted(_grounded_accessions(ligand_row_preview))

    selected_status, selected_reason = _gate_status(
        accession=selected,
        local_source_map_row=source_map_rows.get(selected),
        local_gap_probe_row=gap_probe_rows.get(selected),
    )
    fallback_status, fallback_reason = _gate_status(
        accession=fallback,
        local_source_map_row=source_map_rows.get(fallback),
        local_gap_probe_row=gap_probe_rows.get(fallback),
    )
    can_materialize_now = selected_status == "ready_for_grounded_row_attempt"
    next_unlocked_stage = (
        "emit_accession_scoped_grounded_rows_for_selected_accession"
        if can_materialize_now
        else "record_selected_accession_blocker_then_recheck_fixed_fallback_accession"
    )
    return {
        "artifact_id": "next_real_ligand_row_gate_preview",
        "schema_id": "proteosphere-next-real-ligand-row-gate-preview-2026-04-02",
        "status": "complete",
        "selected_accession": selected,
        "selected_accession_gate_status": selected_status,
        "selected_accession_reason": selected_reason,
        "selected_accession_source_classification": (
            source_map_rows.get(selected, {}).get("classification")
        ),
        "selected_accession_gap_probe_classification": (
            gap_probe_rows.get(selected, {}).get("classification")
        ),
        "fallback_accession": fallback,
        "fallback_accession_gate_status": fallback_status,
        "fallback_accession_reason": fallback_reason,
        "fallback_accession_source_classification": (
            source_map_rows.get(fallback, {}).get("classification")
        ),
        "fallback_accession_gap_probe_classification": (
            gap_probe_rows.get(fallback, {}).get("classification")
        ),
        "current_grounded_accession_count": len(grounded_accessions),
        "current_grounded_accessions": grounded_accessions,
        "can_materialize_new_grounded_accession_now": can_materialize_now,
        "next_unlocked_stage": next_unlocked_stage,
        "truth_boundary": {
            "summary": (
                "This is a report-only gate for the next real ligand-row accession "
                "after the current grounded ligand family. It preserves the fixed "
                "P09105 -> Q2TAC2 order, does not emit new ligand rows, and does not "
                "change split or leakage behavior."
            ),
            "report_only": True,
            "grounded_ligand_rows_mutated": False,
            "split_policy_mutated": False,
            "candidate_only_rows_non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Next Real Ligand Row Gate Preview",
        "",
        f"- Status: `{payload['status']}`",
        (
            f"- Selected accession: `{payload['selected_accession']}` -> "
            f"`{payload['selected_accession_gate_status']}`"
        ),
        (
            f"- Fallback accession: `{payload['fallback_accession']}` -> "
            f"`{payload['fallback_accession_gate_status']}`"
        ),
        "- Current grounded accessions: "
        f"`{', '.join(payload['current_grounded_accessions']) or 'none'}`",
        (
            "- Can materialize a new grounded accession now: "
            f"`{payload['can_materialize_new_grounded_accession_now']}`"
        ),
        f"- Next unlocked stage: `{payload['next_unlocked_stage']}`",
        "",
        "## Reasons",
        "",
        f"- `{payload['selected_accession']}`: {payload['selected_accession_reason']}",
        f"- `{payload['fallback_accession']}`: {payload['fallback_accession_reason']}",
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the next real ligand-row gate preview."
    )
    parser.add_argument("--validation-contract", type=Path, default=DEFAULT_VALIDATION_CONTRACT)
    parser.add_argument("--local-source-map", type=Path, default=DEFAULT_LOCAL_SOURCE_MAP)
    parser.add_argument("--local-gap-probe", type=Path, default=DEFAULT_LOCAL_GAP_PROBE)
    parser.add_argument("--ligand-row-preview", type=Path, default=DEFAULT_LIGAND_ROW_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_next_real_ligand_row_gate_preview(
        _read_json(args.validation_contract),
        _read_json(args.local_source_map),
        _read_json(args.local_gap_probe),
        _read_json(args.ligand_row_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
