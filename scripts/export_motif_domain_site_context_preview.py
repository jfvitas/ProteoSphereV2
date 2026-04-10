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
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "motif_domain_site_context_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "motif_domain_site_context_preview.md"

DOMAIN_DATABASES = ("InterPro", "Pfam", "PROSITE", "SMART", "Gene3D", "SUPFAM")
SITE_FEATURE_TYPES = (
    "Active site",
    "Binding site",
    "DNA binding",
    "Metal binding",
    "Motif",
    "Region",
    "Site",
    "Domain",
    "Zinc finger",
    "Repeat",
    "Compositional bias",
)


def _xref_name(cross_reference: dict[str, Any]) -> str | None:
    for prop in cross_reference.get("properties") or []:
        if not isinstance(prop, dict):
            continue
        if str(prop.get("key") or "") == "EntryName":
            value = prop.get("value")
            if value:
                return str(value)
    return None


def build_motif_domain_site_context_preview(
    training_set_eligibility_matrix_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for training_row in accession_rows(training_set_eligibility_matrix_preview):
        accession = training_row["accession"]
        entry = fetch_json(f"https://rest.uniprot.org/uniprotkb/{accession}.json")
        xrefs = [
            xref
            for xref in (entry.get("uniProtKBCrossReferences") or [])
            if isinstance(xref, dict)
            and str(xref.get("database") or "").strip() in DOMAIN_DATABASES
        ]
        features = [
            feature
            for feature in (entry.get("features") or [])
            if isinstance(feature, dict)
            and str(feature.get("type") or "").strip() in SITE_FEATURE_TYPES
        ]
        xref_counts = Counter(str(xref.get("database") or "").strip() for xref in xrefs)
        feature_counts = Counter(str(feature.get("type") or "").strip() for feature in features)
        rows.append(
            {
                "accession": accession,
                "motif_domain_support_status": (
                    (training_row.get("modality_readiness") or {}).get("motif_domain") or "absent"
                ),
                "domain_database_counts": dict(xref_counts),
                "feature_type_counts": dict(feature_counts),
                "interpro_entries": [
                    {
                        "id": xref.get("id"),
                        "entry_name": _xref_name(xref),
                    }
                    for xref in xrefs
                    if xref.get("database") == "InterPro"
                ][:10],
                "pfam_ids": [
                    xref.get("id") for xref in xrefs if xref.get("database") == "Pfam"
                ][:10],
                "prosite_ids": [
                    xref.get("id") for xref in xrefs if xref.get("database") == "PROSITE"
                ][:10],
                "site_feature_total": sum(feature_counts.values()),
                "source_url": f"https://rest.uniprot.org/uniprotkb/{accession}.json",
            }
        )
    return {
        "artifact_id": "motif_domain_site_context_preview",
        "schema_id": "proteosphere-motif-domain-site-context-preview-2026-04-03",
        "status": "report_only_live_harvest",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accessions_with_interpro": sum(
                1 for row in rows if row["domain_database_counts"].get("InterPro", 0) > 0
            ),
            "accessions_with_site_features": sum(
                1 for row in rows if row["site_feature_total"] > 0
            ),
            "accessions_with_pfam": sum(
                1 for row in rows if row["domain_database_counts"].get("Pfam", 0) > 0
            ),
        },
        "truth_boundary": {
            "summary": (
                "Motif/domain/site context is a structured UniProt cross-reference and "
                "feature harvest only. It is additive and non-governing in this phase."
            ),
            "report_only": True,
            "governing": False,
            "structured_sources_only": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Motif Domain Site Context Preview", ""]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / InterPro "
            f"`{row['domain_database_counts'].get('InterPro', 0)}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build motif/domain/site context preview.")
    parser.add_argument("--training-set", type=Path, default=DEFAULT_TRAINING_SET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_motif_domain_site_context_preview(read_json(args.training_set))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
