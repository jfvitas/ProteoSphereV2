from __future__ import annotations

import json
from pathlib import Path

from execution.materialization.raw_canonical_materializer import (
    load_alphafold_records,
    load_bindingdb_local_assay_rows,
    materialize_raw_bootstrap_to_canonical,
    resolve_bindingdb_local_summary_path,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_load_alphafold_records_uses_first_record_only_by_default(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    prediction_path = (
        root
        / "data"
        / "raw"
        / "alphafold"
        / "20260323T000000Z"
        / "P12345"
        / "P12345.prediction.json"
    )
    _write_json(
        prediction_path,
        [
            {
                "modelEntityId": "AF-P12345-F1",
                "uniprotAccession": "P12345",
                "sequence": "MKT",
                "globalMetricValue": 90.0,
                "providerId": "GDM",
                "toolUsed": "AlphaFold",
            },
            {
                "modelEntityId": "AF-P12345-2-F1",
                "uniprotAccession": "P12345-2",
                "sequence": "MKTA",
                "globalMetricValue": 80.0,
                "providerId": "GDM",
                "toolUsed": "AlphaFold",
            },
        ],
    )
    summary = {
        "generated_at": "2026-03-23T00:00:00+00:00",
        "results": [
            {
                "source": "alphafold",
                "downloaded_files": [
                    "data/raw/alphafold/20260323T000000Z/P12345/P12345.prediction.json"
                ],
                "manifest": {
                    "source_name": "AlphaFold DB",
                    "release_version": "2026-03-23",
                    "retrieval_mode": "api",
                    "source_locator": "https://alphafold.ebi.ac.uk/api/prediction",
                    "local_artifact_refs": [],
                    "provenance": ["raw_bootstrap"],
                },
            }
        ],
    }

    records = load_alphafold_records(summary, repo_root=root)

    assert len(records) == 1
    assert records[0].qualifier == "P12345"
    assert records[0].model_entity_id == "AF-P12345-F1"


def test_materialize_raw_bootstrap_to_canonical_writes_store_and_report(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    bootstrap_summary = root / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    local_registry_summary = root / "data" / "raw" / "local_registry_runs" / "LATEST.json"
    canonical_root = root / "data" / "canonical"

    _write_json(
        root / "data" / "raw" / "uniprot" / "20260323T000000Z" / "P12345" / "P12345.json",
        {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P12345",
            "uniProtkbId": "P12345_HUMAN",
            "organism": {"scientificName": "Homo sapiens"},
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Example protein"}}},
            "genes": [{"geneName": {"value": "EX1"}}],
            "sequence": {"value": "MKT", "length": 3},
        },
    )
    _write_json(
        root
        / "data"
        / "raw"
        / "bindingdb"
        / "20260323T000000Z"
        / "P12345"
        / "P12345.bindingdb.json",
        {
            "getLindsByUniprotResponse": {
                "bdb.primary": "P12345",
                "bdb.affinities": [
                    {
                        "BindingDB Reactant_set_id": "rs1",
                        "bdb.monomerid": "100",
                        "bdb.affinity_type": "IC50",
                        "bdb.affinity": "10.0",
                    }
                ],
            }
        },
    )
    _write_json(
        root
        / "data"
        / "raw"
        / "alphafold"
        / "20260323T000000Z"
        / "P12345"
        / "P12345.prediction.json",
        [
            {
                "modelEntityId": "AF-P12345-F1",
                "entryId": "AF-P12345-F1",
                "uniprotAccession": "P12345",
                "uniprotId": "P12345_HUMAN",
                "sequence": "MKT",
                "uniprotSequence": "MKT",
                "globalMetricValue": 90.0,
                "providerId": "GDM",
                "toolUsed": "AlphaFold",
                "pdbUrl": "https://example.test/p12345.pdb",
            }
        ],
    )
    (root / "data" / "raw" / "alphafold" / "20260323T000000Z" / "P12345" / "P12345.pdb").write_text(
        "MODEL 1",
        encoding="utf-8",
    )

    _write_json(
        bootstrap_summary,
        {
            "generated_at": "2026-03-23T00:00:00+00:00",
            "results": [
                {
                    "source": "uniprot",
                    "downloaded_files": [
                        "data/raw/uniprot/20260323T000000Z/P12345/P12345.json"
                    ],
                    "manifest": {
                        "source_name": "UniProt",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://rest.uniprot.org/uniprotkb",
                        "local_artifact_refs": [],
                        "provenance": ["raw_bootstrap"],
                    },
                },
                {
                    "source": "bindingdb",
                    "downloaded_files": [
                        "data/raw/bindingdb/20260323T000000Z/P12345/P12345.bindingdb.json"
                    ],
                    "manifest": {
                        "source_name": "BindingDB",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://www.bindingdb.org/rest/getLigandsByUniprot",
                        "local_artifact_refs": [],
                        "provenance": ["raw_bootstrap"],
                    },
                },
                {
                    "source": "alphafold",
                    "downloaded_files": [
                        "data/raw/alphafold/20260323T000000Z/P12345/P12345.prediction.json",
                        "data/raw/alphafold/20260323T000000Z/P12345/P12345.pdb",
                    ],
                    "manifest": {
                        "source_name": "AlphaFold DB",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://alphafold.ebi.ac.uk/api/prediction",
                        "local_artifact_refs": [],
                        "provenance": ["raw_bootstrap"],
                    },
                },
                {
                    "source": "rcsb_pdbe",
                    "downloaded_files": [],
                    "manifest": {
                        "source_name": "RCSB/PDBe",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://www.ebi.ac.uk/pdbe/api/mappings/best_structures",
                        "local_artifact_refs": [],
                        "provenance": ["raw_bootstrap"],
                    },
                },
            ],
        },
    )
    _write_json(
        local_registry_summary,
        {
            "stamp": "20260323T000100Z",
            "selected_source_count": 3,
            "imported_source_count": 3,
        },
    )

    result = materialize_raw_bootstrap_to_canonical(
        bootstrap_summary_path=bootstrap_summary,
        canonical_root=canonical_root,
        local_registry_summary_path=local_registry_summary,
        bindingdb_local_summary_path=None,
        run_id="test-run",
    )

    assert result.status in {"ready", "partial"}
    assert result.created_at
    assert result.sequence_result.canonical_ids == ("protein:P12345",)
    assert len(result.assay_result.canonical_assays) == 1
    assert len(result.structure_result.chains) >= 1
    assert result.record_counts["protein"] == 1
    assert result.record_counts["assay"] == 1
    assert result.unresolved_counts["assay_unresolved_cases"] == 0
    assert result.bindingdb_selection["selected_summary_path"] is None
    assert result.bindingdb_selection["selection_mode"] == "rest_fallback"
    assert result.bindingdb_selection["rest_payload_count"] == 1
    assert result.canonical_store.get("protein:P12345") is not None
    assert any(item["source"] == "rcsb_pdbe" for item in result.skipped_sources)
    assert (canonical_root / "runs" / "test-run" / "canonical_store.json").exists()
    assert (canonical_root / "LATEST.json").exists()


def test_load_bindingdb_local_assay_rows_filters_by_accession(tmp_path: Path) -> None:
    summary = tmp_path / "bindingdb_dump_local" / "LATEST.json"
    _write_json(
        summary,
        {
            "slices": [
                {
                    "accession": "P12345",
                    "assay_rows": [
                        {
                            "BindingDB Reactant_set_id": "RS1",
                            "BindingDB MonomerID": "100",
                            "UniProtKB/SwissProt": "P12345",
                            "Affinity Type": "IC50",
                            "affinity_value_nM": "10.0",
                        }
                    ],
                },
                {
                    "accession": "Q99999",
                    "assay_rows": [
                        {
                            "BindingDB Reactant_set_id": "RS2",
                            "BindingDB MonomerID": "200",
                            "UniProtKB/SwissProt": "Q99999",
                            "Affinity Type": "Ki",
                            "affinity_value_nM": "3.0",
                        }
                    ],
                },
            ]
        },
    )

    rows = load_bindingdb_local_assay_rows(summary, accessions=("P12345",))

    assert len(rows) == 1
    assert rows[0]["BindingDB Reactant_set_id"] == "RS1"


def test_materialize_raw_bootstrap_to_canonical_surfaces_bindingdb_selection_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    bootstrap_summary = root / "data" / "raw" / "bootstrap_runs" / "LATEST.json"
    canonical_root = root / "data" / "canonical"
    local_summary = root / "data" / "raw" / "bindingdb_dump_local" / "LATEST.json"

    _write_json(
        root / "data" / "raw" / "uniprot" / "20260323T000000Z" / "P12345" / "P12345.json",
        {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P12345",
            "uniProtkbId": "P12345_HUMAN",
            "organism": {"scientificName": "Homo sapiens"},
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Example protein"}}},
            "genes": [{"geneName": {"value": "EX1"}}],
            "sequence": {"value": "MKT", "length": 3},
        },
    )
    _write_json(
        root
        / "data"
        / "raw"
        / "bindingdb"
        / "20260323T000000Z"
        / "P12345"
        / "P12345.bindingdb.json",
        {
            "getLindsByUniprotResponse": {
                "bdb.primary": "P12345",
                "bdb.affinities": [
                    {
                        "BindingDB Reactant_set_id": "rs-rest",
                        "bdb.monomerid": "100",
                        "bdb.affinity_type": "IC50",
                        "bdb.affinity": "10.0",
                    }
                ],
            }
        },
    )
    _write_json(
        bootstrap_summary,
        {
            "generated_at": "2026-03-23T00:00:00+00:00",
            "results": [
                {
                    "source": "uniprot",
                    "downloaded_files": [
                        "data/raw/uniprot/20260323T000000Z/P12345/P12345.json"
                    ],
                    "manifest": {
                        "source_name": "UniProt",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://rest.uniprot.org/uniprotkb",
                        "local_artifact_refs": [],
                        "provenance": ["raw_bootstrap"],
                    },
                },
                {
                    "source": "bindingdb",
                    "downloaded_files": [
                        "data/raw/bindingdb/20260323T000000Z/P12345/P12345.bindingdb.json"
                    ],
                    "manifest": {
                        "source_name": "BindingDB",
                        "release_version": "2026-03-23",
                        "retrieval_mode": "api",
                        "source_locator": "https://www.bindingdb.org/rest/getLigandsByUniprot",
                        "local_artifact_refs": [],
                        "provenance": ["raw_bootstrap"],
                    },
                },
            ],
        },
    )

    _write_json(local_summary, {"slices": []})

    fallback_result = materialize_raw_bootstrap_to_canonical(
        bootstrap_summary_path=bootstrap_summary,
        canonical_root=canonical_root,
        bindingdb_local_summary_path=local_summary,
        local_registry_summary_path=None,
        run_id="selection-fallback",
    )

    assert fallback_result.bindingdb_selection["selection_mode"] == "rest_fallback"
    assert fallback_result.bindingdb_selection["local_row_count"] == 0
    assert fallback_result.bindingdb_selection["rest_payload_count"] == 1
    assert fallback_result.bindingdb_selection["matched_accession_count"] == 0

    _write_json(
        local_summary,
        {
            "slices": [
                {
                    "accession": "P12345",
                    "assay_row_count": 1,
                    "measurement_result_count": 1,
                    "assay_rows": [
                        {
                            "BindingDB Reactant_set_id": "RS1",
                            "BindingDB MonomerID": "100",
                            "UniProtKB/SwissProt": "P12345",
                            "Affinity Type": "IC50",
                            "affinity_value_nM": "10.0",
                        }
                    ],
                }
            ]
        },
    )

    local_result = materialize_raw_bootstrap_to_canonical(
        bootstrap_summary_path=bootstrap_summary,
        canonical_root=canonical_root,
        bindingdb_local_summary_path=local_summary,
        local_registry_summary_path=None,
        run_id="selection-local",
    )

    assert local_result.bindingdb_selection["selection_mode"] == "local_summary"
    assert local_result.bindingdb_selection["local_row_count"] == 1
    assert local_result.bindingdb_selection["rest_payload_count"] == 1
    assert local_result.bindingdb_selection["matched_accession_count"] == 1
    assert local_result.bindingdb_selection["summary_assay_row_count"] == 1
    assert local_result.bindingdb_selection["selected_summary_path"] == (
        "data\\raw\\bindingdb_dump_local\\LATEST.json"
    )


def test_resolve_bindingdb_local_summary_path_prefers_richer_matching_summary(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bindingdb_dump_local"
    latest_summary = root / "LATEST.json"
    narrow_summary = root / "bindingdb-gap-probe-20260323T1632Z" / "summary.json"
    rich_summary = root / "bindingdb-local-20260323" / "summary.json"

    _write_json(
        latest_summary,
        {
            "slices": [
                {
                    "accession": "Q9NZD4",
                    "assay_row_count": 0,
                    "measurement_result_count": 0,
                    "assay_rows": [],
                }
            ]
        },
    )
    _write_json(
        narrow_summary,
        {
            "slices": [
                {
                    "accession": "Q9NZD4",
                    "assay_row_count": 0,
                    "measurement_result_count": 0,
                    "assay_rows": [],
                }
            ]
        },
    )
    _write_json(
        rich_summary,
        {
            "slices": [
                {
                    "accession": "P04637",
                    "assay_row_count": 66,
                    "measurement_result_count": 66,
                    "assay_rows": [
                        {
                            "BindingDB Reactant_set_id": "RS1",
                            "BindingDB MonomerID": "100",
                            "UniProtKB/SwissProt": "P04637",
                            "Affinity Type": "IC50",
                            "affinity_value_nM": "10.0",
                        }
                    ],
                },
                {
                    "accession": "P31749",
                    "assay_row_count": 5072,
                    "measurement_result_count": 5069,
                    "assay_rows": [
                        {
                            "BindingDB Reactant_set_id": "RS2",
                            "BindingDB MonomerID": "200",
                            "UniProtKB/SwissProt": "P31749",
                            "Affinity Type": "Ki",
                            "affinity_value_nM": "3.0",
                        }
                    ],
                },
            ]
        },
    )

    resolved = resolve_bindingdb_local_summary_path(
        latest_summary,
        accessions=("P04637", "P31749"),
    )

    assert resolved == rich_summary
