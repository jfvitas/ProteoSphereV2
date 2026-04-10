from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MISSING_DATA_POLICY = (
    REPO_ROOT / "artifacts" / "status" / "missing_data_policy_preview.json"
)
DEFAULT_COMPACT_ENRICHMENT_POLICY = (
    REPO_ROOT / "artifacts" / "status" / "compact_enrichment_policy_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "scrape_readiness_registry_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "scrape_readiness_registry_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_scrape_readiness_registry_preview(
    missing_data_policy: dict[str, Any],
    compact_enrichment_policy: dict[str, Any],
) -> dict[str, Any]:
    compact_summary = compact_enrichment_policy.get("summary") or {}
    rows = [
        {
            "rank": 1,
            "target_id": "motif_active_site_enrichment",
            "status": "decision_complete_waiting_on_curated_integration",
            "why_now": (
                "Motif and active-site breadth still has high scientific payoff while the "
                "current compact motif/domain family remains intentionally non-governing."
            ),
            "candidate_sources": ["PROSITE", "ELM", "InterPro complements"],
            "provenance_tags": [
                "scraped_support",
                "source_quality_tagged",
                "non_governing_until_validated",
            ],
            "default_ingest_status": "candidate_only_non_governing",
        },
        {
            "rank": 2,
            "target_id": "interaction_context_enrichment",
            "status": "decision_complete_ready_for_non_governing_materialization",
            "why_now": (
                "Interaction context enrichment is now materially executable, but STRING-"
                "derived rows must remain explicitly non-governing until separate "
                "validation and release authorization."
            ),
            "candidate_sources": [
                "BioGRID complements",
                "IntAct complements",
                "literature context",
            ],
            "provenance_tags": [
                "scraped_support",
                "curated_backfill_only",
                "non_governing_until_validated",
            ],
            "default_ingest_status": "candidate_only_non_governing",
        },
        {
            "rank": 3,
            "target_id": "kinetics_pathway_metadata_enrichment",
            "status": "decision_complete_waiting_on_curated_integration",
            "why_now": (
                "Kinetics support is bundle-safe but still compact and non-governing, so "
                "the next scrape lane should focus on explanatory metadata rather than "
                "replacing primary scientific truth."
            ),
            "candidate_sources": ["SABIO-RK complements", "pathway narrative metadata"],
            "provenance_tags": [
                "scraped_support",
                "explanatory_metadata_only",
                "non_governing_until_validated",
            ],
            "default_ingest_status": "support-only",
        },
    ]
    top_next_acquisitions = (
        missing_data_policy.get("scrape_and_enrichment_priorities", {}).get(
            "top_next_acquisitions"
        )
        or []
    )
    return {
        "artifact_id": "scrape_readiness_registry_preview",
        "schema_id": "proteosphere-scrape-readiness-registry-preview-2026-04-02",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "top_scrape_targets": [row["target_id"] for row in rows],
            "default_ingest_statuses": {
                row["target_id"]: row["default_ingest_status"] for row in rows
            },
            "bundle_safe_non_governing_families": compact_summary.get(
                "bundle_included_families", []
            ),
            "policy_seed_targets": [row.get("target") for row in top_next_acquisitions[:3]],
        },
        "truth_boundary": {
            "summary": (
                "This is a scrape-preparation registry only. It does not perform scraping, "
                "does not mutate curated families, and keeps any future scraped material "
                "non-governing until separately validated."
            ),
            "report_only": True,
            "scraping_started": True,
            "default_scraped_ingest_non_governing": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Scrape Readiness Registry Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Row count: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['rank']}` `{row['target_id']}` / `{row['status']}` / "
            f"default ingest `{row['default_ingest_status']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a report-only scrape readiness registry preview."
    )
    parser.add_argument(
        "--missing-data-policy",
        type=Path,
        default=DEFAULT_MISSING_DATA_POLICY,
    )
    parser.add_argument(
        "--compact-enrichment-policy",
        type=Path,
        default=DEFAULT_COMPACT_ENRICHMENT_POLICY,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_scrape_readiness_registry_preview(
        _read_json(args.missing_data_policy),
        _read_json(args.compact_enrichment_policy),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
