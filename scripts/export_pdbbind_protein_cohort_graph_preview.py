from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import (
        build_pdbbind_expanded_structured_corpus,
        build_pdbbind_protein_cohort_graph,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        build_pdbbind_expanded_structured_corpus,
        build_pdbbind_protein_cohort_graph,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "pdbbind_protein_cohort_graph_preview.json"
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdbbind_protein_cohort_graph_preview.md"


def render_markdown(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# PDBbind Protein Cohort Graph Preview",
        "",
        f"- Protein count: `{summary.get('protein_count')}`",
        f"- Direct PPI edge count: `{summary.get('direct_ppi_edge_count')}`",
        "- Proteins with direct PPI partners: "
        + f"`{summary.get('proteins_with_direct_ppi_partners')}`",
        f"- Proteins with cohort neighbors: `{summary.get('proteins_with_cohort_neighbors')}`",
        "- Accession-root groups (>1 member): "
        + f"`{summary.get('accession_root_multi_member_group_count')}`",
        f"- UniRef100 groups (>1 member): `{summary.get('uniref100_multi_member_group_count')}`",
        f"- UniRef90 groups (>1 member): `{summary.get('uniref90_multi_member_group_count')}`",
        f"- UniRef50 groups (>1 member): `{summary.get('uniref50_multi_member_group_count')}`",
        "",
        "## Top Accession Focus Rows",
        "",
    ]
    for row in list(payload.get("accession_focus_rows") or [])[:20]:
        lines.append(
            "- "
            + f"`{row.get('accession')}` total_neighbors=`{row.get('total_neighbor_count')}` "
            + f"ppi=`{row.get('direct_ppi_partner_count')}` "
            + f"cohort=`{row.get('cohort_neighbor_count')}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    corpus = build_pdbbind_expanded_structured_corpus()
    payload = build_pdbbind_protein_cohort_graph(corpus)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
