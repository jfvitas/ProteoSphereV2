from __future__ import annotations

from collections.abc import Collection
from typing import Any

LADDER_ABSENT = "absent"
LADDER_SUPPORT_ONLY = "support-only"
LADDER_CANDIDATE_ONLY = "candidate-only non-governing"
LADDER_GROUNDED_PREVIEW_SAFE = "grounded preview-safe"
LADDER_GROUNDED_GOVERNING = "grounded governing"

LADDER_ORDER = (
    LADDER_ABSENT,
    LADDER_SUPPORT_ONLY,
    LADDER_CANDIDATE_ONLY,
    LADDER_GROUNDED_PREVIEW_SAFE,
    LADDER_GROUNDED_GOVERNING,
)


def _normalize_accessions(values: Collection[str] | None) -> set[str]:
    return {
        str(value).strip()
        for value in (values or ())
        if str(value).strip()
    }


def classify_ligand_readiness(
    accession: str,
    *,
    grounded_accessions: Collection[str] | None = None,
    candidate_only_accessions: Collection[str] | None = None,
    support_accessions: Collection[str] | None = None,
    packet_status: str | None = None,
    packet_missing_modalities: Collection[str] | None = None,
    bundle_ligands_included: bool = False,
) -> str:
    accession = str(accession).strip()
    grounded = _normalize_accessions(grounded_accessions)
    candidate_only = _normalize_accessions(candidate_only_accessions)
    support_only = _normalize_accessions(support_accessions)
    missing_modalities = {
        str(value).strip()
        for value in (packet_missing_modalities or ())
        if str(value).strip()
    }

    if accession in grounded:
        return LADDER_GROUNDED_GOVERNING if bundle_ligands_included else LADDER_GROUNDED_PREVIEW_SAFE
    if accession in candidate_only:
        return LADDER_CANDIDATE_ONLY
    if accession in support_only:
        return LADDER_SUPPORT_ONLY
    if packet_status == "complete" and "ligand" not in missing_modalities:
        return LADDER_SUPPORT_ONLY
    return LADDER_ABSENT


def ladder_counts(values: Collection[str]) -> dict[str, int]:
    counts = {label: 0 for label in LADDER_ORDER}
    for value in values:
        label = str(value).strip()
        if label in counts:
            counts[label] += 1
    return {label: count for label, count in counts.items() if count}


def ladder_accession_buckets(rows: Collection[dict[str, Any]]) -> dict[str, list[str]]:
    buckets = {label: [] for label in LADDER_ORDER}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        label = str(row.get("ligand_readiness_ladder") or "").strip()
        if accession and label in buckets:
            buckets[label].append(accession)
    return {label: sorted(values) for label, values in buckets.items() if values}
