from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_preview.json"
)
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_GATE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_gate_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_validation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_similarity_signature_validation.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_ligand_similarity_signature_validation(
    ligand_similarity_signature_preview: dict[str, Any],
    ligand_similarity_signature_gate_preview: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    rows = ligand_similarity_signature_preview.get("rows", [])
    summary = ligand_similarity_signature_preview.get("summary", {})
    truth = ligand_similarity_signature_preview.get("truth_boundary", {})

    candidate_only_rows = [row for row in rows if row.get("candidate_only")]
    candidate_only_accessions = sorted({row["accession"] for row in candidate_only_rows})
    grounded_accessions = sorted(
        {row["accession"] for row in rows if not row.get("candidate_only")}
    )
    candidate_only_namespaces = sorted(
        {row["ligand_namespace"] for row in candidate_only_rows}
    )

    if ligand_similarity_signature_preview.get("row_count") != len(rows):
        issues.append("row_count does not match emitted ligand similarity rows")
    if summary.get("candidate_only_count") != len(candidate_only_rows):
        issues.append("candidate_only_count does not match candidate-only rows")
    if summary.get("accession_count") != len({row["accession"] for row in rows}):
        issues.append("accession_count does not match unique accessions in rows")
    if summary.get("exact_identity_group_count") != len(
        {row["exact_ligand_identity_group"] for row in rows}
    ):
        issues.append("exact_identity_group_count does not match emitted groups")
    if summary.get("chemical_series_group_count") != len(
        {row["chemical_series_group"] for row in rows}
    ):
        issues.append("chemical_series_group_count does not match emitted groups")
    if ligand_similarity_signature_gate_preview.get("gate_status") != "ready_for_signature_preview":
        issues.append("ligand similarity gate is not in ready_for_signature_preview state")
    if ligand_similarity_signature_gate_preview.get("ligands_materialized") is not True:
        issues.append("ligand similarity gate must confirm ligands_materialized=true")
    if truth.get("canonical_ligand_reconciliation_claimed") is not False:
        issues.append("canonical ligand reconciliation must remain false on preview surface")
    if truth.get("split_claims_changed") is not False:
        issues.append("split claims must remain unchanged on preview surface")

    for row in rows:
        if row.get("ligand_rows_materialized") is not True:
            issues.append(f"{row['signature_id']} is missing ligand_rows_materialized=true")
        if row.get("candidate_only"):
            if row.get("canonical_smiles_present") is True:
                issues.append(
                    f"{row['signature_id']} candidate-only row unexpectedly carries "
                    "canonical smiles"
                )
            if row.get("evidence_kind") != "local_structure_bridge_component":
                warnings.append(
                    f"{row['signature_id']} candidate-only row uses unexpected evidence_kind"
                )
        else:
            if row.get("ligand_namespace") != "ChEMBL":
                warnings.append(
                    f"{row['signature_id']} grounded row is outside the expected ChEMBL slice"
                )
            if row.get("canonical_smiles_present") is not True:
                issues.append(
                    f"{row['signature_id']} grounded row is missing canonical smiles support"
                )

    if candidate_only_rows:
        warnings.append(
            "candidate-only ligand similarity rows are present and must remain non-governing"
        )

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "ligand_similarity_signature_validation",
        "schema_id": "proteosphere-ligand-similarity-signature-validation-2026-04-01",
        "status": status,
        "validation": {
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "row_count": len(rows),
            "grounded_accession_count": len(grounded_accessions),
            "grounded_accessions": grounded_accessions,
            "candidate_only_accession_count": len(candidate_only_accessions),
            "candidate_only_accessions": candidate_only_accessions,
            "candidate_only_namespaces": candidate_only_namespaces,
            "policy_mode": "mixed_grounded_and_candidate_only_preview",
            "issues": issues,
            "warnings": warnings,
        },
        "truth_boundary": {
            "summary": (
                "This validation confirms the first ligand similarity signature family is "
                "internally aligned and still preview-scoped. Candidate-only rows remain "
                "non-governing and do not certify canonical ligand reconciliation or split changes."
            ),
            "report_only": True,
            "candidate_only_rows_non_governing": True,
            "canonical_ligand_reconciliation_claimed": False,
            "split_claims_changed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Ligand Similarity Signature Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Rows: `{validation['row_count']}`",
        f"- Grounded accessions: `{validation['grounded_accession_count']}`",
        f"- Candidate-only accessions: `{validation['candidate_only_accession_count']}`",
        f"- Policy mode: `{validation['policy_mode']}`",
        "",
        "## Accessions",
        "",
        f"- Grounded: `{', '.join(validation['grounded_accessions']) or 'none'}`",
        (
            "- Candidate-only: "
            f"`{', '.join(validation['candidate_only_accessions']) or 'none'}`"
        ),
    ]
    if validation["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in validation["warnings"])
    if validation["issues"]:
        lines.extend(["", "## Issues", ""])
        lines.extend(f"- {issue}" for issue in validation["issues"])
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
        description="Validate the first lightweight ligand similarity signature preview."
    )
    parser.add_argument(
        "--ligand-similarity-signature-preview",
        type=Path,
        default=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--ligand-similarity-signature-gate-preview",
        type=Path,
        default=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_GATE_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_similarity_signature_validation(
        _read_json(args.ligand_similarity_signature_preview),
        _read_json(args.ligand_similarity_signature_gate_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
