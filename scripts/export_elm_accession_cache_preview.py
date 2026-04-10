from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.pre_tail_readiness_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from pre_tail_readiness_support import read_json, write_json, write_text

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_ELM_CLASSES = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "elm" / "elm_classes.tsv"
)
DEFAULT_ELM_INTERACTIONS = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "elm" / "elm_interaction_domains.tsv"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "elm_accession_cache_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "elm_accession_cache_preview.md"


def build_elm_accession_cache_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    *,
    elm_classes_path: Path,
    elm_interactions_path: Path,
) -> dict[str, Any]:
    classes_present = elm_classes_path.exists()
    interactions_present = elm_interactions_path.exists()
    rows: list[dict[str, Any]] = []
    for row in training_set_eligibility_matrix_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        rows.append(
            {
                "accession": accession,
                "elm_classes_cached": classes_present,
                "elm_interaction_domains_cached": interactions_present,
                "candidate_only_non_governing": True,
                "cache_refs": [
                    str(elm_classes_path).replace("\\", "/"),
                    str(elm_interactions_path).replace("\\", "/"),
                ],
            }
        )
    return {
        "artifact_id": "elm_accession_cache_preview",
        "schema_id": "proteosphere-elm-accession-cache-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "cohort_accession_count": len(rows),
            "elm_classes_cached": classes_present,
            "elm_interaction_domains_cached": interactions_present,
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This ELM cache preview reflects accession-scoped availability of the "
                "local ELM TSV "
                "resources. Any downstream use remains candidate-only non-governing."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ELM Accession Cache Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / classes `{row['elm_classes_cached']}` / interactions "
            f"`{row['elm_interaction_domains_cached']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export an accession-scoped ELM cache preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--elm-classes", type=Path, default=DEFAULT_ELM_CLASSES)
    parser.add_argument("--elm-interactions", type=Path, default=DEFAULT_ELM_INTERACTIONS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_elm_accession_cache_preview(
        read_json(args.training_set),
        elm_classes_path=args.elm_classes,
        elm_interactions_path=args.elm_interactions,
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
