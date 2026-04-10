from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import (
        build_pdb_paper_split_acceptance_gate,
        build_pdb_paper_split_leakage_matrix,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdb_paper_split_acceptance_gate,
        build_pdb_paper_split_leakage_matrix,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_leakage_matrix_preview.json"
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdb_paper_split_leakage_matrix_preview.md"
GATE_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_acceptance_gate_preview.json"
)


def render_markdown(payload: dict[str, object], gate_payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    gate_summary = dict(gate_payload.get("summary") or {})
    lines = [
        "# PDB Paper Split Leakage Matrix",
        "",
        f"- Decision: `{gate_summary.get('decision')}`",
        f"- Verdict: `{summary.get('verdict')}`",
        f"- Blocked categories: `{summary.get('blocked_category_count')}`",
        f"- Review categories: `{summary.get('review_category_count')}`",
        "",
        "## Categories",
        "",
    ]
    for row in list(payload.get("category_rows") or []):
        lines.append(
            "- "
            + f"`{row.get('category')}` count=`{row.get('count')}` "
            + f"severity=`{row.get('severity')}` blocking=`{row.get('blocking')}`"
        )
    lines.extend(
        [
            "",
            "## Recommended Action",
            "",
            f"- {gate_summary.get('recommended_action')}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    assessment_payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    matrix_payload = build_pdb_paper_split_leakage_matrix(assessment_payload)
    gate_payload = build_pdb_paper_split_acceptance_gate(
        assessment_payload,
        matrix_payload,
    )
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(matrix_payload, indent=2) + "\n", encoding="utf-8")
    GATE_OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    GATE_OUTPUT_JSON.write_text(json.dumps(gate_payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(
        render_markdown(matrix_payload, gate_payload),
        encoding="utf-8",
    )
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
