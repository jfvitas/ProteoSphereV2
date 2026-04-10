from __future__ import annotations

from core.canonical.ligand import CanonicalLigand
from core.canonical.protein import CanonicalProtein
from core.canonical.registry import CanonicalEntityRegistry, UnresolvedCanonicalReference
from execution.ingest.assays import ingest_bindingdb_assays


def _make_registry() -> CanonicalEntityRegistry:
    protein = CanonicalProtein(
        accession="P28482",
        sequence="ACDEFGHIK",
        name="MAPK1",
        organism="Homo sapiens",
    )
    ligand = CanonicalLigand(
        ligand_id="bindingdb:120095",
        name="BindingDB ligand 120095",
        source="BindingDB",
        source_id="120095",
        smiles="CCO",
        inchikey="InChIKey=ABCDEF",
    )
    return CanonicalEntityRegistry(proteins=[protein], ligands=[ligand])


def _bindingdb_row(
    *,
    value: str | float,
    assay_description: str = "Competitive inhibition",
) -> dict[str, object]:
    return {
        "BindingDB Reactant_set_id": "RS123",
        "BindingDB MonomerID": "120095",
        "Ligand SMILES": " CCO ",
        "Ligand InChI Key": "InChIKey=ABCDEF",
        "Target Name": "Mitogen-activated protein kinase 1",
        "UniProtKB/SwissProt": "P28482",
        "PDB": "1abc",
        "Affinity Type": "Ki",
        "affinity_value_nM": value,
        "Assay Description": assay_description,
        "Publication Date": "2022-03-25",
        "BindingDB Curation Date": "2022-04-01",
        "PMID": "12345",
        "DOI": "10.1/example",
    }


def test_ingest_bindingdb_assays_writes_canonical_assay_and_preserves_provenance() -> None:
    result = ingest_bindingdb_assays(
        [_bindingdb_row(value="2.18E+4 nM")],
        registry=_make_registry(),
        acquired_at="2026-03-22T15:00:00Z",
        parser_version="1.0.0",
        run_id="run-001",
    )

    assert result.status == "resolved"
    assert result.is_resolved is True
    assert len(result.cases) == 1
    assert len(result.canonical_assays) == 1

    case = result.cases[0]
    assay = result.canonical_assays[0]
    provenance = case.provenance_records[0]

    assert case.status == "resolved"
    assert assay.assay_id == "assay:BINDINGDB:RS123"
    assert assay.canonical_id == "assay:BINDINGDB:RS123"
    assert assay.target_id == "protein:P28482"
    assert assay.ligand_id == "ligand:bindingdb:120095"
    assert assay.measurement_type == "Ki"
    assert assay.measurement_value == 21800.0
    assert assay.measurement_unit == "nM"
    assert assay.provenance == (provenance.provenance_id,)
    assert assay.references == ("PMID:12345", "DOI:10.1/example")
    assert provenance.source.source_name == "BindingDB"
    assert provenance.source.original_identifier == "RS123"
    assert provenance.parser_version == "1.0.0"
    assert provenance.run_id == "run-001"
    assert provenance.checksum.startswith("sha256:")
    assert provenance.metadata["target_uniprot_ids"] == ("P28482",)
    assert result.to_dict()["canonical_assays"][0]["assay_id"] == "assay:BINDINGDB:RS123"


def test_ingest_bindingdb_assays_marks_duplicate_evidence_as_ambiguous_without_collapse() -> None:
    result = ingest_bindingdb_assays(
        [_bindingdb_row(value=10.0), _bindingdb_row(value=10.0)],
        registry=_make_registry(),
    )

    assert result.status == "ambiguous"
    assert result.cases[0].status == "ambiguous"
    assert result.cases[0].reason == "duplicate_evidence_preserved"
    assert len(result.canonical_assays) == 1
    assert len(result.cases[0].provenance_records) == 2
    assert result.canonical_assays[0].provenance == (
        result.cases[0].provenance_records[0].provenance_id,
        result.cases[0].provenance_records[1].provenance_id,
    )


def test_ingest_bindingdb_assays_exposes_conflicts_and_unresolved_cases() -> None:
    conflict_result = ingest_bindingdb_assays(
        [_bindingdb_row(value=10.0), _bindingdb_row(value=12.0)],
        registry=_make_registry(),
    )

    assert conflict_result.status == "conflict"
    assert conflict_result.canonical_assays == ()
    assert conflict_result.cases[0].status == "conflict"
    assert conflict_result.cases[0].issues[0].kind == "assay_conflict"
    assert conflict_result.cases[0].conflicts[0].kind == "measurement_value_disagreement"

    unresolved_result = ingest_bindingdb_assays(
        [
            {
                "BindingDB Reactant_set_id": "RS456",
                "BindingDB MonomerID": "120096",
                "Target Name": "Mitogen-activated protein kinase 1",
                "UniProtKB/SwissProt": "P28482;Q9XYZ1",
                "Affinity Type": "Ki",
                "affinity_value_nM": 5.0,
            }
        ],
        registry=_make_registry(),
    )

    assert unresolved_result.status == "unresolved"
    assert unresolved_result.canonical_assays == ()
    assert unresolved_result.cases[0].status == "unresolved"
    assert unresolved_result.cases[0].issues[0].kind == "target_ambiguity"
    assert unresolved_result.cases[0].issues[0].target_candidates == (
        "protein:P28482",
        "protein:Q9XYZ1",
    )


def test_ingest_bindingdb_assays_preserves_registry_level_target_ambiguity() -> None:
    registry = _make_registry()
    original_resolve = registry.resolve

    def resolve_with_target_ambiguity(reference: str, *, entity_type: str | None = None):
        if entity_type == "protein" and reference == "P28482":
            return UnresolvedCanonicalReference(
                reference="P28482",
                entity_type="protein",
                reason="ambiguous",
                candidates=("protein:P28482-1", "protein:P28482-2"),
            )
        return original_resolve(reference, entity_type=entity_type)

    registry.resolve = resolve_with_target_ambiguity  # type: ignore[method-assign]

    result = ingest_bindingdb_assays([_bindingdb_row(value=5.0)], registry=registry)

    assert result.status == "unresolved"
    assert result.cases[0].issues[0].kind == "target_ambiguity"
    assert result.cases[0].issues[0].target_candidates == (
        "protein:P28482-1",
        "protein:P28482-2",
    )
    assert result.cases[0].issues[0].provenance_ids == (
        result.cases[0].provenance_records[0].provenance_id,
    )
    assert result.cases[0].status == "unresolved"
    assert result.cases[0].canonical_assay is None


def test_ingest_bindingdb_assays_preserves_registry_level_ligand_ambiguity() -> None:
    registry = _make_registry()
    original_resolve = registry.resolve

    def resolve_with_ligand_ambiguity(reference: str, *, entity_type: str | None = None):
        if entity_type == "ligand" and reference == "bindingdb:120095":
            return UnresolvedCanonicalReference(
                reference="bindingdb:120095",
                entity_type="ligand",
                reason="ambiguous",
                candidates=("ligand:bindingdb:120095-a", "ligand:bindingdb:120095-b"),
            )
        return original_resolve(reference, entity_type=entity_type)

    registry.resolve = resolve_with_ligand_ambiguity  # type: ignore[method-assign]

    result = ingest_bindingdb_assays([_bindingdb_row(value=5.0)], registry=registry)

    assert result.status == "unresolved"
    assert result.cases[0].issues[0].kind == "ligand_ambiguity"
    assert result.cases[0].issues[0].ligand_candidates == (
        "ligand:bindingdb:120095-a",
        "ligand:bindingdb:120095-b",
    )
    assert result.cases[0].issues[0].provenance_ids == (
        result.cases[0].provenance_records[0].provenance_id,
    )
    assert result.cases[0].status == "unresolved"
    assert result.cases[0].canonical_assay is None


def test_ingest_bindingdb_assays_uses_explicit_bindingdb_source_id_when_present() -> None:
    row_ki = _bindingdb_row(value=5.0)
    row_ki["bindingdb_source_id"] = "RS123:ki:1"
    row_ic50 = _bindingdb_row(value=7.0)
    row_ic50["bindingdb_source_id"] = "RS123:ic50:1"
    row_ic50["Affinity Type"] = "IC50"

    result = ingest_bindingdb_assays([row_ki, row_ic50], registry=_make_registry())

    assert result.status == "resolved"
    assert len(result.cases) == 2
    assert len(result.canonical_assays) == 2
    assert {assay.source_id for assay in result.canonical_assays} == {"RS123:ki:1", "RS123:ic50:1"}
    assert {assay.measurement_type for assay in result.canonical_assays} == {"Ki", "IC50"}
