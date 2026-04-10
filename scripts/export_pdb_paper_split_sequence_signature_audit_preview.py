from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import (
        build_pdb_paper_split_sequence_signature_audit,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdb_paper_split_sequence_signature_audit,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_sequence_signature_audit_preview.json"
)
OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdb_paper_split_sequence_signature_audit_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PDB Paper Split Sequence Signature Audit",
        "",
        f"- Sequence decision: `{summary.get('sequence_decision')}`",
        f"- Requested accessions: `{summary.get('requested_accession_count')}`",
        f"- Sequence present: `{summary.get('sequence_present_count')}`",
        f"- Sequence missing: `{summary.get('sequence_missing_count')}`",
        f"- Exact-sequence overlap count: `{summary.get('exact_sequence_overlap_count')}`",
        f"- Near-sequence flagged count: `{summary.get('near_sequence_flagged_count')}`",
        "",
        "## Exact Sequence Overlap",
        "",
    ]
    for row in list(payload.get("exact_sequence_overlap_rows") or [])[:20]:
        lines.append(
            "- "
            + f"`{row.get('sequence_sha256', '')[:16]}` "
            + f"train=`{','.join(row.get('train_accessions') or [])}` "
            + f"test=`{','.join(row.get('test_accessions') or [])}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    assessment_payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    payload = build_pdb_paper_split_sequence_signature_audit(assessment_payload)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
