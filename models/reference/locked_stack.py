from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from connectors.rcsb.parsers import RCSBEntityRecord, RCSBStructureBundle
from connectors.uniprot.parsers import UniProtSequenceRecord
from datasets.splits.locked_split import (
    DEFAULT_PROTEIN_IDENTITY_THRESHOLD,
    DEFAULT_SPLIT_RATIOS,
    LigandScaffoldResolver,
    LockedSplitRecord,
    LockedSplitResult,
    ProteinClusterResolver,
    assign_locked_splits,
)
from features.esm2_embeddings import ESM2UnavailableError, ProteinEmbeddingResult, embed_sequence
from features.interface_contacts import InterfaceContactSummary, extract_interface_contacts
from features.rdkit_descriptors import (
    LigandDescriptorResult,
    RdkitUnavailableError,
    describe_smiles,
)
from features.structure_graphs import AtomGraph, ResidueGraph, extract_structure_graphs
from models.reference.lockdown_model import (
    LockdownReferenceModelResult,
    run_lockdown_reference_model,
)
from normalization.mapping.mmseqs2_backend import (
    MMseqs2AlignmentHit,
    MMseqs2AlignmentResult,
    MMseqs2Backend,
    MMseqs2Sequence,
)
from normalization.mapping.mmseqs2_chain_alignment import (
    ChainAlignmentCandidate,
    ChainUniProtMapping,
)
from training.reference.locked_train import (
    LockedTrainingBackendResult,
    prepare_locked_reference_training,
)

Scalar = str | int | float | bool
StructureGraphs = dict[str, AtomGraph | ResidueGraph]
SequenceEmbedder = Callable[[str], ProteinEmbeddingResult]
LigandDescriptorFactory = Callable[[str], LigandDescriptorResult]
XGBoostStylePredictor = Any

_CHAIN_MAPPING_MIN_IDENTITY = 0.85
_CHAIN_MAPPING_MIN_QUERY_COVERAGE = 0.90
_CHAIN_MAPPING_AMBIGUITY_MARGIN = 0.02


@dataclass(frozen=True, slots=True)
class LockedSplitSpec:
    protein_identity_threshold: float
    ratios: dict[str, float]
    source_path: str


@dataclass(frozen=True, slots=True)
class LockedStageSpec:
    name: str
    config: dict[str, Scalar]
    source_path: str


@dataclass(frozen=True, slots=True)
class LockedReferenceSpecs:
    split: LockedSplitSpec
    model: LockedStageSpec
    training: LockedStageSpec
    pipeline_source_path: str


@dataclass(frozen=True, slots=True)
class LockedStackBlocker:
    stage: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class LockedStageStatus:
    name: str
    config: dict[str, Scalar]
    source_path: str
    backend_ready: bool
    local_backend_files: tuple[str, ...]
    requested_backend: str
    resolved_backend: str
    contract_fidelity: str
    blocked_substages: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    blocker: LockedStackBlocker | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "config": dict(self.config),
            "source_path": self.source_path,
            "backend_ready": self.backend_ready,
            "local_backend_files": list(self.local_backend_files),
            "requested_backend": self.requested_backend,
            "resolved_backend": self.resolved_backend,
            "contract_fidelity": self.contract_fidelity,
            "blocked_substages": list(self.blocked_substages),
            "provenance": dict(self.provenance),
            "blocker": self.blocker.to_dict() if self.blocker is not None else None,
        }


@dataclass(frozen=True, slots=True)
class LockedReferenceFeatureResult:
    structure_graphs: StructureGraphs
    interface_contacts: InterfaceContactSummary
    sequence_embedding: ProteinEmbeddingResult | None
    ligand_descriptors: LigandDescriptorResult | None


@dataclass(frozen=True, slots=True)
class LockedReferenceStackResult:
    specs: LockedReferenceSpecs
    split_result: LockedSplitResult
    chain_mappings: tuple[ChainUniProtMapping, ...]
    chain_mapping_provenance: dict[str, object]
    features: LockedReferenceFeatureResult
    model_backend: LockdownReferenceModelResult
    training_backend: LockedTrainingBackendResult
    model_stage: LockedStageStatus
    training_stage: LockedStageStatus
    blockers: tuple[LockedStackBlocker, ...]

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for blocker in self.blockers:
            seen.setdefault(blocker.stage, None)
        return tuple(seen)

    def to_dict(self) -> dict[str, object]:
        return {
            "specs": {
                "split": {
                    "protein_identity_threshold": self.specs.split.protein_identity_threshold,
                    "ratios": dict(self.specs.split.ratios),
                    "source_path": self.specs.split.source_path,
                },
                "model": {
                    "name": self.specs.model.name,
                    "config": dict(self.specs.model.config),
                    "source_path": self.specs.model.source_path,
                },
                "training": {
                    "name": self.specs.training.name,
                    "config": dict(self.specs.training.config),
                    "source_path": self.specs.training.source_path,
                },
                "pipeline_source_path": self.specs.pipeline_source_path,
            },
            "split_result": self.split_result.to_dict(),
            "chain_mappings": [mapping.to_dict() for mapping in self.chain_mappings],
            "chain_mapping_provenance": dict(self.chain_mapping_provenance),
            "features": {
                "structure_graphs": {
                    name: {
                        "pdb_id": graph.pdb_id,
                        "node_ids": list(graph.node_ids),
                        "edge_count": len(graph.edges),
                        "provenance": dict(graph.provenance),
                    }
                    for name, graph in self.features.structure_graphs.items()
                },
                "interface_contacts": self.features.interface_contacts.to_dict(),
                "sequence_embedding": (
                    self.features.sequence_embedding.to_dict()
                    if self.features.sequence_embedding is not None
                    else None
                ),
                "ligand_descriptors": (
                    self.features.ligand_descriptors.to_dict()
                    if self.features.ligand_descriptors is not None
                    else None
                ),
            },
            "model_backend": self.model_backend.to_dict(),
            "training_backend": self.training_backend.to_dict(),
            "model_stage": self.model_stage.to_dict(),
            "training_stage": self.training_stage.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


class LockedReferenceStack:
    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        sequence_embedder: SequenceEmbedder | None = None,
        ligand_descriptor_factory: LigandDescriptorFactory | None = None,
        mmseqs2_backend: MMseqs2Backend | None = None,
        xgboost_predictor: XGBoostStylePredictor | None = None,
        interface_backend: str = "auto",
    ) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.specs = load_locked_reference_specs(self.repo_root)
        self.sequence_embedder = sequence_embedder or embed_sequence
        self.ligand_descriptor_factory = ligand_descriptor_factory or describe_smiles
        self.mmseqs2_backend = mmseqs2_backend or MMseqs2Backend()
        self.xgboost_predictor = xgboost_predictor
        self.interface_backend = interface_backend
        _validate_split_contract(self.specs.split)

    def build(
        self,
        *,
        split_records: Sequence[Mapping[str, Any] | Any | LockedSplitRecord],
        structure_bundle: RCSBStructureBundle,
        atom_rows: Iterable[Mapping[str, Any]],
        residue_rows: Iterable[Mapping[str, Any]] | None,
        protein_sequence: str,
        ligand_smiles: str,
        uniprot_records: Iterable[UniProtSequenceRecord] = (),
        split_seed: int = 0,
        protein_cluster_resolver: ProteinClusterResolver | None = None,
        ligand_scaffold_resolver: LigandScaffoldResolver | None = None,
        interface_chain_pairs: Iterable[tuple[str, str]] | None = None,
        model_target_names: Sequence[str] = ("affinity",),
        training_gradient_accumulation_steps: int = 1,
        training_device_target: str = "cpu",
        training_mixed_precision_dtype: str | None = None,
    ) -> LockedReferenceStackResult:
        atom_row_list = list(atom_rows)
        residue_row_list = list(residue_rows or ())
        split_result = assign_locked_splits(
            split_records,
            seed=split_seed,
            protein_identity_threshold=self.specs.split.protein_identity_threshold,
            split_ratios=self.specs.split.ratios,
            protein_cluster_resolver=protein_cluster_resolver,
            ligand_scaffold_resolver=ligand_scaffold_resolver,
        )

        blockers: list[LockedStackBlocker] = []
        uniprot_record_tuple = tuple(uniprot_records)
        chain_mappings, chain_mapping_provenance, chain_mapping_blockers = self._map_chains(
            structure_bundle,
            uniprot_record_tuple,
        )
        blockers.extend(chain_mapping_blockers)

        structure_graphs = extract_structure_graphs(
            structure_bundle,
            atom_rows=atom_row_list,
            residue_rows=residue_row_list,
        )
        interface_contacts = extract_interface_contacts(
            atom_row_list,
            pdb_id=structure_bundle.pdb_id,
            chain_pairs=interface_chain_pairs,
            backend=self.interface_backend,
        )

        sequence_embedding = self._embed_sequence(protein_sequence, blockers)
        ligand_descriptors = self._describe_ligand(ligand_smiles, blockers)

        model_backend = run_lockdown_reference_model(
            structure_graphs=structure_graphs,
            sequence_embedding=sequence_embedding,
            protein_sequence=protein_sequence if sequence_embedding is None else None,
            ligand_descriptors=ligand_descriptors,
            target_names=model_target_names,
            repo_root=self.repo_root,
            sequence_embedder=self.sequence_embedder,
            xgboost_predictor=self.xgboost_predictor,
        )
        training_backend = prepare_locked_reference_training(
            train_examples=split_result.split_counts.get("train", 0),
            val_examples=split_result.split_counts.get("val", 0),
            gradient_accumulation_steps=training_gradient_accumulation_steps,
            deterministic_seed=split_seed,
            device_target=training_device_target,
            mixed_precision_dtype=training_mixed_precision_dtype,
            repo_root=self.repo_root,
        )

        model_stage = _model_stage_status(
            repo_root=self.repo_root,
            spec=self.specs.model,
            result=model_backend,
        )
        training_stage = _training_stage_status(
            repo_root=self.repo_root,
            spec=self.specs.training,
            result=training_backend,
        )

        blockers.extend(
            LockedStackBlocker(stage=blocker.stage, reason=blocker.reason)
            for blocker in model_backend.blockers
        )
        blockers.extend(
            LockedStackBlocker(stage=blocker.stage, reason=blocker.reason)
            for blocker in training_backend.blockers
        )
        blockers = _dedupe_blockers(blockers)

        return LockedReferenceStackResult(
            specs=self.specs,
            split_result=split_result,
            chain_mappings=chain_mappings,
            chain_mapping_provenance=chain_mapping_provenance,
            features=LockedReferenceFeatureResult(
                structure_graphs=structure_graphs,
                interface_contacts=interface_contacts,
                sequence_embedding=sequence_embedding,
                ligand_descriptors=ligand_descriptors,
            ),
            model_backend=model_backend,
            training_backend=training_backend,
            model_stage=model_stage,
            training_stage=training_stage,
            blockers=tuple(blockers),
        )

    def _map_chains(
        self,
        structure_bundle: RCSBStructureBundle,
        uniprot_records: tuple[UniProtSequenceRecord, ...],
    ) -> tuple[tuple[ChainUniProtMapping, ...], dict[str, object], list[LockedStackBlocker]]:
        all_mappings: list[ChainUniProtMapping] = []
        entity_runs: list[dict[str, object]] = []
        blockers: list[LockedStackBlocker] = []

        for entity in structure_bundle.entities:
            if "protein" not in entity.polymer_type.lower():
                continue
            mappings, entity_result = _map_entity_chains_with_mmseqs2(
                entity,
                uniprot_records,
                self.mmseqs2_backend,
            )
            all_mappings.extend(mappings)
            entity_runs.append(entity_result)
            if entity_result["status"] in {"runtime_unavailable", "execution_failed"}:
                blockers.append(
                    LockedStackBlocker(
                        stage="chain_mapping",
                        reason=(
                            "MMseqs2-backed chain mapping could not run: "
                            f"{entity_result['reason']}"
                        ),
                    )
                )

        provenance = {
            "backend": "mmseqs2",
            "fallback_used": False,
            "entities": entity_runs,
        }
        return tuple(all_mappings), provenance, _dedupe_blockers(blockers)

    def _embed_sequence(
        self,
        sequence: str,
        blockers: list[LockedStackBlocker],
    ) -> ProteinEmbeddingResult | None:
        try:
            return self.sequence_embedder(sequence)
        except ESM2UnavailableError as exc:
            blockers.append(LockedStackBlocker(stage="sequence_encoder", reason=str(exc)))
            return None

    def _describe_ligand(
        self,
        smiles: str,
        blockers: list[LockedStackBlocker],
    ) -> LigandDescriptorResult | None:
        try:
            return self.ligand_descriptor_factory(smiles)
        except RdkitUnavailableError as exc:
            blockers.append(LockedStackBlocker(stage="ligand_descriptors", reason=str(exc)))
            return None


def build_locked_reference_stack(
    *,
    split_records: Sequence[Mapping[str, Any] | Any | LockedSplitRecord],
    structure_bundle: RCSBStructureBundle,
    atom_rows: Iterable[Mapping[str, Any]],
    residue_rows: Iterable[Mapping[str, Any]] | None,
    protein_sequence: str,
    ligand_smiles: str,
    uniprot_records: Iterable[UniProtSequenceRecord] = (),
    split_seed: int = 0,
    protein_cluster_resolver: ProteinClusterResolver | None = None,
    ligand_scaffold_resolver: LigandScaffoldResolver | None = None,
    interface_chain_pairs: Iterable[tuple[str, str]] | None = None,
    sequence_embedder: SequenceEmbedder | None = None,
    ligand_descriptor_factory: LigandDescriptorFactory | None = None,
    mmseqs2_backend: MMseqs2Backend | None = None,
    xgboost_predictor: XGBoostStylePredictor | None = None,
    model_target_names: Sequence[str] = ("affinity",),
    training_gradient_accumulation_steps: int = 1,
    training_device_target: str = "cpu",
    training_mixed_precision_dtype: str | None = None,
    interface_backend: str = "auto",
    repo_root: str | Path | None = None,
) -> LockedReferenceStackResult:
    return LockedReferenceStack(
        repo_root=repo_root,
        sequence_embedder=sequence_embedder,
        ligand_descriptor_factory=ligand_descriptor_factory,
        mmseqs2_backend=mmseqs2_backend,
        xgboost_predictor=xgboost_predictor,
        interface_backend=interface_backend,
    ).build(
        split_records=split_records,
        structure_bundle=structure_bundle,
        atom_rows=atom_rows,
        residue_rows=residue_rows,
        protein_sequence=protein_sequence,
        ligand_smiles=ligand_smiles,
        uniprot_records=uniprot_records,
        split_seed=split_seed,
        protein_cluster_resolver=protein_cluster_resolver,
        ligand_scaffold_resolver=ligand_scaffold_resolver,
        interface_chain_pairs=interface_chain_pairs,
        model_target_names=model_target_names,
        training_gradient_accumulation_steps=training_gradient_accumulation_steps,
        training_device_target=training_device_target,
        training_mixed_precision_dtype=training_mixed_precision_dtype,
    )


def load_locked_reference_specs(repo_root: str | Path | None = None) -> LockedReferenceSpecs:
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    lockdown_root = root / "master_handoff_package" / "01_LOCKDOWN_SPEC"
    split_path = lockdown_root / "data" / "split_strategy.md"
    model_path = lockdown_root / "models" / "default_model.yaml"
    training_path = lockdown_root / "training" / "default_training.yaml"
    pipeline_path = lockdown_root / "pipeline" / "reference_pipeline.md"

    split_spec = _parse_split_spec(split_path)
    model_spec = LockedStageSpec(
        name="model",
        config=_parse_simple_yaml_mapping(model_path),
        source_path=_relative_path(root, model_path),
    )
    training_spec = LockedStageSpec(
        name="training",
        config=_parse_simple_yaml_mapping(training_path),
        source_path=_relative_path(root, training_path),
    )
    return LockedReferenceSpecs(
        split=split_spec,
        model=model_spec,
        training=training_spec,
        pipeline_source_path=_relative_path(root, pipeline_path),
    )


def _parse_split_spec(path: Path) -> LockedSplitSpec:
    text = path.read_text(encoding="utf-8")
    threshold_match = re.search(r"MMseqs2 at\s+(\d+(?:\.\d+)?)%\s+identity", text, re.IGNORECASE)
    if threshold_match is None:
        raise ValueError(f"Unable to parse protein identity threshold from {path}")
    ratio_matches = dict(
        (split.lower(), float(percent) / 100.0)
        for split, percent in re.findall(r"-\s*(train|val|test):\s*(\d+(?:\.\d+)?)%", text)
    )
    if set(ratio_matches) != {"train", "val", "test"}:
        raise ValueError(f"Unable to parse split ratios from {path}")
    return LockedSplitSpec(
        protein_identity_threshold=float(threshold_match.group(1)) / 100.0,
        ratios=ratio_matches,
        source_path=_relative_path(path.parents[3], path),
    )


def _parse_simple_yaml_mapping(path: Path) -> dict[str, Scalar]:
    config: dict[str, Scalar] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Unsupported YAML line in {path}: {raw_line!r}")
        config[key.strip()] = _parse_scalar(value.strip())
    return config


def _parse_scalar(value: str) -> Scalar:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?", value, re.IGNORECASE):
        return float(value)
    return value


def _validate_split_contract(spec: LockedSplitSpec) -> None:
    if abs(spec.protein_identity_threshold - DEFAULT_PROTEIN_IDENTITY_THRESHOLD) > 1e-9:
        raise RuntimeError(
            "Locked split spec and local split primitive disagree on protein identity threshold"
        )
    for split_name, expected_ratio in spec.ratios.items():
        local_ratio = DEFAULT_SPLIT_RATIOS.get(split_name)
        if local_ratio is None or abs(local_ratio - expected_ratio) > 1e-9:
            raise RuntimeError(
                f"Locked split spec and local split primitive disagree on ratio for {split_name}"
            )


def _map_entity_chains_with_mmseqs2(
    entity: RCSBEntityRecord,
    uniprot_records: tuple[UniProtSequenceRecord, ...],
    backend: MMseqs2Backend,
) -> tuple[tuple[ChainUniProtMapping, ...], dict[str, object]]:
    chain_ids = entity.chain_ids or ("",)
    query_sequence = str(entity.sequence or "").strip()
    accession_lookup = {record.accession: record for record in uniprot_records}

    if not query_sequence:
        mappings = tuple(
            _unresolved_chain_mapping(
                entity=entity,
                chain_id=chain_id,
                provided_uniprot_ids=entity.uniprot_ids,
                reason="empty_query_sequence",
                alignment_backend="mmseqs2",
                query_sequence_length=0,
            )
            for chain_id in chain_ids
        )
        return mappings, {
            "entity_id": entity.entity_id,
            "status": "empty_input",
            "reason": "empty_query_sequence",
            "provenance": {
                "backend": "mmseqs2",
                "runtime_available": False,
                "fallback_used": False,
            },
        }

    query_ids = [f"{entity.entity_id}:{chain_id or 'entity'}" for chain_id in chain_ids]
    query_sequences = tuple(
        MMseqs2Sequence(sequence_id=query_id, sequence=query_sequence)
        for query_id in query_ids
    )
    target_sequences = tuple(
        MMseqs2Sequence(
            sequence_id=record.accession,
            sequence=record.sequence,
            description=record.entry_name,
        )
        for record in uniprot_records
    )

    alignment_result = backend.align(query_sequences, target_sequences)
    hits_by_query: dict[str, list[MMseqs2AlignmentHit]] = {}
    for hit in alignment_result.hits:
        hits_by_query.setdefault(hit.query_id, []).append(hit)

    mappings = tuple(
        _resolve_chain_mapping_from_mmseqs2(
            entity=entity,
            chain_id=chain_id,
            query_sequence=query_sequence,
            provided_uniprot_ids=entity.uniprot_ids,
            accession_lookup=accession_lookup,
            alignment_result=alignment_result,
            hits=tuple(hits_by_query.get(query_id, ())),
        )
        for chain_id, query_id in zip(chain_ids, query_ids, strict=True)
    )
    return mappings, {
        "entity_id": entity.entity_id,
        "status": alignment_result.status,
        "reason": alignment_result.reason,
        "provenance": alignment_result.provenance.to_dict(),
        "stderr": alignment_result.stderr,
        "chain_ids": list(chain_ids),
    }


def _resolve_chain_mapping_from_mmseqs2(
    *,
    entity: RCSBEntityRecord,
    chain_id: str,
    query_sequence: str,
    provided_uniprot_ids: Sequence[str],
    accession_lookup: Mapping[str, UniProtSequenceRecord],
    alignment_result: MMseqs2AlignmentResult,
    hits: tuple[MMseqs2AlignmentHit, ...],
) -> ChainUniProtMapping:
    if alignment_result.status in {"runtime_unavailable", "execution_failed"}:
        return _unresolved_chain_mapping(
            entity=entity,
            chain_id=chain_id,
            provided_uniprot_ids=provided_uniprot_ids,
            reason=alignment_result.reason,
            alignment_backend="mmseqs2",
            query_sequence_length=len(query_sequence),
        )

    if not accession_lookup:
        return _unresolved_chain_mapping(
            entity=entity,
            chain_id=chain_id,
            provided_uniprot_ids=provided_uniprot_ids,
            reason="no_candidate_sequences",
            alignment_backend="mmseqs2",
            query_sequence_length=len(query_sequence),
        )

    if not hits:
        return _unresolved_chain_mapping(
            entity=entity,
            chain_id=chain_id,
            provided_uniprot_ids=provided_uniprot_ids,
            reason="no_hits",
            alignment_backend="mmseqs2",
            query_sequence_length=len(query_sequence),
        )

    candidates = tuple(
        sorted(
            (
                _candidate_from_hit(
                    hit,
                    query_length=len(query_sequence),
                    accession_lookup=accession_lookup,
                    provided_uniprot_ids=provided_uniprot_ids,
                )
                for hit in hits
            ),
            key=_candidate_sort_key,
        )
    )
    qualified = tuple(
        candidate
        for candidate in candidates
        if candidate.identity >= _CHAIN_MAPPING_MIN_IDENTITY
        and candidate.query_coverage >= _CHAIN_MAPPING_MIN_QUERY_COVERAGE
    )
    if not qualified:
        return ChainUniProtMapping(
            pdb_id=entity.pdb_id,
            entity_id=entity.entity_id,
            chain_id=chain_id,
            status="unresolved",
            alignment_backend="mmseqs2",
            resolved_accession=None,
            reason="no_alignment_passed_thresholds",
            query_sequence_length=len(query_sequence),
            provided_uniprot_ids=tuple(provided_uniprot_ids),
            candidates=candidates,
        )

    winner = qualified[0]
    runner_up = qualified[1] if len(qualified) > 1 else None
    if runner_up is not None and _is_ambiguous_mmseqs2(winner, runner_up):
        return ChainUniProtMapping(
            pdb_id=entity.pdb_id,
            entity_id=entity.entity_id,
            chain_id=chain_id,
            status="ambiguous",
            alignment_backend="mmseqs2",
            resolved_accession=None,
            reason="ambiguous_top_alignment",
            query_sequence_length=len(query_sequence),
            provided_uniprot_ids=tuple(provided_uniprot_ids),
            candidates=candidates,
        )

    return ChainUniProtMapping(
        pdb_id=entity.pdb_id,
        entity_id=entity.entity_id,
        chain_id=chain_id,
        status="resolved",
        alignment_backend="mmseqs2",
        resolved_accession=winner.accession,
        reason="alignment_resolved",
        query_sequence_length=len(query_sequence),
        provided_uniprot_ids=tuple(provided_uniprot_ids),
        candidates=candidates,
    )


def _candidate_from_hit(
    hit: MMseqs2AlignmentHit,
    *,
    query_length: int,
    accession_lookup: Mapping[str, UniProtSequenceRecord],
    provided_uniprot_ids: Sequence[str],
) -> ChainAlignmentCandidate:
    record = accession_lookup.get(hit.target_id)
    hint_accessions = set(provided_uniprot_ids)
    return ChainAlignmentCandidate(
        accession=hit.target_id,
        entry_name=record.entry_name if record is not None else hit.target_id,
        alignment_backend="mmseqs2",
        score=int(round(hit.bit_score)),
        identity=float(hit.percent_identity) / 100.0,
        query_coverage=min(1.0, float(hit.query_coverage)),
        target_coverage=min(1.0, float(hit.target_coverage)),
        aligned_query_length=min(query_length, max(0, hit.query_end - hit.query_start + 1)),
        aligned_target_length=max(0, hit.target_end - hit.target_start + 1),
        is_reference_hint=hit.target_id in hint_accessions,
    )


def _candidate_sort_key(
    candidate: ChainAlignmentCandidate,
) -> tuple[float, float, float, float, str]:
    return (
        -float(candidate.score),
        -candidate.identity,
        -candidate.query_coverage,
        -candidate.target_coverage,
        candidate.accession,
    )


def _is_ambiguous_mmseqs2(
    winner: ChainAlignmentCandidate,
    runner_up: ChainAlignmentCandidate,
) -> bool:
    return (
        abs(float(winner.score) - float(runner_up.score)) <= 1.0
        and abs(winner.identity - runner_up.identity) <= _CHAIN_MAPPING_AMBIGUITY_MARGIN
        and abs(winner.query_coverage - runner_up.query_coverage)
        <= _CHAIN_MAPPING_AMBIGUITY_MARGIN
    )


def _unresolved_chain_mapping(
    *,
    entity: RCSBEntityRecord,
    chain_id: str,
    provided_uniprot_ids: Sequence[str],
    reason: str,
    alignment_backend: str,
    query_sequence_length: int,
) -> ChainUniProtMapping:
    return ChainUniProtMapping(
        pdb_id=entity.pdb_id,
        entity_id=entity.entity_id,
        chain_id=chain_id,
        status="unresolved",
        alignment_backend=alignment_backend,
        resolved_accession=None,
        reason=reason,
        query_sequence_length=query_sequence_length,
        provided_uniprot_ids=tuple(provided_uniprot_ids),
        candidates=(),
    )


def _model_stage_status(
    *,
    repo_root: Path,
    spec: LockedStageSpec,
    result: LockdownReferenceModelResult,
) -> LockedStageStatus:
    blocked_substages = tuple(dict.fromkeys(blocker.stage for blocker in result.blockers))
    blocker = None
    if blocked_substages:
        blocker = LockedStackBlocker(
            stage="model",
            reason="Locked model backend remains blocked at " + ", ".join(blocked_substages) + ".",
        )
    return LockedStageStatus(
        name=spec.name,
        config=spec.config,
        source_path=spec.source_path,
        backend_ready=not blocked_substages,
        local_backend_files=_existing_backend_files(
            repo_root,
            (repo_root / "models" / "reference" / "lockdown_model.py",),
        ),
        requested_backend=_format_requested_model_backend(spec.config),
        resolved_backend="lockdown_reference_model",
        contract_fidelity=_summarize_model_contract_fidelity(result),
        blocked_substages=blocked_substages,
        provenance={
            "real_components": [
                "frozen sequence encoding contract",
                "deterministic feature wiring",
            ],
            "surrogate_components": [
                "graph-summary structure encoder",
                "deterministic attention-style fusion",
            ],
            "blocked_components": list(blocked_substages),
            "structure_path": result.structure_path.status.to_dict(),
            "sequence_path": result.sequence_path.status.to_dict(),
            "fusion": result.fusion.status.to_dict(),
            "head": result.head.status.to_dict(),
        },
        blocker=blocker,
    )


def _training_stage_status(
    *,
    repo_root: Path,
    spec: LockedStageSpec,
    result: LockedTrainingBackendResult,
) -> LockedStageStatus:
    blocked_substages = tuple(dict.fromkeys(result.blocked_stages))
    blocker = None
    if blocked_substages:
        blocker = LockedStackBlocker(
            stage="training",
            reason=(
                "Locked training backend remains blocked at "
                + ", ".join(blocked_substages)
                + "."
            ),
        )
    return LockedStageStatus(
        name=spec.name,
        config=spec.config,
        source_path=spec.source_path,
        backend_ready=not blocked_substages and result.plan.status.backend_ready,
        local_backend_files=_existing_backend_files(
            repo_root,
            (repo_root / "training" / "reference" / "locked_train.py",),
        ),
        requested_backend=result.plan.status.requested_backend,
        resolved_backend="locked_reference_training_backend",
        contract_fidelity=result.plan.status.contract_fidelity,
        blocked_substages=blocked_substages,
        provenance={
            "plan_status": result.plan.status.to_dict(),
            "plan_signature": result.plan.plan_signature,
            "state_signature": result.state.state_signature,
            "train_examples": result.plan.train_examples,
            "val_examples": result.plan.val_examples,
            "real_components": list(result.plan.status.provenance.get("real_components", [])),
            "abstracted_components": list(
                result.plan.status.provenance.get("abstracted_components", [])
            ),
        },
        blocker=blocker,
    )


def _format_requested_model_backend(config: Mapping[str, Scalar]) -> str:
    return "+".join(
        str(config.get(key, "")).strip()
        for key in ("structure_encoder", "sequence_encoder", "fusion", "head")
        if str(config.get(key, "")).strip()
    )


def _summarize_model_contract_fidelity(result: LockdownReferenceModelResult) -> str:
    component_fidelities = (
        result.structure_path.status.contract_fidelity,
        result.sequence_path.status.contract_fidelity,
        result.fusion.status.contract_fidelity,
        result.head.status.contract_fidelity,
    )
    if result.blockers:
        return "partially-blocked-model-contract"
    if any("surrogate" in fidelity for fidelity in component_fidelities):
        return "surrogate-model-contract"
    return "predictive-model-contract"


def _existing_backend_files(repo_root: Path, paths: Sequence[Path]) -> tuple[str, ...]:
    return tuple(_relative_path(repo_root, path) for path in paths if path.is_file())


def _dedupe_blockers(blockers: Sequence[LockedStackBlocker]) -> list[LockedStackBlocker]:
    seen: dict[tuple[str, str], LockedStackBlocker] = {}
    for blocker in blockers:
        seen.setdefault((blocker.stage, blocker.reason), blocker)
    return list(seen.values())


def _relative_path(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


__all__ = [
    "LockedReferenceFeatureResult",
    "LockedReferenceSpecs",
    "LockedReferenceStack",
    "LockedReferenceStackResult",
    "LockedSplitSpec",
    "LockedStackBlocker",
    "LockedStageSpec",
    "LockedStageStatus",
    "build_locked_reference_stack",
    "load_locked_reference_specs",
]
