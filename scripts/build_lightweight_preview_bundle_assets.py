from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.model_studio.reference_library import DECODER_VERSION, encode_chunk_payload  # noqa: E402
from core.library.summary_record import SummaryLibrarySchema  # noqa: E402

try:
    import compression.zstd as zstd
except ModuleNotFoundError:  # pragma: no cover - fallback for older envs
    import zstandard as zstd  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTEIN_LIBRARY = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_VARIANT_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "protein_variant_summary_library.json"
)
DEFAULT_STRUCTURE_LIBRARY = (
    REPO_ROOT / "artifacts" / "status" / "structure_unit_summary_library.json"
)
DEFAULT_STRUCTURE_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_similarity_signature_preview.json"
)
DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "protein_similarity_signature_preview.json"
)
DEFAULT_DICTIONARY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "dictionary_preview.json"
)
DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "structure_followup_payload_preview.json"
)
DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_pilot_preview.json"
)
DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_stage1_validation_panel_preview.json"
)
DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_identity_core_materialization_preview.json"
)
DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_similarity_signature_preview.json"
)
DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "q9nzd4_bridge_validation_preview.json"
)
DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_KINETICS_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_LEAKAGE_GROUP_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "leakage_group_preview.json"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "bundles" / "preview"
DEFAULT_BUNDLE_FILENAME = "proteosphere-lite.sqlite.zst"
DEFAULT_RELEASE_MANIFEST_FILENAME = "proteosphere-lite.release_manifest.json"
DEFAULT_CHECKSUM_FILENAME = "proteosphere-lite.sha256"
DEFAULT_CHUNK_INDEX_FILENAME = "proteosphere-lite.chunk_index.json"
DEFAULT_CHUNK_DIRNAME = "chunks"


def _read_library(path: Path) -> SummaryLibrarySchema:
    return SummaryLibrarySchema.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE bundle_metadata (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        CREATE TABLE protein_records (
            summary_id TEXT PRIMARY KEY,
            protein_ref TEXT NOT NULL,
            organism_name TEXT,
            taxon_id INTEGER,
            join_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE protein_variant_records (
            summary_id TEXT PRIMARY KEY,
            protein_ref TEXT NOT NULL,
            variant_signature TEXT NOT NULL,
            variant_kind TEXT,
            sequence_delta_signature TEXT,
            join_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE structure_unit_records (
            summary_id TEXT PRIMARY KEY,
            protein_ref TEXT NOT NULL,
            structure_id TEXT NOT NULL,
            chain_id TEXT,
            variant_ref TEXT,
            mapping_status TEXT NOT NULL,
            join_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE ligand_records (
            row_id TEXT PRIMARY KEY,
            accession TEXT NOT NULL,
            protein_ref TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            ligand_ref TEXT NOT NULL,
            ligand_namespace TEXT NOT NULL,
            materialization_status TEXT NOT NULL,
            evidence_kind TEXT NOT NULL,
            candidate_only INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE reference_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_summary_id TEXT NOT NULL,
            owner_record_type TEXT NOT NULL,
            reference_kind TEXT NOT NULL,
            namespace TEXT NOT NULL,
            identifier TEXT NOT NULL,
            join_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE provenance_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_summary_id TEXT NOT NULL,
            owner_record_type TEXT NOT NULL,
            provenance_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            join_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE structure_similarity_signature_records (
            signature_id TEXT PRIMARY KEY,
            entity_ref TEXT NOT NULL,
            protein_ref TEXT NOT NULL,
            structure_ref TEXT NOT NULL,
            fold_signature_id TEXT NOT NULL,
            experimental_or_predicted TEXT,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE protein_similarity_signature_records (
            signature_id TEXT PRIMARY KEY,
            protein_ref TEXT NOT NULL,
            accession TEXT NOT NULL,
            protein_similarity_group TEXT NOT NULL,
            sequence_equivalence_group TEXT NOT NULL,
            similarity_basis TEXT NOT NULL,
            provenance_ref TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE ligand_similarity_signature_records (
            signature_id TEXT PRIMARY KEY,
            entity_ref TEXT NOT NULL,
            protein_ref TEXT NOT NULL,
            accession TEXT NOT NULL,
            ligand_ref TEXT NOT NULL,
            exact_ligand_identity_group TEXT NOT NULL,
            chemical_series_group TEXT NOT NULL,
            candidate_only INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE dictionary_records (
            dictionary_id TEXT PRIMARY KEY,
            reference_kind TEXT NOT NULL,
            namespace TEXT NOT NULL,
            identifier TEXT NOT NULL,
            label TEXT,
            source_name TEXT,
            usage_count INTEGER NOT NULL,
            supporting_record_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE structure_followup_payload_preview_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            accession TEXT NOT NULL,
            protein_ref TEXT NOT NULL,
            variant_ref TEXT NOT NULL,
            structure_ref TEXT NOT NULL,
            coverage REAL,
            join_status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE ligand_support_readiness_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            accession TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            pilot_role TEXT NOT NULL,
            pilot_lane_status TEXT NOT NULL,
            packet_status TEXT,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE ligand_identity_pilot_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            accession TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            pilot_role TEXT NOT NULL,
            pilot_lane_status TEXT NOT NULL,
            grounded_evidence_kind TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE ligand_stage1_validation_panel_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            accession TEXT NOT NULL,
            lane_kind TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            evidence_kind TEXT NOT NULL,
            target_or_structure TEXT NOT NULL,
            next_truthful_stage TEXT NOT NULL,
            candidate_only INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE q9nzd4_bridge_validation_preview_records (
            accession TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            best_pdb_id TEXT NOT NULL,
            component_id TEXT NOT NULL,
            component_role TEXT,
            matched_pdb_id_count INTEGER NOT NULL,
            candidate_only INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE ligand_identity_core_materialization_preview_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            accession TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            materialization_status TEXT NOT NULL,
            grounded_evidence_kind TEXT NOT NULL,
            next_truthful_stage TEXT NOT NULL,
            candidate_only INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE motif_domain_compact_preview_records (
            dictionary_id TEXT PRIMARY KEY,
            reference_kind TEXT NOT NULL,
            namespace TEXT NOT NULL,
            identifier TEXT NOT NULL,
            source_name TEXT,
            supporting_record_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE kinetics_support_preview_records (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            accession TEXT NOT NULL,
            protein_ref TEXT NOT NULL,
            kinetics_support_status TEXT NOT NULL,
            support_source_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE leakage_group_records (
            linked_group_id TEXT PRIMARY KEY,
            protein_ref TEXT NOT NULL,
            accession TEXT NOT NULL,
            split_name TEXT NOT NULL,
            leakage_risk_class TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        """
    )


def _json_text(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _insert_bundle_metadata(
    connection: sqlite3.Connection,
    *,
    protein_library: SummaryLibrarySchema,
    variant_library: SummaryLibrarySchema,
    structure_library: SummaryLibrarySchema,
    dictionary_preview: dict[str, Any] | None,
    structure_followup_payload_preview: dict[str, Any] | None,
    ligand_support_readiness_preview: dict[str, Any] | None,
    ligand_identity_pilot_preview: dict[str, Any] | None,
    ligand_stage1_validation_panel_preview: dict[str, Any] | None,
    ligand_identity_core_materialization_preview: dict[str, Any] | None,
    ligand_row_materialization_preview: dict[str, Any] | None,
    ligand_similarity_signature_preview: dict[str, Any] | None,
    q9nzd4_bridge_validation_preview: dict[str, Any] | None,
    motif_domain_compact_preview_family: dict[str, Any] | None,
    kinetics_support_preview: dict[str, Any] | None,
    structure_signature_preview: dict[str, Any] | None,
    leakage_group_preview: dict[str, Any] | None,
) -> None:
    metadata = {
        "bundle_kind": "debug_bundle",
        "bundle_version": "0.1.0-preview",
        "manifest_status": "preview_generated_unverified",
        "source_library_ids": {
            "protein": protein_library.library_id,
            "variant": variant_library.library_id,
            "structure": structure_library.library_id,
        },
        "optional_preview_artifacts": {
            "dictionary_preview": (
                dictionary_preview.get("artifact_id", "dictionary_preview")
                if dictionary_preview is not None
                else None
            ),
            "structure_followup_payload_preview": (
                structure_followup_payload_preview.get(
                    "artifact_id",
                    "structure_followup_payload_preview",
                )
                if structure_followup_payload_preview is not None
                else None
            ),
            "ligand_support_readiness_preview": (
                ligand_support_readiness_preview.get(
                    "artifact_id",
                    "ligand_support_readiness_preview",
                )
                if ligand_support_readiness_preview is not None
                else None
            ),
            "ligand_identity_pilot_preview": (
                ligand_identity_pilot_preview.get(
                    "artifact_id",
                    "ligand_identity_pilot_preview",
                )
                if ligand_identity_pilot_preview is not None
                else None
            ),
            "ligand_stage1_validation_panel_preview": (
                ligand_stage1_validation_panel_preview.get(
                    "artifact_id",
                    "ligand_stage1_validation_panel_preview",
                )
                if ligand_stage1_validation_panel_preview is not None
                else None
            ),
            "ligand_identity_core_materialization_preview": (
                ligand_identity_core_materialization_preview.get(
                    "artifact_id",
                    "ligand_identity_core_materialization_preview",
                )
                if ligand_identity_core_materialization_preview is not None
                else None
            ),
            "ligand_row_materialization_preview": (
                ligand_row_materialization_preview.get(
                    "artifact_id",
                    "ligand_row_materialization_preview",
                )
                if ligand_row_materialization_preview is not None
                else None
            ),
            "ligand_similarity_signature_preview": (
                ligand_similarity_signature_preview.get(
                    "artifact_id",
                    "ligand_similarity_signature_preview",
                )
                if ligand_similarity_signature_preview is not None
                else None
            ),
            "q9nzd4_bridge_validation_preview": (
                q9nzd4_bridge_validation_preview.get(
                    "artifact_id",
                    "q9nzd4_bridge_validation_preview",
                )
                if q9nzd4_bridge_validation_preview is not None
                else None
            ),
            "motif_domain_compact_preview_family": (
                motif_domain_compact_preview_family.get(
                    "artifact_id",
                    "motif_domain_compact_preview_family",
                )
                if motif_domain_compact_preview_family is not None
                else None
            ),
            "kinetics_support_preview": (
                kinetics_support_preview.get(
                    "artifact_id",
                    "kinetics_enzyme_support_preview",
                )
                if kinetics_support_preview is not None
                else None
            ),
            "structure_similarity_signature_preview": (
                structure_signature_preview.get(
                    "artifact_id",
                    "structure_similarity_signature_preview",
                )
                if structure_signature_preview is not None
                else None
            ),
            "leakage_group_preview": (
                leakage_group_preview.get("artifact_id", "leakage_group_preview")
                if leakage_group_preview is not None
                else None
            ),
        },
    }
    connection.execute(
        "INSERT INTO bundle_metadata (key, value_json) VALUES (?, ?)",
        ("bundle_metadata", _json_text(metadata)),
    )


def _insert_records(connection: sqlite3.Connection, library: SummaryLibrarySchema) -> None:
    for record in library.protein_records:
        payload = record.to_dict()
        connection.execute(
            """
            INSERT INTO protein_records (
                summary_id, protein_ref, organism_name, taxon_id, join_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record.summary_id,
                record.protein_ref,
                record.organism_name,
                record.taxon_id,
                record.join_status,
                _json_text(payload),
            ),
        )
        _insert_context_rows(connection, record.summary_id, record.record_type, payload["context"])

    for record in library.variant_records:
        payload = record.to_dict()
        connection.execute(
            """
            INSERT INTO protein_variant_records (
                summary_id, protein_ref, variant_signature, variant_kind,
                sequence_delta_signature, join_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.summary_id,
                record.protein_ref,
                record.variant_signature,
                record.variant_kind,
                record.sequence_delta_signature,
                record.join_status,
                _json_text(payload),
            ),
        )
        _insert_context_rows(connection, record.summary_id, record.record_type, payload["context"])

    for record in library.structure_unit_records:
        payload = record.to_dict()
        connection.execute(
            """
            INSERT INTO structure_unit_records (
                summary_id, protein_ref, structure_id, chain_id, variant_ref,
                mapping_status, join_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.summary_id,
                record.protein_ref,
                record.structure_id,
                record.chain_id,
                record.variant_ref,
                record.mapping_status,
                record.join_status,
                _json_text(payload),
            ),
        )
        _insert_context_rows(connection, record.summary_id, record.record_type, payload["context"])


def _insert_context_rows(
    connection: sqlite3.Connection,
    summary_id: str,
    record_type: str,
    context: dict[str, Any],
) -> None:
    reference_buckets = (
        "cross_references",
        "motif_references",
        "domain_references",
        "pathway_references",
    )
    for bucket in reference_buckets:
        for item in context.get(bucket, []):
            connection.execute(
                """
                INSERT INTO reference_records (
                    owner_summary_id, owner_record_type, reference_kind,
                    namespace, identifier, join_status, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_id,
                    record_type,
                    item["reference_kind"],
                    item["namespace"],
                    item["identifier"],
                    item["join_status"],
                    _json_text(item),
                ),
            )
    for item in context.get("provenance_pointers", []):
        connection.execute(
            """
            INSERT INTO provenance_records (
                owner_summary_id, owner_record_type, provenance_id, source_name,
                join_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                summary_id,
                record_type,
                item["provenance_id"],
                item["source_name"],
                item["join_status"],
                _json_text(item),
            ),
            )


def _insert_structure_similarity_signature_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO structure_similarity_signature_records (
                signature_id, entity_ref, protein_ref, structure_ref,
                fold_signature_id, experimental_or_predicted, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["entity_ref"],
                row["entity_ref"],
                row["protein_ref"],
                row["structure_ref"],
                row["fold_signature_id"],
                row.get("experimental_or_predicted"),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_protein_similarity_signature_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO protein_similarity_signature_records (
                signature_id, protein_ref, accession, protein_similarity_group,
                sequence_equivalence_group, similarity_basis, provenance_ref, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["signature_id"],
                row["protein_ref"],
                row["accession"],
                row["protein_similarity_group"],
                row["sequence_equivalence_group"],
                row["similarity_basis"],
                row["provenance_ref"],
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_dictionary_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO dictionary_records (
                dictionary_id, reference_kind, namespace, identifier, label,
                source_name, usage_count, supporting_record_count, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["dictionary_id"],
                row["reference_kind"],
                row["namespace"],
                row["identifier"],
                row.get("label"),
                row.get("source_name"),
                row["usage_count"],
                row["supporting_record_count"],
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_structure_followup_payload_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("payload_rows", []):
        structure_ref = f"{row['structure_id']}:{row['chain_id']}"
        connection.execute(
            """
            INSERT INTO structure_followup_payload_preview_records (
                accession, protein_ref, variant_ref, structure_ref,
                coverage, join_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["accession"],
                row["protein_ref"],
                row["variant_ref"],
                structure_ref,
                row.get("coverage"),
                row["join_status"],
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_ligand_support_readiness_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO ligand_support_readiness_records (
                accession, source_ref, pilot_role, pilot_lane_status,
                packet_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["accession"],
                row["source_ref"],
                row["pilot_role"],
                row["pilot_lane_status"],
                row.get("packet_status"),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_ligand_identity_pilot_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO ligand_identity_pilot_records (
                accession, source_ref, pilot_role, pilot_lane_status,
                grounded_evidence_kind, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["accession"],
                row["source_ref"],
                row["pilot_role"],
                row["pilot_lane_status"],
                row.get("grounded_evidence_kind", "support_only_no_grounded_payload"),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_ligand_stage1_validation_panel_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO ligand_stage1_validation_panel_records (
                accession, lane_kind, validation_status, evidence_kind,
                target_or_structure, next_truthful_stage, candidate_only, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["accession"],
                row["lane_kind"],
                row["status"],
                row["evidence_kind"],
                row["target_or_structure"],
                row["next_truthful_stage"],
                int(bool(row["candidate_only"])),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_q9nzd4_bridge_validation_preview_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    connection.execute(
        """
        INSERT INTO q9nzd4_bridge_validation_preview_records (
            accession, status, best_pdb_id, component_id, component_role,
            matched_pdb_id_count, candidate_only, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["accession"],
            payload["status"],
            payload["best_pdb_id"],
            payload["component_id"],
            payload.get("component_role"),
            int(payload["matched_pdb_id_count"]),
            int(bool(payload["truth_boundary"]["candidate_only"])),
            _json_text(payload),
        ),
    )
    return 1


def _insert_motif_domain_compact_preview_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO motif_domain_compact_preview_records (
                dictionary_id, reference_kind, namespace, identifier,
                source_name, supporting_record_count, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["dictionary_id"],
                row["reference_kind"],
                row["namespace"],
                row["identifier"],
                row.get("source_name"),
                int(row.get("supporting_record_count") or 0),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_kinetics_support_preview_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO kinetics_support_preview_records (
                accession, protein_ref, kinetics_support_status,
                support_source_count, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["accession"],
                row["protein_ref"],
                row["kinetics_support_status"],
                int(row.get("support_source_count") or 0),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_ligand_identity_core_materialization_preview_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO ligand_identity_core_materialization_preview_records (
                accession, source_ref, materialization_status, grounded_evidence_kind,
                next_truthful_stage, candidate_only, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["accession"],
                row["source_ref"],
                row["materialization_status"],
                row["grounded_evidence_kind"],
                row["next_truthful_stage"],
                int(bool(row["candidate_only"])),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_ligand_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO ligand_records (
                row_id, accession, protein_ref, source_ref, ligand_ref,
                ligand_namespace, materialization_status, evidence_kind,
                candidate_only, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["row_id"],
                row["accession"],
                row["protein_ref"],
                row["source_ref"],
                row["ligand_ref"],
                row["ligand_namespace"],
                row["materialization_status"],
                row["evidence_kind"],
                int(bool(row["candidate_only"])),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_ligand_similarity_signature_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO ligand_similarity_signature_records (
                signature_id, entity_ref, protein_ref, accession, ligand_ref,
                exact_ligand_identity_group, chemical_series_group, candidate_only,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["signature_id"],
                row["entity_ref"],
                row["protein_ref"],
                row["accession"],
                row["ligand_ref"],
                row["exact_ligand_identity_group"],
                row["chemical_series_group"],
                int(bool(row["candidate_only"])),
                _json_text(row),
            ),
        )
        count += 1
    return count


def _insert_leakage_group_rows(
    connection: sqlite3.Connection,
    payload: dict[str, Any] | None,
) -> int:
    if payload is None:
        return 0
    count = 0
    for row in payload.get("rows", []):
        connection.execute(
            """
            INSERT INTO leakage_group_records (
                linked_group_id, protein_ref, accession, split_name,
                leakage_risk_class, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["linked_group_id"],
                row["protein_ref"],
                row["accession"],
                row["split_name"],
                row["leakage_risk_class"],
                _json_text(row),
            ),
        )
        count += 1
    return count


def _compress_zstd(source_path: Path, destination_path: Path) -> None:
    with source_path.open("rb") as src, destination_path.open("wb") as dst:
        if hasattr(zstd, "open"):
            with zstd.open(dst, "wb") as compressor:  # type: ignore[arg-type]
                while chunk := src.read(1024 * 1024):
                    compressor.write(chunk)
        else:  # pragma: no cover
            compressor = zstd.ZstdCompressor()
            with compressor.stream_writer(dst) as writer:
                while chunk := src.read(1024 * 1024):
                    writer.write(chunk)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_chunk(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = encode_chunk_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return {
        "chunk_id": payload["chunk_id"],
        "label": payload["label"],
        "filename": path.relative_to(path.parents[1]).as_posix(),
        "storage_kind": "suite_framed_chunk",
        "families": list(payload.get("families", [])),
        "record_counts": dict(payload.get("record_counts", {})),
        "hydration_mode": payload.get("hydration_mode", "local_chunk_hydration"),
        "decoder_expectation": DECODER_VERSION,
        "chunk_sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
        "source_snapshot_ids": list(payload.get("source_snapshot_ids", [])),
    }


def build_preview_bundle_assets(
    *,
    protein_library_path: Path,
    variant_library_path: Path,
    structure_library_path: Path,
    protein_similarity_signature_preview_path: Path | None,
    dictionary_preview_path: Path | None,
    structure_followup_payload_preview_path: Path | None,
    ligand_support_readiness_preview_path: Path | None,
    ligand_identity_pilot_preview_path: Path | None,
    ligand_stage1_validation_panel_preview_path: Path | None,
    ligand_identity_core_materialization_preview_path: Path | None,
    ligand_row_materialization_preview_path: Path | None,
    ligand_similarity_signature_preview_path: Path | None,
    q9nzd4_bridge_validation_preview_path: Path | None,
    motif_domain_compact_preview_family_path: Path | None,
    kinetics_support_preview_path: Path | None,
    structure_signature_preview_path: Path | None,
    leakage_group_preview_path: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    protein_library = _read_library(protein_library_path)
    variant_library = _read_library(variant_library_path)
    structure_library = _read_library(structure_library_path)
    protein_similarity_signature_preview = (
        json.loads(protein_similarity_signature_preview_path.read_text(encoding="utf-8"))
        if protein_similarity_signature_preview_path is not None
        and protein_similarity_signature_preview_path.exists()
        else None
    )
    dictionary_preview = (
        json.loads(dictionary_preview_path.read_text(encoding="utf-8"))
        if dictionary_preview_path is not None and dictionary_preview_path.exists()
        else None
    )
    structure_followup_payload_preview = (
        json.loads(structure_followup_payload_preview_path.read_text(encoding="utf-8"))
        if structure_followup_payload_preview_path is not None
        and structure_followup_payload_preview_path.exists()
        else None
    )
    ligand_support_readiness_preview = (
        json.loads(ligand_support_readiness_preview_path.read_text(encoding="utf-8"))
        if ligand_support_readiness_preview_path is not None
        and ligand_support_readiness_preview_path.exists()
        else None
    )
    ligand_identity_pilot_preview = (
        json.loads(ligand_identity_pilot_preview_path.read_text(encoding="utf-8"))
        if ligand_identity_pilot_preview_path is not None
        and ligand_identity_pilot_preview_path.exists()
        else None
    )
    ligand_stage1_validation_panel_preview = (
        json.loads(ligand_stage1_validation_panel_preview_path.read_text(encoding="utf-8"))
        if ligand_stage1_validation_panel_preview_path is not None
        and ligand_stage1_validation_panel_preview_path.exists()
        else None
    )
    ligand_identity_core_materialization_preview = (
        json.loads(
            ligand_identity_core_materialization_preview_path.read_text(encoding="utf-8")
        )
        if ligand_identity_core_materialization_preview_path is not None
        and ligand_identity_core_materialization_preview_path.exists()
        else None
    )
    ligand_row_materialization_preview = (
        json.loads(ligand_row_materialization_preview_path.read_text(encoding="utf-8"))
        if ligand_row_materialization_preview_path is not None
        and ligand_row_materialization_preview_path.exists()
        else None
    )
    ligand_similarity_signature_preview = (
        json.loads(ligand_similarity_signature_preview_path.read_text(encoding="utf-8"))
        if ligand_similarity_signature_preview_path is not None
        and ligand_similarity_signature_preview_path.exists()
        else None
    )
    q9nzd4_bridge_validation_preview = (
        json.loads(q9nzd4_bridge_validation_preview_path.read_text(encoding="utf-8"))
        if q9nzd4_bridge_validation_preview_path is not None
        and q9nzd4_bridge_validation_preview_path.exists()
        else None
    )
    motif_domain_compact_preview_family = (
        json.loads(motif_domain_compact_preview_family_path.read_text(encoding="utf-8"))
        if motif_domain_compact_preview_family_path is not None
        and motif_domain_compact_preview_family_path.exists()
        else None
    )
    kinetics_support_preview = (
        json.loads(kinetics_support_preview_path.read_text(encoding="utf-8"))
        if kinetics_support_preview_path is not None and kinetics_support_preview_path.exists()
        else None
    )
    structure_signature_preview = (
        json.loads(structure_signature_preview_path.read_text(encoding="utf-8"))
        if structure_signature_preview_path is not None
        and structure_signature_preview_path.exists()
        else None
    )
    leakage_group_preview = (
        json.loads(leakage_group_preview_path.read_text(encoding="utf-8"))
        if leakage_group_preview_path is not None
        and leakage_group_preview_path.exists()
        else None
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    compressed_bundle_path = output_dir / DEFAULT_BUNDLE_FILENAME
    release_manifest_path = output_dir / DEFAULT_RELEASE_MANIFEST_FILENAME
    checksum_path = output_dir / DEFAULT_CHECKSUM_FILENAME
    chunk_index_path = output_dir / DEFAULT_CHUNK_INDEX_FILENAME
    chunk_dir = output_dir / DEFAULT_CHUNK_DIRNAME

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as handle:
        sqlite_path = Path(handle.name)
    try:
        connection = _connect(sqlite_path)
        try:
            _create_schema(connection)
            _insert_bundle_metadata(
                connection,
                protein_library=protein_library,
                variant_library=variant_library,
                structure_library=structure_library,
                dictionary_preview=dictionary_preview,
                structure_followup_payload_preview=structure_followup_payload_preview,
                ligand_support_readiness_preview=ligand_support_readiness_preview,
                ligand_identity_pilot_preview=ligand_identity_pilot_preview,
                ligand_stage1_validation_panel_preview=ligand_stage1_validation_panel_preview,
                ligand_identity_core_materialization_preview=(
                    ligand_identity_core_materialization_preview
                ),
                ligand_row_materialization_preview=ligand_row_materialization_preview,
                ligand_similarity_signature_preview=ligand_similarity_signature_preview,
                q9nzd4_bridge_validation_preview=q9nzd4_bridge_validation_preview,
                motif_domain_compact_preview_family=motif_domain_compact_preview_family,
                kinetics_support_preview=kinetics_support_preview,
                structure_signature_preview=structure_signature_preview,
                leakage_group_preview=leakage_group_preview,
            )
            _insert_records(connection, protein_library)
            _insert_records(connection, variant_library)
            _insert_records(connection, structure_library)
            protein_similarity_signature_count = _insert_protein_similarity_signature_rows(
                connection,
                protein_similarity_signature_preview,
            )
            dictionary_count = _insert_dictionary_rows(connection, dictionary_preview)
            structure_followup_payload_count = _insert_structure_followup_payload_rows(
                connection,
                structure_followup_payload_preview,
            )
            ligand_support_readiness_count = _insert_ligand_support_readiness_rows(
                connection,
                ligand_support_readiness_preview,
            )
            ligand_identity_pilot_count = _insert_ligand_identity_pilot_rows(
                connection,
                ligand_identity_pilot_preview,
            )
            ligand_stage1_validation_panel_count = (
                _insert_ligand_stage1_validation_panel_rows(
                    connection,
                    ligand_stage1_validation_panel_preview,
                )
            )
            ligand_identity_core_materialization_count = (
                _insert_ligand_identity_core_materialization_preview_rows(
                    connection,
                    ligand_identity_core_materialization_preview,
                )
            )
            ligand_row_count = _insert_ligand_rows(
                connection,
                ligand_row_materialization_preview,
            )
            ligand_similarity_signature_count = (
                _insert_ligand_similarity_signature_rows(
                    connection,
                    ligand_similarity_signature_preview,
                )
            )
            q9nzd4_bridge_validation_preview_count = (
                _insert_q9nzd4_bridge_validation_preview_rows(
                    connection,
                    q9nzd4_bridge_validation_preview,
                )
            )
            motif_domain_compact_preview_count = (
                _insert_motif_domain_compact_preview_rows(
                    connection,
                    motif_domain_compact_preview_family,
                )
            )
            kinetics_support_preview_count = _insert_kinetics_support_preview_rows(
                connection,
                kinetics_support_preview,
            )
            structure_signature_count = _insert_structure_similarity_signature_rows(
                connection,
                structure_signature_preview,
            )
            leakage_group_count = _insert_leakage_group_rows(
                connection,
                leakage_group_preview,
            )
            connection.commit()
        finally:
            connection.close()

        _compress_zstd(sqlite_path, compressed_bundle_path)
    finally:
        if sqlite_path.exists():
            sqlite_path.unlink()
        wal_path = sqlite_path.with_suffix(sqlite_path.suffix + "-wal")
        shm_path = sqlite_path.with_suffix(sqlite_path.suffix + "-shm")
        for extra in (wal_path, shm_path):
            if extra.exists():
                extra.unlink()

    checksum = _sha256(compressed_bundle_path)
    checksum_path.write_text(
        f"{checksum}  {compressed_bundle_path.name}\n",
        encoding="utf-8",
    )

    source_snapshot_ids = [
        protein_library.library_id,
        variant_library.library_id,
        structure_library.library_id,
    ]
    family_counts = {
        "proteins": protein_library.record_count,
        "protein_variants": variant_library.record_count,
        "structures": structure_library.record_count,
        "ligands": ligand_row_count,
        "dictionaries": dictionary_count,
        "structure_followup_payloads": structure_followup_payload_count,
        "ligand_support_readiness": ligand_support_readiness_count,
        "ligand_identity_pilot": ligand_identity_pilot_count,
        "ligand_stage1_validation_panel": ligand_stage1_validation_panel_count,
        "ligand_identity_core_materialization_preview": (
            ligand_identity_core_materialization_count
        ),
        "ligand_row_materialization_preview": ligand_row_count,
        "ligand_similarity_signatures": ligand_similarity_signature_count,
        "q9nzd4_bridge_validation_preview": q9nzd4_bridge_validation_preview_count,
        "motif_domain_compact_preview_family": motif_domain_compact_preview_count,
        "kinetics_support_preview": kinetics_support_preview_count,
        "protein_similarity_signatures": protein_similarity_signature_count,
        "structure_similarity_signatures": structure_signature_count,
        "leakage_groups": leakage_group_count,
    }
    chunk_catalog = [
        _write_chunk(
            chunk_dir / "ligand_support_family.pslchunk",
            {
                "chunk_id": "ligand_support_family",
                "label": "Ligand support and provenance family",
                "families": [
                    "ligands",
                    "ligand_support_readiness",
                    "ligand_identity_pilot",
                    "ligand_stage1_validation_panel",
                    "ligand_identity_core_materialization_preview",
                    "ligand_row_materialization_preview",
                    "ligand_similarity_signatures",
                    "q9nzd4_bridge_validation_preview",
                ],
                "record_counts": {
                    key: family_counts[key]
                    for key in (
                        "ligands",
                        "ligand_support_readiness",
                        "ligand_identity_pilot",
                        "ligand_stage1_validation_panel",
                        "ligand_identity_core_materialization_preview",
                        "ligand_row_materialization_preview",
                        "ligand_similarity_signatures",
                        "q9nzd4_bridge_validation_preview",
                    )
                },
                "hydration_mode": "local_chunk_hydration",
                "source_snapshot_ids": source_snapshot_ids,
            },
        ),
        _write_chunk(
            chunk_dir / "motif_and_signature_family.pslchunk",
            {
                "chunk_id": "motif_and_signature_family",
                "label": "Motif and signature family",
                "families": [
                    "motif_domain_compact_preview_family",
                    "protein_similarity_signatures",
                    "structure_similarity_signatures",
                    "leakage_groups",
                ],
                "record_counts": {
                    key: family_counts[key]
                    for key in (
                        "motif_domain_compact_preview_family",
                        "protein_similarity_signatures",
                        "structure_similarity_signatures",
                        "leakage_groups",
                    )
                },
                "hydration_mode": "local_chunk_hydration",
                "source_snapshot_ids": source_snapshot_ids,
            },
        ),
    ]
    chunk_index_path.write_text(json.dumps(chunk_catalog, indent=2) + "\n", encoding="utf-8")

    release_manifest = {
        "artifact_id": "lightweight_preview_bundle_release_manifest",
        "schema_id": "proteosphere-lite-release-manifest-2026-04-01",
        "status": "preview_generated_assets",
        "bundle_id": "proteosphere-lite",
        "bundle_version": "2026.04.preview",
        "bundle_kind": "compressed_sqlite",
        "packaging_layout": "core_bundle_plus_family_chunks",
        "content_scope": "planning_governance_balance_leakage_and_packet_blueprints",
        "schema_version": "proteosphere-lite-release-manifest-2026-04-01",
        "bundle_filename": compressed_bundle_path.name,
        "bundle_sha256": checksum,
        "bundle_size_bytes": compressed_bundle_path.stat().st_size,
        "checksum_filename": checksum_path.name,
        "source_libraries": {
            "protein": protein_library.library_id,
            "variant": variant_library.library_id,
            "structure": structure_library.library_id,
        },
        "record_counts": family_counts,
        "family_counts": family_counts,
        "chunks": chunk_catalog,
        "checksums": {
            "bundle_sha256": checksum,
            "chunk_index_sha256": _sha256(chunk_index_path),
            "chunk_sha256": {
                item["chunk_id"]: item["chunk_sha256"] for item in chunk_catalog
            },
        },
        "decoder_version": DECODER_VERSION,
        "source_snapshot_ids": source_snapshot_ids,
        "chunk_index_filename": chunk_index_path.name,
    }
    release_manifest_path.write_text(
        json.dumps(release_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return release_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build preview bundle assets for the lightweight ProteoSphere library."
    )
    parser.add_argument("--protein-library", type=Path, default=DEFAULT_PROTEIN_LIBRARY)
    parser.add_argument("--variant-library", type=Path, default=DEFAULT_VARIANT_LIBRARY)
    parser.add_argument("--structure-library", type=Path, default=DEFAULT_STRUCTURE_LIBRARY)
    parser.add_argument(
        "--protein-similarity-signature-preview",
        type=Path,
        default=DEFAULT_PROTEIN_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--dictionary-preview",
        type=Path,
        default=DEFAULT_DICTIONARY_PREVIEW,
    )
    parser.add_argument(
        "--structure-followup-payload-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_FOLLOWUP_PAYLOAD_PREVIEW,
    )
    parser.add_argument(
        "--ligand-support-readiness-preview",
        type=Path,
        default=DEFAULT_LIGAND_SUPPORT_READINESS_PREVIEW,
    )
    parser.add_argument(
        "--ligand-identity-pilot-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_PILOT_PREVIEW,
    )
    parser.add_argument(
        "--ligand-stage1-validation-panel-preview",
        type=Path,
        default=DEFAULT_LIGAND_STAGE1_VALIDATION_PANEL_PREVIEW,
    )
    parser.add_argument(
        "--ligand-identity-core-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_IDENTITY_CORE_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-row-materialization-preview",
        type=Path,
        default=DEFAULT_LIGAND_ROW_MATERIALIZATION_PREVIEW,
    )
    parser.add_argument(
        "--ligand-similarity-signature-preview",
        type=Path,
        default=DEFAULT_LIGAND_SIMILARITY_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--q9nzd4-bridge-validation-preview",
        type=Path,
        default=DEFAULT_Q9NZD4_BRIDGE_VALIDATION_PREVIEW,
    )
    parser.add_argument(
        "--motif-domain-compact-preview-family",
        type=Path,
        default=DEFAULT_MOTIF_DOMAIN_COMPACT_PREVIEW_FAMILY,
    )
    parser.add_argument(
        "--kinetics-support-preview",
        type=Path,
        default=DEFAULT_KINETICS_SUPPORT_PREVIEW,
    )
    parser.add_argument(
        "--structure-signature-preview",
        type=Path,
        default=DEFAULT_STRUCTURE_SIGNATURE_PREVIEW,
    )
    parser.add_argument(
        "--leakage-group-preview",
        type=Path,
        default=DEFAULT_LEAKAGE_GROUP_PREVIEW,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_preview_bundle_assets(
        protein_library_path=args.protein_library,
        variant_library_path=args.variant_library,
        structure_library_path=args.structure_library,
        protein_similarity_signature_preview_path=args.protein_similarity_signature_preview,
        dictionary_preview_path=args.dictionary_preview,
        structure_followup_payload_preview_path=args.structure_followup_payload_preview,
        ligand_support_readiness_preview_path=args.ligand_support_readiness_preview,
        ligand_identity_pilot_preview_path=args.ligand_identity_pilot_preview,
        ligand_stage1_validation_panel_preview_path=(
            args.ligand_stage1_validation_panel_preview
        ),
        ligand_identity_core_materialization_preview_path=(
            args.ligand_identity_core_materialization_preview
        ),
        ligand_row_materialization_preview_path=args.ligand_row_materialization_preview,
        ligand_similarity_signature_preview_path=args.ligand_similarity_signature_preview,
        q9nzd4_bridge_validation_preview_path=args.q9nzd4_bridge_validation_preview,
        motif_domain_compact_preview_family_path=args.motif_domain_compact_preview_family,
        kinetics_support_preview_path=args.kinetics_support_preview,
        structure_signature_preview_path=args.structure_signature_preview,
        leakage_group_preview_path=args.leakage_group_preview,
        output_dir=args.output_dir,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
