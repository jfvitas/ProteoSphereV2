from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import parse_psicquic_tab25
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import parse_psicquic_tab25
    from web_enrichment_preview_support import accession_rows, read_json, write_json, write_text

DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_INTERACTION_SIGNATURE = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_INTACT_DIR = REPO_ROOT / "data" / "raw" / "intact"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "interaction_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "interaction_context_preview.md"


def _latest_snapshot_dir(root: Path) -> Path:
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    snapshots.sort(
        key=lambda path: (
            len(list(path.glob("*/*.psicquic.tab25.txt"))),
            path.name,
        )
    )
    return snapshots[-1]


def build_interaction_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    interaction_similarity_signature_preview: dict[str, Any],
    intact_root: Path,
) -> dict[str, Any]:
    signature_by_accession = {
        str(row.get("accession") or "").strip(): row
        for row in (interaction_similarity_signature_preview.get("rows") or [])
        if isinstance(row, dict)
    }
    snapshot_dir = _latest_snapshot_dir(intact_root)
    rows = []
    for training_row in accession_rows(training_set_eligibility_matrix_preview):
        accession = training_row["accession"]
        tab_path = snapshot_dir / accession / f"{accession}.psicquic.tab25.txt"
        intact_rows = parse_psicquic_tab25(tab_path, accession) if tab_path.exists() else []
        detection_counts = Counter(row["detection_method"] for row in intact_rows)
        type_counts = Counter(row["interaction_type"] for row in intact_rows)
        partner_count = len({row["partner_ref"] for row in intact_rows})
        max_miscore = max(
            (
                row["confidence_scores"].get("intact-miscore")
                for row in intact_rows
                if row["confidence_scores"].get("intact-miscore") is not None
            ),
            default=None,
        )
        signature = signature_by_accession.get(accession) or {}
        rows.append(
            {
                "accession": accession,
                "protein_ref": training_row.get("protein_ref"),
                "intact_row_count": len(intact_rows),
                "intact_unique_partner_count": partner_count,
                "top_detection_methods": [key for key, _ in detection_counts.most_common(3)],
                "top_interaction_types": [key for key, _ in type_counts.most_common(3)],
                "max_intact_miscore": max_miscore,
                "biogrid_row_count": signature.get("biogrid_matched_row_count", 0),
                "string_disk_state": signature.get("string_disk_state", "absent"),
                "interaction_support_status": "support-only"
                if intact_rows or signature.get("biogrid_matched_row_count")
                else "absent",
            }
        )
    return {
        "artifact_id": "interaction_context_preview",
        "schema_id": "proteosphere-interaction-context-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_intact_rows": sum(1 for row in rows if row["intact_row_count"] > 0),
            "accessions_with_biogrid_rows": sum(1 for row in rows if row["biogrid_row_count"] > 0),
        },
        "truth_boundary": {
            "summary": (
                "This surface summarizes current BioGRID and IntAct interaction "
                "context only. STRING remains non-governing until the procurement "
                "tail completes."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Interaction Context Preview", ""]
    for row in payload["rows"]:
        if row["intact_row_count"] or row["biogrid_row_count"]:
            lines.append(
                f"- `{row['accession']}` / IntAct "
                f"`{row['intact_row_count']}` / BioGRID "
                f"`{row['biogrid_row_count']}`"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build interaction context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--interaction-signature", type=Path, default=DEFAULT_INTERACTION_SIGNATURE)
    parser.add_argument("--intact-root", type=Path, default=DEFAULT_INTACT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_interaction_context_preview(
        read_json(args.training_set),
        read_json(args.interaction_signature),
        args.intact_root,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
