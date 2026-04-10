from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIGAND_ROW_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_similarity_signature_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_hash(parts: list[str]) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _chemical_series_group(row: dict[str, Any]) -> str:
    canonical_smiles = row.get("canonical_smiles")
    if canonical_smiles:
        return f"smiles:{_stable_hash([canonical_smiles])}"
    return row["ligand_ref"]


def build_ligand_similarity_signature_preview(
    ligand_row_preview: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    namespace_counts: dict[str, int] = {}

    for row in ligand_row_preview.get("rows", []):
        ligand_namespace = row["ligand_namespace"]
        namespace_counts[ligand_namespace] = namespace_counts.get(ligand_namespace, 0) + 1
        exact_identity_group = row["ligand_ref"]
        chemical_series_group = _chemical_series_group(row)
        rows.append(
            {
                "signature_id": f"ligand_similarity:{row['row_id']}",
                "entity_ref": row["row_id"],
                "protein_ref": row["protein_ref"],
                "accession": row["accession"],
                "ligand_ref": row["ligand_ref"],
                "ligand_namespace": ligand_namespace,
                "exact_ligand_identity_group": exact_identity_group,
                "chemical_series_group": chemical_series_group,
                "candidate_only": bool(row.get("candidate_only")),
                "evidence_kind": row["evidence_kind"],
                "canonical_smiles_present": bool(row.get("canonical_smiles")),
                "ligand_rows_materialized": True,
            }
        )

    exact_identity_group_count = len({row["exact_ligand_identity_group"] for row in rows})
    chemical_series_group_count = len({row["chemical_series_group"] for row in rows})
    candidate_only_count = sum(1 for row in rows if row["candidate_only"])

    return {
        "artifact_id": "ligand_similarity_signature_preview",
        "schema_id": "proteosphere-ligand-similarity-signature-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accession_count": len({row["accession"] for row in rows}),
            "exact_identity_group_count": exact_identity_group_count,
            "chemical_series_group_count": chemical_series_group_count,
            "candidate_only_count": candidate_only_count,
            "ligand_namespace_counts": namespace_counts,
        },
        "truth_boundary": {
            "summary": (
                "This is the first compact ligand similarity signature family derived from "
                "materialized lightweight ligand rows. It is suitable for bundle and split "
                "planning, but it does not claim cross-source canonical ligand reconciliation."
            ),
            "ready_for_bundle_preview": True,
            "ligand_rows_materialized": True,
            "canonical_ligand_reconciliation_claimed": False,
            "split_claims_changed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Ligand Similarity Signature Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Accessions: `{summary['accession_count']}`",
        f"- Exact identity groups: `{summary['exact_identity_group_count']}`",
        f"- Chemical series groups: `{summary['chemical_series_group_count']}`",
        f"- Candidate-only rows: `{summary['candidate_only_count']}`",
        "",
        "## Namespaces",
        "",
    ]
    for namespace, count in sorted(summary["ligand_namespace_counts"].items()):
        lines.append(f"- `{namespace}`: `{count}`")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact ligand similarity signature preview."
    )
    parser.add_argument(
        "--ligand-row-preview",
        type=Path,
        default=DEFAULT_LIGAND_ROW_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_similarity_signature_preview(
        _read_json(args.ligand_row_preview)
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
