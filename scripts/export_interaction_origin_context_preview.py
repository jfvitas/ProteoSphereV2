from __future__ import annotations

import argparse
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
DEFAULT_INTACT_DIR = REPO_ROOT / "data" / "raw" / "intact"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "interaction_origin_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "interaction_origin_context_preview.md"


def _latest_snapshot_dir(root: Path) -> Path:
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    snapshots.sort(
        key=lambda path: (
            len(list(path.glob("*/*.psicquic.tab25.txt"))),
            path.name,
        )
    )
    return snapshots[-1]


def build_interaction_origin_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    intact_root: Path,
) -> dict[str, Any]:
    snapshot_dir = _latest_snapshot_dir(intact_root)
    rows = []
    for training_row in accession_rows(training_set_eligibility_matrix_preview):
        accession = training_row["accession"]
        tab_path = snapshot_dir / accession / f"{accession}.psicquic.tab25.txt"
        parsed = parse_psicquic_tab25(tab_path, accession) if tab_path.exists() else []
        physical = sum(1 for row in parsed if "physical" in row["interaction_type"].lower())
        association = sum(1 for row in parsed if "association" in row["interaction_type"].lower())
        rows.append(
            {
                "accession": accession,
                "physical_evidence_count": physical,
                "association_evidence_count": association,
                "other_evidence_count": len(parsed) - physical - association,
                "non_governing": True,
            }
        )
    return {
        "artifact_id": "interaction_origin_context_preview",
        "schema_id": "proteosphere-interaction-origin-context-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_evidence": sum(
                1
                for row in rows
                if row["physical_evidence_count"]
                + row["association_evidence_count"]
                + row["other_evidence_count"]
                > 0
            )
        },
        "truth_boundary": {
            "summary": "Interaction origin classes are descriptive only in this phase.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Interaction Origin Context Preview", ""]
    for row in payload["rows"]:
        if (
            row["physical_evidence_count"]
            or row["association_evidence_count"]
            or row["other_evidence_count"]
        ):
            lines.append(
                f"- `{row['accession']}` / physical "
                f"`{row['physical_evidence_count']}` / association "
                f"`{row['association_evidence_count']}`"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build interaction origin context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--intact-root", type=Path, default=DEFAULT_INTACT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_interaction_origin_context_preview(
        read_json(args.training_set), args.intact_root
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
