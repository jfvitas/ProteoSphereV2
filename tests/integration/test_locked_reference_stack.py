from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import features.esm2_embeddings as esm2_embeddings
import features.rdkit_descriptors as rdkit_descriptors
from connectors.rcsb.parsers import (
    RCSBAssemblyRecord,
    RCSBEntityRecord,
    RCSBEntryRecord,
    RCSBStructureBundle,
)
from connectors.uniprot.parsers import UniProtSequenceRecord
from models.reference.locked_stack import build_locked_reference_stack
from normalization.mapping.mmseqs2_backend import MMseqs2Backend


class _FakeParameter:
    def __init__(self) -> None:
        self.requires_grad = True


class _FakeTensor:
    def __init__(self, rows):
        self._rows = rows

    def to(self, device: str):  # noqa: ARG002
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self._rows


class _FakeNoGrad:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
        return False


class _FakeTorch:
    @staticmethod
    def no_grad():
        return _FakeNoGrad()


class _FakeTokenizer:
    @classmethod
    def from_pretrained(cls, model_name: str, cache_dir: str | None = None):  # noqa: ARG003
        return cls()

    def __call__(self, sequence: str, return_tensors: str = "pt"):  # noqa: ARG002
        width = len(sequence) + 2
        return {
            "input_ids": _FakeTensor([list(range(width))]),
            "attention_mask": _FakeTensor([[1] * width]),
        }


class _FakeModelOutput:
    def __init__(self, rows):
        self.last_hidden_state = _FakeTensor(rows)


class _FakeModel:
    def __init__(self) -> None:
        self.parameters_list = [_FakeParameter(), _FakeParameter()]

    @classmethod
    def from_pretrained(cls, model_name: str, cache_dir: str | None = None):  # noqa: ARG003
        return cls()

    def eval(self):
        return self

    def to(self, device: str):  # noqa: ARG002
        return self

    def parameters(self):
        return self.parameters_list

    def __call__(self, **batch):  # noqa: ARG002
        return _FakeModelOutput(
            [
                [
                    [0.0, 0.0],
                    [1.0, 1.0],
                    [2.0, 2.0],
                    [3.0, 3.0],
                ]
            ]
        )


class _FakeESMBackend:
    torch = _FakeTorch
    AutoTokenizer = _FakeTokenizer
    EsmModel = _FakeModel


@dataclass(frozen=True)
class _FakeMol:
    smiles: str


class _FakeChem:
    @staticmethod
    def MolFromSmiles(smiles: str):
        if not smiles.strip():
            return None
        return _FakeMol(smiles=smiles.strip())

    @staticmethod
    def MolToSmiles(mol: _FakeMol, canonical: bool = True):  # noqa: ARG004
        return mol.smiles

    @staticmethod
    def GetFormalCharge(mol: _FakeMol):  # noqa: ARG004
        return 0


class _FakeDescriptors:
    @staticmethod
    def MolWt(mol: _FakeMol):  # noqa: ARG004
        return 46.07

    @staticmethod
    def ExactMolWt(mol: _FakeMol):  # noqa: ARG004
        return 46.0419

    @staticmethod
    def HeavyAtomCount(mol: _FakeMol):  # noqa: ARG004
        return 3

    @staticmethod
    def NumHeteroatoms(mol: _FakeMol):  # noqa: ARG004
        return 1


class _FakeLipinski:
    @staticmethod
    def NumRotatableBonds(mol: _FakeMol):  # noqa: ARG004
        return 0

    @staticmethod
    def NumHDonors(mol: _FakeMol):  # noqa: ARG004
        return 1

    @staticmethod
    def NumHAcceptors(mol: _FakeMol):  # noqa: ARG004
        return 1


class _FakeRdMolDescriptors:
    @staticmethod
    def CalcNumRings(mol: _FakeMol):  # noqa: ARG004
        return 0

    @staticmethod
    def CalcNumAromaticRings(mol: _FakeMol):  # noqa: ARG004
        return 0

    @staticmethod
    def CalcTPSA(mol: _FakeMol):  # noqa: ARG004
        return 20.23

    @staticmethod
    def CalcFractionCSP3(mol: _FakeMol):  # noqa: ARG004
        return 1.0


class _FakeCrippen:
    @staticmethod
    def MolLogP(mol: _FakeMol):  # noqa: ARG004
        return -0.3


class _FakeMMseqsRunner:
    def __init__(
        self,
        *,
        version_output: str = "MMseqs2 Version 15-6f452\n",
        search_output: str | None = None,
    ) -> None:
        self.version_output = version_output
        self.search_output = search_output
        self.calls: list[tuple[str, ...]] = []

    def __call__(
        self,
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, env
        self.calls.append(tuple(command))
        if len(command) > 1 and command[1] == "--version":
            return subprocess.CompletedProcess(command, 0, self.version_output, "")
        if len(command) > 1 and command[1] == "easy-search":
            Path(command[4]).write_text(self.search_output or "", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected MMseqs2 command: {command}")


def test_locked_reference_stack_integrates_wired_backends_with_honest_blockers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        rdkit_descriptors,
        "_RDKit_CACHE",
        rdkit_descriptors._RDKitModules(
            Chem=_FakeChem,
            Descriptors=_FakeDescriptors,
            Lipinski=_FakeLipinski,
            rdMolDescriptors=_FakeRdMolDescriptors,
            Crippen=_FakeCrippen,
        ),
    )
    monkeypatch.setattr(rdkit_descriptors, "_RDKit_IMPORT_FAILED", False)

    mmseqs2_backend = MMseqs2Backend(
        which=lambda _: "C:\\tools\\mmseqs.exe",
        runner=_FakeMMseqsRunner(
            search_output=(
                "1:A\tP_MATCH\t97.5\t3\t0\t0\t1\t3\t3\t5\t1e-10\t110.0\t1.0\t0.43\n"
                "1:B\tP_MATCH\t97.5\t3\t0\t0\t1\t3\t3\t5\t1e-10\t110.0\t1.0\t0.43\n"
            )
        ),
        temp_root=tmp_path,
    )
    bundle = _bundle()
    result = build_locked_reference_stack(
        split_records=[
            {"record_id": "A1", "protein_cluster_id": "PC1", "ligand_scaffold_id": "SC1"},
            {"record_id": "A2", "protein_cluster_id": "PC1", "ligand_scaffold_id": "SC2"},
            {"record_id": "A3", "protein_cluster_id": "PC2", "ligand_scaffold_id": "SC2"},
            {"record_id": "B1", "protein_cluster_id": "PC3", "ligand_scaffold_id": "SC3"},
            {"record_id": "B2", "protein_cluster_id": "PC4", "ligand_scaffold_id": "SC4"},
            {"record_id": "U1", "protein_cluster_id": "PC5", "ligand_smiles": "CCO"},
        ],
        structure_bundle=bundle,
        atom_rows=_atom_rows(),
        residue_rows=[],
        protein_sequence="ACD",
        ligand_smiles="CCO",
        uniprot_records=(
            UniProtSequenceRecord(
                accession="P_MATCH",
                entry_name="P_MATCH_ENTRY",
                protein_name="Matched protein",
                organism_name="Test organism",
                gene_names=(),
                reviewed=True,
                sequence="TTACDAA",
                sequence_length=7,
                source_format="test",
            ),
        ),
        split_seed=11,
        interface_chain_pairs=(("A", "B"),),
        interface_backend="python-fallback",
        mmseqs2_backend=mmseqs2_backend,
        sequence_embedder=lambda sequence: esm2_embeddings.embed_sequence(
            sequence,
            backend=_FakeESMBackend(),
        ),
    )

    assert result.split_result.protein_identity_threshold == 0.30
    assert result.split_result.split_ratios == {"train": 0.70, "val": 0.15, "test": 0.15}
    assert result.split_result.unresolved[0].record_id == "U1"
    split_by_record = {
        assignment.record_id: assignment.split for assignment in result.split_result.assignments
    }
    assert len({split_by_record["A1"], split_by_record["A2"], split_by_record["A3"]}) == 1

    protein_clusters_by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    scaffolds_by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for assignment in result.split_result.assignments:
        protein_clusters_by_split[assignment.split].add(assignment.protein_cluster_id)
        scaffolds_by_split[assignment.split].add(assignment.ligand_scaffold_id)
    assert protein_clusters_by_split["train"].isdisjoint(protein_clusters_by_split["val"])
    assert protein_clusters_by_split["train"].isdisjoint(protein_clusters_by_split["test"])
    assert protein_clusters_by_split["val"].isdisjoint(protein_clusters_by_split["test"])
    assert scaffolds_by_split["train"].isdisjoint(scaffolds_by_split["val"])
    assert scaffolds_by_split["train"].isdisjoint(scaffolds_by_split["test"])
    assert scaffolds_by_split["val"].isdisjoint(scaffolds_by_split["test"])

    assert [mapping.chain_id for mapping in result.chain_mappings] == ["A", "B"]
    assert all(mapping.status == "resolved" for mapping in result.chain_mappings)
    assert all(mapping.alignment_backend == "mmseqs2" for mapping in result.chain_mappings)
    assert all(mapping.resolved_accession == "P_MATCH" for mapping in result.chain_mappings)
    assert result.chain_mapping_provenance["backend"] == "mmseqs2"
    assert result.chain_mapping_provenance["fallback_used"] is False
    entity_run = result.chain_mapping_provenance["entities"][0]
    assert entity_run["status"] == "ok"
    assert entity_run["provenance"]["backend"] == "mmseqs2"
    assert entity_run["provenance"]["runtime_available"] is True
    assert entity_run["provenance"]["command"][1] == "easy-search"

    atom_graph = result.features.structure_graphs["atom"]
    residue_graph = result.features.structure_graphs["residue"]
    assert atom_graph.node_ids == ("A1", "A2", "B1", "B2")
    assert "A:1" in residue_graph.node_ids
    assert residue_graph.provenance["entry_title"] == "Locked reference test bundle"

    assert result.features.interface_contacts.backend == "python-fallback"
    assert result.features.interface_contacts.chain_pair_counts == {"A|B": 2}
    assert result.features.interface_contacts.contacting_chains == ("A", "B")

    assert result.features.sequence_embedding is not None
    assert result.features.sequence_embedding.sequence == "ACD"
    assert result.features.sequence_embedding.pooled_embedding == (2.0, 2.0)

    assert result.features.ligand_descriptors is not None
    assert result.features.ligand_descriptors.canonical_smiles == "CCO"
    assert result.features.ligand_descriptors.descriptors["molecular_weight"] == 46.07
    assert result.features.ligand_descriptors.descriptors["formal_charge"] == 0

    assert result.model_stage.backend_ready is False
    assert result.model_stage.requested_backend == "EGNN+ESM2+cross_attention+xgboost"
    assert result.model_stage.resolved_backend == "lockdown_reference_model"
    assert result.model_stage.contract_fidelity == "partially-blocked-model-contract"
    assert result.model_stage.blocked_substages == ("prediction_head",)
    assert result.training_stage.backend_ready is False
    assert result.training_stage.requested_backend == "adamw+cosine+fp16"
    assert result.training_stage.resolved_backend == "locked_reference_training_backend"
    assert result.training_stage.contract_fidelity == "configuration-and-plan-only"
    assert result.training_stage.blocked_substages == ("trainer_runtime",)
    assert result.model_stage.config["structure_encoder"] == "EGNN"
    assert result.model_stage.config["fusion"] == "cross_attention"
    assert result.model_stage.config["head"] == "xgboost"
    assert result.training_stage.config["optimizer"] == "adamw"
    assert result.training_stage.config["scheduler"] == "cosine"
    assert result.training_stage.config["mixed_precision"] is True
    assert result.model_stage.local_backend_files == ("models/reference/lockdown_model.py",)
    assert result.training_stage.local_backend_files == ("training/reference/locked_train.py",)

    assert result.model_backend.structure_path.status.resolved_backend == "local-graph-summary"
    assert result.model_backend.sequence_path.status.contract_fidelity == "pretrained-frozen"
    assert result.model_backend.fusion.status.resolved_backend == "local-cross-attention"
    assert result.model_backend.head.status.resolved_backend == "feature-vector-contract-only"
    assert result.training_backend.plan.status.resolved_backend == "contract-plan-only"
    assert result.training_backend.state.phase == "blocked"
    assert result.training_backend.plan.train_examples == result.split_result.split_counts["train"]
    assert result.training_backend.plan.val_examples == result.split_result.split_counts["val"]

    payload = result.to_dict()
    assert payload["chain_mapping_provenance"]["backend"] == "mmseqs2"
    assert payload["model_backend"]["head"]["status"]["backend_ready"] is False
    assert payload["training_backend"]["plan"]["status"]["resolved_backend"] == "contract-plan-only"
    assert result.blocked_stages == ("prediction_head", "trainer_runtime")


def _bundle() -> RCSBStructureBundle:
    return RCSBStructureBundle(
        entry=RCSBEntryRecord(
            pdb_id="1ABC",
            title="Locked reference test bundle",
            experimental_methods=("X-RAY DIFFRACTION",),
            resolution=1.8,
            release_date="2024-01-01",
            assembly_ids=("1",),
            polymer_entity_ids=("1",),
            nonpolymer_entity_ids=("2",),
        ),
        entities=(
            RCSBEntityRecord(
                pdb_id="1ABC",
                entity_id="1",
                description="Example protein",
                polymer_type="Protein",
                sequence="ACD",
                sequence_length=3,
                chain_ids=("A", "B"),
                uniprot_ids=("P_HINT",),
                organism_names=("Test organism",),
                taxonomy_ids=("1234",),
            ),
        ),
        assemblies=(
            RCSBAssemblyRecord(
                pdb_id="1ABC",
                assembly_id="1",
                method="author_defined_assembly",
                oligomeric_state="dimer",
                oligomeric_count=2,
                stoichiometry="A2",
                chain_ids=("A", "B"),
                polymer_entity_ids=("1",),
            ),
        ),
    )


def _atom_rows() -> list[dict[str, object]]:
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
            "bond_partners": ("A2",),
        },
        {
            "atom_id": "A2",
            "chain_id": "A",
            "residue_name": "CYS",
            "residue_number": 2,
            "atom_name": "CA",
            "x": 0.0,
            "y": 0.0,
            "z": 1.0,
            "bond_partners": ("A1",),
        },
        {
            "atom_id": "B1",
            "chain_id": "B",
            "residue_name": "ASP",
            "residue_number": 1,
            "atom_name": "CA",
            "x": 0.0,
            "y": 0.0,
            "z": 2.0,
            "bond_partners": ("B2",),
        },
        {
            "atom_id": "B2",
            "chain_id": "B",
            "residue_name": "GLY",
            "residue_number": 2,
            "atom_name": "CA",
            "x": 10.0,
            "y": 0.0,
            "z": 0.0,
            "bond_partners": ("B1",),
        },
    ]
