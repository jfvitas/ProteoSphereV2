from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ENTITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "entity_signature_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "entity_split_candidate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "entity_split_candidate_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _entity_bucket(row: dict[str, Any]) -> str:
    family = row["entity_family"]
    if family == "protein":
        return "protein_spine"
    if family == "protein_variant":
        return "variant_entity"
    if family == "structure_unit":
        return "structure_entity"
    return "other"


def _entity_validation_class(row: dict[str, Any]) -> str:
    family = row["entity_family"]
    readiness = row.get("family_readiness") or {}
    if family == "structure_unit":
        return (
            "structure_candidate_overlap"
            if not readiness.get("protein_variant")
            else "join_ready"
        )
    if family == "protein_variant":
        return "variant_entity"
    if family == "protein":
        return "protein_backbone"
    return "other"


def _entity_lane_depth(row: dict[str, Any]) -> int:
    family = row["entity_family"]
    readiness = row.get("family_readiness") or {}
    depth = 1
    if readiness.get("protein_variant"):
        depth += 1
    if readiness.get("structure_unit"):
        depth += 1
    if readiness.get("protein_ligand"):
        depth += 1
    if family == "structure_unit":
        depth += 1
    return depth


def build_entity_split_candidate_preview(
    entity_signature_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = entity_signature_preview.get("rows", [])
    candidate_rows: list[dict[str, Any]] = []
    split_group_sizes: dict[str, int] = {}
    family_counts: dict[str, int] = {}

    for row in rows:
        family = row["entity_family"]
        family_counts[family] = family_counts.get(family, 0) + 1
        linked_group_id = row["protein_spine_group"]
        split_group_sizes[linked_group_id] = split_group_sizes.get(linked_group_id, 0) + 1

        candidate_rows.append(
            {
                "canonical_id": row["entity_ref"],
                "entity_family": family,
                "accession": row["accession"],
                "protein_ref": row["protein_ref"],
                "leakage_key": row["exact_entity_group"],
                "linked_group_id": linked_group_id,
                "bucket": _entity_bucket(row),
                "validation_class": _entity_validation_class(row),
                "lane_depth": _entity_lane_depth(row),
                "metadata": {
                    "entity_family": family,
                    "protein_spine_group": row["protein_spine_group"],
                    "sequence_equivalence_group": row["sequence_equivalence_group"],
                    "variant_delta_group": row["variant_delta_group"],
                    "structure_chain_group": row["structure_chain_group"],
                    "structure_fold_group": row["structure_fold_group"],
                    "ligand_identity_group": row["ligand_identity_group"],
                    "binding_context_group": row["binding_context_group"],
                },
            }
        )

    largest_groups = sorted(
        (
            {"linked_group_id": key, "entity_count": value}
            for key, value in split_group_sizes.items()
        ),
        key=lambda item: (-item["entity_count"], item["linked_group_id"]),
    )[:10]

    return {
        "artifact_id": "entity_split_candidate_preview",
        "schema_id": "proteosphere-entity-split-candidate-preview-2026-04-01",
        "status": "complete",
        "row_count": len(candidate_rows),
        "candidate_rows": candidate_rows,
        "summary": {
            "entity_family_counts": family_counts,
            "linked_group_count": len(split_group_sizes),
            "largest_linked_groups": largest_groups,
            "default_atomic_unit": "entity_signature_row",
            "default_hard_group": "protein_spine_group",
        },
        "truth_boundary": {
            "summary": (
                "This surface is a split-candidate preview only. It maps entity-signature rows "
                "into future split-engine inputs using exact entity groups as leakage keys and "
                "protein spine groups as the default hard linked group."
            ),
            "ligand_rows_materialized": False,
            "ready_for_split_engine": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Entity Split Candidate Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Linked groups: `{summary['linked_group_count']}`",
        f"- Default atomic unit: `{summary['default_atomic_unit']}`",
        f"- Default hard group: `{summary['default_hard_group']}`",
        "",
        "## Families",
        "",
    ]
    for family, count in sorted(summary["entity_family_counts"].items()):
        lines.append(f"- `{family}`: `{count}`")
    lines.extend(["", "## Largest Linked Groups", ""])
    for item in summary["largest_linked_groups"]:
        lines.append(
            f"- `{item['linked_group_id']}`: `{item['entity_count']}` candidate rows"
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
        description="Export a split-candidate preview derived from entity_signature_preview."
    )
    parser.add_argument(
        "--entity-signature-preview",
        type=Path,
        default=DEFAULT_ENTITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_entity_split_candidate_preview(
        _read_json(args.entity_signature_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
