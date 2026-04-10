from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.affinity_interaction_preview_support import summarize_best_exact_affinity
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import summarize_best_exact_affinity
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_REGISTRY = (
    REPO_ROOT / "artifacts" / "status" / "binding_measurement_registry_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "structure_binding_affinity_context_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "structure_binding_affinity_context_preview.md"
)


def build_structure_binding_affinity_context_preview(
    binding_measurement_registry_preview: dict[str, Any],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in binding_measurement_registry_preview.get("rows") or []:
        if row.get("measurement_origin") != "pdbbind":
            continue
        grouped.setdefault(str(row.get("pdb_id") or ""), []).append(row)

    rows = []
    for pdb_id, measurements in sorted(grouped.items()):
        rows.append(
            {
                "structure_id": pdb_id,
                "complex_type": measurements[0].get("complex_type"),
                "chain_role_summary": measurements[0].get("parenthetical_tokens") or [],
                "affinity_measurement_count": len(measurements),
                "best_exact_affinity": summarize_best_exact_affinity(measurements),
                "thermodynamic_field_presence": any(
                    row.get("delta_g_reported_kcal_per_mol") is not None
                    or row.get("delta_g_derived_298k_kcal_per_mol") is not None
                    for row in measurements
                ),
                "measurements": [
                    {
                        "measurement_id": row.get("measurement_id"),
                        "raw_binding_string": row.get("raw_binding_string"),
                        "measurement_type": row.get("measurement_type"),
                        "relation": row.get("relation"),
                        "p_affinity": row.get("p_affinity"),
                    }
                    for row in measurements
                ],
            }
        )

    return {
        "artifact_id": "structure_binding_affinity_context_preview",
        "schema_id": "proteosphere-structure-binding-affinity-context-preview-2026-04-03",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "structure_count": len(rows),
            "complex_type_counts": {
                key: sum(1 for row in rows if row.get("complex_type") == key)
                for key in sorted({row.get("complex_type") for row in rows})
            },
        },
        "truth_boundary": {
            "summary": (
                "This surface groups parsed PDBbind affinities by structure. It is report-only "
                "and does not imply structure-linked grounding for library accessions."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Structure Binding Affinity Context Preview",
        "",
        f"- Structures: `{payload['row_count']}`",
        "",
    ]
    for row in payload["rows"][:10]:
        lines.append(
            f"- `{row['structure_id']}` / `{row['complex_type']}` / "
            f"measurements `{row['affinity_measurement_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build structure binding affinity summaries.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_structure_binding_affinity_context_preview(read_json(args.registry))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()
