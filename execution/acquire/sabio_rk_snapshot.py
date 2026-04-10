from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pre_tail_readiness_support import read_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAINING_SET = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_SABIO_ACCESSION_SEED = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "sabio_rk" / "sabio_uniprotkb_acs.txt"
)
DEFAULT_SABIO_SEARCH_FIELDS = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "sabio_rk" / "sabio_search_fields.xml"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "sabio_rk_accession_cache_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "sabio_rk_accession_cache_preview.md"


def build_sabio_rk_accession_cache_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
    sabio_accession_seed_text: str,
    sabio_search_fields_text: str,
) -> dict[str, Any]:
    seed_accessions = {
        line.strip()
        for line in sabio_accession_seed_text.splitlines()
        if line.strip() and not line.startswith("#")
    }
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
                "seed_present": accession in seed_accessions,
                "query_scope": "accession_scoped_support_only",
                "search_fields_available": "<field" in sabio_search_fields_text,
                "modality_readiness": (
                    (row.get("modality_readiness") or {}).get("kinetics") or "absent"
                ),
                "non_governing": True,
            }
        )
    return {
        "artifact_id": "sabio_rk_accession_cache_preview",
        "schema_id": "proteosphere-sabio-rk-accession-cache-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "cohort_accession_count": len(rows),
            "supported_accession_count": sum(1 for row in rows if row["seed_present"]),
            "unsupported_accession_count": sum(1 for row in rows if not row["seed_present"]),
            "search_fields_available": "<field" in sabio_search_fields_text,
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This cache is accession-scoped and support-only. It reflects local SABIO-RK seed "
                "coverage for the current cohort and does not imply broad assay acquisition."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SABIO-RK Accession Cache Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Supported accessions: `{payload.get('summary', {}).get('supported_accession_count')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(f"- `{row['accession']}` / seed `{row['seed_present']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a query-scoped SABIO-RK accession cache.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--sabio-accession-seed", type=Path, default=DEFAULT_SABIO_ACCESSION_SEED)
    parser.add_argument("--sabio-search-fields", type=Path, default=DEFAULT_SABIO_SEARCH_FIELDS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_sabio_rk_accession_cache_preview(
        read_json(args.training_set),
        args.sabio_accession_seed.read_text(encoding="utf-8"),
        args.sabio_search_fields.read_text(encoding="utf-8"),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
