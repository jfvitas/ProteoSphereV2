from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.affinity_interaction_preview_support import (
    build_bindingdb_subset_measurements,
    find_table_tuples_containing,
    split_sql_tuple_values,
)
from scripts.export_binding_measurement_registry_preview import (
    build_binding_measurement_registry_preview,
)
from scripts.export_bindingdb_accession_assay_profile_preview import (
    build_bindingdb_accession_assay_profile_preview,
)
from scripts.export_bindingdb_accession_partner_identity_profile_preview import (
    build_bindingdb_accession_partner_identity_profile_preview,
)
from scripts.export_bindingdb_assay_condition_profile_preview import (
    build_bindingdb_assay_condition_profile_preview,
)
from scripts.export_bindingdb_future_structure_alignment_preview import (
    build_bindingdb_future_structure_alignment_preview,
)
from scripts.export_bindingdb_future_structure_registry_preview import (
    build_bindingdb_future_structure_registry_preview,
)
from scripts.export_bindingdb_future_structure_triage_preview import (
    build_bindingdb_future_structure_triage_preview,
)
from scripts.export_bindingdb_measurement_subset_preview import (
    build_bindingdb_measurement_subset_preview,
)
from scripts.export_bindingdb_off_target_adjacent_context_profile_preview import (
    build_bindingdb_off_target_adjacent_context_profile_preview,
)
from scripts.export_bindingdb_off_target_target_profile_preview import (
    build_bindingdb_off_target_target_profile_preview,
)
from scripts.export_bindingdb_partner_descriptor_reconciliation_preview import (
    build_bindingdb_partner_descriptor_reconciliation_preview,
)
from scripts.export_bindingdb_partner_monomer_context_preview import (
    build_bindingdb_partner_monomer_context_preview,
)
from scripts.export_bindingdb_structure_assay_summary_preview import (
    build_bindingdb_structure_assay_summary_preview,
)
from scripts.export_bindingdb_structure_bridge_preview import (
    build_bindingdb_structure_bridge_preview,
)
from scripts.export_bindingdb_structure_grounding_candidate_preview import (
    build_bindingdb_structure_grounding_candidate_preview,
)
from scripts.export_bindingdb_structure_measurement_projection_preview import (
    build_bindingdb_structure_measurement_projection_preview,
)
from scripts.export_bindingdb_structure_partner_profile_preview import (
    build_bindingdb_structure_partner_profile_preview,
)
from scripts.export_bindingdb_target_polymer_context_preview import (
    build_bindingdb_target_polymer_context_preview,
)


def _make_bindingdb_zip(tmp_path: Path) -> Path:
    zip_path = tmp_path / "bindingdb.zip"
    polymer_create = (
        "CREATE TABLE `polymer` ("
        "`component_id` bigint DEFAULT NULL, "
        "`comments` varchar(1000) DEFAULT NULL, "
        "`topology` varchar(200) DEFAULT NULL, "
        "`weight` varchar(200) DEFAULT NULL, "
        "`source_organism` varchar(200) DEFAULT NULL, "
        "`unpid2` varchar(300) DEFAULT NULL, "
        "`scientific_name` varchar(200) DEFAULT NULL, "
        "`type` varchar(200) DEFAULT NULL, "
        "`display_name` varchar(200) DEFAULT NULL, "
        "`res_count` int DEFAULT NULL, "
        "`sequence` text, "
        "`n_pdb_ids` int DEFAULT NULL, "
        "`taxid` varchar(200) DEFAULT NULL, "
        "`unpid1` varchar(300) DEFAULT NULL, "
        "`polymerid` int NOT NULL, "
        "`pdb_ids` varchar(4000) DEFAULT NULL, "
        "`short_name` varchar(20) DEFAULT NULL, "
        "`common_name` varchar(200) DEFAULT NULL, "
        "`chembl_id` varchar(20) DEFAULT NULL"
        ") ENGINE=InnoDB;"
    )
    polymer_insert = (
        "INSERT INTO `polymer` VALUES "
        "(NULL,NULL,'Linear','15264.42','Human',NULL,'Homo sapiens',"
        "'PROTEIN','Hemoglobin subunit alpha',142,'SEQ',241,'9606',"
        "'P69905',50001268,'1Y01,4HHB',NULL,NULL,NULL),"
        "(NULL,NULL,'Linear','55681.25','Human',NULL,'Homo sapiens',"
        "'Enzyme','RAC-alpha serine/threonine-protein kinase',480,'SEQ2',"
        "48,'9606','P31749',513,'4LXM,3QBH',NULL,NULL,NULL);"
    )
    pdb_bdb_create = (
        "CREATE TABLE `pdb_bdb` ("
        "`pdbid` char(4) NOT NULL, "
        "`reactant_set_id_str` text, "
        "`reactant_set_id_90` text, "
        "`itc_result_a_b_ab_id_90` varchar(4000) DEFAULT NULL, "
        "`monomerid_str_90` text, "
        "`monomerid_str` text, "
        "`polymerid_str` text, "
        "`complexid_str` varchar(4000) DEFAULT NULL, "
        "`itc_result_a_b_ab_id_str` varchar(4000) DEFAULT NULL"
        ") ENGINE=InnoDB;"
    )
    pdb_bdb_insert = (
        "INSERT INTO `pdb_bdb` VALUES "
        "('1Y01',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),"
        "('4HHB',NULL,NULL,NULL,NULL,'50155537','50001268,50001270',"
        "'50001066',NULL);"
    )
    entry_create = (
        "CREATE TABLE `entry` ("
        "`depoid` varchar(100) DEFAULT NULL, "
        "`comments` varchar(1000) DEFAULT NULL, "
        "`entrydate` datetime DEFAULT NULL, "
        "`entrytitle` varchar(300) NOT NULL, "
        "`entrantid` int DEFAULT NULL, "
        "`revised` varchar(1000) DEFAULT NULL, "
        "`entryid` int NOT NULL, "
        "`meas_tech` varchar(200) NOT NULL, "
        "`hold` varchar(20) DEFAULT NULL, "
        "`ezid` varchar(50) DEFAULT NULL"
        ") ENGINE=InnoDB;"
    )
    entry_insert = (
        "INSERT INTO `entry` VALUES "
        "(NULL,NULL,NULL,'Hemoglobin Î± test entry',NULL,NULL,10,'SPR',NULL,NULL);"
    )
    assay_create = (
        "CREATE TABLE `assay` ("
        "`assayid` int NOT NULL, "
        "`description` varchar(4000) DEFAULT NULL, "
        "`assay_name` varchar(200) DEFAULT NULL, "
        "`entryid` int NOT NULL"
        ") ENGINE=InnoDB;"
    )
    assay_insert = (
        "INSERT INTO `assay` VALUES "
        "(3,'competition experiment','hb-alpha assay',10);"
    )
    enzyme_reactant_set_create = (
        "CREATE TABLE `enzyme_reactant_set` ("
        "`enzyme` varchar(200) DEFAULT NULL, "
        "`comments` varchar(1000) DEFAULT NULL, "
        "`sources` tinyint DEFAULT NULL, "
        "`reactant_set_id` int NOT NULL, "
        "`inhibitor_complexid` int DEFAULT NULL, "
        "`inhibitor_polymerid` int DEFAULT NULL, "
        "`entryid` int NOT NULL, "
        "`e_prep` varchar(1000) DEFAULT NULL, "
        "`enzyme_monomerid` int DEFAULT NULL, "
        "`substrate_monomerid` int DEFAULT NULL, "
        "`inhibitor` varchar(250) DEFAULT NULL, "
        "`s_prep` varchar(1000) DEFAULT NULL, "
        "`inhibitor_monomerid` int DEFAULT NULL, "
        "`enzyme_complexid` int DEFAULT NULL, "
        "`substrate_complexid` int DEFAULT NULL, "
        "`substrate_polymerid` int DEFAULT NULL, "
        "`enzyme_polymerid` int DEFAULT NULL, "
        "`category` varchar(200) DEFAULT NULL, "
        "`substrate` varchar(200) DEFAULT NULL, "
        "`i_prep` varchar(1000) DEFAULT NULL"
        ") ENGINE=InnoDB;"
    )
    enzyme_reactant_set_insert = (
        "INSERT INTO `enzyme_reactant_set` VALUES "
        "('Hemoglobin alpha',NULL,NULL,91,NULL,NULL,10,NULL,NULL,NULL,"
        "'BDBM1',NULL,50155537,NULL,NULL,NULL,50001268,'enzyme',NULL,NULL);"
    )
    ki_result_create = (
        "CREATE TABLE `ki_result` ("
        "`kd_uncert` varchar(10) DEFAULT NULL, "
        "`ic50` varchar(15) DEFAULT NULL, "
        "`ki_result_id` int NOT NULL, "
        "`koff_uncert` varchar(10) DEFAULT NULL, "
        "`reactant_set_id` int NOT NULL, "
        "`kon` varchar(15) DEFAULT NULL, "
        "`solution_id` int DEFAULT NULL, "
        "`ic_percent` decimal(10,4) DEFAULT NULL, "
        "`vmax_uncert` decimal(10,4) DEFAULT NULL, "
        "`delta_g` decimal(10,4) DEFAULT NULL, "
        "`k_cat` decimal(10,4) DEFAULT NULL, "
        "`k_cat_uncert` decimal(10,4) DEFAULT NULL, "
        "`ec50` varchar(15) DEFAULT NULL, "
        "`koff` varchar(15) DEFAULT NULL, "
        "`data_fit_meth_id` int DEFAULT NULL, "
        "`ic_percent_def` varchar(200) DEFAULT NULL, "
        "`kd` varchar(15) DEFAULT NULL, "
        "`vmax` decimal(10,4) DEFAULT NULL, "
        "`ph_uncert` decimal(10,4) DEFAULT NULL, "
        "`e_conc_range` varchar(100) DEFAULT NULL, "
        "`ec50_uncert` varchar(10) DEFAULT NULL, "
        "`press` decimal(10,4) DEFAULT NULL, "
        "`i_conc_range` varchar(100) DEFAULT NULL, "
        "`temp_uncert` decimal(10,4) DEFAULT NULL, "
        "`ki` varchar(15) DEFAULT NULL, "
        "`kon_uncert` varchar(10) DEFAULT NULL, "
        "`temp` decimal(10,4) DEFAULT NULL, "
        "`km` decimal(20,4) DEFAULT NULL, "
        "`comments` varchar(1000) DEFAULT NULL, "
        "`instrumentid` int DEFAULT NULL, "
        "`assayid` int DEFAULT NULL, "
        "`ic50_uncert` varchar(10) DEFAULT NULL, "
        "`biological_data` varchar(200) DEFAULT NULL, "
        "`entryid` int NOT NULL, "
        "`delta_g_uncert` decimal(10,4) DEFAULT NULL, "
        "`s_conc_range` varchar(100) DEFAULT NULL, "
        "`km_uncert` decimal(20,4) DEFAULT NULL, "
        "`ki_uncert` varchar(10) DEFAULT NULL, "
        "`ph` decimal(10,4) DEFAULT NULL, "
        "`ic_percent_uncert` decimal(10,4) DEFAULT NULL, "
        "`press_uncert` decimal(10,4) DEFAULT NULL"
        ") ENGINE=InnoDB;"
    )
    ki_result_insert = (
        "INSERT INTO `ki_result` VALUES "
        "(NULL,NULL,1001,NULL,91,NULL,NULL,NULL,NULL,-8.1000,NULL,NULL,NULL,NULL,"
        "NULL,NULL,'0.48',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'0.24',NULL,310.1500,"
        "NULL,'local bindingdb test',NULL,3,NULL,'yes',10,NULL,NULL,NULL,NULL,"
        "7.4000,NULL,NULL);"
    )
    monomer_create = (
        "CREATE TABLE `monomer` ("
        "`n_pdb_ids_sub` int DEFAULT NULL, "
        "`pdb_ids_exact` text, "
        "`comments` varchar(1000) DEFAULT NULL, "
        "`emp_form` varchar(200) DEFAULT NULL, "
        "`het_pdb` char(7) DEFAULT NULL, "
        "`display_name` varchar(500) DEFAULT NULL, "
        "`inchi_key` varchar(27) DEFAULT NULL, "
        "`pdb_ids_sub` text, "
        "`chembl_id` varchar(20) DEFAULT NULL, "
        "`monomerid` int NOT NULL, "
        "`inchi` text, "
        "`weight` varchar(200) DEFAULT NULL, "
        "`type` varchar(200) DEFAULT NULL, "
        "`n_pdb_ids_exact` int DEFAULT NULL, "
        "`smiles_string` text, "
        "`rdmid` int DEFAULT NULL"
        ") ENGINE=InnoDB;"
    )
    monomer_insert = (
        "INSERT INTO `monomer` VALUES "
        "(NULL,'1Y01,4HHB',NULL,NULL,NULL,'Test ligand',NULL,NULL,NULL,50155537,"
        "NULL,NULL,'Small molecule',2,NULL,NULL);"
    )
    dump_text = "\n".join(
        [
            polymer_create,
            polymer_insert,
            pdb_bdb_create,
            pdb_bdb_insert,
            entry_create,
            entry_insert,
            assay_create,
            assay_insert,
            enzyme_reactant_set_create,
            enzyme_reactant_set_insert,
            ki_result_create,
            ki_result_insert,
            monomer_create,
            monomer_insert,
        ]
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("BDB-mySQL_All_202603.dmp", dump_text)
    return zip_path


def test_split_sql_tuple_values_handles_null_and_strings() -> None:
    values = split_sql_tuple_values("('4HHB',NULL,'50155537','50001268,50001270','50001066')")
    assert values == ["4HHB", None, "50155537", "50001268,50001270", "50001066"]


def test_find_table_tuples_containing_finds_needles(tmp_path: Path) -> None:
    zip_path = _make_bindingdb_zip(tmp_path)
    matched = find_table_tuples_containing(zip_path, "pdb_bdb", ["'4HHB'"])
    assert matched["'4HHB'"][0] == "4HHB"
    assert matched["'4HHB'"][5] == "50155537"


def test_build_bindingdb_target_polymer_context_preview(tmp_path: Path) -> None:
    zip_path = _make_bindingdb_zip(tmp_path)
    payload = build_bindingdb_target_polymer_context_preview(
        zip_path,
        {"rows": [{"accession": "P69905"}, {"accession": "P00387"}]},
    )
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P69905"]["bindingdb_polymer_presence"] == "present"
    assert rows["P69905"]["bindingdb_polymer_id"] == "50001268"
    assert "1Y01" in rows["P69905"]["bindingdb_pdb_ids_sample"]
    assert rows["P00387"]["bindingdb_polymer_presence"] == "absent"


def test_build_bindingdb_structure_bridge_preview(tmp_path: Path) -> None:
    zip_path = _make_bindingdb_zip(tmp_path)
    payload = build_bindingdb_structure_bridge_preview(
        zip_path,
        {"rows": [{"structure_id": "1Y01"}, {"structure_id": "4HHB"}]},
    )
    rows = {row["structure_id"]: row for row in payload["rows"]}
    assert rows["1Y01"]["bindingdb_bridge_status"] == "present"
    assert rows["1Y01"]["bindingdb_monomer_ids"] == []
    assert rows["4HHB"]["bindingdb_bridge_status"] == "present"
    assert rows["4HHB"]["bindingdb_monomer_ids"] == ["50155537"]
    assert rows["4HHB"]["bindingdb_polymer_ids"] == ["50001268", "50001270"]


def test_build_bindingdb_subset_measurements_materializes_ki_kd_and_delta_g(
    tmp_path: Path,
) -> None:
    zip_path = _make_bindingdb_zip(tmp_path)
    rows = build_bindingdb_subset_measurements(
        zip_path,
        [
            {
                "accession": "P69905",
                "bindingdb_polymer_presence": "present",
                "bindingdb_polymer_id": "50001268",
            }
        ],
    )
    assert [row["measurement_type"] for row in rows] == ["Ki", "Kd", "ΔG"]
    assert {row["accession"] for row in rows} == {"P69905"}
    assert rows[0]["bindingdb_target_role"] == "enzyme"
    assert rows[0]["bindingdb_assay_name"] == "hb-alpha assay"
    assert rows[0]["bindingdb_measurement_technique"] == "SPR"
    assert rows[0]["reported_temperature_celsius"] == 310.15
    assert rows[0]["reported_pH"] == 7.4
    assert rows[0]["bindingdb_partner_monomer_names"] == ["Test ligand"]
    assert rows[0]["confidence_for_normalization"] == "bindingdb_exact_value_without_unit"
    assert rows[2]["delta_g_reported_kcal_per_mol"] == -8.1


def test_build_bindingdb_measurement_subset_preview_summarizes_accessions(
    tmp_path: Path,
) -> None:
    zip_path = _make_bindingdb_zip(tmp_path)
    payload = build_bindingdb_measurement_subset_preview(
        zip_path,
        {
            "rows": [
                {
                    "accession": "P69905",
                    "bindingdb_polymer_presence": "present",
                    "bindingdb_polymer_id": "50001268",
                }
            ]
        },
    )
    assert payload["row_count"] == 3
    assert payload["summary"]["accessions_with_bindingdb_measurements"] == 1
    assert payload["summary"]["measurement_type_counts"]["Ki"] == 1
    assert payload["summary"]["measurement_type_counts"]["Kd"] == 1
    assert payload["summary"]["measurement_type_counts"]["ΔG"] == 1


def test_build_binding_measurement_registry_preview_includes_bindingdb_subset(
    tmp_path: Path,
) -> None:
    zip_path = _make_bindingdb_zip(tmp_path)
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    for filename in (
        "INDEX_general_PL.2020R1.lst",
        "INDEX_general_PP.2020R1.lst",
        "INDEX_general_PN.2020R1.lst",
        "INDEX_general_NL.2020R1.lst",
    ):
        (index_dir / filename).write_text("", encoding="utf-8")

    payload = build_binding_measurement_registry_preview(
        index_dir,
        {
            "rows": [
                {
                    "accession": "P00387",
                    "ligand_identifier": "CHEMBL1",
                    "representative_activity_id": "ACT1",
                    "standard_type": "IC50",
                    "standard_relation": "=",
                    "standard_value": 1.0,
                    "standard_units": "uM",
                    "candidate_only": False,
                    "ligand_ref": "ligand:CHEMBL1",
                    "ligand_label": "Test ligand",
                    "evidence_kind": "local_test",
                }
            ]
        },
        zip_path,
        {
            "rows": [
                {
                    "accession": "P69905",
                    "bindingdb_polymer_presence": "present",
                    "bindingdb_polymer_id": "50001268",
                }
            ]
        },
    )

    assert payload["summary"]["source_counts"]["bindingdb"] == 3
    assert payload["summary"]["source_counts"]["chembl_lightweight"] == 1
    assert payload["row_count"] == 4


def test_build_bindingdb_structure_measurement_projection_preview_projects_to_4hhb() -> None:
    payload = build_bindingdb_structure_measurement_projection_preview(
        {
            "rows": [
                {
                    "structure_id": "1Y01",
                    "mapped_uniprot_accessions": ["Q9NZD4", "P69905"],
                },
                {
                    "structure_id": "4HHB",
                    "mapped_uniprot_accessions": ["P69905", "P68871"],
                },
            ]
        },
        {
            "rows": [
                {
                    "structure_id": "1Y01",
                    "bindingdb_bridge_status": "present",
                    "bindingdb_polymer_ids": [],
                },
                {
                    "structure_id": "4HHB",
                    "bindingdb_bridge_status": "present",
                    "bindingdb_polymer_ids": ["50001268", "50001270"],
                },
            ]
        },
        {
            "rows": [
                {
                    "accession": "P69905",
                    "bindingdb_polymer_id": "50001268",
                    "measurement_type": "Kd",
                    "bindingdb_entry_title": "Entry A",
                    "bindingdb_assay_name": "Assay A",
                    "bindingdb_partner_monomer_names": ["Ligand A"],
                },
                {
                    "accession": "P68871",
                    "bindingdb_polymer_id": "50001270",
                    "measurement_type": "IC50",
                    "bindingdb_entry_title": "Entry B",
                    "bindingdb_assay_name": "Assay B",
                    "bindingdb_partner_monomer_names": ["Ligand B"],
                },
                {
                    "accession": "Q9NZD4",
                    "bindingdb_polymer_id": "99999999",
                    "measurement_type": "Ki",
                    "bindingdb_entry_title": "Entry C",
                    "bindingdb_assay_name": "Assay C",
                    "bindingdb_partner_monomer_names": ["Ligand C"],
                },
            ]
        },
    )
    rows = {row["structure_id"]: row for row in payload["rows"]}
    assert rows["1Y01"]["bindingdb_projection_status"] == "bridge_only_or_absent"
    assert rows["1Y01"]["measurement_count"] == 0
    assert rows["4HHB"]["bindingdb_projection_status"] == "present"
    assert rows["4HHB"]["measurement_count"] == 2
    assert rows["4HHB"]["measurement_type_counts"] == {"IC50": 1, "Kd": 1}
    assert rows["4HHB"]["matched_accessions"] == ["P68871", "P69905"]


def test_build_bindingdb_partner_monomer_context_preview_aggregates_refs() -> None:
    payload = build_bindingdb_partner_monomer_context_preview(
        {
            "rows": [
                {
                    "accession": "P31749",
                    "measurement_id": "m1",
                    "primary_structure_or_target_ref": "protein:P31749",
                    "bindingdb_partner_monomer_refs": [
                        {
                            "monomer_id": "5001",
                            "display_name": "Ligand A",
                            "chembl_id": "CHEMBL1",
                            "het_pdb": "ABC",
                            "type": "Small molecule",
                            "inchi_key_present": True,
                            "smiles_present": True,
                            "pdb_ids_exact_sample": ["4HHB"],
                        }
                    ],
                },
                {
                    "accession": "P31749",
                    "measurement_id": "m2",
                    "primary_structure_or_target_ref": "protein:P31749",
                    "bindingdb_partner_monomer_refs": [
                        {
                            "monomer_id": "5001",
                            "display_name": "Ligand A",
                            "chembl_id": "CHEMBL1",
                            "het_pdb": "ABC",
                            "type": "Small molecule",
                            "inchi_key_present": True,
                            "smiles_present": True,
                            "pdb_ids_exact_sample": ["4HHB"],
                        }
                    ],
                },
            ]
        }
    )
    row = payload["rows"][0]
    assert payload["summary"]["monomer_count"] == 1
    assert row["bindingdb_monomer_id"] == "5001"
    assert row["linked_measurement_count"] == 2
    assert row["linked_accessions"] == ["P31749"]


def test_build_bindingdb_structure_assay_summary_preview_summarizes_projected_rows() -> None:
    payload = build_bindingdb_structure_assay_summary_preview(
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "bindingdb_projection_status": "present",
                    "matched_accessions": ["P68871"],
                    "bindingdb_bridge_polymer_ids": ["50001270"],
                    "measurement_type_counts": {"IC50": 2},
                }
            ]
        },
        {
            "rows": [
                {
                    "accession": "P68871",
                    "bindingdb_polymer_id": "50001270",
                    "bindingdb_assay_name": "Assay A",
                    "bindingdb_measurement_technique": "Enzyme Inhibition",
                    "bindingdb_partner_monomer_refs": [
                        {"display_name": "Ligand A", "monomer_id": "5001"}
                    ],
                },
                {
                    "accession": "P68871",
                    "bindingdb_polymer_id": "50001270",
                    "bindingdb_assay_name": "Assay A",
                    "bindingdb_measurement_technique": "Enzyme Inhibition",
                    "bindingdb_partner_monomer_refs": [
                        {"display_name": "Ligand B", "monomer_id": "5002"}
                    ],
                },
            ]
        },
    )
    row = payload["rows"][0]
    assert payload["summary"]["structures_with_assay_summary"] == 1
    assert row["measurement_count"] == 2
    assert row["top_assay_names"] == ["Assay A"]
    assert row["measurement_technique_counts"] == {"Enzyme Inhibition": 2}
    assert row["partner_monomer_name_sample"] == ["Ligand A", "Ligand B"]


def test_build_bindingdb_accession_assay_profile_preview_summarizes_by_accession() -> None:
    payload = build_bindingdb_accession_assay_profile_preview(
        {
            "rows": [
                {
                    "accession": "P68871",
                    "measurement_type": "IC50",
                    "relation": "=",
                    "value_molar_normalized": None,
                    "delta_g_reported_kcal_per_mol": None,
                    "delta_g_derived_298k_kcal_per_mol": None,
                    "bindingdb_measurement_technique": "Enzyme Inhibition",
                    "bindingdb_target_role": "enzyme",
                    "bindingdb_assay_name": "Assay A",
                    "bindingdb_entry_title": "Entry A",
                    "bindingdb_partner_monomer_refs": [
                        {"display_name": "Ligand A", "monomer_id": "5001"}
                    ],
                },
                {
                    "accession": "P68871",
                    "measurement_type": "ΔG",
                    "relation": "=",
                    "value_molar_normalized": None,
                    "delta_g_reported_kcal_per_mol": -8.1,
                    "delta_g_derived_298k_kcal_per_mol": None,
                    "bindingdb_measurement_technique": "Enzyme Inhibition",
                    "bindingdb_target_role": "enzyme",
                    "bindingdb_assay_name": "Assay B",
                    "bindingdb_entry_title": "Entry B",
                    "bindingdb_partner_monomer_refs": [
                        {"display_name": "Ligand B", "monomer_id": "5002"}
                    ],
                },
            ]
        },
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "matched_accessions": ["P68871"],
                }
            ]
        },
    )
    row = payload["rows"][0]
    assert payload["summary"]["accessions_with_assay_profile"] == 1
    assert payload["summary"]["accessions_with_projected_structure_support"] == 1
    assert payload["summary"]["accessions_with_direct_thermodynamics"] == 1
    assert row["accession"] == "P68871"
    assert row["measurement_count"] == 2
    assert row["projected_structure_ids"] == ["4HHB"]
    assert row["measurement_type_counts"] == {"IC50": 1, "ΔG": 1}
    assert row["top_partner_monomer_names"] == ["Ligand A", "Ligand B"]


def test_build_bindingdb_assay_condition_profile_preview_summarizes_condition_coverage() -> None:
    payload = build_bindingdb_assay_condition_profile_preview(
        {
            "rows": [
                {
                    "accession": "P31749",
                    "reported_pH": 7.4,
                    "reported_temperature_celsius": 295.15,
                    "bindingdb_measurement_technique": "Enzyme Inhibition",
                    "bindingdb_assay_name": "Assay A",
                    "assay_context": {
                        "i_conc_range": "100 uM to 20 pM",
                        "e_conc_range": None,
                        "s_conc_range": "200 nM",
                    },
                },
                {
                    "accession": "P31749",
                    "reported_pH": 7.5,
                    "reported_temperature_celsius": 298.15,
                    "bindingdb_measurement_technique": "Enzyme Inhibition",
                    "bindingdb_assay_name": "Assay B",
                    "assay_context": {
                        "i_conc_range": None,
                        "e_conc_range": "1 nM",
                        "s_conc_range": None,
                    },
                },
            ]
        }
    )
    row = payload["rows"][0]
    assert payload["summary"]["accessions_with_condition_profile"] == 1
    assert payload["summary"]["accessions_with_reported_pH"] == 1
    assert payload["summary"]["accessions_with_reported_temperature"] == 1
    assert payload["summary"]["accessions_with_concentration_ranges"] == 1
    assert row["reported_pH_range"] == {"min": 7.4, "max": 7.5}
    assert row["reported_temperature_celsius_range"] == {"min": 295.15, "max": 298.15}
    assert row["rows_with_i_conc_range"] == 1
    assert row["rows_with_e_conc_range"] == 1
    assert row["rows_with_s_conc_range"] == 1


def test_build_bindingdb_structure_partner_profile_preview_summarizes_partner_density() -> None:
    payload = build_bindingdb_structure_partner_profile_preview(
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "bindingdb_projection_status": "present",
                    "measurement_count": 2,
                    "matched_accessions": ["P68871"],
                    "bindingdb_bridge_polymer_ids": ["50001270"],
                }
            ]
        },
        {
            "rows": [
                {
                    "accession": "P68871",
                    "bindingdb_polymer_id": "50001270",
                    "bindingdb_partner_monomer_refs": [
                        {
                            "display_name": "Ligand A",
                            "monomer_id": "5001",
                            "smiles_present": True,
                            "inchi_key_present": True,
                            "chembl_id": "CHEMBL1",
                            "pdb_ids_exact_sample": ["4HHB"],
                        }
                    ],
                },
                {
                    "accession": "P68871",
                    "bindingdb_polymer_id": "50001270",
                    "bindingdb_partner_monomer_refs": [
                        {
                            "display_name": "Ligand A",
                            "monomer_id": "5001",
                            "smiles_present": True,
                            "inchi_key_present": True,
                            "chembl_id": "CHEMBL1",
                            "pdb_ids_exact_sample": ["4HHB"],
                        },
                        {
                            "display_name": "Ligand B",
                            "monomer_id": "5002",
                            "smiles_present": False,
                            "inchi_key_present": False,
                            "chembl_id": None,
                            "pdb_ids_exact_sample": [],
                        },
                    ],
                },
            ]
        },
    )
    row = payload["rows"][0]
    assert payload["summary"]["structures_with_partner_profile"] == 1
    assert payload["summary"]["structures_with_smiles_backed_partners"] == 1
    assert row["structure_id"] == "4HHB"
    assert row["unique_partner_monomer_count"] == 2
    assert row["top_partner_monomers"][0]["display_name"] == "Ligand A"
    assert row["top_partner_monomers"][0]["linked_measurement_count"] == 2


def test_build_bindingdb_partner_descriptor_reconciliation_preview_compares_seed_overlap() -> None:
    payload = build_bindingdb_partner_descriptor_reconciliation_preview(
        {
            "rows": [
                {
                    "bindingdb_monomer_id": "5001",
                    "display_name": "Ligand A",
                    "chembl_id": "CHEMBL1",
                    "het_pdb": "HEM",
                    "smiles_present": True,
                    "inchi_key_present": True,
                    "pdb_ids_exact_sample": ["4HHB", "9XYZ"],
                    "linked_accessions": ["P68871"],
                    "linked_measurement_count": 2,
                },
                {
                    "bindingdb_monomer_id": "5002",
                    "display_name": "Ligand B",
                    "chembl_id": None,
                    "het_pdb": None,
                    "smiles_present": True,
                    "inchi_key_present": False,
                    "pdb_ids_exact_sample": [],
                    "linked_accessions": ["P31749"],
                    "linked_measurement_count": 1,
                },
            ]
        },
        {
            "rows": [
                {"structure_id": "4HHB", "ccd_id": "HEM"},
                {"structure_id": "4HHB", "ccd_id": "PO4"},
            ]
        },
    )
    first = payload["rows"][0]
    second = payload["rows"][1]
    assert payload["summary"]["partner_monomer_count"] == 2
    assert payload["summary"]["partners_with_seed_structure_overlap"] == 1
    assert payload["summary"]["partners_with_chemistry_descriptors"] == 2
    assert first["reconciliation_status"] == "seed_structure_and_het_code_overlap"
    assert first["seed_structure_overlap_ids"] == ["4HHB"]
    assert first["seed_structure_overlap_ccd_ids"] == ["HEM", "PO4"]
    assert second["reconciliation_status"] == "descriptor_rich_no_seed_overlap"


def test_build_bindingdb_accession_partner_identity_profile_preview_summarizes_identity_richness(
) -> None:
    payload = build_bindingdb_accession_partner_identity_profile_preview(
        {
            "rows": [
                {
                    "bindingdb_monomer_id": "5001",
                    "display_name": "Ligand A",
                    "chembl_id": "CHEMBL1",
                    "het_pdb": "HEM",
                    "smiles_present": True,
                    "inchi_key_present": True,
                    "linked_accessions": ["P68871"],
                    "linked_measurement_count": 2,
                },
                {
                    "bindingdb_monomer_id": "5002",
                    "display_name": "Ligand B",
                    "chembl_id": None,
                    "het_pdb": None,
                    "smiles_present": True,
                    "inchi_key_present": False,
                    "linked_accessions": ["P68871", "P31749"],
                    "linked_measurement_count": 1,
                },
            ]
        },
        {
            "rows": [
                {
                    "bindingdb_monomer_id": "5001",
                    "reconciliation_status": "seed_structure_and_het_code_overlap",
                    "seed_structure_overlap_ids": ["4HHB"],
                },
                {
                    "bindingdb_monomer_id": "5002",
                    "reconciliation_status": "descriptor_rich_no_seed_overlap",
                    "seed_structure_overlap_ids": [],
                },
            ]
        },
    )
    first = {row["accession"]: row for row in payload["rows"]}["P68871"]
    second = {row["accession"]: row for row in payload["rows"]}["P31749"]
    assert payload["summary"]["accessions_with_partner_identity_profile"] == 2
    assert payload["summary"]["accessions_with_seed_bridgeable_partners"] == 1
    assert payload["summary"]["accessions_with_descriptor_rich_partners"] == 2
    assert first["partner_monomer_count"] == 2
    assert first["partners_with_seed_structure_overlap_count"] == 1
    assert first["descriptor_coverage_fraction"] == 1.0
    assert first["reconciliation_status_counts"] == {
        "descriptor_rich_no_seed_overlap": 1,
        "seed_structure_and_het_code_overlap": 1,
    }
    assert second["partner_monomer_count"] == 1
    assert second["partners_with_seed_structure_overlap_count"] == 0


def test_build_bindingdb_structure_grounding_candidate_preview_ranks_future_structures() -> None:
    payload = build_bindingdb_structure_grounding_candidate_preview(
        {
            "rows": [
                {
                    "bindingdb_monomer_id": "5001",
                    "display_name": "Ligand A",
                    "het_pdb": "ABC",
                    "pdb_ids_exact_sample": ["4HHB", "7XYZ", "8AAA"],
                    "linked_accessions": ["P68871"],
                    "linked_measurement_count": 3,
                },
                {
                    "bindingdb_monomer_id": "5002",
                    "display_name": "Ligand B",
                    "het_pdb": None,
                    "pdb_ids_exact_sample": ["6DEF"],
                    "linked_accessions": ["P31749"],
                    "linked_measurement_count": 2,
                },
                {
                    "bindingdb_monomer_id": "5003",
                    "display_name": "Ligand C",
                    "het_pdb": "HEM",
                    "pdb_ids_exact_sample": [],
                    "linked_accessions": ["P04637"],
                    "linked_measurement_count": 1,
                },
            ]
        },
        {
            "rows": [
                {
                    "accession": "P68871",
                    "descriptor_coverage_fraction": 1.0,
                    "partners_with_seed_structure_overlap_count": 0,
                },
                {
                    "accession": "P31749",
                    "descriptor_coverage_fraction": 1.0,
                    "partners_with_seed_structure_overlap_count": 0,
                },
                {
                    "accession": "P04637",
                    "descriptor_coverage_fraction": 1.0,
                    "partners_with_seed_structure_overlap_count": 0,
                },
            ]
        },
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "mapped_uniprot_accessions": ["P68871"],
                    "matched_accessions": ["P68871"],
                },
                {
                    "structure_id": "1Y01",
                    "mapped_uniprot_accessions": ["P69905"],
                    "matched_accessions": [],
                },
            ]
        },
        {
            "rows": [
                {"structure_id": "4HHB", "ccd_id": "HEM"},
                {"structure_id": "1Y01", "ccd_id": "CHK"},
            ]
        },
    )

    rows = {row["accession"]: row for row in payload["rows"]}
    assert payload["summary"]["accessions_with_seed_structure_support"] == 1
    assert payload["summary"]["accessions_with_future_structure_candidates"] == 1
    assert payload["summary"]["accessions_with_het_code_candidates"] == 2
    assert payload["summary"]["global_future_structure_candidate_count"] == 3
    assert rows["P68871"]["grounding_readiness_status"] == "seed_structure_supported"
    assert rows["P68871"]["top_future_structure_ids"] == ["7XYZ", "8AAA"]
    assert rows["P31749"]["grounding_readiness_status"] == "future_structure_candidate_available"
    assert rows["P31749"]["top_future_structure_ids"] == ["6DEF"]
    assert rows["P04637"]["grounding_readiness_status"] == "het_code_candidate_only"


def test_build_bindingdb_future_structure_registry_preview_selects_top_structures() -> None:
    payload = build_bindingdb_future_structure_registry_preview(
        {
            "rows": [
                {
                    "accession": "P31749",
                    "top_future_structure_ids": ["1AQ1", "1BYG"],
                    "top_candidate_monomers": [
                        {
                            "bindingdb_monomer_id": "5001",
                            "display_name": "Ligand A",
                            "het_pdb": "STU",
                            "linked_measurement_count": 2,
                            "future_structure_ids": ["1AQ1", "1BYG"],
                        }
                    ],
                },
                {
                    "accession": "P04637",
                    "top_future_structure_ids": ["1AQ1", "4JPS"],
                    "top_candidate_monomers": [
                        {
                            "bindingdb_monomer_id": "5002",
                            "display_name": "Ligand B",
                            "het_pdb": "NUT",
                            "linked_measurement_count": 3,
                            "future_structure_ids": ["4JPS", "1AQ1"],
                        }
                    ],
                },
            ]
        },
        max_structures=3,
    )
    assert payload["summary"]["registered_future_structure_count"] == 3
    assert payload["summary"]["source_accession_count"] == 2
    first = payload["rows"][0]
    assert first["structure_id"] == "1AQ1"
    assert first["source_accessions"] == ["P04637", "P31749"]
    assert sorted(first["supporting_het_codes"]) == ["NUT", "STU"]


def test_build_bindingdb_future_structure_alignment_preview_detects_mismatch() -> None:
    payload = build_bindingdb_future_structure_alignment_preview(
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "source_accessions": ["P68871"],
                    "mapped_uniprot_accessions": ["P68871"],
                    "supporting_het_codes": ["HEM"],
                    "linked_measurement_count": 9,
                },
                {
                    "structure_id": "7C44",
                    "source_accessions": ["P04637"],
                    "mapped_uniprot_accessions": ["O15151"],
                    "supporting_het_codes": ["NUT"],
                    "linked_measurement_count": 3,
                },
            ]
        }
    )
    rows = {row["structure_id"]: row for row in payload["rows"]}
    assert payload["summary"]["aligned_structure_count"] == 1
    assert payload["summary"]["mismatched_structure_count"] == 1
    assert rows["4HHB"]["alignment_status"] == "aligned_to_source_accession"
    assert rows["7C44"]["alignment_status"] == "mapped_to_different_accession"


def test_build_bindingdb_future_structure_triage_preview_separates_off_target_context() -> None:
    payload = build_bindingdb_future_structure_triage_preview(
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "source_accessions": ["P68871"],
                    "mapped_uniprot_accessions": ["P68871"],
                    "shared_accessions": ["P68871"],
                    "supporting_het_codes": ["HEM"],
                    "linked_measurement_count": 9,
                    "alignment_status": "aligned_to_source_accession",
                },
                {
                    "structure_id": "7C44",
                    "source_accessions": ["P04637"],
                    "mapped_uniprot_accessions": ["O15151"],
                    "shared_accessions": [],
                    "supporting_het_codes": ["NUT"],
                    "linked_measurement_count": 3,
                    "alignment_status": "mapped_to_different_accession",
                },
            ]
        },
        {
            "rows": [
                {
                    "structure_id": "4HHB",
                    "experimental_method": "X-RAY DIFFRACTION",
                    "resolution_angstrom": 1.7,
                    "title": "Aligned example",
                },
                {
                    "structure_id": "7C44",
                    "experimental_method": "X-RAY DIFFRACTION",
                    "resolution_angstrom": 1.65,
                    "title": "Off target example",
                },
            ]
        },
    )
    rows = {row["structure_id"]: row for row in payload["rows"]}
    assert payload["summary"]["direct_grounding_candidate_count"] == 1
    assert payload["summary"]["off_target_adjacent_context_only_count"] == 1
    assert rows["4HHB"]["triage_status"] == "direct_grounding_candidate"
    assert rows["7C44"]["triage_status"] == "off_target_adjacent_context_only"


def test_build_bindingdb_off_target_adjacent_context_profile_preview_rolls_up_sources() -> None:
    payload = build_bindingdb_off_target_adjacent_context_profile_preview(
        {
            "rows": [
                {
                    "structure_id": "7C44",
                    "triage_status": "off_target_adjacent_context_only",
                    "source_accessions": ["P04637"],
                    "mapped_uniprot_accessions": ["O15151"],
                    "supporting_het_codes": ["NUT"],
                    "linked_measurement_count": 3,
                    "experimental_method": "X-RAY DIFFRACTION",
                    "title": "MdmX with Nutlin",
                },
                {
                    "structure_id": "5Z02",
                    "triage_status": "off_target_adjacent_context_only",
                    "source_accessions": ["P04637"],
                    "mapped_uniprot_accessions": ["Q00987"],
                    "supporting_het_codes": ["NUT"],
                    "linked_measurement_count": 3,
                    "experimental_method": "X-RAY DIFFRACTION",
                    "title": "Mdm2 with Nutlin",
                },
            ]
        }
    )
    assert payload["summary"]["source_accession_count"] == 1
    row = payload["rows"][0]
    assert row["source_accession"] == "P04637"
    assert row["off_target_structure_count"] == 2
    assert row["mapped_target_accessions"] == ["O15151", "Q00987"]
    assert row["supporting_het_codes"] == ["NUT"]


def test_build_bindingdb_off_target_target_profile_preview_rolls_up_targets() -> None:
    payload = build_bindingdb_off_target_target_profile_preview(
        {
            "rows": [
                {
                    "structure_id": "7C44",
                    "triage_status": "off_target_adjacent_context_only",
                    "source_accessions": ["P04637"],
                    "mapped_uniprot_accessions": ["O15151"],
                    "supporting_het_codes": ["NUT"],
                    "linked_measurement_count": 3,
                    "experimental_method": "X-RAY DIFFRACTION",
                    "title": "MdmX with Nutlin",
                },
                {
                    "structure_id": "5Z02",
                    "triage_status": "off_target_adjacent_context_only",
                    "source_accessions": ["P04637"],
                    "mapped_uniprot_accessions": ["Q00987"],
                    "supporting_het_codes": ["NUT"],
                    "linked_measurement_count": 3,
                    "experimental_method": "X-RAY DIFFRACTION",
                    "title": "Mdm2 with Nutlin",
                },
            ]
        }
    )
    assert payload["summary"]["mapped_target_accession_count"] == 2
    rows = {row["mapped_target_accession"]: row for row in payload["rows"]}
    assert rows["O15151"]["source_accessions"] == ["P04637"]
    assert rows["Q00987"]["structure_count"] == 1

