from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.library.summary_record import SummaryLibrarySchema  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTEIN_LIBRARY = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "entity_signature_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "entity_signature_preview.md"
)


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _stable_hash(parts: list[str]) -> str:
    if not parts:
        return ""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _accession_from_ref(protein_ref: str) -> str:
    return protein_ref.split(":", 1)[1] if ":" in protein_ref else protein_ref


def build_entity_signature_preview(
    protein_library: SummaryLibrarySchema,
    variant_library: SummaryLibrarySchema,
    structure_library: SummaryLibrarySchema,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    for record in sorted(protein_library.protein_records, key=lambda item: item.summary_id):
        rows.append(
            {
                "entity_ref": record.summary_id,
                "entity_family": "protein",
                "accession": _accession_from_ref(record.protein_ref),
                "protein_ref": record.protein_ref,
                "exact_entity_group": record.summary_id,
                "protein_spine_group": record.protein_ref,
                "sequence_equivalence_group": record.sequence_checksum,
                "variant_delta_group": None,
                "structure_chain_group": None,
                "structure_fold_group": None,
                "ligand_identity_group": None,
                "binding_context_group": None,
                "family_readiness": {
                    "protein": True,
                    "protein_variant": False,
                    "structure_unit": False,
                    "protein_ligand": False,
                },
            }
        )

    for record in sorted(variant_library.variant_records, key=lambda item: item.summary_id):
        rows.append(
            {
                "entity_ref": record.summary_id,
                "entity_family": "protein_variant",
                "accession": _accession_from_ref(record.protein_ref),
                "protein_ref": record.protein_ref,
                "exact_entity_group": record.summary_id,
                "protein_spine_group": record.protein_ref,
                "sequence_equivalence_group": record.protein_ref,
                "variant_delta_group": record.sequence_delta_signature or record.variant_signature,
                "structure_chain_group": None,
                "structure_fold_group": None,
                "ligand_identity_group": None,
                "binding_context_group": None,
                "family_readiness": {
                    "protein": True,
                    "protein_variant": True,
                    "structure_unit": False,
                    "protein_ligand": False,
                },
            }
        )

    for record in sorted(
        structure_library.structure_unit_records,
        key=lambda item: item.summary_id,
    ):
        domain_ids = [
            f"{reference.namespace}:{reference.identifier}"
            for reference in record.context.domain_references
        ]
        rows.append(
            {
                "entity_ref": record.summary_id,
                "entity_family": "structure_unit",
                "accession": _accession_from_ref(record.protein_ref),
                "protein_ref": record.protein_ref,
                "exact_entity_group": record.summary_id,
                "protein_spine_group": record.protein_ref,
                "sequence_equivalence_group": record.protein_ref,
                "variant_delta_group": record.variant_ref,
                "structure_chain_group": (
                    f"{record.structure_id}:{record.chain_id}"
                    if record.chain_id
                    else record.structure_id
                ),
                "structure_fold_group": _stable_hash(sorted(domain_ids)) or record.structure_id,
                "ligand_identity_group": None,
                "binding_context_group": None,
                "family_readiness": {
                    "protein": True,
                    "protein_variant": record.variant_ref is not None,
                    "structure_unit": True,
                    "protein_ligand": False,
                },
            }
        )

    family_counts: dict[str, int] = {}
    for row in rows:
        family = row["entity_family"]
        family_counts[family] = family_counts.get(family, 0) + 1

    return {
        "artifact_id": "entity_signature_preview",
        "schema_id": "proteosphere-entity-signature-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "entity_family_counts": family_counts,
            "protein_spine_count": len({row["protein_spine_group"] for row in rows}),
            "structure_chain_group_count": len(
                {row["structure_chain_group"] for row in rows if row["structure_chain_group"]}
            ),
            "variant_delta_group_count": len(
                {row["variant_delta_group"] for row in rows if row["variant_delta_group"]}
            ),
            "ligand_identity_group_count": 0,
            "binding_context_group_count": 0,
        },
        "truth_boundary": {
            "summary": (
                "This preview emits compact cross-entity signatures for currently materialized "
                "protein, protein-variant, and structure-unit families only. Ligand identity "
                "and binding context groups remain reserved but unmaterialized."
            ),
            "ligand_groups_materialized": False,
            "direct_structure_backed_variant_join_materialized": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    family_counts = summary["entity_family_counts"]
    lines = [
        "# Entity Signature Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Protein rows: `{family_counts.get('protein', 0)}`",
        f"- Protein-variant rows: `{family_counts.get('protein_variant', 0)}`",
        f"- Structure-unit rows: `{family_counts.get('structure_unit', 0)}`",
        "",
        "## Summary",
        "",
        f"- Protein spine groups: `{summary['protein_spine_count']}`",
        f"- Variant delta groups: `{summary['variant_delta_group_count']}`",
        f"- Structure chain groups: `{summary['structure_chain_group_count']}`",
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact cross-entity signature preview."
    )
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_entity_signature_preview(
        _read_library(args.protein_library),
        _read_library(args.variant_library),
        _read_library(args.structure_library),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
