from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from core.library.summary_record import (
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
    SummaryReference,
)
from execution.library.protein_summary_materializer import (
    materialize_protein_summary_library,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _scalar_consensus_payloads(record: ProteinSummaryRecord) -> list[dict[str, object]]:
    return [
        json.loads(note.removeprefix("scalar_consensus:"))
        for note in record.notes
        if note.startswith("scalar_consensus:")
    ]


def _source_rollup_payloads(record: ProteinSummaryRecord) -> list[dict[str, object]]:
    return [rollup.to_dict() for rollup in record.context.source_rollups]


def _source_connection_payloads(record: ProteinSummaryRecord) -> list[dict[str, object]]:
    return [connection.to_dict() for connection in record.context.source_connections]


def _canonical_latest_payload() -> dict[str, object]:
    return {
        "sequence_result": {
            "source_release": {
                "manifest_id": "UniProt:2026-03-23:api:test",
                "source_name": "UniProt",
                "release_version": "2026-03-23",
            },
            "canonical_ids": ["protein:P12345", "protein:P69905", "protein:Q99999"],
            "records": [
                {
                    "accession": "P12345",
                    "source_id": "P12345_HUMAN",
                    "source_kind": "uniprot_entry_mapping",
                    "sequence": "MKT",
                    "sequence_length": 3,
                    "name": "Example protein",
                    "organism": "Homo sapiens",
                    "gene_names": ["GENE1"],
                    "aliases": ["EX1_HUMAN"],
                    "reviewed": True,
                    "raw_payload": {
                        "sequence": {"md5": "ABC123"},
                        "entryAudit": {"sequenceVersion": 2},
                    },
                    "provenance_record": {
                        "provenance_id": "sequence:P12345:P12345_HUMAN:0",
                        "source": {
                            "source_name": "UniProt",
                            "release_version": "2026-03-23",
                        },
                        "acquired_at": "2026-03-23T18:17:26.514563+00:00",
                        "checksum": "sha256:aaaaaaaa",
                        "transformation_step": "sequence_observation",
                        "metadata": {
                            "source_release": {
                                "manifest_id": "UniProt:2026-03-23:api:test",
                                "source_name": "UniProt",
                                "release_version": "2026-03-23",
                            }
                        },
                    },
                },
                {
                    "accession": "P69905",
                    "source_id": "P69905_HUMAN",
                    "source_kind": "uniprot_entry_mapping",
                    "sequence": "M" * 142,
                    "sequence_length": 142,
                    "name": "Hemoglobin subunit alpha",
                    "organism": "Homo sapiens",
                    "gene_names": ["HBA1", "HBA2"],
                    "aliases": ["HBA_HUMAN"],
                    "reviewed": True,
                    "raw_payload": {
                        "sequence": {"md5": "ABC69905"},
                        "entryAudit": {"sequenceVersion": 2},
                        "organism": {"taxonId": 9606},
                        "uniProtKBCrossReferences": [
                            {
                                "database": "InterPro",
                                "id": "IPR000971",
                                "properties": [{"key": "EntryName", "value": "Globin"}],
                            },
                            {
                                "database": "InterPro",
                                "id": "IPR009050",
                                "properties": [{"key": "EntryName", "value": "Globin-like_sf"}],
                            },
                            {
                                "database": "InterPro",
                                "id": "IPR012292",
                                "properties": [{"key": "EntryName", "value": "Globin/Proto"}],
                            },
                            {
                                "database": "InterPro",
                                "id": "IPR002338",
                                "properties": [{"key": "EntryName", "value": "Hemoglobin_a-typ"}],
                            },
                            {
                                "database": "InterPro",
                                "id": "IPR050056",
                                "properties": [
                                    {"key": "EntryName", "value": "Hemoglobin_oxygen_transport"}
                                ],
                            },
                            {
                                "database": "InterPro",
                                "id": "IPR002339",
                                "properties": [{"key": "EntryName", "value": "Hemoglobin_pi"}],
                            },
                            {
                                "database": "Pfam",
                                "id": "PF00042",
                                "properties": [
                                    {"key": "EntryName", "value": "Globin"},
                                    {"key": "MatchStatus", "value": "1"},
                                ],
                            },
                            {
                                "database": "PROSITE",
                                "id": "PS01033",
                                "properties": [
                                    {"key": "EntryName", "value": "GLOBIN"},
                                    {"key": "MatchStatus", "value": "1"},
                                ],
                            },
                            {"database": "PDB", "id": "4HHB", "properties": []},
                        ],
                    },
                    "provenance_record": {
                        "provenance_id": "sequence:P69905:P69905_HUMAN:0",
                        "source": {
                            "source_name": "UniProt",
                            "release_version": "2026-03-23",
                        },
                        "acquired_at": "2026-03-23T18:17:26.514563+00:00",
                        "checksum": "sha256:cccccccc",
                        "transformation_step": "sequence_observation",
                        "metadata": {
                            "source_release": {
                                "manifest_id": "UniProt:2026-03-23:api:test",
                                "source_name": "UniProt",
                                "release_version": "2026-03-23",
                            }
                        },
                    },
                },
                {
                    "accession": "Q99999",
                    "source_id": "Q99999_HUMAN",
                    "source_kind": "uniprot_entry_mapping",
                    "sequence": "MKTAA",
                    "sequence_length": 5,
                    "name": "Second protein",
                    "organism": "Homo sapiens",
                    "gene_names": ["GENE2"],
                    "aliases": ["EX2_HUMAN"],
                    "reviewed": True,
                    "raw_payload": {
                        "sequence": {"md5": "DEF456"},
                        "entryAudit": {"sequenceVersion": 1},
                    },
                    "provenance_record": {
                        "provenance_id": "sequence:Q99999:Q99999_HUMAN:0",
                        "source": {
                            "source_name": "UniProt",
                            "release_version": "2026-03-23",
                        },
                        "acquired_at": "2026-03-23T18:17:26.514563+00:00",
                        "checksum": "sha256:bbbbbbbb",
                        "transformation_step": "sequence_observation",
                        "metadata": {
                            "source_release": {
                                "manifest_id": "UniProt:2026-03-23:api:test",
                                "source_name": "UniProt",
                                "release_version": "2026-03-23",
                            }
                        },
                    },
                },
            ],
        }
    }


def _reactome_library_payload() -> dict[str, object]:
    return SummaryLibrarySchema(
        library_id="summary-library:reactome-local:test",
        source_manifest_id="bio-agent-lab/reactome:test",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P12345",
                protein_ref="protein:P12345",
                protein_name="Example protein",
                organism_name="Homo sapiens",
                gene_names=("GENE1",),
                aliases=("P12345",),
                join_status="joined",
                context=SummaryRecordContext(
                    provenance_pointers=(
                        SummaryProvenancePointer(
                            provenance_id="reactome-local:P12345",
                            source_name="Reactome",
                            source_record_id="P12345",
                            release_version="2026-03-16",
                        ),
                    ),
                    pathway_references=(
                        SummaryReference(
                            reference_kind="pathway",
                            namespace="Reactome",
                            identifier="R-HSA-1",
                            label="Pathway One",
                            join_status="joined",
                            source_name="Reactome",
                            source_record_id="R-HSA-1",
                            evidence_refs=("TAS",),
                        ),
                    ),
                ),
            ),
        ),
    ).to_dict()


def _intact_library_payload() -> dict[str, object]:
    return SummaryLibrarySchema(
        library_id="summary-library:intact-local:test",
        source_manifest_id="IntAct:test:download:abc123",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P12345",
                protein_ref="protein:P12345",
                protein_name="Example protein",
                organism_name="Homo sapiens",
                gene_names=("GENE1",),
                aliases=("P12345",),
                join_status="partial",
                join_reason="intact_self_only_probe",
                context=SummaryRecordContext(
                    provenance_pointers=(
                        SummaryProvenancePointer(
                            provenance_id="intact:P12345:test",
                            source_name="IntAct",
                            source_record_id="P12345",
                            release_version="20260323T002625Z",
                        ),
                    ),
                ),
                notes=("probe_state:reachable_empty",),
            ),
            ProteinSummaryRecord(
                summary_id="protein:Q99999",
                protein_ref="protein:Q99999",
                protein_name="Second protein (Reactome)",
                organism_name="Homo sapiens",
                gene_names=("GENE2",),
                aliases=("Q99999",),
                join_status="partial",
                context=SummaryRecordContext(
                    provenance_pointers=(
                        SummaryProvenancePointer(
                            provenance_id="intact:Q99999:test",
                            source_name="IntAct",
                            source_record_id="Q99999",
                            release_version="20260323T002625Z",
                        ),
                    ),
                ),
            ),
            ProteinProteinSummaryRecord(
                summary_id="pair:protein_protein:protein:P12345|protein:Q99999",
                protein_a_ref="protein:P12345",
                protein_b_ref="protein:Q99999",
                interaction_type="physical association",
                interaction_refs=("EBI-1", "IM-1"),
                evidence_refs=("pubmed:1",),
                physical_interaction=True,
                evidence_count=1,
                confidence=0.8,
                join_status="joined",
                context=SummaryRecordContext(
                    provenance_pointers=(
                        SummaryProvenancePointer(
                            provenance_id="intact:pair:test",
                            source_name="IntAct",
                            source_record_id="EBI-1",
                            release_version="20260323T002625Z",
                        ),
                    ),
                ),
            ),
        ),
    ).to_dict()


def test_materialize_protein_summary_library_merges_reactome_and_intact_context(
    tmp_path: Path,
) -> None:
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    reactome_summary = tmp_path / "artifacts" / "status" / "reactome_local_summary_library.json"
    intact_summary = tmp_path / "artifacts" / "status" / "intact_local_summary_library.json"

    _write_json(canonical_latest, _canonical_latest_payload())
    _write_json(reactome_summary, _reactome_library_payload())
    _write_json(intact_summary, _intact_library_payload())

    library = materialize_protein_summary_library(
        canonical_latest_path=canonical_latest,
        reactome_summary_path=reactome_summary,
        intact_summary_path=intact_summary,
        library_id="summary-library:protein-materialized:test",
    )

    assert library.library_id == "summary-library:protein-materialized:test"
    assert "UniProt:2026-03-23:api:test" in (library.source_manifest_id or "")
    assert "bio-agent-lab/reactome:test" in (library.source_manifest_id or "")
    assert "IntAct:test:download:abc123" in (library.source_manifest_id or "")
    assert library.record_count == 3

    proteins = {record.summary_id: record for record in library.protein_records}
    p12345 = proteins["protein:P12345"]
    p69905 = proteins["protein:P69905"]
    q99999 = proteins["protein:Q99999"]

    assert p12345.protein_name == "Example protein"
    assert p12345.sequence_length == 3
    assert p12345.sequence_checksum == "md5:ABC123"
    assert p12345.join_status == "joined"
    assert p12345.join_reason == "canonical_plus_reactome_plus_intact"
    assert len(p12345.context.pathway_references) == 1
    assert any(ref.namespace == "IntAct" for ref in p12345.context.cross_references)
    assert any(pointer.source_name == "UniProt" for pointer in p12345.context.provenance_pointers)
    assert any(pointer.source_name == "Reactome" for pointer in p12345.context.provenance_pointers)
    assert any(pointer.source_name == "IntAct" for pointer in p12345.context.provenance_pointers)
    assert any(note.startswith("scalar_consensus_policy:") for note in p12345.context.storage_notes)
    summary_note = next(
        note
        for note in p12345.context.storage_notes
        if note.startswith("scalar_consensus_summary:")
    )
    summary_payload = json.loads(summary_note.removeprefix("scalar_consensus_summary:"))
    assert summary_payload["status_counts"]["resolved"] >= 1
    assert summary_payload["status_counts"]["partial"] >= 1
    p12345_consensus = {payload["field"]: payload for payload in _scalar_consensus_payloads(p12345)}
    assert p12345_consensus["protein_name"]["winner_source"] == "UniProt"
    assert p12345_consensus["protein_name"]["status"] == "resolved"
    assert p12345_consensus["protein_name"]["supporting_sources"] == ["Reactome", "IntAct"]
    assert p12345_consensus["sequence_checksum"]["winner_source"] == "UniProt"
    assert p12345_consensus["sequence_checksum"]["status"] == "partial"
    assert p12345_consensus["sequence_checksum"]["partial_reason"] == "single_source_value"
    assert p12345_consensus["aliases"]["status"] == "conflict"
    assert p12345_consensus["aliases"]["disagreeing_sources"] == ["Reactome", "IntAct"]
    p12345_rollups = {payload["field_name"]: payload for payload in _source_rollup_payloads(p12345)}
    assert p12345_rollups["protein_name"]["source_precedence"] == ["UniProt", "Reactome", "IntAct"]
    assert p12345_rollups["protein_name"]["winner_source"] == "UniProt"
    assert p12345_rollups["protein_name"]["corroborating_sources"] == ["Reactome", "IntAct"]
    assert p12345_rollups["aliases"]["disagreeing_sources"] == ["Reactome", "IntAct"]
    p12345_connections = _source_connection_payloads(p12345)
    assert any(
        connection["connection_kind"] == "accession"
        and connection["source_names"] == ["UniProt", "Reactome", "IntAct"]
        and connection["join_mode"] == "direct"
        and connection["bridge_ids"] == ["accession:P12345"]
        for connection in p12345_connections
    )
    assert p12345.context.cross_source_view is not None
    assert p12345.context.cross_source_view.direct_joins

    assert p69905.protein_name == "Hemoglobin subunit alpha"
    assert p69905.join_status == "joined"
    assert p69905.join_reason == "canonical"
    assert any(
        ref.namespace == "InterPro" and ref.identifier == "IPR000971"
        for ref in p69905.context.domain_references
    )
    assert any(
        ref.namespace == "Pfam" and ref.identifier == "PF00042"
        for ref in p69905.context.domain_references
    )
    assert any(
        ref.namespace == "PROSITE" and ref.identifier == "PS01033"
        for ref in p69905.context.motif_references
    )
    assert any(
        ref.namespace == "CATH"
        and ref.identifier == "1.10.490.10"
        and ref.span_start == 2
        and ref.span_end == 142
        for ref in p69905.context.domain_references
    )
    assert any(
        ref.namespace == "SCOPe"
        and ref.identifier == "a.1.1.2"
        and ref.span_start == 2
        and ref.span_end == 142
        for ref in p69905.context.domain_references
    )
    assert "registry_lane:elm=partial" in p69905.context.storage_notes
    assert any(note.startswith("joined_lane:cath=") for note in p69905.context.storage_notes)
    assert any(note.startswith("joined_lane:scope=") for note in p69905.context.storage_notes)
    p69905_rollups = {payload["field_name"]: payload for payload in _source_rollup_payloads(p69905)}
    assert p69905_rollups["protein_name"]["source_precedence"] == ["UniProt", "Reactome", "IntAct"]
    assert p69905_rollups["protein_name"]["winner_source"] == "UniProt"
    assert p69905_rollups["protein_name"]["source_values"] == [
        {"source_name": "UniProt", "value": "Hemoglobin subunit alpha"}
    ]
    assert p69905_rollups["protein_name"]["status"] == "partial"
    p69905_connections = _source_connection_payloads(p69905)
    assert any(
        connection["connection_kind"] == "domain"
        and connection["source_names"] == ["UniProt", "InterPro"]
        and connection["join_mode"] == "direct"
        and "IPR000971" in connection["bridge_ids"]
        for connection in p69905_connections
    )
    assert any(
        connection["connection_kind"] == "structure"
        and connection["source_names"] == ["UniProt", "CATH"]
        and connection["join_mode"] == "indirect"
        and connection["bridge_source"] == "SIFTS"
        for connection in p69905_connections
    )
    assert any(
        connection["connection_kind"] == "motif"
        and connection["source_names"] == ["UniProt", "ELM"]
        and connection["join_mode"] == "partial"
        for connection in p69905_connections
    )
    assert p69905.context.cross_source_view is not None
    assert p69905.context.cross_source_view.direct_joins
    assert p69905.context.cross_source_view.indirect_bridges
    assert p69905.context.cross_source_view.partial_joins

    assert q99999.protein_name == "Second protein"
    assert q99999.join_status == "joined"
    assert q99999.join_reason == "canonical_plus_intact"
    assert any(ref.namespace == "IntAct" for ref in q99999.context.cross_references)
    assert q99999.context.pathway_references == ()
    q99999_consensus = {payload["field"]: payload for payload in _scalar_consensus_payloads(q99999)}
    assert q99999_consensus["protein_name"]["winner_source"] == "UniProt"
    assert q99999_consensus["protein_name"]["status"] == "conflict"
    assert q99999_consensus["protein_name"]["disagreeing_sources"] == ["IntAct"]
    q99999_rollups = {payload["field_name"]: payload for payload in _source_rollup_payloads(q99999)}
    assert q99999_rollups["protein_name"]["disagreeing_sources"] == ["IntAct"]
    assert q99999_rollups["protein_name"]["status"] == "conflict"


def test_materialize_protein_summary_library_cli_writes_json_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    reactome_summary = tmp_path / "artifacts" / "status" / "reactome_local_summary_library.json"
    intact_summary = tmp_path / "artifacts" / "status" / "intact_local_summary_library.json"
    output = tmp_path / "artifacts" / "status" / "protein_summary_library.json"

    _write_json(canonical_latest, _canonical_latest_payload())
    _write_json(reactome_summary, _reactome_library_payload())
    _write_json(intact_summary, _intact_library_payload())

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "materialize_protein_summary_library.py"),
            "--canonical-latest",
            str(canonical_latest),
            "--reactome-summary",
            str(reactome_summary),
            "--intact-summary",
            str(intact_summary),
            "--local-registry-summary",
            str(repo_root / "data" / "raw" / "local_registry_runs" / "LATEST.json"),
            "--output",
            str(output),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert payload == saved
    assert payload["library_id"] == "summary-library:protein-materialized:v1"
    assert payload["record_count"] == 3
    assert any(record["summary_id"] == "protein:P12345" for record in payload["records"])
    assert any(record["summary_id"] == "protein:P69905" for record in payload["records"])
    assert any(
        note.startswith("scalar_consensus:")
        for record in payload["records"]
        for note in record["notes"]
    )
    p69905_record = next(
        record for record in payload["records"] if record["summary_id"] == "protein:P69905"
    )
    assert any(
        ref["namespace"] == "CATH" and ref["identifier"] == "1.10.490.10"
        for ref in p69905_record["context"]["domain_references"]
    )
    assert any(
        rollup["field_name"] == "protein_name" and rollup["winner_source"] == "UniProt"
        for rollup in p69905_record["context"]["source_rollups"]
    )
    assert any(
        connection["connection_kind"] == "structure"
        and connection["source_names"] == ["UniProt", "CATH"]
        for connection in p69905_record["context"]["source_connections"]
    )
    assert p69905_record["context"]["cross_source_view"]["direct_joins"]
    assert p69905_record["context"]["cross_source_view"]["indirect_bridges"]
    assert p69905_record["context"]["cross_source_view"]["partial_joins"]
    assert "registry_lane:elm=partial" in p69905_record["context"]["storage_notes"]
    assert output.exists()
