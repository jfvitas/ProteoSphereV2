from __future__ import annotations

from pathlib import Path

from scripts.affinity_interaction_preview_support import (
    bindingdb_zip_inventory,
    parse_binding_measurement,
    parse_psicquic_tab25,
)


def test_parse_binding_measurement_normalizes_kd_and_derives_delta_g() -> None:
    parsed = parse_binding_measurement("Kd=49uM")

    assert parsed.measurement_type == "Kd"
    assert parsed.relation == "="
    assert parsed.raw_value == 49.0
    assert parsed.raw_unit == "uM"
    assert parsed.normalized_molar is not None
    assert parsed.p_affinity is not None
    assert parsed.delta_g_derived_298k_kcal_per_mol is not None
    assert parsed.derivation_method == "RTlnK_at_298.15K"


def test_parse_binding_measurement_does_not_derive_delta_g_from_ic50() -> None:
    parsed = parse_binding_measurement("IC50=10840nM")

    assert parsed.measurement_type == "IC50"
    assert parsed.normalized_molar is not None
    assert parsed.p_affinity is not None
    assert parsed.delta_g_derived_298k_kcal_per_mol is None


def test_parse_psicquic_tab25_extracts_partner_and_confidence(tmp_path: Path) -> None:
    path = tmp_path / "sample.tab25.txt"
    path.write_text(
        "\t".join(
            [
                "uniprotkb:P09105",
                "uniprotkb:P69905",
                "intact:EBI-1",
                "intact:EBI-2",
                "psi-mi:hbat_human(display_long)",
                "psi-mi:hba_human(display_long)",
                'psi-mi:"MI:0397"(two hybrid array)',
                "Luck et al. (2017)",
                "pubmed:32296183|imex:IM-25472",
                "taxid:9606(human)",
                "taxid:9606(human)",
                'psi-mi:"MI:0915"(physical association)',
                'psi-mi:"MI:0469"(IntAct)',
                "intact:EBI-23498192|imex:IM-25472-65526",
                "author score:0.845733390249|intact-miscore:0.56",
            ]
        ),
        encoding="utf-8",
    )

    rows = parse_psicquic_tab25(path, "P09105")

    assert len(rows) == 1
    assert rows[0]["partner_ref"] == "uniprotkb:P69905"
    assert rows[0]["confidence_scores"]["intact-miscore"] == 0.56


def test_bindingdb_zip_inventory_reports_mysql_dump() -> None:
    inventory = bindingdb_zip_inventory(
        Path(
            r"D:\documents\ProteoSphereV2\data\raw\local_copies\bindingdb\BDB-mySQL_All_202603_dmp.zip"
        )
    )

    assert inventory["has_mysql_dump"] is True
    assert inventory["entry_count"] >= 2
