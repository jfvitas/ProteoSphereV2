from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import write_json, write_text

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pdb_chain_projection_contract_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pdb_chain_projection_contract_preview.md"


def build_pdb_chain_projection_contract_preview() -> dict[str, object]:
    return {
        "artifact_id": "pdb_chain_projection_contract_preview",
        "schema_id": "proteosphere-pdb-chain-projection-contract-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "join_keys": ["structure_id", "chain_id", "mapped_uniprot_accessions"],
        "projection_targets": [
            "structure_unit_summary_library",
            "structure_chain_origin_preview",
            "structure_ligand_context_preview",
            "structure_binding_affinity_context_preview",
        ],
        "projection_rules": [
            "attach structure-chain context only through structured mapping surfaces",
            (
                "never infer accession grounding from a structure row without "
                "a chain-aware UniProt bridge"
            ),
            (
                "keep structure-derived binding and ligand context "
                "non-governing during the current download window"
            ),
        ],
        "truth_boundary": {
            "summary": "This is a report-only contract for later chain projection work.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# PDB Chain Projection Contract Preview",
        "",
        f"- Status: `{payload['status']}`",
        "",
    ]
    for rule in payload["projection_rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a report-only PDB chain projection contract preview."
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pdb_chain_projection_contract_preview()
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
