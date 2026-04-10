from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENTITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_signature_preview.json"
)
DEFAULT_PROTEIN_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "protein_similarity_signature_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "protein_similarity_signature_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_protein_similarity_signature_preview(
    entity_signature_preview: dict[str, Any],
    protein_library: dict[str, Any],
) -> dict[str, Any]:
    protein_rows = [
        row for row in entity_signature_preview.get("rows", []) if row["entity_family"] == "protein"
    ]
    protein_records = {
        record["protein_ref"]: record
        for record in protein_library.get("records", [])
        if record.get("record_type") == "protein"
    }

    rows: list[dict[str, Any]] = []
    for row in sorted(protein_rows, key=lambda item: item["accession"]):
        record = protein_records[row["protein_ref"]]
        context = record.get("context", {})
        domain_refs = context.get("domain_references", [])
        motif_refs = context.get("motif_references", [])
        family_label = (
            domain_refs[0]["label"]
            if domain_refs
            else record.get("protein_name")
        )
        provenance_ref = (
            context.get("provenance_pointers", [{}])[0].get("provenance_id")
            or f"summary:{record['summary_id']}"
        )
        rows.append(
            {
                "signature_id": f"protein_similarity:{row['protein_ref']}",
                "protein_ref": row["protein_ref"],
                "accession": row["accession"],
                "protein_similarity_group": row["sequence_equivalence_group"],
                "sequence_equivalence_group": row["sequence_equivalence_group"],
                "similarity_basis": "sequence_equivalence_group",
                "provenance_ref": provenance_ref,
                "family_label": family_label,
                "similarity_rank": 1,
                "notes": [
                    f"domain_ref_count:{len(domain_refs)}",
                    f"motif_ref_count:{len(motif_refs)}",
                    "derived_from:entity_signature_preview",
                ],
            }
        )

    return {
        "artifact_id": "protein_similarity_signature_preview",
        "schema_id": "proteosphere-protein-similarity-signature-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "protein_count": len(rows),
            "unique_similarity_group_count": len(
                {row["protein_similarity_group"] for row in rows}
            ),
            "family_labels": [row["family_label"] for row in rows],
        },
        "truth_boundary": {
            "summary": (
                "This is a compact protein-family similarity preview derived from the "
                "existing protein spine and sequence-equivalence grouping. It does not "
                "materialize ligand or interaction similarity."
            ),
            "ready_for_bundle_preview": True,
            "ligand_similarity_materialized": False,
            "interaction_similarity_materialized": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Protein Similarity Signature Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Proteins: `{summary['protein_count']}`",
        f"- Unique similarity groups: `{summary['unique_similarity_group_count']}`",
        "",
        "## Example Families",
        "",
    ]
    for row in payload["rows"][:10]:
        lines.append(
            f"- `{row['accession']}` -> `{row['protein_similarity_group']}` "
            f"via `{row['similarity_basis']}`"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact protein similarity signature preview."
    )
    parser.add_argument(
        "--entity-signature-preview",
        type=Path,
        default=DEFAULT_ENTITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_protein_similarity_signature_preview(
        _read_json(args.entity_signature_preview),
        _read_json(args.protein_library),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
