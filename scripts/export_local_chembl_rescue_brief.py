from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_chembl_rescue import build_local_chembl_rescue_brief  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHEMBL_PATH = Path(
    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "local_chembl_rescue_brief.json"
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "local_chembl_rescue_brief.md"
DEFAULT_ACCESSION = "P00387"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}
    planning_input = (
        payload.get("packet_planning_input")
        if isinstance(payload.get("packet_planning_input"), dict)
        else {}
    )
    hit_rows = evidence.get("target_hits") or []
    hit_lines = []
    for hit in hit_rows[:5]:
        if not isinstance(hit, dict):
            continue
        hit_lines.append(
            f"- `{hit.get('accession')}` -> `{hit.get('chembl_id')}` "
            f"(`{hit.get('pref_name')}`), activities={hit.get('activity_count')}"
        )
    if not hit_lines:
        hit_lines.append("- none")

    return "\n".join(
        [
            "# Local ChEMBL Rescue Brief",
            "",
            f"- Generated at: `{payload.get('generated_at')}`",
            f"- Accession: `{payload.get('accession')}`",
            f"- Packet source ref: `{payload.get('packet_source_ref')}`",
            f"- Status: `{payload.get('status')}`",
            "- Wiring: planning-only, not canonical resolution",
            "",
            "## Evidence",
            "",
            f"- Source file: `{evidence.get('source_file')}`",
            f"- Source tables: `{evidence.get('source_tables')}`",
            f"- Source columns: `{evidence.get('source_columns')}`",
            "",
            "## Hits",
            "",
            *hit_lines,
            "",
            "## Recommendation",
            "",
            f"- Next action: `{payload.get('packet_recommendation', {}).get('next_action')}`",
            (
                "- Expected effect: "
                f"`{payload.get('packet_recommendation', {}).get('expected_effect')}`"
            ),
            (
                "- Extraction readiness: "
                f"`{planning_input.get('extraction_readiness', {}).get('state')}`"
            ),
            (
                "- Assay / activity counts: "
                f"`{planning_input.get('assay_count')}` / "
                f"`{planning_input.get('activity_count')}`"
            ),
            f"- Blockers: `{planning_input.get('blockers')}`",
            "",
            (
                "- Planning note: "
                f"{payload.get('planning_note')}"
            ),
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a planning-only local ChEMBL rescue brief."
    )
    parser.add_argument("--accession", default=DEFAULT_ACCESSION)
    parser.add_argument("--chembl", type=Path, default=DEFAULT_CHEMBL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_chembl_rescue_brief(
        accession=args.accession,
        chembl_path=args.chembl,
    )
    payload = {
        "report_type": "local_chembl_rescue_brief",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        **payload,
    }
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local ChEMBL rescue brief exported: "
            f"accession={payload['accession']} status={payload['status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
