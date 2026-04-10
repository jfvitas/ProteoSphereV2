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
DEFAULT_CANDIDATE_MAP = (
    REPO_ROOT / "artifacts" / "status" / "structure_variant_candidate_map.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "leakage_signature_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "leakage_signature_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(_read_json(path))


def _accession_from_ref(protein_ref: str) -> str:
    return protein_ref.split(":", 1)[1] if ":" in protein_ref else protein_ref


def _stable_hash(parts: list[str]) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def build_leakage_signature_preview(
    protein_library: SummaryLibrarySchema,
    variant_library: SummaryLibrarySchema,
    structure_library: SummaryLibrarySchema,
    candidate_map: dict[str, Any],
) -> dict[str, Any]:
    variant_counts: dict[str, int] = {}
    for record in variant_library.variant_records:
        variant_counts[record.protein_ref] = variant_counts.get(record.protein_ref, 0) + 1

    structure_ids_by_protein: dict[str, set[str]] = {}
    for record in structure_library.structure_unit_records:
        structure_ids_by_protein.setdefault(record.protein_ref, set()).add(record.structure_id)

    candidate_status_by_protein = {
        row["protein_ref"]: row["candidate_status"]
        for row in candidate_map.get("candidate_rows", [])
    }

    rows: list[dict[str, Any]] = []
    for record in sorted(protein_library.protein_records, key=lambda item: item.protein_ref):
        protein_ref = record.protein_ref
        accession = _accession_from_ref(protein_ref)
        structure_ids = sorted(structure_ids_by_protein.get(protein_ref, set()))
        domain_ids = sorted(
            {
                f"{item.namespace}:{item.identifier}"
                for item in record.context.domain_references
            }
        )
        pathway_ids = sorted(
            {
                f"{item.namespace}:{item.identifier}"
                for item in record.context.pathway_references
            }
        )
        motif_ids = sorted(
            {
                f"{item.namespace}:{item.identifier}"
                for item in record.context.motif_references
            }
        )
        variant_count = variant_counts.get(protein_ref, 0)
        candidate_status = candidate_status_by_protein.get(protein_ref)
        leakage_risk = (
            "candidate_overlap"
            if candidate_status == "candidate_only_no_variant_anchor"
            else "structure_followup"
            if variant_count > 0 and not structure_ids
            else "protein_only"
        )
        row = {
            "accession": accession,
            "protein_ref": protein_ref,
            "exact_accession_group": accession,
            "sequence_checksum_group": record.sequence_checksum,
            "structure_signature_group": (
                _stable_hash(structure_ids) if structure_ids else None
            ),
            "domain_signature_group": _stable_hash(domain_ids) if domain_ids else None,
            "pathway_signature_group": _stable_hash(pathway_ids) if pathway_ids else None,
            "motif_signature_group": _stable_hash(motif_ids) if motif_ids else None,
            "variant_count": variant_count,
            "structure_ids": structure_ids,
            "candidate_status": candidate_status,
            "leakage_risk_class": leakage_risk,
            "truth_note": (
                "Candidate overlap exists, but direct structure-backed variant "
                "joining is still blocked."
                if candidate_status == "candidate_only_no_variant_anchor"
                else "Variant-bearing accession without structure slice."
                if variant_count > 0 and not structure_ids
                else "Protein-only surface; no structure or variant slice in current preview."
            ),
        }
        rows.append(row)

    return {
        "artifact_id": "leakage_signature_preview",
        "schema_id": "proteosphere-leakage-signature-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "candidate_overlap_accessions": [
                row["accession"]
                for row in rows
                if row["candidate_status"] == "candidate_only_no_variant_anchor"
            ],
            "structure_followup_accessions": [
                row["accession"]
                for row in rows
                if row["leakage_risk_class"] == "structure_followup"
            ],
            "protein_only_accessions": [
                row["accession"]
                for row in rows
                if row["leakage_risk_class"] == "protein_only"
            ],
        },
        "truth_boundary": {
            "summary": (
                "This preview emits compact accession-level leakage signatures from current "
                "lightweight-library surfaces only. It does not yet materialize learned "
                "similarity clusters, ligand overlap, or full leakage groups."
            ),
            "report_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Leakage Signature Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        "",
        "## Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.extend(
            [
                f"- `{row['accession']}`",
                (
                    f"  risk `{row['leakage_risk_class']}`; variants "
                    f"`{row['variant_count']}`; structures "
                    f"`{', '.join(row['structure_ids']) if row['structure_ids'] else 'none'}`"
                ),
                f"  {row['truth_note']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a minimum viable leakage-signature preview."
    )
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--candidate-map", type=Path, default=DEFAULT_CANDIDATE_MAP)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_leakage_signature_preview(
        _read_library(args.protein_library),
        _read_library(args.variant_library),
        _read_library(args.structure_library),
        _read_json(args.candidate_map),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
