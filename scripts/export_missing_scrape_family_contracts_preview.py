from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_COVERAGE_MATRIX = REPO_ROOT / "artifacts" / "status" / "source_coverage_matrix.json"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "missing_scrape_family_contracts_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "missing_scrape_family_contracts_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _as_posix(path: Path | str | None) -> str | None:
    if path is None:
        return None
    return str(path).replace("\\", "/")


def _source_row(matrix: dict[str, Any], source_name: str) -> dict[str, Any]:
    for row in matrix.get("matrix") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("source_name") or "").strip().casefold() == source_name.casefold():
            return row
    return {}


def _member_detail(row: dict[str, Any]) -> dict[str, Any]:
    facets = row.get("facets") or []
    for facet in facets:
        detail = (facet or {}).get("detail") or {}
        members = detail.get("member_details") or []
        if members:
            return dict(members[0])
    return {}


def _contract_row(
    *,
    lane_id: str,
    source_name: str,
    public_surfaces: list[str],
    raw_capture_locators: list[str],
    normalization_note: str,
    overlap_behavior: str,
    matrix: dict[str, Any],
) -> dict[str, Any]:
    source_row = _source_row(matrix, source_name)
    member = _member_detail(source_row)
    manifest_path = member.get("manifest_path")
    inventory_path = member.get("inventory_path")
    row_family = "motif_site"
    return {
        "lane_id": lane_id,
        "source_name": source_name,
        "current_state": "deferred_until_external_drive",
        "coverage_status": source_row.get("effective_status"),
        "external_drive_required": True,
        "procurement_state": "spec_pinned_waiting_for_capture",
        "local_registry_stub": {
            "manifest_path": manifest_path,
            "inventory_path": inventory_path,
            "source_locator": member.get("manifest_source_locator"),
            "snapshot_fingerprint": member.get("snapshot_fingerprint"),
        },
        "public_surfaces": public_surfaces,
        "raw_capture_locators": raw_capture_locators,
        "normalization_contract": {
            "row_family": row_family,
            "accession_anchoring_rule": "require_uniprot_accession",
            "default_governing_status": "candidate_only_non_governing",
            "support_promotion_rule": (
                "promote_to_support_only_only_after_pinned_raw_capture_"
                "and_shape_validation"
            ),
            "preserve_fields": [
                "source_native_id",
                "source_page_url",
                "source_record_id",
                "organism",
                "residue_span",
                "evidence_provenance",
            ],
            "normalization_note": normalization_note,
            "overlap_behavior": overlap_behavior,
        },
        "planned_outputs": {
            "raw_snapshot_cache": f"artifacts/status/{source_name}_raw_snapshot_preview.json",
            "registry_preview": f"artifacts/status/{source_name}_registry_preview.json",
            "normalized_support_preview": f"artifacts/status/{source_name}_support_preview.json",
            "validation_preview": f"artifacts/status/{source_name}_validation_preview.json",
        },
        "truth_boundary": {
            "report_only": True,
            "governing_use_allowed": False,
            "summary": (
                "This contract pins the missing-family intake path without claiming "
                "that a real payload has "
                "already been captured."
            ),
        },
    }


def build_missing_scrape_family_contracts_preview(matrix: dict[str, Any]) -> dict[str, Any]:
    rows = [
        _contract_row(
            lane_id="mega_motif_base_backbone",
            source_name="mega_motif_base",
            public_surfaces=[
                "https://caps.ncbs.res.in/MegaMotifbase/",
                "http://caps.ncbs.res.in/MegaMotifbase/download.html",
                "http://caps.ncbs.res.in/MegaMotifbase/search.html",
                "http://caps.ncbs.res.in/MegaMotifbase/famlist.html",
                "http://caps.ncbs.res.in/MegaMotifbase/sflist.html",
            ],
            raw_capture_locators=[
                r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\mega_motif_base\mega_motif_base_latest.json_latest",
                r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\mega_motif_base\mega_motif_base_latest.tsv_latest",
            ],
            normalization_note=(
                "Attach MegaMotifBase rows as supplemental motif-family context "
                "without coercing them into "
                "InterPro, PROSITE, Pfam, or ELM namespaces."
            ),
            overlap_behavior=(
                "Keep independent namespace and attach as additional motif "
                "references when accession/span aligns."
            ),
            matrix=matrix,
        ),
        _contract_row(
            lane_id="motivated_proteins_backbone",
            source_name="motivated_proteins",
            public_surfaces=[],
            raw_capture_locators=[
                r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\motivated_proteins\motivated_proteins_lookup_manifest_latest.json",
                r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\motivated_proteins\motivated_proteins_export_latest.json_latest",
            ],
            normalization_note=(
                "Map lookup-manifest/export rows into motif-linked protein "
                "evidence while preserving curation "
                "support and source-native identifiers."
            ),
            overlap_behavior=(
                "Keep rows separate from InterPro/PROSITE/ELM and merge only "
                "through explicit accession and span "
                "alignment with provenance carried through."
            ),
            matrix=matrix,
        ),
    ]

    return {
        "artifact_id": "missing_scrape_family_contracts_preview",
        "schema_id": "proteosphere-missing-scrape-family-contracts-preview-2026-04-06",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "missing_lane_count": len(rows),
            "contract_ready_count": len(rows),
            "deferred_until_external_drive_count": len(rows),
            "dataset_generation_mode": "v2_post_procurement_expanded",
            "lane_ids": [row["lane_id"] for row in rows],
        },
        "rows": rows,
        "truth_boundary": {
            "report_only": True,
            "release_authority": False,
            "summary": (
                "These contracts prepare the two still-missing scrape families "
                "for post-drive procurement and "
                "normalization without claiming that the families are currently implemented."
            ),
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    rows = payload.get("rows") or []
    lines = [
        "# Missing Scrape Family Contracts Preview",
        "",
        f"- Missing lane count: `{(payload.get('summary') or {}).get('missing_lane_count')}`",
        f"- Contract-ready count: `{(payload.get('summary') or {}).get('contract_ready_count')}`",
        "",
        "## Lanes",
        "",
    ]
    for row in rows:
        surfaces = row.get("public_surfaces") or row.get("raw_capture_locators") or []
        surface_text = ", ".join(f"`{item}`" for item in surfaces[:3])
        lines.append(
            f"- `{row.get('lane_id')}` -> `{row.get('procurement_state')}` via {surface_text}"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the missing scrape-family contracts preview."
    )
    parser.add_argument(
        "--source-coverage-matrix",
        type=Path,
        default=DEFAULT_SOURCE_COVERAGE_MATRIX,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_missing_scrape_family_contracts_preview(
        _read_json(args.source_coverage_matrix)
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, _render_markdown(payload))
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
