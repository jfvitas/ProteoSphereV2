from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import build_pdb_paper_split_remediation_plan
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdb_paper_split_remediation_plan,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
QUALITY_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_dataset_quality_verdict_preview.json"
)
STRUCTURE_STATE_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_structure_state_audit_preview.json"
)
OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_remediation_plan_preview.json"
)
OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdb_paper_split_remediation_plan_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    plans = dict(payload.get("plans") or {})
    lines = [
        "# PDB Paper Split Remediation Plan",
        "",
        f"- Preferred plan: `{summary.get('preferred_plan')}`",
        f"- Blocking conflict edges: `{summary.get('blocking_edge_count')}`",
        f"- Hybrid holdout count: `{summary.get('hybrid_holdout_count')}`",
        f"- Test-only holdout count: `{summary.get('test_only_holdout_count')}`",
        f"- Train-only holdout count: `{summary.get('train_only_holdout_count')}`",
        "",
        "## Preferred Holdout Structures",
        "",
    ]
    preferred_plan = dict(plans.get(str(summary.get("preferred_plan") or "")) or {})
    rows = list(preferred_plan.get("rows") or [])
    if rows:
        for row in rows[:20]:
            lines.append(
                "- "
                + f"`{row.get('structure_id')}` split=`{row.get('split')}` "
                + f"conflicts=`{row.get('conflict_edge_count')}` "
                + f"critical=`{row.get('critical_edge_count')}`"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    assessment_payload = json.loads(ASSESSMENT_JSON.read_text(encoding="utf-8"))
    quality_payload = json.loads(QUALITY_JSON.read_text(encoding="utf-8"))
    structure_state_payload = json.loads(STRUCTURE_STATE_JSON.read_text(encoding="utf-8"))
    payload = build_pdb_paper_split_remediation_plan(
        assessment_payload,
        quality_payload,
        structure_state_payload,
    )
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
