from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_similarity_signature_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_similarity_signature_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_hash(parts: list[str]) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _accession_from_ref(protein_ref: str) -> str:
    return protein_ref.split(":", 1)[1] if ":" in protein_ref else protein_ref


def build_structure_similarity_signature_preview(
    structure_library: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    structure_source_counts: dict[str, int] = {}

    for record in structure_library.get("records", []):
        if record.get("record_type") != "structure_unit":
            continue
        domain_refs = record.get("context", {}).get("domain_references", [])
        domain_signature_parts = sorted(
            f"{item['namespace']}:{item['identifier']}" for item in domain_refs
        )
        fold_signature = (
            _stable_hash(domain_signature_parts)
            if domain_signature_parts
            else record["structure_id"]
        )
        span_start = record.get("residue_span_start")
        span_end = record.get("residue_span_end")
        span_signature = (
            f"{span_start}-{span_end}"
            if span_start is not None and span_end is not None
            else "unknown"
        )
        source_names = sorted(
            {
                source
                for connection in record.get("context", {}).get("source_connections", [])
                for source in connection.get("source_names", [])
            }
        )

        structure_source = record["structure_source"]
        structure_source_counts[structure_source] = (
            structure_source_counts.get(structure_source, 0) + 1
        )

        rows.append(
            {
                "entity_ref": record["summary_id"],
                "protein_ref": record["protein_ref"],
                "accession": _accession_from_ref(record["protein_ref"]),
                "structure_ref": (
                    f"{record['structure_id']}:{record['chain_id']}"
                    if record.get("chain_id")
                    else record["structure_id"]
                ),
                "structure_kind": record["structure_kind"],
                "experimental_or_predicted": record["experimental_or_predicted"],
                "fold_signature_id": fold_signature,
                "domain_signature_parts": domain_signature_parts,
                "span_signature": span_signature,
                "source_names": source_names,
                "variant_anchor_materialized": record.get("variant_ref") is not None,
            }
        )

    fold_signature_count = len({row["fold_signature_id"] for row in rows})
    candidate_only_count = sum(
        1 for row in rows if not row["variant_anchor_materialized"]
    )

    return {
        "artifact_id": "structure_similarity_signature_preview",
        "schema_id": "proteosphere-structure-similarity-signature-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "protein_count": len({row["protein_ref"] for row in rows}),
            "structure_source_counts": structure_source_counts,
            "fold_signature_count": fold_signature_count,
            "candidate_only_count": candidate_only_count,
        },
        "truth_boundary": {
            "summary": (
                "This is a compact structure-family signature preview derived from the "
                "current structure-unit summary library. It is intended for bundle and "
                "split planning, not as a claim of direct variant-structure anchoring."
            ),
            "direct_structure_backed_variant_join_materialized": False,
            "ready_for_bundle_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Structure Similarity Signature Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Proteins: `{summary['protein_count']}`",
        f"- Fold signatures: `{summary['fold_signature_count']}`",
        f"- Candidate-only rows: `{summary['candidate_only_count']}`",
        "",
        "## Structure Sources",
        "",
    ]
    for source_name, count in sorted(summary["structure_source_counts"].items()):
        lines.append(f"- `{source_name}`: `{count}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact structure similarity signature preview."
    )
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_similarity_signature_preview(
        _read_json(args.structure_library)
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
