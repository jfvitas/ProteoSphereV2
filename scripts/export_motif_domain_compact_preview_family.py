from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "dictionary_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "motif_domain_compact_preview_family.md"
)

NAMESPACE_RULES: dict[str, str] = {
    "InterPro": "domain",
    "Pfam": "domain",
    "PROSITE": "motif",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_motif_domain_compact_preview_family(
    dictionary_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        row
        for row in dictionary_preview.get("rows", [])
        if isinstance(row, dict)
        and row.get("namespace") in NAMESPACE_RULES
        and row.get("reference_kind") == NAMESPACE_RULES[str(row.get("namespace"))]
    ]
    rows.sort(
        key=lambda row: (
            str(row.get("namespace") or ""),
            str(row.get("identifier") or ""),
        )
    )

    namespace_counter: Counter[str] = Counter()
    reference_kind_counter: Counter[str] = Counter()
    supporting_record_count = 0
    for row in rows:
        namespace = str(row.get("namespace") or "").strip()
        reference_kind = str(row.get("reference_kind") or "").strip()
        namespace_counter[namespace] += 1
        reference_kind_counter[reference_kind] += 1
        supporting_record_count += int(row.get("supporting_record_count") or 0)

    included_namespaces = [
        {
            "namespace": namespace,
            "reference_kind": NAMESPACE_RULES[namespace],
            "row_count": namespace_counter[namespace],
        }
        for namespace in sorted(namespace_counter)
    ]

    return {
        "artifact_id": "motif_domain_compact_preview_family",
        "schema_id": "proteosphere-motif-domain-compact-preview-family-2026-04-02",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "namespace_count": len(namespace_counter),
            "included_namespaces": included_namespaces,
            "reference_kind_counts": dict(sorted(reference_kind_counter.items())),
            "supporting_record_count": supporting_record_count,
        },
        "truth_boundary": {
            "summary": (
                "This is a compact motif/domain family derived from the current live "
                "dictionary and summary-library references. It is preview-safe and "
                "bundle-safe, but it remains a compact annotation layer rather than a "
                "claim of complete motif or domain coverage."
            ),
            "ready_for_bundle_preview": True,
            "biological_content_family": True,
            "preview_only": True,
            "governing_for_split_or_leakage": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Motif Domain Compact Preview Family",
        "",
        f"- Status: `{payload['status']}`",
        f"- Rows: `{payload['row_count']}`",
        f"- Namespaces: `{payload['summary']['namespace_count']}`",
        "",
        "## Included Namespaces",
        "",
    ]
    for row in payload["summary"]["included_namespaces"]:
        lines.append(
            f"- `{row['namespace']}`: `{row['row_count']}` rows as `{row['reference_kind']}`"
        )
    lines.extend(
        [
            "",
            "## Reference Kinds",
            "",
        ]
    )
    for reference_kind, count in payload["summary"]["reference_kind_counts"].items():
        lines.append(f"- `{reference_kind}`: `{count}`")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the compact motif/domain preview family."
    )
    parser.add_argument("--dictionary-preview", type=Path, default=DEFAULT_DICTIONARY_PREVIEW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_motif_domain_compact_preview_family(
        _read_json(args.dictionary_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
