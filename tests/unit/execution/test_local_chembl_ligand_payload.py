from __future__ import annotations

import sqlite3
from pathlib import Path

from execution.acquire.local_chembl_ligand_payload import build_local_chembl_ligand_payload


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        create table component_sequences (
            component_id integer,
            component_type text,
            accession text,
            sequence text,
            sequence_md5sum text,
            description text,
            tax_id integer,
            organism text,
            db_source text,
            db_version text
        );
        create table target_components (
            tid integer,
            component_id integer,
            targcomp_id integer,
            homologue integer
        );
        create table target_dictionary (
            tid integer,
            target_type text,
            pref_name text,
            tax_id integer,
            organism text,
            chembl_id text,
            species_group_flag integer
        );
        create table assays (
            assay_id integer,
            doc_id integer,
            description text,
            assay_type text,
            assay_test_type text,
            assay_category text,
            assay_organism text,
            assay_tax_id integer,
            assay_strain text,
            assay_tissue text,
            assay_cell_type text,
            assay_subcellular_fraction text,
            tid integer,
            relationship_type text,
            confidence_score integer,
            curated_by text,
            src_id integer,
            src_assay_id text,
            chembl_id text,
            cell_id integer,
            bao_format text,
            tissue_id integer,
            variant_id integer,
            aidx integer,
            assay_group text
        );
        create table activities (
            activity_id integer,
            assay_id integer,
            doc_id integer,
            record_id integer,
            molregno integer,
            standard_relation text,
            standard_value real,
            standard_units text,
            standard_flag integer,
            standard_type text,
            activity_comment text,
            data_validity_comment text,
            potential_duplicate integer,
            pchembl_value real,
            bao_endpoint text,
            uo_units text,
            qudt_units text,
            toid integer,
            upper_value real,
            standard_upper_value real,
            src_id integer,
            type text,
            relation text,
            value real,
            units text,
            text_value text,
            standard_text_value text,
            action_type text
        );
        create table molecule_dictionary (
            molregno integer,
            pref_name text,
            chembl_id text,
            max_phase integer,
            therapeutic_flag integer,
            dosed_ingredient integer,
            structure_type text,
            molecule_type text,
            first_approval integer,
            oral integer,
            parenteral integer,
            topical integer,
            black_box_warning integer,
            natural_product integer,
            first_in_class integer,
            chirality integer,
            prodrug integer,
            inorganic_flag integer,
            usan_year integer,
            availability_type integer,
            usan_stem text,
            polymer_flag integer,
            usan_substem text,
            usan_stem_definition text,
            withdrawn_flag integer,
            chemical_probe integer,
            orphan integer,
            veterinary integer
        );
        create table compound_structures (
            molregno integer,
            molfile text,
            standard_inchi text,
            standard_inchi_key text,
            canonical_smiles text
        );
        create table compound_properties (
            molregno integer,
            mw_freebase real,
            alogp real,
            hba integer,
            hbd integer,
            psa real,
            rtb integer,
            ro3_pass text,
            num_ro5_violations integer,
            full_mwt real,
            aromatic_rings integer,
            heavy_atoms integer,
            qed_weighted real,
            full_molformula text,
            np_likeness_score real
        );
        """
    )
    cur.execute(
        """
        insert into component_sequences
        values (1, 'PROTEIN', 'P00387', 'SEQ', '', '', 9606, 'Human', 'UniProt', '1')
        """
    )
    cur.execute("insert into target_components values (10, 1, 10, 0)")
    cur.execute(
        """
        insert into target_dictionary
        values (
            10, 'SINGLE PROTEIN', 'NADH-cytochrome b5 reductase', 9606, 'Human', 'CHEMBL2146', 0
        )
        """
    )
    cur.execute(
        """
        insert into assays
        values (
            100, 1, 'assay', 'B', '', '', 'Human', 9606, '', '', '', '', 10, '', 9, '', 1,
            '', 'CHEMBL_ASSAY_1', null, '', null, null, null, ''
        )
        """
    )
    cur.execute(
        """
        insert into molecule_dictionary
        values (
            1000, 'PRIMAQUINE', 'CHEMBL506', 4, 1, 0, 'MOL', 'Small molecule', null, 1, 0,
            0, 0, 0, 0, 0, 0, 0, null, null, '', 0, '', '', 0, 0, 0, 0
        )
        """
    )
    cur.execute(
        "insert into compound_structures values (1000, '', '', '', 'COc1cc(NC(C)CCCN)c2ncccc2c1')"
    )
    cur.execute(
        """
        insert into compound_properties
        values (1000, 259.35, 2.1, 2, 2, 40.0, 5, 'Y', 0, 259.35, 2, 18, 0.55, 'C15H21N3O', 0.1)
        """
    )
    cur.execute(
        """
        insert into activities
        values (
            5000, 100, 1, 1, 1000, '=', 0.052, 'nM min-1 (mg of protein)-1', 1, 'Activity',
            '', '', 0, null, '', '', '', null, null, null, 1, '', '', null, '', '', '', ''
        )
        """
    )
    conn.commit()
    conn.close()


def test_build_local_chembl_ligand_payload_resolves_rows(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    _seed_db(chembl_path)

    payload = build_local_chembl_ligand_payload(
        accession="P00387",
        chembl_path=chembl_path,
        max_rows=5,
    )

    assert payload["status"] == "resolved"
    assert payload["packet_source_ref"] == "ligand:P00387"
    assert payload["summary"]["target_chembl_id"] == "CHEMBL2146"
    assert payload["summary"]["activity_count_total"] == 1
    assert payload["rows"][0]["ligand_chembl_id"] == "CHEMBL506"
    assert payload["truth_boundary"]["can_promote_latest_now"] is False


def test_build_local_chembl_ligand_payload_handles_missing_db(tmp_path: Path) -> None:
    payload = build_local_chembl_ligand_payload(
        accession="P00387",
        chembl_path=tmp_path / "missing.db",
    )

    assert payload["status"] == "no_local_ligand_payload"
    assert payload["summary"]["rows_emitted"] == 0
