from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "next_real_ligand_row_gate_preview.json"
)
DEFAULT_LOCAL_SOURCE_MAP = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.refresh.json"
)
DEFAULT_LOCAL_GAP_PROBE = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_gap_probe.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "next_real_ligand_row_decision_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "next_real_ligand_row_decision_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _index_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def build_next_real_ligand_row_decision_preview(
    gate_preview: dict[str, Any],
    local_source_map: dict[str, Any],
    local_gap_probe: dict[str, Any],
) -> dict[str, Any]:
    selected_accession = str(gate_preview.get("selected_accession") or "").strip()
    fallback_accession = str(gate_preview.get("fallback_accession") or "").strip()
    source_rows = _index_by_accession(local_source_map.get("entries") or [])
    gap_rows = _index_by_accession(local_gap_probe.get("entries") or [])

    selected_source = source_rows.get(selected_accession, {})
    selected_gap = gap_rows.get(selected_accession, {})
    fallback_source = source_rows.get(fallback_accession, {})
    fallback_gap = gap_rows.get(fallback_accession, {})

    fallback_trigger = (
        "Only advance from P09105 to Q2TAC2 after the selected accession remains "
        "blocked_pending_acquisition and the blocker has been recorded without emitting "
        "new grounded ligand rows."
    )

    minimum_grounded_promotion_evidence = [
        (
            "validated local bulk-assay payload or a truthful local structure "
            "bridge with ligand-bearing evidence"
        ),
        "grounded row emission passes accession-scoped validation without changing split policy",
        "candidate-only evidence is excluded from governance claims",
    ]

    return {
        "artifact_id": "next_real_ligand_row_decision_preview",
        "schema_id": "proteosphere-next-real-ligand-row-decision-preview-2026-04-02",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "selected_accession": selected_accession,
        "selected_accession_gate_status": gate_preview.get(
            "selected_accession_gate_status"
        ),
        "selected_accession_probe_criteria": {
            "source_classification": selected_source.get("classification"),
            "gap_probe_classification": selected_gap.get("classification"),
            "best_next_action": selected_gap.get("best_next_action")
            or selected_source.get("recommended_next_action"),
            "best_next_source": selected_gap.get("best_next_source"),
        },
        "fallback_accession": fallback_accession,
        "fallback_accession_gate_status": gate_preview.get(
            "fallback_accession_gate_status"
        ),
        "fallback_probe_criteria": {
            "source_classification": fallback_source.get("classification"),
            "gap_probe_classification": fallback_gap.get("classification"),
            "best_next_action": fallback_gap.get("best_next_action")
            or fallback_source.get("recommended_next_action"),
            "best_next_source": fallback_gap.get("best_next_source"),
        },
        "fallback_trigger_rule": fallback_trigger,
        "minimum_grounded_promotion_evidence": minimum_grounded_promotion_evidence,
        "current_grounded_accessions": gate_preview.get("current_grounded_accessions") or [],
        "truth_boundary": {
            "summary": (
                "This is a report-only decision surface for the next grounded ligand "
                "accession path. It documents probe criteria, fallback behavior, and "
                "minimum promotion evidence without emitting new grounded ligand rows."
            ),
            "report_only": True,
            "grounded_ligand_rows_mutated": False,
            "candidate_only_rows_non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Next Real Ligand Row Decision Preview",
        "",
        f"- Selected accession: `{payload['selected_accession']}`",
        f"- Selected gate status: `{payload['selected_accession_gate_status']}`",
        f"- Fallback accession: `{payload['fallback_accession']}`",
        f"- Fallback gate status: `{payload['fallback_accession_gate_status']}`",
        "",
        "## Fallback Trigger",
        "",
        f"- {payload['fallback_trigger_rule']}",
        "",
        "## Minimum Grounded Promotion Evidence",
        "",
    ]
    for item in payload["minimum_grounded_promotion_evidence"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only next grounded ligand accession decision preview."
    )
    parser.add_argument("--gate-preview", type=Path, default=DEFAULT_GATE_PREVIEW)
    parser.add_argument("--local-source-map", type=Path, default=DEFAULT_LOCAL_SOURCE_MAP)
    parser.add_argument("--local-gap-probe", type=Path, default=DEFAULT_LOCAL_GAP_PROBE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_next_real_ligand_row_decision_preview(
        _read_json(args.gate_preview),
        _read_json(args.local_source_map),
        _read_json(args.local_gap_probe),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
