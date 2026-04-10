from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEAKAGE_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "leakage_signature_preview.json"
)
DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_assignment_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "leakage_group_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "leakage_group_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_leakage_group_preview(
    leakage_signature_preview: dict[str, Any],
    entity_split_assignment_preview: dict[str, Any],
) -> dict[str, Any]:
    leakage_rows = {
        row["protein_ref"]: row for row in leakage_signature_preview.get("rows", [])
    }
    group_rows: list[dict[str, Any]] = []
    risk_counts: dict[str, int] = {}
    split_group_counts: dict[str, int] = {}

    for assignment_row in entity_split_assignment_preview.get("group_rows", []):
        linked_group_id = assignment_row["linked_group_id"]
        leakage_row = leakage_rows[linked_group_id]
        risk_class = leakage_row["leakage_risk_class"]
        split_name = assignment_row["split_name"]
        risk_counts[risk_class] = risk_counts.get(risk_class, 0) + 1
        split_group_counts[split_name] = split_group_counts.get(split_name, 0) + 1

        group_rows.append(
            {
                "linked_group_id": linked_group_id,
                "protein_ref": leakage_row["protein_ref"],
                "accession": leakage_row["accession"],
                "split_name": split_name,
                "entity_count": assignment_row["entity_count"],
                "entity_family_counts": assignment_row["entity_family_counts"],
                "exact_accession_group": leakage_row["exact_accession_group"],
                "sequence_checksum_group": leakage_row["sequence_checksum_group"],
                "structure_signature_group": leakage_row["structure_signature_group"],
                "domain_signature_group": leakage_row["domain_signature_group"],
                "pathway_signature_group": leakage_row["pathway_signature_group"],
                "motif_signature_group": leakage_row["motif_signature_group"],
                "candidate_status": leakage_row["candidate_status"],
                "leakage_risk_class": risk_class,
                "variant_count": leakage_row["variant_count"],
                "structure_ids": leakage_row["structure_ids"],
                "truth_note": leakage_row["truth_note"],
            }
        )

    group_rows.sort(key=lambda item: (item["split_name"], item["accession"]))

    return {
        "artifact_id": "leakage_group_preview",
        "schema_id": "proteosphere-leakage-group-preview-2026-04-01",
        "status": "complete",
        "row_count": len(group_rows),
        "rows": group_rows,
        "summary": {
            "split_group_counts": split_group_counts,
            "risk_class_counts": risk_counts,
            "candidate_overlap_accessions": sorted(
                row["accession"]
                for row in group_rows
                if row["candidate_status"] == "candidate_only_no_variant_anchor"
            ),
            "structure_followup_accessions": sorted(
                row["accession"]
                for row in group_rows
                if row["leakage_risk_class"] == "structure_followup"
            ),
            "protein_only_accessions": sorted(
                row["accession"]
                for row in group_rows
                if row["leakage_risk_class"] == "protein_only"
            ),
        },
        "truth_boundary": {
            "summary": (
                "This preview emits one leakage-group row per linked protein spine group "
                "using the live assignment and accession-level leakage surfaces. It does "
                "not yet materialize ligand overlap groups or CV fold exports."
            ),
            "ligand_overlap_materialized": False,
            "final_fold_export_committed": False,
            "ready_for_bundle_preview": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Leakage Group Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        "",
        "## Split Group Counts",
        "",
    ]
    for split_name, count in summary["split_group_counts"].items():
        lines.append(f"- `{split_name}`: `{count}`")
    lines.extend(["", "## Risk Class Counts", ""])
    for risk_class, count in summary["risk_class_counts"].items():
        lines.append(f"- `{risk_class}`: `{count}`")
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a linked-group leakage preview from current split surfaces."
    )
    parser.add_argument(
        "--leakage-signature-preview",
        type=Path,
        default=DEFAULT_LEAKAGE_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--entity-split-assignment-preview",
        type=Path,
        default=DEFAULT_ENTITY_SPLIT_ASSIGNMENT_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_leakage_group_preview(
        _read_json(args.leakage_signature_preview),
        _read_json(args.entity_split_assignment_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
