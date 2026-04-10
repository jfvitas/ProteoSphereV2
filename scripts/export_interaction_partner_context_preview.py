from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "interaction_partner_context_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "interaction_partner_context_preview.md"


def _latest_snapshot_dir(root: Path) -> Path:
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    snapshots.sort(
        key=lambda path: (
            len(list(path.glob("*/*.psicquic.tab25.txt"))),
            path.name,
        )
    )
    return snapshots[-1]


def build_interaction_partner_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    intact_root: Path,
) -> dict[str, Any]:
    snapshot_dir = _latest_snapshot_dir(intact_root)
    rows = []
    for training_row in accession_rows(training_set_eligibility_matrix_preview):
        accession = training_row["accession"]
        tab_path = snapshot_dir / accession / f"{accession}.psicquic.tab25.txt"
        parsed = parse_psicquic_tab25(tab_path, accession) if tab_path.exists() else []
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in parsed:
            grouped[record["partner_ref"]].append(record)
        top_partners = []
        for partner_ref, records in grouped.items():
            score_values = [
                row["confidence_scores"].get("intact-miscore")
                for row in records
                if row["confidence_scores"].get("intact-miscore") is not None
            ]
            alias_counter = Counter(
                alias for row in records for alias in row.get("partner_aliases") or []
            )
            top_partners.append(
                {
                    "partner_ref": partner_ref,
                    "interaction_count": len(records),
                    "best_intact_miscore": max(score_values) if score_values else None,
                    "top_partner_alias": alias_counter.most_common(1)[0][0]
                    if alias_counter
                    else None,
                }
            )
        top_partners.sort(key=lambda row: (-row["interaction_count"], str(row["partner_ref"])))
        rows.append(
            {
                "accession": accession,
                "top_partners": top_partners[:5],
                "partner_count": len(top_partners),
            }
        )
    return {
        "artifact_id": "interaction_partner_context_preview",
        "schema_id": "proteosphere-interaction-partner-context-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {"accessions_with_partners": sum(1 for row in rows if row["partner_count"] > 0)},
        "truth_boundary": {
            "summary": "Top partner context is descriptive only in this phase.",
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Interaction Partner Context Preview", ""]
    for row in payload["rows"]:
        if row["partner_count"]:
            lines.append(f"- `{row['accession']}` / partners `{row['partner_count']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build interaction partner context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--intact-root", type=Path, default=DEFAULT_INTACT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_interaction_partner_context_preview(
        read_json(args.training_set), args.intact_root
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
