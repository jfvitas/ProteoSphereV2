from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_MANIFEST = (
    REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
)
DEFAULT_LIGAND_IDENTITY_CORE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_core_materialization_preview.json"
)
DEFAULT_LIGAND_ROW_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_gate_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "ligand_similarity_signature_gate_preview.md"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_ligand_similarity_signature_gate_preview(
    bundle_manifest: dict[str, Any],
    ligand_identity_core_preview: dict[str, Any],
    ligand_row_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counts = bundle_manifest["record_counts"]
    manifest_ligand_count = int(counts.get("ligands", 0))
    preview_ligand_count = (
        int(ligand_row_preview.get("row_count", 0)) if ligand_row_preview is not None else 0
    )
    ligand_record_count = max(manifest_ligand_count, preview_ligand_count)
    ligands_included = ligand_record_count > 0
    identity_core_count = ligand_identity_core_preview["row_count"]
    gate_status = (
        "blocked_pending_real_ligands" if not ligands_included else "ready_for_signature_preview"
    )
    return {
        "artifact_id": "ligand_similarity_signature_gate_preview",
        "schema_id": "proteosphere-ligand-similarity-signature-gate-preview-2026-04-01",
        "status": "complete",
        "stage_id": "ligand_similarity_signature_gate",
        "gate_status": gate_status,
        "identity_core_preview_row_count": identity_core_count,
        "identity_core_grounded_accession_count": ligand_identity_core_preview["summary"][
            "grounded_accession_count"
        ],
        "ligands_materialized": ligands_included,
        "ligand_record_count": ligand_record_count,
        "next_unlocked_stage": (
            "ligand_similarity_signature_preview"
            if ligands_included
            else "materialize_real_ligand_rows_first"
        ),
        "truth_boundary": {
            "summary": (
                "This gate states whether ligand similarity signatures can be emitted yet. "
                "It remains report-only and does not materialize ligand rows or signature rows."
            ),
            "report_only": True,
            "ligand_rows_materialized": ligands_included,
            "ligand_similarity_signatures_materialized": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Ligand Similarity Signature Gate Preview",
        "",
        f"- Gate status: `{payload['gate_status']}`",
        f"- Identity-core preview rows: `{payload['identity_core_preview_row_count']}`",
        (
            "- Grounded accessions in identity-core preview: "
            f"`{payload['identity_core_grounded_accession_count']}`"
        ),
        f"- Ligands materialized: `{payload['ligands_materialized']}`",
        f"- Next unlocked stage: `{payload['next_unlocked_stage']}`",
        "",
        "## Truth Boundary",
        "",
        f"- {payload['truth_boundary']['summary']}",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the live gate for ligand similarity signature preview readiness."
    )
    parser.add_argument("--bundle-manifest", type=Path, default=DEFAULT_BUNDLE_MANIFEST)
    parser.add_argument(
        "--ligand-identity-core-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_CORE_PREVIEW,
    )
    parser.add_argument(
        "--ligand-row-preview",
        type=Path,
        default=DEFAULT_LIGAND_ROW_PREVIEW,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_ligand_similarity_signature_gate_preview(
        _read_json(args.bundle_manifest),
        _read_json(args.ligand_identity_core_preview),
        _read_json(args.ligand_row_preview),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
