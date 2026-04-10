from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        read_json,
        write_json,
        write_text,
    )
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import (
        accession_rows,
        fetch_json,
        read_json,
        write_json,
        write_text,
    )

DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "protein_feature_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "protein_feature_context_preview.md"


def build_protein_feature_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for row in accession_rows(training_set_eligibility_matrix_preview):
        accession = row["accession"]
        entry = fetch_json(f"https://rest.uniprot.org/uniprotkb/{accession}.json")
        features = [
            feature for feature in (entry.get("features") or []) if isinstance(feature, dict)
        ]
        feature_counts = Counter(str(feature.get("type") or "").strip() for feature in features)
        rows.append(
            {
                "accession": accession,
                "feature_count": len(features),
                "feature_type_counts": dict(feature_counts),
                "has_transmembrane_feature": feature_counts.get("Transmembrane", 0) > 0,
                "has_disulfide_feature": feature_counts.get("Disulfide bond", 0) > 0,
                "has_modified_residue_feature": feature_counts.get("Modified residue", 0) > 0,
                "source_url": f"https://rest.uniprot.org/uniprotkb/{accession}.json",
            }
        )
    return {
        "artifact_id": "protein_feature_context_preview",
        "schema_id": "proteosphere-protein-feature-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {"accessions_with_features": sum(1 for row in rows if row["feature_count"] > 0)},
        "truth_boundary": {
            "summary": "Protein feature context is a structured UniProt feature harvest only.",
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Protein Feature Context Preview", ""]
    for row in payload["rows"][:10]:
        lines.append(f"- `{row['accession']}` / features `{row['feature_count']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build protein feature context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_protein_feature_context_preview(read_json(args.training_set))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
