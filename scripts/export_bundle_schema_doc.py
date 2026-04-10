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
DEFAULT_OUTLINE = REPO_ROOT / "artifacts" / "status" / "p56_bundle_schema_doc_outline.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "reports" / "proteosphere-lite.schema.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_bundle_schema_doc(
    manifest: dict[str, Any],
    outline: dict[str, Any],
) -> str:
    lines: list[str] = [
        "# ProteoSphere Lite Bundle Schema",
        "",
        "## Bundle Overview",
        "",
        f"- Bundle ID: `{manifest['bundle_id']}`",
        f"- Bundle kind: `{manifest['bundle_kind']}`",
        f"- Schema version: `{manifest['schema_version']}`",
        f"- Packaging layout: `{manifest['packaging_layout']}`",
        f"- Content scope: `{manifest['content_scope']}`",
        f"- Build state: `{manifest['manifest_status']}`",
        "",
        "## Included Assets",
        "",
    ]
    lines.extend(
        [
            f"- `{item['filename']}`: role `{item['role']}`, required `{item['required']}`"
            for item in manifest.get("artifact_files", [])
        ]
    )
    lines.extend(
        [
            "",
            "## Schema Conventions",
            "",
            "- IDs are namespace-scoped, compact string keys such as `protein:P04637`.",
            (
                "- Nested reference arrays carry lineage and source context "
                "instead of flattening all joins into separate tables in this preview."
            ),
            "- Null or zero-count reserved families are declared explicitly rather than omitted.",
            "- Provenance pointers and source snapshot IDs remain first-class schema elements.",
            "",
            "## Current Live Table Families",
            "",
        ]
    )
    for family in manifest.get("table_families", []):
        status = "included" if family.get("included") else "reserved"
        lines.append(
            f"- `{family['family_name']}`: `{status}`, `{family['record_count']}` records"
        )
    lines.extend(
        [
            "",
            "## Family Notes",
            "",
            "### Proteins Family",
            "",
            "- Primary keys: `summary_id`, `protein_ref`",
            (
                "- Carries identity, sequence, classification, pathway, "
                "provenance, and source-rollup context."
            ),
            "- Example anchor: `protein:P00387`.",
            "",
            "### Protein Variants Family",
            "",
            "- Primary keys: `summary_id`, `protein_ref`, `variant_signature`",
            (
                "- Current slice uses compact mutation/isoform signatures and "
                "keeps construct lineage deferred when unsupported."
            ),
            "- Included now only where materialized by the live variant summary library.",
            "",
            "### Structures Family",
            "",
            "- Current representation is structure-unit oriented, not full coordinate payloads.",
            "- Keys include `protein_ref`, `structure_id`, and `chain_id`.",
            "- Intended for leakage/similarity planning rather than heavy structure hydration.",
            "",
            "### Motif, Pathway, And Provenance Families",
            "",
            (
                "- These are still compact preview families derived from "
                "current live library surfaces."
            ),
            (
                "- Motif/domain annotations remain logically distinct but are "
                "budgeted together in the current bundle manifest."
            ),
            (
                "- Provenance records preserve source lineage and should not "
                "be treated as completeness claims."
            ),
            "",
            "### Dictionaries Family",
            "",
            (
                "- This family is a compact lookup layer built from unique live "
                "reference entries across motif, domain, pathway, and cross-reference rows."
            ),
            (
                "- It is packaging-oriented and helps future consumers resolve "
                "stable namespace/identifier labels without shipping heavy source payloads."
            ),
            "- It should not be treated as a new biological acquisition family.",
            "",
            "## Reserved Families",
            "",
        ]
    )
    reserved = [item for item in manifest.get("table_families", []) if not item.get("included")]
    lines.extend([f"- `{item['family_name']}`" for item in reserved])
    lines.extend(
        [
            "",
            "## Source Lineage And Trust Notes",
            "",
            *[
                f"- `{item['source_name']}` -> `{item['snapshot_id']}`"
                for item in manifest.get("source_snapshot_ids", [])
            ],
            "",
            "## Exclusions",
            "",
            *[f"- `{item}`" for item in manifest.get("exclusions", [])],
            "",
            "## Schema Evolution Notes",
            "",
            (
                "- This schema doc is generated from the live bundle manifest "
                "and should evolve with emitted families."
            ),
            "- Reserved families stay reserved until they have real materialized surfaces.",
            (
                "- The current default layout remains `compressed_sqlite`; "
                "future partitioning is a growth path, not current truth."
            ),
            "",
            "## Basis",
            "",
            *[
                f"- `{key}`: `{value}`"
                for key, value in outline.get("basis", {}).items()
            ],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a schema-oriented markdown doc for the current lightweight bundle."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--outline", type=Path, default=DEFAULT_OUTLINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = _read_json(args.manifest)
    outline = _read_json(args.outline)
    content = render_bundle_schema_doc(manifest, outline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
