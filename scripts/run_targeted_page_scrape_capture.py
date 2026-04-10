from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.export_targeted_page_scrape_registry_preview import (
        build_targeted_page_scrape_registry_preview,
    )
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from export_targeted_page_scrape_registry_preview import (
        build_targeted_page_scrape_registry_preview,
    )
    from web_enrichment_preview_support import read_json, write_json, write_text

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
DEFAULT_RAW_ROOT = REPO_ROOT / "artifacts" / "page_scrape" / "raw"
DEFAULT_RAW_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_raw_payload_registry_preview.json"
)
DEFAULT_NORMALIZATION = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_normalization_preview.json"
)
DEFAULT_SUPPORT = (
    REPO_ROOT / "artifacts" / "status" / "targeted_page_scrape_candidate_support_preview.json"
)


def _slug(url: str) -> str:
    return (
        url.replace("https://", "")
        .replace("http://", "")
        .replace("/", "_")
        .replace(":", "_")
        .replace("?", "_")
        .replace("=", "_")
    )


def _fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ProteoSphereV2 targeted page capture/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "")
    return payload, content_type


def _normalize_uniprot_payload(payload: dict[str, Any], accession: str, url: str) -> dict[str, Any]:
    protein_description = payload.get("proteinDescription") or {}
    recommended_name = (protein_description.get("recommendedName") or {})
    full_name = (recommended_name.get("fullName") or {})
    protein = full_name.get("value") or ""
    gene_names = [
        str((gene.get("geneName") or {}).get("value") or "").strip()
        for gene in (payload.get("genes") or [])
        if isinstance(gene, dict)
    ]
    feature_count = len(
        [feature for feature in (payload.get("features") or []) if isinstance(feature, dict)]
    )
    keyword_count = len([kw for kw in (payload.get("keywords") or []) if isinstance(kw, dict)])
    return {
        "accession": accession,
        "source_url": url,
        "source_kind": "uniprot_rest_json",
        "protein_name": protein,
        "gene_names": [name for name in gene_names if name],
        "feature_count": feature_count,
        "keyword_count": keyword_count,
        "candidate_only_non_governing": True,
    }


def run_targeted_page_scrape_capture(
    targeted_page_scrape_registry: dict[str, Any],
    *,
    raw_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw_root.mkdir(parents=True, exist_ok=True)
    registry_rows = targeted_page_scrape_registry.get("rows") or []
    raw_rows: list[dict[str, Any]] = []
    normalization_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []

    for row in registry_rows:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        accession_dir = raw_root / accession
        accession_dir.mkdir(parents=True, exist_ok=True)
        support_refs: list[str] = []
        normalized_fact_refs: list[str] = []
        for url in row.get("candidate_pages") or []:
            url_text = str(url or "").strip()
            if not url_text:
                continue
            try:
                payload, content_type = _fetch(url_text)
            except Exception as exc:  # pragma: no cover - network variability
                raw_rows.append(
                    {
                        "accession": accession,
                        "source_url": url_text,
                        "content_type": "fetch_error",
                        "payload_path": None,
                        "payload_size_bytes": 0,
                        "fetch_error": str(exc),
                    }
                )
                continue
            suffix = ".json" if "json" in content_type or url_text.endswith(".json") else ".html"
            payload_path = accession_dir / f"{_slug(url_text)}{suffix}"
            if suffix == ".json":
                payload_path.write_text(
                    json.dumps(json.loads(payload.decode("utf-8")), indent=2) + "\n",
                    encoding="utf-8",
                )
            else:
                payload_path.write_bytes(payload)
            support_refs.append(str(payload_path).replace("\\", "/"))
            raw_rows.append(
                {
                    "accession": accession,
                    "source_url": url_text,
                    "content_type": content_type,
                    "payload_path": str(payload_path).replace("\\", "/"),
                    "payload_size_bytes": payload_path.stat().st_size,
                }
            )
            if "rest.uniprot.org" in url_text and suffix == ".json":
                normalized = _normalize_uniprot_payload(
                    json.loads(payload.decode("utf-8")),
                    accession,
                    url_text,
                )
                normalization_rows.append(normalized)
                normalized_fact_refs.append("uniprot_rest_json")

        support_rows.append(
            {
                "accession": accession,
                "candidate_page_count": len(support_refs),
                "payload_refs": support_refs,
                "normalized_fact_refs": normalized_fact_refs,
                "candidate_only_non_governing": True,
            }
        )

    raw_registry = {
        "artifact_id": "targeted_page_scrape_raw_payload_registry_preview",
        "schema_id": "proteosphere-targeted-page-scrape-raw-payload-registry-preview-2026-04-04",
        "status": "report_only_live_capture",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {"payload_count": len(raw_rows), "accession_count": len(support_rows)},
        "rows": raw_rows,
        "truth_boundary": {"report_only": True, "non_governing": True},
    }
    normalization_preview = {
        "artifact_id": "targeted_page_scrape_normalization_preview",
        "schema_id": "proteosphere-targeted-page-scrape-normalization-preview-2026-04-04",
        "status": "report_only_live_capture",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {"normalized_row_count": len(normalization_rows)},
        "rows": normalization_rows,
        "truth_boundary": {"report_only": True, "candidate_only_non_governing": True},
    }
    support_preview = {
        "artifact_id": "targeted_page_scrape_candidate_support_preview",
        "schema_id": "proteosphere-targeted-page-scrape-candidate-support-preview-2026-04-04",
        "status": "report_only_live_capture",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {"accession_count": len(support_rows)},
        "rows": support_rows,
        "truth_boundary": {"report_only": True, "candidate_only_non_governing": True},
    }
    return raw_registry, normalization_preview, support_preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture targeted candidate-only page payloads for the current accession set."
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--raw-registry-output", type=Path, default=DEFAULT_RAW_REGISTRY)
    parser.add_argument("--normalization-output", type=Path, default=DEFAULT_NORMALIZATION)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    registry = (
        read_json(args.registry)
        if args.registry.exists()
        else build_targeted_page_scrape_registry_preview()
    )
    raw_registry, normalization_preview, support_preview = run_targeted_page_scrape_capture(
        registry,
        raw_root=args.raw_root,
    )
    write_json(args.raw_registry_output, raw_registry)
    write_json(args.normalization_output, normalization_preview)
    write_json(args.support_output, support_preview)
    write_text(
        args.support_output.with_suffix(".md"),
        "# Targeted Page Scrape Candidate Support Preview\n",
    )
    print(args.support_output)


if __name__ == "__main__":
    main()
