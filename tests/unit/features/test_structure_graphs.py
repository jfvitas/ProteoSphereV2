from __future__ import annotations

from connectors.rcsb.parsers import parse_structure_bundle
from features.structure_graphs import (
    AtomGraph,
    ResidueGraph,
    extract_atom_graph,
    extract_residue_graph,
    extract_structure_graphs,
)


def _bundle():
    entry_payload = {
        "rcsb_id": "1abc",
        "struct": {"title": "Example structure"},
        "rcsb_entry_info": {"experimental_method": ["X-RAY DIFFRACTION"]},
        "rcsb_entry_container_identifiers": {
            "assembly_ids": ["1"],
            "polymer_entity_ids": ["1"],
            "nonpolymer_entity_ids": ["2"],
        },
    }
    entity_payload = {
        "rcsb_id": "1abc",
        "entity": {"id": "1", "pdbx_description": "Protein A"},
        "entity_poly": {
            "type": "Protein",
            "pdbx_seq_one_letter_code_can": "ACD",
            "entity_poly_seq_length": 3,
        },
        "rcsb_polymer_entity_container_identifiers": {
            "entity_id": "1",
            "auth_asym_ids": ["A"],
            "uniprot_ids": ["P12345"],
        },
        "rcsb_entity_source_organism": [
            {
                "scientific_name": "Homo sapiens",
                "ncbi_taxonomy_id": 9606,
            }
        ],
    }
    assembly_payload = {
        "rcsb_id": "1abc",
        "rcsb_assembly_container_identifiers": {
            "assembly_id": "1",
            "auth_asym_ids": ["A"],
            "polymer_entity_ids": ["1"],
        },
        "rcsb_assembly_info": {
            "oligomeric_state": "monomer",
            "oligomeric_count": 1,
        },
    }
    return parse_structure_bundle(entry_payload, [entity_payload], [assembly_payload])


def test_extract_atom_graph_builds_nodes_edges_and_provenance():
    bundle = _bundle()
    atom_rows = (
        row
        for row in [
            {
                "atom_id": "A1",
                "chain_id": "A",
                "residue_name": "ALA",
                "residue_number": 1,
                "atom_name": "CA",
                "element": "C",
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "bond_partners": "A2",
            },
            {
                "atom_id": "A2",
                "chain_id": "A",
                "residue_name": "CYS",
                "residue_number": 2,
                "atom_name": "CB",
                "element": "C",
                "x": 1.0,
                "y": 0.0,
                "z": 0.0,
            },
            {
                "atom_id": "B1",
                "chain_id": "B",
                "residue_name": "ALA",
                "residue_number": 1,
                "atom_name": "CA",
                "element": "C",
                "x": 0.0,
                "y": 0.0,
                "z": 2.0,
            },
        ]
    )

    graph = extract_atom_graph(bundle, atom_rows, contact_cutoff=2.5)

    assert isinstance(graph, AtomGraph)
    assert graph.pdb_id == "1ABC"
    assert graph.node_ids == ("A1", "A2", "B1")
    assert graph.provenance["chain_to_entity_ids"] == {"A": ["1"]}
    assert {edge.kind for edge in graph.edges} >= {"atom_to_residue", "bond", "spatial_contact"}
    assert any(
        edge.source == "A1" and edge.target == "A2" and edge.kind == "bond" for edge in graph.edges
    )
    assert any(
        edge.source == "A1" and edge.target == "B1" and edge.kind == "spatial_contact"
        for edge in graph.edges
    )


def test_extract_residue_graph_derives_from_sequence_and_contacts():
    bundle = _bundle()
    atom_rows = [
        {
            "atom_id": "A1",
            "chain_id": "A",
            "residue_name": "ALA",
            "residue_number": 1,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
        {
            "atom_id": "A2",
            "chain_id": "A",
            "residue_name": "CYS",
            "residue_number": 2,
            "x": 0.0,
            "y": 0.0,
            "z": 3.0,
        },
        {
            "atom_id": "A3",
            "chain_id": "A",
            "residue_name": "ASP",
            "residue_number": 3,
            "x": 0.0,
            "y": 0.0,
            "z": 7.0,
        },
    ]

    graph = extract_residue_graph(bundle, atom_rows=atom_rows, contact_cutoff=4.0)

    assert isinstance(graph, ResidueGraph)
    assert graph.pdb_id == "1ABC"
    assert [node.residue_key for node in graph.nodes][:3] == ["A:1", "A:2", "A:3"]
    assert graph.nodes[0].uniprot_ids == ("P12345",)
    assert any(edge.kind == "sequence_adjacent" for edge in graph.edges)
    assert any(edge.kind == "spatial_contact" for edge in graph.edges)


def test_extract_residue_graph_preserves_explicit_rows():
    bundle = _bundle()
    atom_rows = [
        {
            "atom_id": "A1",
            "chain_id": "A",
            "residue_name": "ALA",
            "residue_number": 1,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
    ]
    residue_rows = [
        {
            "chain_id": "A",
            "residue_number": 1,
            "residue_name": "ALA",
            "sequence_position": 1,
            "uniprot_id": "P12345",
            "one_letter_code": "A",
        }
    ]

    graph = extract_residue_graph(
        bundle, atom_rows=atom_rows, residue_rows=residue_rows, contact_cutoff=4.0
    )

    assert graph.nodes[0].residue_key == "A:1"
    assert graph.nodes[0].one_letter_code == "A"
    assert graph.nodes[0].uniprot_ids == ("P12345",)


def test_extract_structure_graphs_returns_both_views():
    bundle = _bundle()
    atom_rows = [
        {
            "atom_id": "A1",
            "chain_id": "A",
            "residue_name": "ALA",
            "residue_number": 1,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
    ]

    graphs = extract_structure_graphs(bundle, atom_rows=atom_rows)

    assert set(graphs) == {"atom", "residue"}
    assert isinstance(graphs["atom"], AtomGraph)
    assert isinstance(graphs["residue"], ResidueGraph)
