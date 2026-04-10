from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import (
        build_pdb_paper_split_structure_state_audit,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdb_paper_split_structure_state_audit,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
LATEST_PDBBIND_EXPANDED = (
    REPO_ROOT
    / "data"
    / "reports"
    / "expansion_staging"
    / "v2_post_procurement_expanded"
    / "LATEST_PDBBIND_EXPANDED.json"
)
CORPUS_PREVIEW_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdbbind_expanded_structured_corpus_preview.json"
)
OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_structure_state_audit_preview.json"
)
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdb_paper_split_structure_state_audit_preview.md"


def resolve_corpus_json() -> Path:
    if LATEST_PDBBIND_EXPANDED.exists():
        latest_payload = json.loads(LATEST_PDBBIND_EXPANDED.read_text(encoding="utf-8"))
        corpus_path = Path(str(latest_payload.get("corpus_path") or "").strip())
        if corpus_path.exists():
            return corpus_path
    return CORPUS_PREVIEW_JSON


def render_markdown(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PDB Paper Split Structure State Audit",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Flagged pairs: `{summary.get('flagged_pair_count')}`",
        "",
        "## Example Pair Classifications",
        "",
    ]
    for row in list(payload.get("rows") or [])[:20]:
        lines.append(
            "- "
            + f"`{row.get('train_structure_id')}` vs `{row.get('test_structure_id')}` "
            + f"relation=`{row.get('relation')}` risk=`{row.get('risk_level')}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    assessment_payload = json.loads(ASSESSMENT_JSON.read_text(encoding="utf-8"))
    corpus_payload = json.loads(resolve_corpus_json().read_text(encoding="utf-8"))
    payload = build_pdb_paper_split_structure_state_audit(
        assessment_payload,
        corpus_payload,
    )
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
