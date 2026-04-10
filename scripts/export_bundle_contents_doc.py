from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
DEFAULT_CONTRACT = REPO_ROOT / "artifacts" / "status" / "p56_bundle_contents_contract.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "reports" / "proteosphere-lite.contents.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _section(title: str, lines: list[str]) -> list[str]:
    return [f"## {title}", "", *lines, ""]


def _rendered_wording_constraints(
    manifest: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    included_families = {
        item["family_name"]
        for item in manifest.get("table_families", [])
        if item.get("included") and item.get("record_count", 0) > 0
    }
    rendered: list[str] = []
    for item in contract.get("bundle_contents_doc", {}).get("wording_constraints", []):
        normalized = item.lower()
        if (
            "protein_variants" in normalized
            and "not yet populated" in normalized
            and "protein_variants" in included_families
        ):
            continue
        rendered.append(item)
    return rendered


def render_bundle_contents_doc(
    manifest: dict[str, Any],
    contract: dict[str, Any],
) -> str:
    included = [item for item in manifest.get("table_families", []) if item.get("included")]
    declared_empty = [
        item for item in manifest.get("table_families", []) if not item.get("included")
    ]
    lines: list[str] = ["# ProteoSphere Lite Bundle Contents", ""]
    lines.extend(
        _section(
            "Bundle Identity",
            [
                f"- Bundle ID: `{manifest['bundle_id']}`",
                f"- Bundle kind: `{manifest['bundle_kind']}`",
                f"- Bundle version: `{manifest['bundle_version']}`",
                f"- Release ID: `{manifest['release_id']}`",
                f"- Packaging layout: `{manifest['packaging_layout']}`",
                f"- Manifest status: `{manifest['manifest_status']}`",
                f"- Validation status: `{manifest['validation_status']}`",
            ],
        )
    )
    lines.extend(
        _section(
            "Release Assets",
            [
                *[
                    (
                        f"- `{item['filename']}`"
                        f" ({item['role']}, size `{item['size_bytes']}` bytes, "
                        f"required `{item['required']}`)"
                    )
                    for item in manifest.get("artifact_files", [])
                ]
            ],
        )
    )
    lines.extend(
        _section(
            "Included Surfaces",
            [
                *[
                    f"- `{item['family_name']}`: `{item['record_count']}` records"
                    for item in included
                ],
                "- Record counts are current live counts, not completeness claims.",
            ],
        )
    )
    lines.extend(
        _section(
            "Declared Empty Surfaces",
            [
                *[
                    (
                        f"- `{item['family_name']}`: declared in schema, "
                        "currently `0` materialized records"
                    )
                    for item in declared_empty
                ]
            ],
        )
    )
    coverage = manifest.get("source_coverage_summary", {})
    lines.extend(
        _section(
            "Source Truth And Gating",
            [
                f"- Source count: `{coverage.get('source_count')}`",
                f"- Present sources: `{coverage.get('present_source_count')}`",
                f"- Partial sources: `{coverage.get('partial_source_count')}`",
                f"- Missing sources: `{coverage.get('missing_source_count')}`",
                (
                    "- Procurement priorities: "
                    f"`{', '.join(coverage.get('procurement_priority_sources', []))}`"
                ),
                "- ELM remains conditional and is not scrape-first.",
                "- `mega_motif_base` and `motivated_proteins` remain outside the live bundle.",
            ],
        )
    )
    lines.extend(
        _section(
            "Excluded Payload Families",
            [f"- `{item}`" for item in manifest.get("exclusions", [])],
        )
    )
    lines.extend(
        _section(
            "Truth Boundaries",
            [
                "- This document is generated from the live bundle manifest, not hand-maintained.",
                (
                    "- Structures currently come from the structure-unit "
                    "feature-cache slice, not coordinate-heavy payloads."
                ),
                (
                    "- Variant, structure, motif, pathway, and provenance "
                    "counts reflect current emitted slices only."
                ),
                (
                    "- Dictionaries are compact lookup rows derived from live "
                    "reference entries; they are not a new biological content family."
                ),
                *[f"- {item}" for item in _rendered_wording_constraints(manifest, contract)],
            ],
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a human-readable lightweight bundle contents document."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = _read_json(args.manifest)
    contract = _read_json(args.contract)
    content = render_bundle_contents_doc(manifest, contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
