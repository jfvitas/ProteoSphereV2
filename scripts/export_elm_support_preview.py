from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.pre_tail_readiness_support import read_json
except ModuleNotFoundError:  # pragma: no cover
    from pre_tail_readiness_support import read_json

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
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "elm_support_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "elm_support_preview.md"


def _read_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        filtered = [line for line in handle if line.strip() and not line.startswith("#")]
    if not filtered:
        return []
    reader = csv.DictReader(filtered, delimiter="\t")
    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({str(key).strip(): str(value or "").strip() for key, value in row.items()})
    return rows


def build_elm_support_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    *,
    elm_classes_path: Path,
    elm_interactions_path: Path,
) -> dict[str, Any]:
    cohort_rows = [
        row
        for row in training_set_eligibility_matrix_preview.get("rows") or []
        if isinstance(row, dict) and str(row.get("accession") or "").strip()
    ]
    cohort_accessions = {str(row.get("accession")).strip() for row in cohort_rows}
    classes_rows = _read_tsv_rows(elm_classes_path) if elm_classes_path.exists() else []
    interaction_rows = (
        _read_tsv_rows(elm_interactions_path) if elm_interactions_path.exists() else []
    )

    overlap_by_accession: dict[str, list[dict[str, str]]] = {
        accession: [] for accession in sorted(cohort_accessions)
    }
    for row in interaction_rows:
        accessions = {
            str(row.get("interactorElm") or "").strip(),
            str(row.get("interactorDomain") or "").strip(),
        }
        overlap = sorted(accessions & cohort_accessions)
        for accession in overlap:
            overlap_by_accession.setdefault(accession, []).append(row)

    domain_counts = Counter(
        str(row.get("Domain") or "").strip()
        for row in interaction_rows
        if row.get("Domain")
    )
    emitted_rows: list[dict[str, Any]] = []
    for cohort_row in cohort_rows:
        accession = str(cohort_row.get("accession") or "").strip()
        accession_rows = overlap_by_accession.get(accession) or []
        sample_domains = sorted(
            {
                str(row.get("Domain") or "").strip()
                for row in accession_rows
                if row.get("Domain")
            }
        )[:5]
        sample_elm_ids = sorted(
            {
                str(row.get("Elm") or "").strip()
                for row in accession_rows
                if row.get("Elm")
            }
        )[:5]
        emitted_rows.append(
            {
                "accession": accession,
                "interaction_overlap_count": len(accession_rows),
                "sample_domains": sample_domains,
                "sample_elm_ids": sample_elm_ids,
                "candidate_only_non_governing": True,
                "cache_refs": [
                    str(elm_classes_path).replace("\\", "/"),
                    str(elm_interactions_path).replace("\\", "/"),
                ],
            }
        )

    supported_accessions = [
        row["accession"] for row in emitted_rows if row["interaction_overlap_count"] > 0
    ]
    return {
        "artifact_id": "elm_support_preview",
        "schema_id": "proteosphere-elm-support-preview-2026-04-05",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "cohort_accession_count": len(emitted_rows),
            "elm_class_catalog_count": len(classes_rows),
            "elm_interaction_row_count": len(interaction_rows),
            "cohort_supported_accession_count": len(supported_accessions),
            "supported_accessions": supported_accessions,
            "top_domain_counts": dict(domain_counts.most_common(10)),
        },
        "rows": emitted_rows,
        "truth_boundary": {
            "summary": (
                "This ELM support surface is built from the local ELM TSV snapshots "
                "already on disk. "
                "It is accession-scoped, candidate-only, and non-governing."
            ),
            "report_only": True,
            "candidate_only_non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# ELM Support Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Cohort accessions: `{summary.get('cohort_accession_count')}`",
        f"- Supported accessions: `{summary.get('cohort_supported_accession_count')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / overlaps `{row['interaction_overlap_count']}` / "
            f"domains `{', '.join(row.get('sample_domains') or []) or 'none'}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the accession-scoped ELM support preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--elm-classes", type=Path, default=DEFAULT_ELM_CLASSES)
    parser.add_argument("--elm-interactions", type=Path, default=DEFAULT_ELM_INTERACTIONS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_elm_support_preview(
        read_json(args.training_set),
        elm_classes_path=args.elm_classes,
        elm_interactions_path=args.elm_interactions,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
