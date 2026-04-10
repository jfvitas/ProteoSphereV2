from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import build_pdb_paper_dataset_quality_verdict
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdb_paper_dataset_quality_verdict,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
LEAKAGE_JSON = REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_leakage_matrix_preview.json"
ACCEPTANCE_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_acceptance_gate_preview.json"
)
SEQUENCE_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "pdb_paper_split_sequence_signature_audit_preview.json"
)
MUTATION_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_mutation_audit_preview.json"
)
STRUCTURE_STATE_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_split_structure_state_audit_preview.json"
)
OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_paper_dataset_quality_verdict_preview.json"
)
OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdb_paper_dataset_quality_verdict_preview.md"
)


def render_markdown(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PDB Paper Dataset Quality Verdict",
        "",
        f"- Overall decision: `{summary.get('overall_decision')}`",
        f"- Readiness: `{summary.get('readiness')}`",
        "- Coverage: "
        + f"`{summary.get('covered_structure_count')}` / "
        + f"`{summary.get('total_structure_count')}`",
        f"- Direct protein overlaps: `{summary.get('direct_protein_overlap_count')}`",
        f"- Exact sequence overlaps: `{summary.get('exact_sequence_overlap_count')}`",
        f"- Mutation-like pairs: `{summary.get('mutation_like_pair_count')}`",
        f"- Flagged structure pairs: `{summary.get('flagged_structure_pair_count')}`",
        "",
        "## Blocking Reasons",
        "",
    ]
    blocked_reasons = list(summary.get("blocked_reasons") or [])
    if blocked_reasons:
        lines.extend(f"- `{reason}`" for reason in blocked_reasons)
    else:
        lines.append("- None")
    lines.extend(["", "## Review Reasons", ""])
    review_reasons = list(summary.get("review_reasons") or [])
    if review_reasons:
        lines.extend(f"- `{reason}`" for reason in review_reasons)
    else:
        lines.append("- None")
    lines.extend(["", f"- Recommendation: {summary.get('top_recommendation')}"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    assessment_payload = json.loads(ASSESSMENT_JSON.read_text(encoding="utf-8"))
    leakage_payload = json.loads(LEAKAGE_JSON.read_text(encoding="utf-8"))
    acceptance_payload = json.loads(ACCEPTANCE_JSON.read_text(encoding="utf-8"))
    sequence_payload = json.loads(SEQUENCE_JSON.read_text(encoding="utf-8"))
    mutation_payload = json.loads(MUTATION_JSON.read_text(encoding="utf-8"))
    structure_state_payload = json.loads(STRUCTURE_STATE_JSON.read_text(encoding="utf-8"))
    payload = build_pdb_paper_dataset_quality_verdict(
        assessment_payload,
        leakage_payload,
        acceptance_payload,
        sequence_payload,
        mutation_payload,
        structure_state_payload,
    )
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
