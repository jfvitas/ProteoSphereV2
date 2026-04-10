from __future__ import annotations

import pytest

from features.assay_features import (
    DEFAULT_ASSAY_FEATURE_NAMES,
    AssayFeatureRecord,
    AssayFeatureSummary,
    extract_assay_row_features,
    summarize_assay_features,
)


def test_extract_assay_row_features_normalizes_bindingdb_style_rows() -> None:
    row = {
        "accession": " P31749 ",
        "bindingdb_measurement_technique": " Enzyme Inhibition ",
        "bindingdb_assay_name": "  Assay A  ",
        "reported_pH": "7.4",
        "reported_temperature_celsius": "310.15",
        "assay_context": {
            "i_conc_range": "100 uM to 20 pM",
            "e_conc_range": "",
            "s_conc_range": "200 nM",
        },
        "source_name": " BindingDB local dump ",
        "source_record_id": " 1001 ",
        "candidate_only": "yes",
    }

    record = extract_assay_row_features(row)

    assert isinstance(record, AssayFeatureRecord)
    assert record.accession == "P31749"
    assert record.measurement_technique == "Enzyme Inhibition"
    assert record.assay_name == "Assay A"
    assert record.reported_pH == 7.4
    assert record.reported_temperature_celsius == 310.15
    assert record.i_conc_range == "100 uM to 20 pM"
    assert record.e_conc_range is None
    assert record.s_conc_range == "200 nM"
    assert record.source_name == "BindingDB local dump"
    assert record.source_record_id == "1001"
    assert record.candidate_only is True
    assert record.condition_flags == {
        "reported_pH": True,
        "reported_temperature_celsius": True,
        "i_conc_range": True,
        "e_conc_range": False,
        "s_conc_range": True,
    }
    assert record.feature_names == DEFAULT_ASSAY_FEATURE_NAMES
    assert record.feature_vector[0] == "P31749"
    assert record.to_dict()["candidate_only"] is True


def test_summarize_assay_features_aggregates_condition_counts_and_ranges() -> None:
    rows = [
        {
            "accession": "P31749",
            "bindingdb_measurement_technique": "Enzyme Inhibition",
            "bindingdb_assay_name": "Assay A",
            "reported_pH": 7.4,
            "reported_temperature_celsius": 295.15,
            "assay_context": {
                "i_conc_range": "100 uM to 20 pM",
                "e_conc_range": None,
                "s_conc_range": "200 nM",
            },
            "candidate_only": False,
        },
        {
            "accession": "P31749",
            "bindingdb_measurement_technique": "Enzyme Inhibition",
            "bindingdb_assay_name": "Assay B",
            "reported_pH": 7.5,
            "reported_temperature_celsius": 298.15,
            "assay_context": {
                "i_conc_range": None,
                "e_conc_range": "1 nM",
                "s_conc_range": None,
            },
            "candidate_only": True,
        },
    ]

    summary = summarize_assay_features(rows)

    assert isinstance(summary, AssayFeatureSummary)
    assert summary.accession == "P31749"
    assert summary.row_count == 2
    assert summary.measurement_techniques == ("Enzyme Inhibition",)
    assert summary.assay_names == ("Assay A", "Assay B")
    assert summary.source_names == ()
    assert summary.rows_with_reported_pH == 2
    assert summary.rows_with_reported_temperature == 2
    assert summary.i_conc_range_count == 1
    assert summary.e_conc_range_count == 1
    assert summary.s_conc_range_count == 1
    assert summary.candidate_only_count == 1
    assert summary.reported_pH_range == (7.4, 7.5)
    assert summary.reported_temperature_celsius_range == (295.15, 298.15)
    assert summary.has_condition_data is True
    assert summary.to_dict()["row_count"] == 2
    assert summary.to_dict()["rows"][1]["candidate_only"] is True


def test_summarize_assay_features_rejects_mixed_accessions_without_filter() -> None:
    with pytest.raises(ValueError, match="single accession"):
        summarize_assay_features(
            [
                {
                    "accession": "P31749",
                    "reported_pH": 7.4,
                },
                {
                    "accession": "P04637",
                    "reported_pH": 7.5,
                },
            ]
        )
