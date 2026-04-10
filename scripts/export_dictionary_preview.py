from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTEIN_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
)
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "dictionary_preview.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "dictionary_preview.md"

REFERENCE_BUCKETS = (
    "cross_references",
    "motif_references",
    "domain_references",
    "pathway_references",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_dictionary_preview(*libraries: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    reference_kind_counts: Counter[str] = Counter()
    namespace_counts: Counter[str] = Counter()

    for library in libraries:
        for record in library.get("records", []):
            summary_id = record.get("summary_id", "")
            record_type = record.get("record_type", "unknown")
            context = record.get("context", {})
            for bucket in REFERENCE_BUCKETS:
                for item in context.get(bucket, []):
                    reference_kind = str(item.get("reference_kind") or "").strip()
                    namespace = str(item.get("namespace") or "").strip()
                    identifier = str(item.get("identifier") or "").strip()
                    if not reference_kind or not namespace or not identifier:
                        continue
                    key = (reference_kind, namespace, identifier)
                    row = grouped.setdefault(
                        key,
                        {
                            "dictionary_id": (
                                f"dictionary:{reference_kind}:{namespace}:{identifier}"
                            ),
                            "reference_kind": reference_kind,
                            "namespace": namespace,
                            "identifier": identifier,
                            "label": str(item.get("label") or "").strip(),
                            "source_name": str(item.get("source_name") or "").strip(),
                            "usage_count": 0,
                            "owner_record_types": set(),
                            "supporting_summary_ids": set(),
                            "notes": set(),
                        },
                    )
                    row["usage_count"] += 1
                    row["owner_record_types"].add(record_type)
                    if summary_id:
                        row["supporting_summary_ids"].add(summary_id)
                    for note in item.get("notes", []):
                        note_text = str(note).strip()
                        if note_text:
                            row["notes"].add(note_text)

                    reference_kind_counts[reference_kind] += 1
                    namespace_counts[namespace] += 1

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        row = grouped[key]
        rows.append(
            {
                "dictionary_id": row["dictionary_id"],
                "reference_kind": row["reference_kind"],
                "namespace": row["namespace"],
                "identifier": row["identifier"],
                "label": row["label"],
                "source_name": row["source_name"],
                "usage_count": row["usage_count"],
                "supporting_record_count": len(row["supporting_summary_ids"]),
                "owner_record_types": sorted(row["owner_record_types"]),
                "supporting_summary_ids": sorted(row["supporting_summary_ids"]),
                "notes": sorted(row["notes"]),
            }
        )

    return {
        "artifact_id": "dictionary_preview",
        "schema_id": "proteosphere-dictionary-preview-2026-04-01",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "namespace_count": len(namespace_counts),
            "namespaces": [
                {"namespace": namespace, "usage_count": namespace_counts[namespace]}
                for namespace in sorted(namespace_counts)
            ],
            "reference_kind_counts": dict(sorted(reference_kind_counts.items())),
            "source_names": sorted(
                {
                    row["source_name"]
                    for row in rows
                    if row.get("source_name")
                }
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a compact dictionary surface derived from the live summary-library "
                "reference rows already present in the protein, variant, and structure slices. "
                "It is a lookup and packaging aid, not a completeness claim or a new biological "
                "acquisition family."
            ),
            "ready_for_bundle_preview": True,
            "biological_content_family": False,
            "source_fusion_required": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Dictionary Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Namespace count: `{payload['summary']['namespace_count']}`",
        "",
        "## Namespaces",
        "",
    ]
    for row in payload["summary"]["namespaces"]:
        lines.append(f"- `{row['namespace']}`: `{row['usage_count']}` uses")
    lines.extend(["", "## Example Rows", ""])
    for row in payload["rows"][:10]:
        lines.append(
            f"- `{row['namespace']}:{row['identifier']}` -> `{row['label']}` "
            f"(`{row['reference_kind']}`, uses `{row['usage_count']}`)"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a compact dictionary preview from live summary-library references."
    )
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_dictionary_preview(
        _read_json(args.protein_library),
        _read_json(args.variant_library),
        _read_json(args.structure_library),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
