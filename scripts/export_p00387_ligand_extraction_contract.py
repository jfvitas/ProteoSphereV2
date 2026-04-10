from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.p00387_ligand_extraction_contract import (  # noqa: E402
    DEFAULT_CHEMBL_PATH,
    build_p00387_ligand_extraction_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "p00387_ligand_extraction_contract.json"
)
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "p00387_ligand_extraction_contract.md"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    candidate_tables = payload.get("candidate_tables") or []
    join_chain = payload.get("join_chain") or []
    live_signal = payload.get("live_signal") if isinstance(payload.get("live_signal"), dict) else {}
    expected_schema = (
        payload.get("expected_output_schema")
        if isinstance(payload.get("expected_output_schema"), dict)
        else {}
    )

    table_lines: list[str] = []
    for table in candidate_tables:
        if not isinstance(table, dict):
            continue
        present = ", ".join(table.get("present_candidate_columns") or []) or "none"
        table_lines.append(
            f"- `{table.get('table')}` ({table.get('role')}): "
            f"candidate columns = {', '.join(table.get('candidate_columns') or [])}; "
            f"present columns = {present}"
        )
    if not table_lines:
        table_lines.append("- none")

    join_lines: list[str] = []
    for step in join_chain:
        if not isinstance(step, dict):
            continue
        join_lines.append(
            f"- `{step.get('from_table')}.{step.get('from_column')}` -> "
            f"`{step.get('to_table')}.{step.get('to_column')}`: {step.get('purpose')}"
        )
    if not join_lines:
        join_lines.append("- none")

    required_fields = expected_schema.get("required") or []
    required_line = (
        ", ".join(f"`{field}`" for field in required_fields) if required_fields else "none"
    )
    blocker_lines = [f"- {item}" for item in payload.get("blockers") or []]
    if not blocker_lines:
        blocker_lines = ["- none"]
    truth_boundary_lines = [
        f"- {item}" for item in payload.get("truth_boundary_notes") or []
    ]
    selected_target = live_signal.get("selected_target_hit")
    if isinstance(selected_target, dict):
        selected_target_line = (
            f"`{selected_target.get('accession')}` -> "
            f"`{selected_target.get('chembl_id')}` "
            f"(`{selected_target.get('pref_name')}`), activities="
            f"{selected_target.get('activity_count')}"
        )
    else:
        selected_target_line = f"`{selected_target}`"
    do_not_claim = ", ".join(payload.get("next_step", {}).get("do_not_claim") or []) or "none"

    return "\n".join(
        [
            "# P00387 Ligand Extraction Contract",
            "",
            f"- Generated at: `{payload.get('generated_at')}`",
            f"- Accession: `{payload.get('accession')}`",
            f"- Contract status: `{payload.get('contract_status')}`",
            f"- Rescue claim permitted: `{payload.get('rescue_claim', {}).get('permitted')}`",
            "",
            "## Source",
            "",
            f"- Source DB path: `{payload.get('source_db_path')}`",
            f"- Source DB exists: `{payload.get('source_db_exists')}`",
            f"- Source table names: `{payload.get('source_table_names')}`",
            "",
            "## Candidate Tables",
            "",
            *table_lines,
            "",
            "## Join Chain",
            "",
            *join_lines,
            "",
            "## Live Signal",
            "",
            f"- Target hit count: `{live_signal.get('target_hit_count')}`",
            f"- Activity count: `{live_signal.get('activity_count')}`",
            f"- Selected target hit: {selected_target_line}",
            "",
            "## Expected Output Schema",
            "",
            f"- Required fields: {required_line}",
            "",
            "## Success Criteria",
            "",
            *[f"- {item}" for item in payload.get("success_criteria") or []],
            "",
            "## Blockers",
            "",
            *blocker_lines,
            "",
            "## Truth Boundary",
            "",
            *truth_boundary_lines,
            "",
            "## Next Step",
            "",
            f"- Name: `{payload.get('next_step', {}).get('name')}`",
            f"- Description: {payload.get('next_step', {}).get('description')}",
            f"- Do not claim: {do_not_claim}",
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the P00387 ligand extraction execution contract."
    )
    parser.add_argument("--accession", default="P00387")
    parser.add_argument("--chembl", type=Path, default=DEFAULT_CHEMBL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_p00387_ligand_extraction_contract(
        accession=args.accession,
        chembl_path=args.chembl,
        output_path=args.output,
    )
    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        **payload,
    }
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "P00387 ligand extraction contract exported: "
            f"status={payload['contract_status']} hits={payload['live_signal']['target_hit_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
