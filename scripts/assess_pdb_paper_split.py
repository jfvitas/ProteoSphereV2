from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.pdbbind_expansion_support import (
        DEFAULT_PDBBIND_INDEX_DIR,
        DEFAULT_SIFTS_CHAIN_UNIPROT,
        build_pdb_paper_split_assessment,
        build_pdbbind_expanded_structured_corpus,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        DEFAULT_PDBBIND_INDEX_DIR,
        DEFAULT_SIFTS_CHAIN_UNIPROT,
        build_pdb_paper_split_assessment,
        build_pdbbind_expanded_structured_corpus,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_pdb_split_assessment.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "paper_pdb_split_assessment.md"


def _parse_id_list(text: str) -> list[str]:
    return [token.strip().upper() for token in text.replace(",", " ").split() if token.strip()]


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    overlap = payload.get("overlap") or {}
    evidence_rows = payload.get("evidence_rows") or {}
    lines = [
        "# PDB Paper Split Assessment",
        "",
        f"- Verdict: `{summary.get('verdict')}`",
        f"- Train structures: `{summary.get('train_structure_count')}`",
        f"- Test structures: `{summary.get('test_structure_count')}`",
        f"- Covered structures: `{summary.get('covered_structure_count')}`",
        f"- Missing structures: `{summary.get('missing_structure_count')}`",
        f"- Direct protein overlap count: `{summary.get('direct_protein_overlap_count')}`",
        f"- Accession-root overlap count: `{summary.get('accession_root_overlap_count')}`",
        f"- UniRef100 overlap count: `{summary.get('uniref100_cluster_overlap_count')}`",
        f"- UniRef90 overlap count: `{summary.get('uniref90_cluster_overlap_count')}`",
        f"- UniRef50 overlap count: `{summary.get('uniref50_cluster_overlap_count')}`",
        f"- Shared partner overlap count: `{summary.get('shared_partner_overlap_count')}`",
        f"- Flagged train/test structure pairs: `{summary.get('flagged_structure_pair_count')}`",
        "",
        "## Direct Protein Overlap",
        "",
    ]
    for accession in (overlap.get("direct_protein_accession_overlap") or [])[:25]:
        lines.append(f"- `{accession}`")
    lines.extend(["", "## Flagged Structure Pairs", ""])
    for row in list(evidence_rows.get("structure_pair_overlap_rows") or [])[:20]:
        lines.append(
            "- "
            + f"`{row.get('train_structure_id')}` vs `{row.get('test_structure_id')}` "
            + f"shared_accessions=`{len(row.get('shared_accessions') or [])}` "
            + f"shared_roots=`{len(row.get('shared_accession_roots') or [])}` "
            + f"shared_u90=`{len(row.get('shared_uniref90_clusters') or [])}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assess a PDB paper split against the local "
            "PDBbind expansion corpus."
        )
    )
    parser.add_argument(
        "--train-ids",
        required=True,
        help="Whitespace or comma separated PDB IDs for the train split.",
    )
    parser.add_argument(
        "--test-ids",
        required=True,
        help="Whitespace or comma separated PDB IDs for the test split.",
    )
    parser.add_argument("--pdbbind-index-dir", type=Path, default=DEFAULT_PDBBIND_INDEX_DIR)
    parser.add_argument("--sifts-chain-uniprot", type=Path, default=DEFAULT_SIFTS_CHAIN_UNIPROT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corpus = build_pdbbind_expanded_structured_corpus(
        pdbbind_index_dir=args.pdbbind_index_dir,
        sifts_chain_uniprot_path=args.sifts_chain_uniprot,
    )
    payload = build_pdb_paper_split_assessment(
        train_ids=_parse_id_list(args.train_ids),
        test_ids=_parse_id_list(args.test_ids),
        corpus_payload=corpus,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
