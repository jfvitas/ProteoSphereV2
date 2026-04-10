from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import build_pdb_paper_split_mutation_audit
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdb_paper_split_mutation_audit,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_mutation_audit_preview.json"
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdb_paper_split_mutation_audit_preview.md"


def render_markdown(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PDB Paper Split Mutation Audit",
        "",
        f"- Decision: `{summary.get('decision')}`",
        f"- Candidate pairs: `{summary.get('candidate_pair_count')}`",
        f"- Mutation-like pairs: `{summary.get('mutation_like_pair_count')}`",
        "",
        "## Example Pairs",
        "",
    ]
    for row in list(payload.get("rows") or [])[:20]:
        lines.append(
            "- "
            + f"`{row.get('train_accession')}` vs `{row.get('test_accession')}` "
            + f"relation=`{row.get('relation')}` "
            + f"edit<=12=`{row.get('bounded_edit_distance_le_12')}` "
            + f"jaccard=`{row.get('shared_kmer_jaccard')}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    assessment_payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    payload = build_pdb_paper_split_mutation_audit(assessment_payload)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
