from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "external_dataset"
OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "external_dataset_fixture_catalog_preview.json"
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "external_dataset_fixture_catalog_preview.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_fixture_catalog() -> dict[str, Any]:
    fixture_rows: list[dict[str, Any]] = []
    manifest_paths = sorted(FIXTURE_DIR.glob("*dataset_manifest.json"))
    for path in manifest_paths:
        payload = _read_json(path)
        fixture_rows.append(
            {
                "fixture_id": payload.get("manifest_id"),
                "fixture_type": payload.get("fixture_type"),
                "path": str(path).replace("\\", "/"),
                "row_count": len(payload.get("rows") or []),
                "accessions": sorted(
                    {
                        str(row.get("accession") or "").strip()
                        for row in (payload.get("rows") or [])
                        if isinstance(row, dict) and str(row.get("accession") or "").strip()
                    }
                ),
            }
        )

    return {
        "artifact_id": "external_dataset_fixture_catalog_preview",
        "schema_id": "proteosphere-external-dataset-fixture-catalog-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "fixture_count": len(fixture_rows),
            "fixture_types": [row["fixture_type"] for row in fixture_rows],
        },
        "rows": fixture_rows,
        "truth_boundary": {
            "summary": (
                "This catalog lists reusable external dataset assessment fixtures. "
                "They are test/support inputs only and do not change internal training truth."
            ),
            "report_only": True,
            "non_mutating": True,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# External Dataset Fixture Catalog Preview",
        "",
        f"- Fixture count: `{payload.get('summary', {}).get('fixture_count')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['fixture_type']}` / `{row['fixture_id']}` / `{row['row_count']}` row(s)"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = build_fixture_catalog()
    _write_json(OUTPUT_JSON, payload)
    _write_text(OUTPUT_MD, render_markdown(payload))
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
