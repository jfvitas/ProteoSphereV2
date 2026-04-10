from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.library.summary_record import (
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
    SummaryReference,
)
from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_cohort_slice import materialize_intact_cohort_slice
from execution.acquire.intact_snapshot import (
    IntActInteractionRecord,
    IntActSnapshotResult,
    acquire_intact_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTACT_RAW_ROOT = ROOT / "data" / "raw" / "intact"
DEFAULT_CANONICAL_SUMMARY_PATH = ROOT / "data" / "canonical" / "LATEST.json"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_accessions(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        accession = _clean_text(value).upper()
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _release_date_from_snapshot_root(snapshot_root: Path) -> str | None:
    match = re.match(r"(?P<date>\d{8})T\d{6}Z$", snapshot_root.name)
    if match is None:
        return None
    stamp = match.group("date")
    return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}"


def _resolve_snapshot_root(raw_root: Path) -> Path:
    if not raw_root.exists():
        raise FileNotFoundError(f"IntAct raw root was not found: {raw_root}")
    if any(raw_root.glob("*/*.psicquic.tab25.txt")):
        return raw_root
    candidates = sorted(
        (path for path in raw_root.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    )
    if not candidates:
        raise FileNotFoundError(
            f"IntAct raw root does not contain snapshot directories: {raw_root}"
        )
    return candidates[-1]


def _canonical_protein_map(canonical_summary_path: Path) -> dict[str, dict[str, Any]]:
    if not canonical_summary_path.exists():
        return {}
    payload = _read_json(canonical_summary_path)
    proteins = ((payload.get("sequence_result") or {}).get("canonical_proteins") or ())
    result: dict[str, dict[str, Any]] = {}
    for protein in proteins:
        if not isinstance(protein, Mapping):
            continue
        accession = _clean_text(protein.get("accession")).upper()
        if accession:
            result[accession] = dict(protein)
    return result


def _snapshot_path(snapshot_root: Path, accession: str) -> Path:
    return snapshot_root / accession / f"{accession}.psicquic.tab25.txt"


def _build_source_manifest(
    snapshot_root: Path,
    accession: str,
    payload_path: Path,
) -> SourceReleaseManifest:
    release_version = snapshot_root.name
    release_date = _release_date_from_snapshot_root(snapshot_root) or "2026-03-23"
    return SourceReleaseManifest(
        source_name="IntAct",
        release_version=release_version,
        release_date=release_date,
        retrieval_mode="download",
        source_locator=str(payload_path),
        local_artifact_refs=(str(payload_path),),
        provenance=(
            "raw_mirror:intact",
            f"snapshot_root:{snapshot_root}",
            f"accession:{accession}",
        ),
    )


def _load_snapshot_result(
    snapshot_root: Path,
    accession: str,
) -> tuple[IntActSnapshotResult | None, str | None]:
    payload_path = _snapshot_path(snapshot_root, accession)
    if not payload_path.exists():
        return None, f"missing IntAct payload: {payload_path}"
    manifest = _build_source_manifest(snapshot_root, accession, payload_path)
    return acquire_intact_snapshot(manifest), None


def _raw_row_stats(snapshot_result: IntActSnapshotResult | None) -> dict[str, Any]:
    if snapshot_result is None or snapshot_result.snapshot is None:
        return {
            "raw_record_count": 0,
            "self_only_rows": 0,
            "binary_pair_rows": 0,
            "lineage_state_counts": {},
        }
    records = snapshot_result.snapshot.records
    lineage = Counter(record.lineage_state for record in records)
    self_only_rows = 0
    binary_pair_rows = 0
    for record in records:
        accession_ids = {
            _clean_text(record.participant_a_primary_id).upper(),
            _clean_text(record.participant_b_primary_id).upper(),
        }
        accession_ids.discard("")
        if len(accession_ids) < 2:
            self_only_rows += 1
        else:
            binary_pair_rows += 1
    return {
        "raw_record_count": len(records),
        "self_only_rows": self_only_rows,
        "binary_pair_rows": binary_pair_rows,
        "lineage_state_counts": dict(lineage),
    }


def _record_pair(record: IntActInteractionRecord) -> tuple[str, str] | None:
    accession_a = _clean_text(record.participant_a_primary_id).upper()
    accession_b = _clean_text(record.participant_b_primary_id).upper()
    if not accession_a or not accession_b or accession_a == accession_b:
        return None
    return tuple(sorted((accession_a, accession_b)))


def _pair_key(accession_pair: tuple[str, str]) -> str:
    accession_a, accession_b = accession_pair
    return f"pair:protein_protein:protein:{accession_a}|protein:{accession_b}"


def _parse_confidence(values: Sequence[str]) -> float | None:
    parsed: list[float] = []
    for value in values:
        match = re.search(r"intact-miscore:(\d+(?:\.\d+)?)", value, flags=re.IGNORECASE)
        if match is None:
            continue
        parsed.append(float(match.group(1)))
    return max(parsed) if parsed else None


def _physical_interaction(interaction_types: Sequence[str]) -> bool | None:
    if not interaction_types:
        return None
    normalized = " ".join(interaction_types).casefold()
    if "direct interaction" in normalized or "physical association" in normalized:
        return True
    if "association" in normalized:
        return True
    return None


def _pair_join_status(records: Sequence[IntActInteractionRecord]) -> tuple[str, str]:
    blockers = {
        blocker
        for record in records
        for blocker in record.lineage_blockers
    }
    if not blockers:
        return "joined", ""
    return "partial", "mixed_intact_lineage"


def _pair_cross_references(
    records: Sequence[IntActInteractionRecord],
) -> tuple[SummaryReference, ...]:
    references: list[SummaryReference] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if record.interaction_ac:
            key = ("IntAct", record.interaction_ac)
            if key not in seen:
                seen.add(key)
                references.append(
                    SummaryReference(
                        reference_kind="cross_reference",
                        namespace="IntAct",
                        identifier=record.interaction_ac,
                        label=record.interaction_type,
                        join_status="joined" if record.interaction_ac else "partial",
                        source_name="IntAct",
                        source_record_id=record.interaction_ac,
                        evidence_refs=tuple(
                            dict.fromkeys(
                                (
                                    *record.publication_ids,
                                    *record.interaction_ids,
                                    *record.confidence_values,
                                )
                            )
                        ),
                        notes=(
                            f"lineage_state:{record.lineage_state}",
                            f"representation:{record.interaction_representation}",
                        ),
                    )
                )
        if record.imex_id:
            key = ("IMEx", record.imex_id)
            if key not in seen:
                seen.add(key)
                references.append(
                    SummaryReference(
                        reference_kind="cross_reference",
                        namespace="IMEx",
                        identifier=record.imex_id,
                        label=record.interaction_type,
                        join_status="joined",
                        source_name="IntAct",
                        source_record_id=record.interaction_ac or record.imex_id,
                        evidence_refs=record.publication_ids,
                        notes=(f"interaction_ac:{record.interaction_ac}",),
                    )
                )
    return tuple(references)


def _release_pointer(
    *,
    provenance_id: str,
    source_record_id: str | None,
    source_manifest: SourceReleaseManifest,
    join_status: str,
    notes: Sequence[str] = (),
) -> SummaryProvenancePointer:
    return SummaryProvenancePointer(
        provenance_id=provenance_id,
        source_name="IntAct",
        source_record_id=source_record_id,
        release_version=source_manifest.release_version,
        release_date=source_manifest.release_date,
        join_status=join_status,
        notes=tuple(note for note in notes if note),
    )


@dataclass(frozen=True, slots=True)
class IntActLocalAccessionProbe:
    accession: str
    snapshot_result: IntActSnapshotResult | None
    missing_reason: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)


def _protein_record(
    *,
    probe: IntActLocalAccessionProbe,
    source_manifest: SourceReleaseManifest,
    canonical: Mapping[str, Any] | None,
    pair_count: int,
) -> ProteinSummaryRecord:
    accession = probe.accession
    snapshot_result = probe.snapshot_result
    stats = probe.stats
    snapshot_state = "unavailable"
    probe_reason = probe.missing_reason or ""
    if snapshot_result is not None:
        slice_result = materialize_intact_cohort_slice(
            accession,
            snapshot_result=snapshot_result,
            selection=None,
        )
        snapshot_state = slice_result.state
        probe_reason = slice_result.probe_reason or probe_reason
    join_status = "joined" if pair_count > 0 else "partial"
    if pair_count > 0:
        join_reason = ""
    elif stats.get("self_only_rows", 0) > 0 and stats.get("binary_pair_rows", 0) == 0:
        join_reason = "intact_self_only_probe"
    elif snapshot_state == "unavailable":
        join_reason = "intact_unavailable"
    else:
        join_reason = "intact_reachable_empty"
    lineage_counts = stats.get("lineage_state_counts") or {}
    lineage_note = "|".join(
        f"{state}:{count}"
        for state, count in sorted(lineage_counts.items(), key=lambda item: item[0])
    )
    notes = tuple(
        note
        for note in (
            f"probe_state:{snapshot_state}",
            f"probe_reason:{probe_reason}" if probe_reason else "",
            f"raw_rows={stats.get('raw_record_count', 0)}",
            f"self_only_rows={stats.get('self_only_rows', 0)}",
            f"binary_pair_rows={stats.get('binary_pair_rows', 0)}",
            f"lineage_states:{lineage_note}" if lineage_note else "",
            join_reason,
        )
        if note
    )
    protein_name = _clean_text(
        (canonical or {}).get("name") or (canonical or {}).get("description")
    )
    organism_name = _clean_text((canonical or {}).get("organism"))
    taxon_id = (canonical or {}).get("taxon_id")
    sequence_length = (canonical or {}).get("sequence_length")
    gene_names = tuple(str(item) for item in (canonical or {}).get("gene_names") or ())
    aliases = tuple(
        dict.fromkeys(
            [
                accession,
                *[str(item) for item in (canonical or {}).get("aliases") or ()],
            ]
        )
    )
    pointer_notes = (
        f"snapshot_state={snapshot_state}",
        f"raw_rows={stats.get('raw_record_count', 0)}",
        f"binary_pair_rows={pair_count}",
    )
    return ProteinSummaryRecord(
        summary_id=f"protein:{accession}",
        protein_ref=f"protein:{accession}",
        protein_name=protein_name,
        organism_name=organism_name,
        taxon_id=taxon_id,
        sequence_length=sequence_length,
        gene_names=gene_names,
        aliases=aliases or (accession,),
        join_status=join_status,
        join_reason=join_reason,
        context=SummaryRecordContext(
            provenance_pointers=(
                _release_pointer(
                    provenance_id=f"intact:{accession}:{source_manifest.manifest_id}",
                    source_record_id=accession,
                    source_manifest=source_manifest,
                    join_status=join_status,
                    notes=pointer_notes,
                ),
            ),
            storage_notes=(
                "local IntAct probe summary derived from raw mirrored MITAB snapshots",
            ),
        ),
        notes=notes,
    )


def _pair_record(
    *,
    accession_pair: tuple[str, str],
    records: Sequence[IntActInteractionRecord],
    source_manifest: SourceReleaseManifest,
    canonical_by_accession: Mapping[str, Mapping[str, Any]],
) -> ProteinProteinSummaryRecord:
    join_status, join_reason = _pair_join_status(records)
    interaction_refs = tuple(
        dict.fromkeys(
            reference
            for record in records
            for reference in (
                record.interaction_ac,
                record.imex_id,
                *record.interaction_ids,
            )
            if reference
        )
    )
    evidence_refs = tuple(
        dict.fromkeys(
            reference
            for record in records
            for reference in (
                *record.publication_ids,
                *record.confidence_values,
                *record.interaction_ids,
            )
            if reference
        )
    )
    interaction_types = tuple(
        dict.fromkeys(
            _clean_text(record.interaction_type)
            for record in records
            if record.interaction_type
        )
    )
    tax_ids = {
        record.participant_a_tax_id
        for record in records
        if record.participant_a_tax_id is not None
    } | {
        record.participant_b_tax_id
        for record in records
        if record.participant_b_tax_id is not None
    }
    accession_a, accession_b = accession_pair
    organism_name = ""
    canonical_a = canonical_by_accession.get(accession_a, {})
    canonical_b = canonical_by_accession.get(accession_b, {})
    if (
        _clean_text(canonical_a.get("organism"))
        and canonical_a.get("organism") == canonical_b.get("organism")
    ):
        organism_name = _clean_text(canonical_a.get("organism"))
    lineage_states = "|".join(
        sorted(dict.fromkeys(record.lineage_state for record in records))
    )
    notes = tuple(
        note
        for note in (
            f"interaction_records={len(records)}",
            f"lineage_states:{lineage_states}",
            "aggregated_from_local_intact_snapshot",
        )
        if note
    )
    return ProteinProteinSummaryRecord(
        summary_id=_pair_key(accession_pair),
        protein_a_ref=f"protein:{accession_a}",
        protein_b_ref=f"protein:{accession_b}",
        interaction_type=interaction_types[0] if interaction_types else "curated interaction",
        interaction_id=None,
        interaction_refs=interaction_refs,
        evidence_refs=evidence_refs,
        organism_name=organism_name,
        taxon_id=next(iter(tax_ids)) if len(tax_ids) == 1 else None,
        physical_interaction=_physical_interaction(interaction_types),
        evidence_count=len(records),
        confidence=_parse_confidence(evidence_refs),
        join_status=join_status,
        join_reason=join_reason,
        context=SummaryRecordContext(
            provenance_pointers=(
                _release_pointer(
                    provenance_id=f"intact:{_pair_key(accession_pair)}",
                    source_record_id=records[0].interaction_ac or records[0].imex_id,
                    source_manifest=source_manifest,
                    join_status=join_status,
                    notes=(f"interaction_records={len(records)}",),
                ),
            ),
            cross_references=_pair_cross_references(records),
            storage_notes=(
                "aggregated from local IntAct MITAB probe rows with lineage preserved",
            ),
        ),
        notes=notes,
    )


def materialize_intact_local_summary_library(
    *,
    accessions: Sequence[str],
    raw_root: Path = DEFAULT_INTACT_RAW_ROOT,
    canonical_summary_path: Path = DEFAULT_CANONICAL_SUMMARY_PATH,
    library_id: str | None = None,
) -> SummaryLibrarySchema:
    selected = _normalize_accessions(accessions)
    snapshot_root = _resolve_snapshot_root(raw_root)
    source_manifest = SourceReleaseManifest(
        source_name="IntAct",
        release_version=snapshot_root.name,
        release_date=_release_date_from_snapshot_root(snapshot_root) or "2026-03-23",
        retrieval_mode="download",
        source_locator=str(snapshot_root),
        local_artifact_refs=(str(snapshot_root),),
        provenance=("raw_mirror:intact", f"snapshot_root:{snapshot_root}"),
    )
    canonical_by_accession = _canonical_protein_map(canonical_summary_path)

    probes: list[IntActLocalAccessionProbe] = []
    pair_records_by_key: dict[tuple[str, str], list[IntActInteractionRecord]] = defaultdict(list)
    pair_accessions: set[str] = set()
    for accession in selected:
        snapshot_result, missing_reason = _load_snapshot_result(snapshot_root, accession)
        stats = _raw_row_stats(snapshot_result)
        probes.append(
            IntActLocalAccessionProbe(
                accession=accession,
                snapshot_result=snapshot_result,
                missing_reason=missing_reason,
                stats=stats,
            )
        )
        if snapshot_result is None or snapshot_result.snapshot is None:
            continue
        for record in snapshot_result.snapshot.records:
            accession_pair = _record_pair(record)
            if accession_pair is None:
                continue
            pair_records_by_key[accession_pair].append(record)
            pair_accessions.update(accession_pair)

    records = []
    for probe in probes:
        pair_count = sum(1 for pair in pair_records_by_key if probe.accession in pair)
        records.append(
            _protein_record(
                probe=probe,
                source_manifest=source_manifest,
                canonical=canonical_by_accession.get(probe.accession),
                pair_count=pair_count,
            )
        )

    for accession_pair in sorted(pair_records_by_key, key=lambda item: (item[0], item[1])):
        records.append(
            _pair_record(
                accession_pair=accession_pair,
                records=pair_records_by_key[accession_pair],
                source_manifest=source_manifest,
                canonical_by_accession=canonical_by_accession,
            )
        )

    return SummaryLibrarySchema(
        library_id=library_id or f"summary-library:intact-local:{_timestamp_slug()}",
        source_manifest_id=source_manifest.manifest_id,
        records=tuple(records),
        index_guidance=(
            "index accession-level IntAct probe summaries alongside pair-level interaction records",
            "preserve IMEx and IntAct identifiers as cross references on pair records",
        ),
        storage_guidance=(
            "store accession probe outcomes even when no binary pair survives filtering",
            "materialize pair summaries only from non-self binary rows with traceable lineage",
        ),
        lazy_loading_guidance=(
            "hydrate full raw MITAB rows only after selecting a candidate interaction pair",
            "treat self-only accession probes as reachable_empty rather than joined pair evidence",
        ),
    )


__all__ = [
    "DEFAULT_CANONICAL_SUMMARY_PATH",
    "DEFAULT_INTACT_RAW_ROOT",
    "materialize_intact_local_summary_library",
]
