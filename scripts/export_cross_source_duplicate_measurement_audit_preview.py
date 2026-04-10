from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_BINDING_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "cross_source_duplicate_measurement_audit_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "cross_source_duplicate_measurement_audit_preview.md"
)


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _measurement_signature(row: dict[str, Any]) -> dict[str, Any]:
    accession = (
        _clean(row.get("accession"))
        or _clean(row.get("target_accession"))
        or _clean(row.get("uniprot_accession"))
    )
    structure_id = _clean(row.get("pdb_id")) or _clean(row.get("structure_id"))
    reference = accession or structure_id or _clean(row.get("source_record_id")) or "unresolved"
    raw_value = row.get("raw_value")
    if isinstance(raw_value, float):
        raw_value = round(raw_value, 8)
    return {
        "reference": reference,
        "reference_type": "accession" if accession else "structure_or_record",
        "complex_type": _clean(row.get("complex_type")) or "unknown",
        "measurement_type": _clean(row.get("measurement_type")) or "unknown",
        "relation": _clean(row.get("relation")) or "unknown",
        "raw_value": raw_value,
        "raw_unit": _clean(row.get("raw_unit")) or "unknown",
        "raw_affinity_string": _clean(row.get("raw_binding_string")) or None,
    }


def build_cross_source_duplicate_measurement_audit_preview(
    binding_registry: dict[str, Any],
) -> dict[str, Any]:
    rows = [dict(row) for row in (binding_registry.get("rows") or []) if isinstance(row, dict)]
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        signature = _measurement_signature(row)
        key = (
            signature["reference"],
            signature["complex_type"],
            signature["measurement_type"],
            signature["relation"],
            signature["raw_value"],
            signature["raw_unit"],
        )
        grouped[key].append(row)

    groups: list[dict[str, Any]] = []
    source_pair_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for key, group_rows in grouped.items():
        if len(group_rows) < 2:
            continue
        distinct_sources = sorted(
            {
                _clean(row.get("measurement_origin"))
                or _clean(row.get("source_name"))
                or "unknown"
                for row in group_rows
            }
        )
        if len(distinct_sources) < 2:
            continue
        signature = _measurement_signature(group_rows[0])
        for source in distinct_sources:
            source_counts[source] += 1
        pair_key = " + ".join(distinct_sources)
        source_pair_counts[pair_key] += 1
        groups.append(
            {
                "duplicate_key": "|".join(str(part) for part in key),
                "reference": signature["reference"],
                "reference_type": signature["reference_type"],
                "complex_type": signature["complex_type"],
                "measurement_type": signature["measurement_type"],
                "relation": signature["relation"],
                "raw_value": signature["raw_value"],
                "raw_unit": signature["raw_unit"],
                "row_count": len(group_rows),
                "distinct_source_count": len(distinct_sources),
                "distinct_sources": distinct_sources,
                "raw_affinity_examples": sorted(
                    {
                        _clean(row.get("raw_binding_string"))
                        or (
                            f"{signature['measurement_type']}"
                            f"{signature['relation']}"
                            f"{signature['raw_value']}"
                            f"{signature['raw_unit']}"
                        )
                        for row in group_rows
                    }
                ),
                "measurement_ids": sorted(
                    {
                        _clean(row.get("measurement_id"))
                        or _clean(row.get("source_record_id"))
                        or "unknown"
                        for row in group_rows
                    }
                )[:20],
            }
        )

    groups.sort(
        key=lambda item: (
            -int(item.get("distinct_source_count") or 0),
            -int(item.get("row_count") or 0),
            str(item.get("reference") or ""),
            str(item.get("measurement_type") or ""),
        )
    )

    return {
        "artifact_id": "cross_source_duplicate_measurement_audit_preview",
        "schema_id": "proteosphere-cross-source-duplicate-measurement-audit-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "registry_row_count": len(rows),
            "cross_source_duplicate_group_count": len(groups),
            "top_source_pair_counts": dict(sorted(source_pair_counts.items())),
            "top_source_presence_counts": dict(sorted(source_counts.items())),
        },
        "groups": groups[:200],
        "truth_boundary": {
            "summary": (
                "This audit flags likely duplicate measurement facts that appear across more than "
                "one source lane. It is intended for review and reconciliation planning only."
            ),
            "report_only": True,
            "governing": False,
            "dedupe_applied": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Cross-Source Duplicate Measurement Audit Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Registry rows scanned: `{summary.get('registry_row_count', 0)}`",
        (
            "- Cross-source duplicate groups: "
            f"`{summary.get('cross_source_duplicate_group_count', 0)}`"
        ),
        "",
    ]
    for pair, count in sorted((summary.get("top_source_pair_counts") or {}).items()):
        lines.append(f"- `{pair}`: `{count}`")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the cross-source duplicate measurement audit preview."
    )
    parser.add_argument("--binding-registry", type=Path, default=DEFAULT_BINDING_REGISTRY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_cross_source_duplicate_measurement_audit_preview(
        read_json(args.binding_registry)
    )
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
