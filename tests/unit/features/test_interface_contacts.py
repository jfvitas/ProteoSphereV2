from __future__ import annotations

from math import sqrt

import pytest

import features.interface_contacts as interface_contacts


class _FakeKDTree:
    def __init__(self, coords):
        self.coords = [tuple(float(value) for value in row) for row in coords]

    def query_pairs(self, cutoff):
        pairs = set()
        for left_index, left in enumerate(self.coords):
            for right_index in range(left_index + 1, len(self.coords)):
                right = self.coords[right_index]
                distance = sqrt(
                    (left[0] - right[0]) ** 2
                    + (left[1] - right[1]) ** 2
                    + (left[2] - right[2]) ** 2
                )
                if distance <= cutoff:
                    pairs.add((left_index, right_index))
        return pairs


def _atom_rows():
    return [
        {
            "atom_id": "A1",
            "chain_id": "A",
            "residue_name": "ALA",
            "residue_number": 1,
            "atom_name": "CA",
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
        {
            "atom_id": "A2",
            "chain_id": "A",
            "residue_name": "CYS",
            "residue_number": 2,
            "atom_name": "CB",
            "x": 0.0,
            "y": 0.0,
            "z": 1.0,
        },
        {
            "atom_id": "B1",
            "chain_id": "B",
            "residue_name": "GLY",
            "residue_number": 1,
            "atom_name": "CA",
            "x": 0.0,
            "y": 0.0,
            "z": 2.0,
        },
        {
            "atom_id": "B2",
            "chain_id": "B",
            "residue_name": "SER",
            "residue_number": 3,
            "atom_name": "CA",
            "x": 10.0,
            "y": 0.0,
            "z": 0.0,
        },
    ]


def test_extract_interface_contacts_prefers_scipy_kdtree_backend(monkeypatch):
    monkeypatch.setattr(
        interface_contacts,
        "_SCIPY_CACHE",
        interface_contacts._SciPyKDTreeModules(cKDTree=_FakeKDTree),
    )
    monkeypatch.setattr(interface_contacts, "_SCIPY_IMPORT_FAILED", False)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_CACHE", None)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_IMPORT_FAILED", True)

    summary = interface_contacts.extract_interface_contacts(
        _atom_rows(),
        pdb_id="1abc",
        cutoff=2.5,
    )

    assert summary.pdb_id == "1ABC"
    assert summary.backend == "scipy-kdtree"
    assert summary.contact_count == 2
    assert summary.chain_pair_counts == {"A|B": 2}
    assert summary.contacting_chains == ("A", "B")
    assert summary.contacting_residues_by_chain["A"] == ("A:1", "A:2")
    assert summary.contacting_residues_by_chain["B"] == ("B:1",)
    assert all(contact.left_chain_id != contact.right_chain_id for contact in summary.atom_contacts)
    assert summary.provenance["requested_backend"] == "auto"
    assert summary.provenance["resolved_backend"] == "scipy-kdtree"
    assert summary.atom_contacts[0].provenance["requested_backend"] == "auto"
    assert summary.atom_contacts[0].provenance["resolved_backend"] == "scipy-kdtree"
    assert summary.to_dict()["contact_count"] == 2


def test_extract_interface_contacts_requires_explicit_python_fallback(monkeypatch):
    monkeypatch.setattr(interface_contacts, "_SCIPY_CACHE", None)
    monkeypatch.setattr(interface_contacts, "_SCIPY_IMPORT_FAILED", True)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_CACHE", None)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_IMPORT_FAILED", True)

    with pytest.raises(
        interface_contacts.InterfaceContactError,
        match="No registered interface-contact backend",
    ):
        interface_contacts.extract_interface_contacts(
            _atom_rows(),
            pdb_id="1abc",
            cutoff=2.5,
        )

    summary = interface_contacts.extract_interface_contacts(
        _atom_rows(),
        pdb_id="1abc",
        cutoff=2.5,
        backend="python-fallback",
    )

    assert summary.backend == "python-fallback"
    assert summary.contact_count == 2
    assert summary.chain_pair_counts == {"A|B": 2}
    assert summary.provenance["requested_backend"] == "python-fallback"
    assert summary.provenance["resolved_backend"] == "python-fallback"
    assert summary.provenance["backend_candidates"] == ("python-fallback",)
    assert summary.atom_contacts[0].provenance["requested_backend"] == "python-fallback"
    assert summary.atom_contacts[0].provenance["resolved_backend"] == "python-fallback"
    assert interface_contacts.interface_contact_backends() == ()
    assert interface_contacts.interface_contact_backends(include_python_fallback=True) == (
        "python-fallback",
    )


def test_extract_interface_contacts_rejects_unavailable_registered_backend(monkeypatch):
    monkeypatch.setattr(interface_contacts, "_SCIPY_CACHE", None)
    monkeypatch.setattr(interface_contacts, "_SCIPY_IMPORT_FAILED", True)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_CACHE", None)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_IMPORT_FAILED", True)

    with pytest.raises(interface_contacts.InterfaceContactError, match="SciPy backend requested"):
        interface_contacts.extract_interface_contacts(
            _atom_rows(),
            pdb_id="1abc",
            cutoff=2.5,
            backend="scipy",
        )


def test_interface_contact_backends_excludes_python_fallback_by_default(monkeypatch):
    monkeypatch.setattr(
        interface_contacts,
        "_SCIPY_CACHE",
        interface_contacts._SciPyKDTreeModules(cKDTree=_FakeKDTree),
    )
    monkeypatch.setattr(interface_contacts, "_SCIPY_IMPORT_FAILED", False)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_CACHE", None)
    monkeypatch.setattr(interface_contacts, "_MDANALYSIS_IMPORT_FAILED", True)

    assert interface_contacts.interface_contact_backends() == ("scipy-kdtree",)
    assert interface_contacts.interface_contact_backends(include_python_fallback=True) == (
        "scipy-kdtree",
        "python-fallback",
    )


def test_extract_interface_contacts_rejects_rows_without_coordinates():
    with pytest.raises(interface_contacts.InterfaceContactError, match="No atom rows"):
        interface_contacts.extract_interface_contacts(
            [{"atom_id": "A1", "chain_id": "A", "residue_name": "ALA", "residue_number": 1}],
            pdb_id="1abc",
        )
