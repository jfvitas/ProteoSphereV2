from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.modality_readiness_ladder import (
        LADDER_ABSENT,
        LADDER_CANDIDATE_ONLY,
        LADDER_GROUNDED_GOVERNING,
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_SUPPORT_ONLY,
        classify_ligand_readiness,
        ladder_accession_buckets,
        ladder_counts,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from modality_readiness_ladder import (
        LADDER_ABSENT,
        LADDER_CANDIDATE_ONLY,
        LADDER_GROUNDED_GOVERNING,
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_SUPPORT_ONLY,
        classify_ligand_readiness,
        ladder_accession_buckets,
        ladder_counts,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUPPORT_SUBSLICE = (
    REPO_ROOT / "artifacts" / "status" / "p74_ligand_support_subslice.json"
)
DEFAULT_PACKET_DEFICIT_DASHBOARD = (
    REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
)
DEFAULT_LOCAL_LIGAND_SOURCE_MAP = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.json"
)
DEFAULT_LOCAL_LIGAND_GAP_PROBE = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_gap_probe.json"
)
DEFAULT_LIGAND_ROW_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_support_readiness_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _index_by_accession(
    rows: list[dict[str, Any]],
    accession_key: str = "accession",
) -> dict[str, dict[str, Any]]:
    return {row[accession_key]: row for row in rows}


def _packet_row_by_accession(packet_dashboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _index_by_accession(packet_dashboard.get("packets", []))


def _local_map_row_by_accession(local_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _index_by_accession(local_map.get("entries", []))


def _gap_probe_row_by_accession(gap_probe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _index_by_accession(gap_probe.get("entries", []))


def _ligand_row_sets(ligand_row_preview: dict[str, Any]) -> tuple[set[str], set[str]]:
    summary = ligand_row_preview.get("summary") if isinstance(ligand_row_preview, dict) else {}
    grounded = {
        str(value).strip()
        for value in (summary or {}).get("grounded_accessions") or []
        if str(value).strip()
    }
    candidate_only = {
        str(value).strip()
        for value in (summary or {}).get("candidate_only_accessions") or []
        if str(value).strip()
    }
    return grounded, candidate_only


def _current_ligand_gap_count(live_grounding: dict[str, Any]) -> int:
    if "current_ligand_gap_count" in live_grounding:
        return int(live_grounding["current_ligand_gap_count"])
    if "current_ligand_gap_accessions" in live_grounding:
        return len(live_grounding["current_ligand_gap_accessions"])
    if "current_ligand_gap_refs" in live_grounding:
        return len(live_grounding["current_ligand_gap_refs"])
    return 0


def _pilot_role(accession: str) -> str:
    if accession == "P00387":
        return "lead_anchor"
    if accession == "Q9NZD4":
        return "bridge_rescue_candidate"
    return "support_candidate"


def _build_row(
    accession: str,
    packet_row: dict[str, Any],
    local_map_row: dict[str, Any] | None,
    gap_probe_row: dict[str, Any] | None,
    ligand_readiness_ladder: str,
    ligand_readiness_reason: str,
    bundle_ligands_included: bool,
) -> dict[str, Any]:
    if local_map_row is not None:
        lane_status = local_map_row["classification"]
        next_stage_target = local_map_row["recommended_next_action"]
        source_provenance_refs = [
            "local_ligand_source_map",
            "packet_deficit_dashboard",
        ]
        if gap_probe_row is not None:
            source_provenance_refs.append("local_ligand_gap_probe")
        if lane_status == "bulk_assay_actionable":
            current_blocker = "support_only_only_no_ligand_rows_materialized"
        elif lane_status == "structure_companion_only":
            current_blocker = "no_local_ligand_evidence_yet"
        else:
            current_blocker = "support_only_bridge_not_materialized"
    elif gap_probe_row is not None:
        lane_status = gap_probe_row["classification"]
        next_stage_target = gap_probe_row["best_next_action"]
        source_provenance_refs = [
            "local_ligand_gap_probe",
            "packet_deficit_dashboard",
        ]
        if lane_status == "rescuable_now":
            current_blocker = "bridge_rescue_not_materialized"
        elif lane_status == "requires_extraction":
            current_blocker = "requires_local_structure_companion_extraction"
        else:
            current_blocker = "no_truthful_local_ligand_rescue_found"
    else:
        lane_status = "no_local_evidence"
        next_stage_target = "hold_for_ligand_acquisition"
        current_blocker = "no_local_ligand_evidence_yet"
        source_provenance_refs = ["packet_deficit_dashboard"]

    if ligand_readiness_ladder in {
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_GROUNDED_GOVERNING,
    }:
        current_blocker = (
            "bundle_inclusion_pending_governing_promotion"
            if not bundle_ligands_included
            else "no_current_ligand_blocker"
        )
        next_stage_target = (
            "keep_grounded_rows_visible_and_non_governing"
            if not bundle_ligands_included
            else "governing_ligand_rows_available"
        )

    return {
        "accession": accession,
        "source_ref": f"ligand:{accession}",
        "pilot_role": _pilot_role(accession),
        "pilot_lane_status": lane_status,
        "packet_status": packet_row["status"],
        "current_blocker": current_blocker,
        "next_stage_target": next_stage_target,
        "source_provenance_refs": source_provenance_refs,
        "ligand_readiness_ladder": ligand_readiness_ladder,
        "ligand_readiness_reason": ligand_readiness_reason,
    }


def build_ligand_support_readiness_preview(
    support_subslice: dict[str, Any],
    packet_dashboard: dict[str, Any],
    local_ligand_source_map: dict[str, Any],
    local_ligand_gap_probe: dict[str, Any],
    ligand_row_preview: dict[str, Any],
) -> dict[str, Any]:
    support = support_subslice["support_only_subslice"]
    live_grounding = support_subslice["live_grounding"]
    support_accessions = support["support_accessions"]
    deferred_accessions = support["deferred_accessions"]
    packet_rows = _packet_row_by_accession(packet_dashboard)
    local_map_rows = _local_map_row_by_accession(local_ligand_source_map)
    gap_probe_rows = _gap_probe_row_by_accession(local_ligand_gap_probe)
    grounded_accessions, candidate_only_accessions = _ligand_row_sets(ligand_row_preview)

    rows = [
        _build_row(
            accession,
            packet_rows[accession],
            local_map_rows.get(accession),
            gap_probe_rows.get(accession),
            ligand_readiness_ladder=classify_ligand_readiness(
                accession,
                grounded_accessions=grounded_accessions,
                candidate_only_accessions=candidate_only_accessions,
                support_accessions=support_accessions,
                packet_status=str(packet_rows[accession].get("status") or ""),
                packet_missing_modalities=packet_rows[accession].get("missing_modalities") or [],
                bundle_ligands_included=bool(live_grounding["bundle_ligands_included"]),
            ),
            ligand_readiness_reason="",
            bundle_ligands_included=bool(live_grounding["bundle_ligands_included"]),
        )
        for accession in support_accessions
    ]
    for row in rows:
        row["ligand_readiness_reason"] = (
            (
                "grounded lightweight ligand rows are materialized, but bundle inclusion is still false."
                if row["ligand_readiness_ladder"] == LADDER_GROUNDED_PREVIEW_SAFE
                else "only candidate-only ligand evidence exists, so this row must remain non-governing."
                if row["ligand_readiness_ladder"] == LADDER_CANDIDATE_ONLY
                else "local support evidence exists, but no grounded ligand row is materialized yet."
                if row["ligand_readiness_ladder"] == LADDER_SUPPORT_ONLY
                else "grounded ligand rows are materialized and bundle inclusion is governing."
                if row["ligand_readiness_ladder"] == LADDER_GROUNDED_GOVERNING
                else "no local ligand evidence is available yet, so the row remains absent."
            )
        )

    ladder_accessions = ladder_accession_buckets(rows)
    absent_accessions = sorted(
        accession
        for accession in deferred_accessions
        if classify_ligand_readiness(
            accession,
            grounded_accessions=grounded_accessions,
            candidate_only_accessions=candidate_only_accessions,
            support_accessions=support_accessions,
            bundle_ligands_included=bool(live_grounding["bundle_ligands_included"]),
        )
        == LADDER_ABSENT
    )
    ladder_counts_payload = ladder_counts(
        [
            *[row["ligand_readiness_ladder"] for row in rows],
            *([LADDER_ABSENT] if absent_accessions else []),
        ]
    )

    return {
        "artifact_id": "ligand_support_readiness_preview",
        "schema_id": "proteosphere-ligand-support-readiness-preview-2026-04-01",
        "status": "complete",
        "surface_kind": "support_only_readiness_card",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "support_accessions": support_accessions,
            "deferred_accessions": deferred_accessions,
            "bundle_ligands_included": live_grounding["bundle_ligands_included"],
            "bundle_ligand_record_count": live_grounding["bundle_ligand_record_count"],
            "current_ligand_gap_count": _current_ligand_gap_count(live_grounding),
            "lane_status_counts": {
                status: sum(1 for row in rows if row["pilot_lane_status"] == status)
                for status in sorted({row["pilot_lane_status"] for row in rows})
            },
            "ligand_readiness_ladder_counts": ladder_counts_payload,
            "ligand_readiness_accessions": ladder_accessions,
            "absent_accessions": absent_accessions,
        },
        "truth_boundary": {
            "summary": (
                "This is a support-only ligand readiness surface for the current gap "
                "accessions. It does not materialize ligand rows, does not change bundle "
                "ligand inclusion, and keeps absent rows conservative."
            ),
            "report_only_support_surface": True,
            "bundle_ligands_included": False,
            "ligand_rows_materialized": False,
            "q9ucm0_deferred": True,
            "support_only_non_governing": True,
            "candidate_only_non_governing": True,
            "grounded_preview_safe_non_governing": True,
            "ready_for_operator_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Ligand Support Readiness Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Surface kind: `{payload['surface_kind']}`",
        f"- Support rows: `{payload['row_count']}`",
        f"- Deferred accessions: `{', '.join(summary['deferred_accessions'])}`",
        f"- Bundle ligands included: `{summary['bundle_ligands_included']}`",
        "- Ligand readiness ladder counts: "
        f"`{json.dumps(summary['ligand_readiness_ladder_counts'], sort_keys=True)}`",
        "",
        "## Support Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['accession']}` -> role=`{row['pilot_role']}`, "
            f"lane=`{row['pilot_lane_status']}`, blocker=`{row['current_blocker']}`, "
            f"readiness=`{row['ligand_readiness_ladder']}`, next=`{row['next_stage_target']}`"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the support-only ligand readiness preview."
    )
    parser.add_argument(
        "--support-subslice",
        type=Path,
        default=DEFAULT_SUPPORT_SUBSLICE,
    )
    parser.add_argument(
        "--packet-deficit-dashboard",
        type=Path,
        default=DEFAULT_PACKET_DEFICIT_DASHBOARD,
    )
    parser.add_argument(
        "--local-ligand-source-map",
        type=Path,
        default=DEFAULT_LOCAL_LIGAND_SOURCE_MAP,
    )
    parser.add_argument(
        "--local-ligand-gap-probe",
        type=Path,
        default=DEFAULT_LOCAL_LIGAND_GAP_PROBE,
    )
    parser.add_argument("--ligand-row-preview", type=Path, default=DEFAULT_LIGAND_ROW_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_support_readiness_preview(
        _read_json(args.support_subslice),
        _read_json(args.packet_deficit_dashboard),
        _read_json(args.local_ligand_source_map),
        _read_json(args.local_ligand_gap_probe),
        _read_json(args.ligand_row_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
