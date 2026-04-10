from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.pdbbind_expansion_support import (
        DEFAULT_EXPANSION_STAGING_ROOT,
        DEFAULT_PDBBIND_INDEX_DIR,
        DEFAULT_SIFTS_CHAIN_UNIPROT,
        build_pdbbind_expanded_structured_corpus,
        write_expansion_stage_bundle,
    )
except ModuleNotFoundError:  # pragma: no cover
    from pdbbind_expansion_support import (  # type: ignore[no-redef]
        DEFAULT_EXPANSION_STAGING_ROOT,
        DEFAULT_PDBBIND_INDEX_DIR,
        DEFAULT_SIFTS_CHAIN_UNIPROT,
        build_pdbbind_expanded_structured_corpus,
        write_expansion_stage_bundle,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdbbind_expanded_structured_corpus_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "pdbbind_expanded_structured_corpus_preview.md"
)


def build_preview(payload: dict[str, Any], latest_bundle: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows") or []
    structure_samples = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("row_family") == "structure"
    ][:5]
    interaction_samples = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("row_family") == "interaction"
    ][:5]
    protein_samples = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("row_family") == "protein"
    ][:5]
    cohort_samples = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("row_family") == "protein_cohort"
    ][:5]
    return {
        "artifact_id": "pdbbind_expanded_structured_corpus_preview",
        "schema_id": "proteosphere-pdbbind-expanded-structured-corpus-preview-2026-04-06",
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "summary": payload.get("summary"),
        "samples": {
            "structure_rows": structure_samples,
            "interaction_rows": interaction_samples,
            "protein_rows": protein_samples,
            "protein_cohort_rows": cohort_samples,
        },
        "staging_bundle": latest_bundle,
        "truth_boundary": payload.get("truth_boundary"),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    bundle = payload.get("staging_bundle") or {}
    lines = [
        "# PDBbind Expanded Structured Corpus Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Row count: `{summary.get('row_count')}`",
        f"- Structure count: `{summary.get('structure_count')}`",
        f"- Protein count: `{summary.get('protein_count')}`",
        f"- Interaction count: `{summary.get('interaction_count')}`",
        f"- Measurement count: `{summary.get('measurement_count')}`",
        f"- Unique protein accessions: `{summary.get('unique_protein_accession_count')}`",
        f"- Mapping coverage fraction: `{summary.get('structure_mapping_coverage_fraction')}`",
        f"- Staging bundle: `{bundle.get('bundle_root')}`",
        "",
        "## Complex Classes",
        "",
    ]
    for key, value in sorted((summary.get("complex_type_counts") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Samples", ""])
    for row in payload.get("samples", {}).get("structure_rows", []):
        pdb_id = (row.get("payload") or {}).get("pdb_id")
        proteins = (row.get("payload") or {}).get("mapped_protein_accessions") or []
        lines.append(f"- Structure `{pdb_id}` -> proteins `{proteins[:6]}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the expanded local PDBbind structured corpus preview."
    )
    parser.add_argument("--pdbbind-index-dir", type=Path, default=DEFAULT_PDBBIND_INDEX_DIR)
    parser.add_argument("--sifts-chain-uniprot", type=Path, default=DEFAULT_SIFTS_CHAIN_UNIPROT)
    parser.add_argument("--staging-root", type=Path, default=DEFAULT_EXPANSION_STAGING_ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdbbind_expanded_structured_corpus(
        pdbbind_index_dir=args.pdbbind_index_dir,
        sifts_chain_uniprot_path=args.sifts_chain_uniprot,
    )
    latest_bundle = write_expansion_stage_bundle(payload, output_root=args.staging_root)
    preview = build_preview(payload, latest_bundle)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(preview, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(preview), encoding="utf-8")
    print(json.dumps(preview, indent=2))


if __name__ == "__main__":
    main()
