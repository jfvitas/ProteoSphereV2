from __future__ import annotations

import json
import zipfile
from pathlib import Path

from execution.acquire.bindingdb_dump_extract import (
    extract_bindingdb_dump_records,
    iter_table_rows,
    write_bindingdb_dump_extract,
)


def _write_zip(path: Path, *, entry_name: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(entry_name, content)


def test_iter_table_rows_parses_insert_payload_with_commas_and_nulls(tmp_path: Path) -> None:
    zip_path = tmp_path / "bindingdb.zip"
    _write_zip(
        zip_path,
        entry_name="BDB-mySQL_All_202603.dmp",
        content=(
            "INSERT INTO `entry` VALUES "
            "(NULL,'Example, comment','2026-03-22 00:00:00','Title',NULL,NULL,10,"
            "'Enzyme Inhibition',NULL,'EZ1');\n"
        ),
    )

    rows = list(iter_table_rows(zip_path, "entry"))

    assert len(rows) == 1
    assert rows[0]["comments"] == "Example, comment"
    assert rows[0]["entryid"] == "10"
    assert rows[0]["depoid"] is None


def test_extract_bindingdb_dump_records_builds_accession_scoped_slice(tmp_path: Path) -> None:
    zip_path = tmp_path / "bindingdb.zip"
    _write_zip(
        zip_path,
        entry_name="BDB-mySQL_All_202603.dmp",
        content="\n".join(
            (
                "INSERT INTO `polymer` VALUES "
                "(NULL,NULL,NULL,NULL,NULL,NULL,'Homo sapiens','Protein','TP53 protein',393,"
                "'MEEPQSD',0,'9606','P04637',7001,'1ABC',NULL,NULL,NULL),"
                "(NULL,NULL,NULL,NULL,NULL,NULL,'Homo sapiens','Protein','Other protein',100,"
                "'MKT',0,'9606','Q99999',7002,'2XYZ',NULL,NULL,NULL);",
                "INSERT INTO `poly_name` VALUES (7001,'Cellular tumor antigen p53');",
                "INSERT INTO `enzyme_reactant_set` VALUES "
                "('TP53',NULL,NULL,9001,NULL,NULL,1001,NULL,NULL,NULL,'BDBM50388626',NULL,50388626,NULL,NULL,NULL,7001,'inhibition',NULL,NULL);",
                "INSERT INTO `assay` VALUES (1,'ELISA inhibition assay','TP53 assay',1001);",
                "INSERT INTO `entry` VALUES "
                "(NULL,'Journal ref','2026-03-22 00:00:00','TP53 entry',NULL,NULL,1001,"
                "'Enzyme Inhibition',NULL,'10.1000/example');",
                "INSERT INTO `ki_result` VALUES "
                "(NULL,'10.0',70001,NULL,9001,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,"
                "'5.0',NULL,NULL,NULL,NULL,NULL,1,NULL,'yes',1001,NULL,NULL,NULL,NULL,NULL,NULL,NULL);",
                "INSERT INTO `monomer` VALUES "
                "(0,'',NULL,NULL,NULL,'BDBM50388626','INCHIKEY1',NULL,NULL,50388626,'InChI=1S/example',"
                "'500.0','Small organic molecule',0,'CCO',NULL);",
            )
        ),
    )

    result = extract_bindingdb_dump_records(zip_path, ("P04637",))

    assert result.accessions == ("P04637",)
    assert len(result.slices) == 1
    slice_result = result.slices[0]
    assert slice_result.accession == "P04637"
    assert len(slice_result.polymers) == 1
    assert slice_result.polymers[0]["polymerid"] == "7001"
    assert slice_result.polymers[0]["names"] == ["Cellular tumor antigen p53"]
    assert len(slice_result.reactant_sets) == 1
    assert slice_result.reactant_sets[0]["reactant_set_id"] == "9001"
    assert len(slice_result.assays) == 1
    assert slice_result.assays[0]["assayid"] == "1"
    assert len(slice_result.entries) == 1
    assert slice_result.entries[0]["entryid"] == "1001"
    assert len(slice_result.monomers) == 1
    assert slice_result.monomers[0]["monomerid"] == "50388626"
    assert len(slice_result.measurement_results) == 1
    assert slice_result.measurement_results[0]["ki_result_id"] == "70001"
    assert len(slice_result.assay_rows) == 2
    assert slice_result.assay_rows[0]["BindingDB Reactant_set_id"] == "9001"
    assert slice_result.assay_rows[0]["BindingDB MonomerID"] == "50388626"
    assert slice_result.assay_rows[0]["UniProtKB/SwissProt"] == "P04637"
    assert {row["Affinity Type"] for row in slice_result.assay_rows} == {"IC50", "Ki"}


def test_write_bindingdb_dump_extract_writes_summary_and_accession_files(tmp_path: Path) -> None:
    zip_path = tmp_path / "bindingdb.zip"
    _write_zip(
        zip_path,
        entry_name="BDB-mySQL_All_202603.dmp",
        content=(
            "INSERT INTO `polymer` VALUES "
            "(NULL,NULL,NULL,NULL,NULL,NULL,'Homo sapiens','Protein','AKT1 protein',480,"
            "'MSDVAI',0,'9606','P31749',8001,'3ABC',NULL,NULL,NULL);\n"
        ),
    )

    result = extract_bindingdb_dump_records(zip_path, ("P31749",))
    paths = write_bindingdb_dump_extract(
        result,
        output_root=tmp_path / "out",
        run_id="bindingdb-local-test",
    )

    summary = json.loads(Path(paths["summary"]).read_text(encoding="utf-8"))
    accession_payload = json.loads(
        (
            tmp_path / "out" / "bindingdb-local-test" / "P31749" / "P31749.bindingdb_dump.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert summary["slice_count"] == 1
    assert accession_payload["accession"] == "P31749"
    assert accession_payload["polymer_count"] == 1
