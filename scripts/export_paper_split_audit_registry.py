from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = REPO_ROOT / "artifacts" / "status" / "paper_split_list"
DEFAULT_WAREHOUSE_ROOT = Path(
    os.environ.get("PROTEOSPHERE_WAREHOUSE_ROOT", r"D:\ProteoSphere\reference_library")
)
DEFAULT_OUTPUT_JSON = DEFAULT_WAREHOUSE_ROOT / "control" / "paper_split_audit_registry.json"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_identifier_bridge_requirements(payload: dict[str, Any]) -> list[dict[str, Any]]:
    text_parts = []
    supplemental = payload.get("supplemental_evidence") or {}
    text_parts.extend(str(item) for item in (supplemental.get("details") or []))
    text_parts.extend(str(item) for item in (payload.get("blockers") or []))
    text = "\n".join(text_parts).casefold()
    requirements: list[dict[str, Any]] = []

    def add_requirement(requirement_id: str, source_namespace: str, target_namespace: str, reason: str) -> None:
        if any(row["requirement_id"] == requirement_id for row in requirements):
            return
        requirements.append(
            {
                "requirement_id": requirement_id,
                "source_namespace": source_namespace,
                "target_namespace": target_namespace,
                "reason": reason,
            }
        )

    if "ensembl" in text and "flybase" in text:
        add_requirement(
            "ensembl_and_flybase_to_uniprot",
            "ensembl_protein|flybase_protein",
            "uniprot_accession",
            "Recovered split files use Ensembl and FlyBase protein identifiers rather than warehouse-native accessions.",
        )
    elif "ensembl" in text:
        add_requirement(
            "ensembl_to_uniprot",
            "ensembl_protein",
            "uniprot_accession",
            "Recovered split files use Ensembl protein identifiers rather than warehouse-native accessions.",
        )
    if "string-style namespace" in text or ("string" in text and "ensembl" in text):
        add_requirement(
            "string_ensembl_to_uniprot",
            "string_ensembl_protein",
            "uniprot_accession",
            "Recovered split artifacts use STRING/Ensembl protein keys that are not yet bridged into warehouse proteins.",
        )
    if "pdb ids" in text or "pdb-id" in text or "shared pdb count" in json.dumps(supplemental).casefold():
        add_requirement(
            "pdb_id_to_structure_entry",
            "pdb_id",
            "pdb_entries.entry_id",
            "Recovered split logic or evidence is keyed by PDB identifiers and should be preserved as a warehouse-visible structure audit surface.",
        )
    return requirements


def _build_record(payload: dict[str, Any], source_path: Path) -> dict[str, Any]:
    supplemental = payload.get("supplemental_evidence") or {}
    overlap = payload.get("overlap_findings") or {}
    leakage = payload.get("leakage_findings") or {}
    bridge_requirements = _infer_identifier_bridge_requirements(payload)
    return {
        "paper_id": payload.get("paper_id"),
        "title": payload.get("title"),
        "doi": payload.get("doi"),
        "project_status": payload.get("project_status"),
        "narrative_verdict": payload.get("verdict"),
        "resolved_split_policy": ((payload.get("resolved_split_policy") or {}).get("policy")),
        "audit_surface_status": (
            "supplemental_artifact_materialized" if supplemental else "paper_summary_only"
        ),
        "benchmark_membership_materialized": False,
        "identifier_bridge_requirements": bridge_requirements,
        "supplemental_evidence": {
            "status": supplemental.get("status"),
            "summary": supplemental.get("summary"),
            "artifact_paths": supplemental.get("artifact_paths", []),
            "source_links": supplemental.get("source_links", []),
            "reproduction": supplemental.get("reproduction"),
        }
        if supplemental
        else None,
        "evidence_notes": {
            "direct_overlap_status": ((overlap.get("direct_overlap") or {}).get("status")),
            "uniref_overlap_status": ((overlap.get("uniref_overlap") or {}).get("status")),
            "leakage_status": leakage.get("status"),
            "blockers": payload.get("blockers", []),
            "warnings": payload.get("warnings", []),
            "recommended_canonical_treatment": payload.get("recommended_canonical_treatment"),
        },
        "source_artifact_path": str(source_path),
    }


def export_registry(input_dir: Path, output_json: Path) -> dict[str, Any]:
    records = []
    for path in sorted(input_dir.glob("*.json")):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        records.append(_build_record(payload, path))
    registry = {
        "artifact_id": "paper_split_audit_registry",
        "schema_id": "proteosphere-paper-split-audit-registry-v1",
        "generated_at": _utc_now(),
        "warehouse_root": str(DEFAULT_WAREHOUSE_ROOT).replace("\\", "/"),
        "source_input_dir": str(input_dir),
        "record_count": len(records),
        "records": records,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    return registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export recovered paper split audit artifacts into a warehouse-facing control registry."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = export_registry(args.input_dir, args.output_json)
    print(args.output_json)
    print(json.dumps({"record_count": payload["record_count"]}, indent=2))


if __name__ == "__main__":
    main()
