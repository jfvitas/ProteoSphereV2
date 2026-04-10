from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from connectors.uniprot.client import UniProtClient

try:
    from scripts.affinity_interaction_preview_support import iter_pdbbind_rows
except ModuleNotFoundError:  # pragma: no cover
    from affinity_interaction_preview_support import iter_pdbbind_rows  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDBBIND_INDEX_DIR = REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind" / "index"
DEFAULT_SIFTS_CHAIN_UNIPROT = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "sifts" / "pdb_chain_uniprot.tsv.gz"
)
DEFAULT_PDBBIND_ROOT = REPO_ROOT / "data" / "raw" / "local_copies" / "pdbbind"
DEFAULT_UNIPROT_IDMAPPING_SELECTED = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "uniprot" / "idmapping_selected.tab.gz"
)
DEFAULT_EXPANSION_STAGING_ROOT = (
    REPO_ROOT / "data" / "reports" / "expansion_staging" / "v2_post_procurement_expanded"
)
DEFAULT_SEQUENCE_CACHE_ROOT = (
    REPO_ROOT / "data" / "raw" / "uniprot" / "accession_scoped_fasta_cache"
)

PDBBIND_CLASS_SHORT = {
    "protein_ligand": "PL",
    "protein_protein": "PP",
    "protein_nucleic_acid": "PN",
    "nucleic_acid_ligand": "NL",
}

PDBBIND_CLASS_DIR = {
    "protein_ligand": "P-L",
    "protein_protein": "P-P",
    "protein_nucleic_acid": "P-NA",
    "nucleic_acid_ligand": "NA-L",
}


def _accession_root(accession: str) -> str:
    return accession.split("-", 1)[0].strip()


def load_sifts_chain_uniprot(
    path: Path = DEFAULT_SIFTS_CHAIN_UNIPROT,
) -> dict[str, list[dict[str, str]]]:
    by_pdb: dict[str, list[dict[str, str]]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            header = line.rstrip("\n").split("\t")
            if header[:3] == ["PDB", "CHAIN", "SP_PRIMARY"]:
                break
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            pdb_id, chain_id, accession = parts[:3]
            if not pdb_id or not chain_id or not accession or accession == "None":
                continue
            row = {
                "pdb_id": pdb_id.upper(),
                "chain_id": chain_id.strip(),
                "accession": accession.strip(),
                "accession_root": _accession_root(accession.strip()),
            }
            by_pdb[row["pdb_id"]].append(row)
    return dict(by_pdb)


def load_uniref_cluster_map(
    target_accessions: set[str],
    path: Path = DEFAULT_UNIPROT_IDMAPPING_SELECTED,
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    if not target_accessions:
        return mapping
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 10:
                continue
            accession = parts[0].strip()
            if accession not in target_accessions:
                continue
            mapping[accession] = {
                "uniref100": parts[7].strip(),
                "uniref90": parts[8].strip(),
                "uniref50": parts[9].strip(),
            }
            if len(mapping) == len(target_accessions):
                break
    return mapping


def _fasta_sequence_from_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    if lines[0].startswith(">"):
        lines = lines[1:]
    return "".join(lines).upper()


def _sequence_kmers(sequence: str, k: int = 5) -> set[str]:
    if len(sequence) < k:
        return {sequence} if sequence else set()
    return {sequence[index : index + k] for index in range(len(sequence) - k + 1)}


def _sequence_similarity_metrics(left: str, right: str) -> dict[str, Any]:
    if not left or not right:
        return {
            "length_delta": None,
            "length_ratio": None,
            "shared_kmer_jaccard": None,
            "exact_sequence_match": False,
        }
    left_len = len(left)
    right_len = len(right)
    left_kmers = _sequence_kmers(left)
    right_kmers = _sequence_kmers(right)
    union = left_kmers | right_kmers
    intersection = left_kmers & right_kmers
    return {
        "length_delta": abs(left_len - right_len),
        "length_ratio": round(min(left_len, right_len) / max(left_len, right_len), 6),
        "shared_kmer_jaccard": round(len(intersection) / len(union), 6) if union else 1.0,
        "exact_sequence_match": left == right,
    }


def _bounded_levenshtein_distance(left: str, right: str, *, max_distance: int) -> int | None:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > max_distance:
        return None
    if len(left) > len(right):
        left, right = right, left

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        row_min = current_row[0]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current_row[right_index - 1] + 1
            delete_cost = previous_row[right_index] + 1
            replace_cost = previous_row[right_index - 1] + (left_char != right_char)
            cost = min(insert_cost, delete_cost, replace_cost)
            current_row.append(cost)
            row_min = min(row_min, cost)
        if row_min > max_distance:
            return None
        previous_row = current_row

    distance = previous_row[-1]
    return distance if distance <= max_distance else None


def ensure_uniprot_sequence_cache(
    accessions: set[str],
    *,
    cache_root: Path = DEFAULT_SEQUENCE_CACHE_ROOT,
) -> dict[str, dict[str, Any]]:
    client = UniProtClient()
    cached: dict[str, dict[str, Any]] = {}
    cache_root.mkdir(parents=True, exist_ok=True)

    for accession in sorted(accessions):
        cache_path = cache_root / f"{accession}.json"
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                cached[accession] = payload
                continue
        sequence = ""
        sequence_source = "unavailable"
        fetch_error = None
        try:
            fasta_text = client.get_fasta(accession)
            sequence = _fasta_sequence_from_text(fasta_text)
            sequence_source = "uniprot_rest_fasta"
        except Exception as exc:  # pragma: no cover - network-dependent fallback
            fetch_error = str(exc)
        payload = {
            "accession": accession,
            "sequence_present": bool(sequence),
            "sequence_source": sequence_source,
            "sequence_length": len(sequence) if sequence else None,
            "sequence_sha256": hashlib.sha256(sequence.encode("utf-8")).hexdigest()
            if sequence
            else None,
            "fasta_sequence": sequence if sequence else None,
            "fetch_error": fetch_error,
            "cached_at": datetime.now(UTC).isoformat(),
        }
        cache_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        cached[accession] = payload

    return cached


def _protein_payload_by_accession(corpus_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    protein_payloads: dict[str, dict[str, Any]] = {}
    for row in corpus_payload.get("rows") or []:
        if not isinstance(row, dict) or row.get("row_family") != "protein":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        accession = str(payload.get("accession") or "").strip()
        if accession:
            protein_payloads[accession] = payload
    return protein_payloads


def _interaction_partner_index(corpus_payload: dict[str, Any]) -> dict[str, set[str]]:
    partner_index: dict[str, set[str]] = defaultdict(set)
    for row in corpus_payload.get("rows") or []:
        if not isinstance(row, dict) or row.get("row_family") != "interaction":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        left = str(payload.get("left_accession") or "").strip()
        right = str(payload.get("right_accession") or "").strip()
        if not left or not right:
            continue
        partner_index[left].add(right)
        partner_index[right].add(left)
    return dict(partner_index)


def _group_members_from_payloads(
    protein_payloads: dict[str, dict[str, Any]],
    key_name: str,
) -> dict[str, list[str]]:
    members: dict[str, list[str]] = defaultdict(list)
    for accession, payload in protein_payloads.items():
        key = str(payload.get(key_name) or "").strip()
        if key:
            members[key].append(accession)
    return {
        key: sorted(values)
        for key, values in members.items()
        if len(values) > 1
    }


def build_pdbbind_expanded_structured_corpus(
    *,
    pdbbind_index_dir: Path = DEFAULT_PDBBIND_INDEX_DIR,
    sifts_chain_uniprot_path: Path = DEFAULT_SIFTS_CHAIN_UNIPROT,
    uniprot_idmapping_selected_path: Path = DEFAULT_UNIPROT_IDMAPPING_SELECTED,
) -> dict[str, Any]:
    pdbbind_rows = iter_pdbbind_rows(pdbbind_index_dir)
    chain_map_by_pdb = load_sifts_chain_uniprot(sifts_chain_uniprot_path)

    structure_rows: list[dict[str, Any]] = []
    measurement_rows: list[dict[str, Any]] = []
    interaction_rows: list[dict[str, Any]] = []

    protein_rollup: dict[str, dict[str, Any]] = {}
    structure_file_coverage_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    structures_with_protein_mappings = 0
    protein_protein_structures_with_pairings = 0

    for row in pdbbind_rows:
        pdb_id = str(row.get("pdb_id") or "").upper()
        complex_type = str(row.get("complex_type") or "unknown")
        class_short = PDBBIND_CLASS_SHORT.get(complex_type, "UNK")
        class_dir = PDBBIND_CLASS_DIR.get(complex_type)
        class_counts[complex_type] += 1

        chain_refs = list(chain_map_by_pdb.get(pdb_id, []))
        chain_ids = sorted({entry["chain_id"] for entry in chain_refs})
        protein_accessions = sorted({entry["accession"] for entry in chain_refs})
        accession_roots = sorted({_accession_root(entry["accession"]) for entry in chain_refs})
        structure_path = None
        if class_dir:
            suffix = "complex.pdb"
            if complex_type == "protein_ligand":
                suffix = "protein.pdb"
            elif complex_type == "protein_nucleic_acid":
                suffix = "protein.pdb"
            elif complex_type == "nucleic_acid_ligand":
                suffix = "nucleic_acid.pdb"
            candidate = DEFAULT_PDBBIND_ROOT / class_dir / class_dir / f"{pdb_id.lower()}_{suffix}"
            if candidate.exists():
                structure_path = candidate
                structure_file_coverage_counts["present"] += 1
            else:
                structure_file_coverage_counts["missing"] += 1

        if protein_accessions:
            structures_with_protein_mappings += 1

        structure_rows.append(
            {
                "row_id": f"pdbbind_structure:{pdb_id}",
                "seed_accession": None,
                "canonical_ids": [f"structure:{pdb_id}"]
                + [f"protein:{acc}" for acc in protein_accessions],
                "row_family": "structure",
                "governing_status": "candidate_only_non_governing",
                "training_admissibility": "candidate_only_non_governing",
                "join_status": "joined" if protein_accessions else "candidate",
                "relationship_context": "direct_structure",
                "source_provenance_refs": [f"PDBbind:{class_short}", f"PDB:{pdb_id}"],
                "modality_payload_refs": (
                    [str(structure_path).replace("\\", "/")] if structure_path else []
                ),
                "inclusion_rationale": "structure discovered in the local PDBbind expansion corpus",
                "exclusion_or_hold_reasons": [],
                "payload": {
                    "pdb_id": pdb_id,
                    "complex_type": complex_type,
                    "structure_file_path": str(structure_path).replace("\\", "/")
                    if structure_path
                    else None,
                    "mapped_chain_ids": chain_ids,
                    "mapped_protein_accessions": protein_accessions,
                    "mapped_protein_accession_roots": accession_roots,
                    "resolution_angstrom": row.get("resolution_angstrom"),
                    "release_year": row.get("release_year"),
                },
            }
        )

        measurement_rows.append(
            {
                "row_id": str(
                    row.get("measurement_id")
                    or f"binding_measurement:pdbbind:{class_short}:{pdb_id}"
                ),
                "seed_accession": protein_accessions[0] if protein_accessions else None,
                "canonical_ids": [f"structure:{pdb_id}"]
                + [f"protein:{acc}" for acc in protein_accessions],
                "row_family": "measurement",
                "governing_status": "candidate_only_non_governing",
                "training_admissibility": "candidate_only_non_governing",
                "join_status": "joined" if protein_accessions else "candidate",
                "relationship_context": (
                    "direct_partner"
                    if complex_type == "protein_protein"
                    else "direct_ligand"
                ),
                "source_provenance_refs": [
                    f"PDBbind:{class_short}",
                    str(row.get("source_record_id") or ""),
                ],
                "modality_payload_refs": (
                    [str(structure_path).replace("\\", "/")] if structure_path else []
                ),
                "inclusion_rationale": (
                    "binding/affinity measurement parsed from the local "
                    "PDBbind index"
                ),
                "exclusion_or_hold_reasons": [],
                "payload": {
                    "pdb_id": pdb_id,
                    "complex_type": complex_type,
                    "measurement_type": row.get("measurement_type"),
                    "relation": row.get("relation"),
                    "raw_binding_string": row.get("raw_binding_string"),
                    "value_molar_normalized": row.get("value_molar_normalized"),
                    "p_affinity": row.get("p_affinity"),
                    "source_comment": row.get("source_comment"),
                    "mapped_chain_ids": chain_ids,
                    "mapped_protein_accessions": protein_accessions,
                },
            }
        )

        for accession in protein_accessions:
            protein_entry = protein_rollup.setdefault(
                accession,
                {
                    "accession": accession,
                    "accession_root": _accession_root(accession),
                    "structure_ids": set(),
                    "complex_types": Counter(),
                    "chain_refs": set(),
                    "measurement_count": 0,
                },
            )
            protein_entry["structure_ids"].add(pdb_id)
            protein_entry["complex_types"][complex_type] += 1
            protein_entry["measurement_count"] += 1
            for chain_ref in chain_refs:
                if chain_ref["accession"] == accession:
                    protein_entry["chain_refs"].add(f"{pdb_id}:{chain_ref['chain_id']}")

        if complex_type == "protein_protein" and len(protein_accessions) >= 2:
            protein_protein_structures_with_pairings += 1
            for left, right in combinations(protein_accessions, 2):
                interaction_rows.append(
                    {
                        "row_id": f"pdbbind_interaction:{pdb_id}:{left}:{right}",
                        "seed_accession": left,
                        "canonical_ids": [
                            f"structure:{pdb_id}",
                            f"protein:{left}",
                            f"protein:{right}",
                        ],
                        "row_family": "interaction",
                        "governing_status": "candidate_only_non_governing",
                        "training_admissibility": "candidate_only_non_governing",
                        "join_status": "joined",
                        "relationship_context": "direct_partner",
                        "source_provenance_refs": [f"PDBbind:{class_short}", f"PDB:{pdb_id}"],
                        "modality_payload_refs": (
                            [str(structure_path).replace("\\", "/")]
                            if structure_path
                            else []
                        ),
                        "inclusion_rationale": (
                            "protein-protein interaction inferred from a "
                            "PDBbind P-P complex"
                        ),
                        "exclusion_or_hold_reasons": [],
                        "payload": {
                            "pdb_id": pdb_id,
                            "left_accession": left,
                            "right_accession": right,
                            "mapped_chain_ids": chain_ids,
                        },
                    }
                )

    uniref_map = load_uniref_cluster_map(
        set(protein_rollup),
        path=uniprot_idmapping_selected_path,
    )
    protein_rows = []
    accession_root_counts = Counter(entry["accession_root"] for entry in protein_rollup.values())
    uniref100_counts = Counter(
        data["uniref100"] for data in uniref_map.values() if data.get("uniref100")
    )
    cohort_rows: list[dict[str, Any]] = []
    for accession, entry in sorted(protein_rollup.items()):
        clusters = uniref_map.get(accession, {})
        protein_rows.append(
            {
                "row_id": f"protein:{accession}:pdbbind_expansion",
                "seed_accession": accession,
                "canonical_ids": [f"protein:{accession}"],
                "row_family": "protein",
                "governing_status": "candidate_only_non_governing",
                "training_admissibility": "candidate_only_non_governing",
                "join_status": "joined",
                "relationship_context": "direct_structure",
                "source_provenance_refs": ["PDBbind", "SIFTS:pdb_chain_uniprot"],
                "modality_payload_refs": [],
                "inclusion_rationale": (
                    "protein accession discovered through PDBbind "
                    "structure-chain mapping"
                ),
                "exclusion_or_hold_reasons": [],
                "payload": {
                    "accession": accession,
                    "accession_root": entry["accession_root"],
                    "uniref100_cluster": clusters.get("uniref100"),
                    "uniref90_cluster": clusters.get("uniref90"),
                    "uniref50_cluster": clusters.get("uniref50"),
                    "associated_structure_count": len(entry["structure_ids"]),
                    "associated_structure_ids_sample": sorted(entry["structure_ids"])[:25],
                    "complex_type_counts": dict(sorted(entry["complex_types"].items())),
                    "mapped_chain_refs_sample": sorted(entry["chain_refs"])[:25],
                    "measurement_count": entry["measurement_count"],
                    "accession_root_group_size": accession_root_counts[entry["accession_root"]],
                },
            }
        )
        if clusters.get("uniref100") and uniref100_counts[clusters["uniref100"]] > 1:
            cohort_rows.append(
                {
                    "row_id": f"protein_cohort:{accession}:{clusters['uniref100']}",
                    "seed_accession": accession,
                    "canonical_ids": [f"protein:{accession}"],
                    "row_family": "protein_cohort",
                    "governing_status": "candidate_only_non_governing",
                    "training_admissibility": "candidate_only_non_governing",
                    "join_status": "joined",
                    "relationship_context": "direct_seed",
                    "source_provenance_refs": [
                        "UniProt:idmapping_selected",
                        clusters["uniref100"],
                    ],
                    "modality_payload_refs": [],
                    "inclusion_rationale": (
                        "protein accession linked to a close matching cohort "
                        "through UniRef cluster membership"
                    ),
                    "exclusion_or_hold_reasons": [],
                    "payload": {
                        "accession": accession,
                        "accession_root": entry["accession_root"],
                        "uniref100_cluster": clusters.get("uniref100"),
                        "uniref90_cluster": clusters.get("uniref90"),
                        "uniref50_cluster": clusters.get("uniref50"),
                        "uniref100_group_size": uniref100_counts[clusters["uniref100"]],
                    },
                }
            )

    rows = protein_rows + cohort_rows + structure_rows + interaction_rows + measurement_rows
    row_family_counts = Counter(str(row["row_family"]) for row in rows)
    proteins_with_multiple_structures = sum(
        1 for entry in protein_rollup.values() if len(entry["structure_ids"]) > 1
    )
    return {
        "artifact_id": "pdbbind_expanded_structured_corpus",
        "schema_id": "proteosphere-pdbbind-expanded-structured-corpus-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "dataset_generation_mode": "v2_post_procurement_expanded_staging",
            "structure_count": len(structure_rows),
            "measurement_count": len(measurement_rows),
            "interaction_count": len(interaction_rows),
            "protein_count": len(protein_rows),
            "protein_cohort_count": len(cohort_rows),
            "row_count": len(rows),
            "row_family_counts": dict(sorted(row_family_counts.items())),
            "complex_type_counts": dict(sorted(class_counts.items())),
            "structure_mapping_coverage_fraction": (
                structures_with_protein_mappings / len(structure_rows) if structure_rows else 0.0
            ),
            "structure_file_coverage_counts": dict(sorted(structure_file_coverage_counts.items())),
            "unique_protein_accession_count": len(protein_rollup),
            "unique_accession_root_count": len(accession_root_counts),
            "mapped_uniref100_cluster_count": len(uniref100_counts),
            "proteins_in_multi_member_uniref100_clusters": sum(
                count for count in uniref100_counts.values() if count > 1
            ),
            "proteins_with_multiple_structures": proteins_with_multiple_structures,
            "protein_protein_structures_with_pairings": protein_protein_structures_with_pairings,
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This staged expansion corpus opens the dataset beyond the "
                "frozen 12-accession cohort using local PDBbind plus SIFTS "
                "chain mapping. It is still candidate-only/non-governing "
                "until broader expansion procurement and release review complete."
            ),
            "report_only": True,
            "non_governing": True,
            "expansion_staging": True,
        },
    }


def build_pdbbind_protein_cohort_graph(
    corpus_payload: dict[str, Any],
) -> dict[str, Any]:
    protein_payloads = _protein_payload_by_accession(corpus_payload)
    partner_index = _interaction_partner_index(corpus_payload)

    root_groups = _group_members_from_payloads(protein_payloads, "accession_root")
    uniref100_groups = _group_members_from_payloads(protein_payloads, "uniref100_cluster")
    uniref90_groups = _group_members_from_payloads(protein_payloads, "uniref90_cluster")
    uniref50_groups = _group_members_from_payloads(protein_payloads, "uniref50_cluster")

    cohort_groups = {
        "accession_root": root_groups,
        "uniref100": uniref100_groups,
        "uniref90": uniref90_groups,
        "uniref50": uniref50_groups,
    }

    accession_rows: list[dict[str, Any]] = []
    proteins_with_cohort_neighbors = 0
    proteins_with_ppi_neighbors = 0
    max_total_neighbor_count = 0
    direct_ppi_edge_count = sum(len(neighbors) for neighbors in partner_index.values()) // 2

    for accession, payload in sorted(protein_payloads.items()):
        cohort_neighbors: set[str] = set()
        group_refs: list[dict[str, Any]] = []
        for group_type, groups in cohort_groups.items():
            key_name = (
                "accession_root"
                if group_type == "accession_root"
                else f"{group_type}_cluster"
            )
            if group_type == "uniref100":
                key_name = "uniref100_cluster"
            elif group_type == "uniref90":
                key_name = "uniref90_cluster"
            elif group_type == "uniref50":
                key_name = "uniref50_cluster"
            group_id = str(payload.get(key_name) or "").strip()
            if not group_id or group_id not in groups:
                continue
            members = [member for member in groups[group_id] if member != accession]
            if not members:
                continue
            cohort_neighbors.update(members)
            group_refs.append(
                {
                    "group_type": group_type,
                    "group_id": group_id,
                    "group_size": len(groups[group_id]),
                    "neighbor_sample": members[:12],
                }
            )

        direct_partners = sorted(partner_index.get(accession, set()))
        if cohort_neighbors:
            proteins_with_cohort_neighbors += 1
        if direct_partners:
            proteins_with_ppi_neighbors += 1
        total_neighbors = len(set(direct_partners) | cohort_neighbors)
        max_total_neighbor_count = max(max_total_neighbor_count, total_neighbors)

        accession_rows.append(
            {
                "accession": accession,
                "accession_root": payload.get("accession_root"),
                "uniref100_cluster": payload.get("uniref100_cluster"),
                "uniref90_cluster": payload.get("uniref90_cluster"),
                "uniref50_cluster": payload.get("uniref50_cluster"),
                "associated_structure_count": int(payload.get("associated_structure_count") or 0),
                "measurement_count": int(payload.get("measurement_count") or 0),
                "direct_ppi_partner_count": len(direct_partners),
                "direct_ppi_partner_sample": direct_partners[:12],
                "cohort_neighbor_count": len(cohort_neighbors),
                "cohort_neighbor_sample": sorted(cohort_neighbors)[:12],
                "total_neighbor_count": total_neighbors,
                "group_refs": group_refs,
            }
        )

    accession_rows.sort(
        key=lambda row: (
            -int(row["total_neighbor_count"]),
            -int(row["associated_structure_count"]),
            str(row["accession"]),
        )
    )

    cohort_group_samples: list[dict[str, Any]] = []
    for group_type, groups in cohort_groups.items():
        ranked = sorted(
            groups.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        for group_id, members in ranked[:25]:
            cohort_group_samples.append(
                {
                    "group_type": group_type,
                    "group_id": group_id,
                    "group_size": len(members),
                    "member_sample": members[:15],
                }
            )

    return {
        "artifact_id": "pdbbind_protein_cohort_graph_preview",
        "schema_id": "proteosphere-pdbbind-protein-cohort-graph-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "protein_count": len(protein_payloads),
            "direct_ppi_edge_count": direct_ppi_edge_count,
            "proteins_with_direct_ppi_partners": proteins_with_ppi_neighbors,
            "proteins_with_cohort_neighbors": proteins_with_cohort_neighbors,
            "accession_root_multi_member_group_count": len(root_groups),
            "uniref100_multi_member_group_count": len(uniref100_groups),
            "uniref90_multi_member_group_count": len(uniref90_groups),
            "uniref50_multi_member_group_count": len(uniref50_groups),
            "max_total_neighbor_count": max_total_neighbor_count,
            "accession_focus_count": min(len(accession_rows), 250),
        },
        "accession_focus_rows": accession_rows[:250],
        "cohort_group_samples": cohort_group_samples,
        "truth_boundary": {
            "summary": (
                "This graph preview summarizes protein-level neighborhoods in the staged "
                "PDBbind expansion corpus using direct PPI edges plus accession-root and "
                "UniRef 100/90/50 cohort membership. It is intended for leakage planning "
                "and expansion diagnostics, not governing promotion."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def write_expansion_stage_bundle(
    payload: dict[str, Any],
    *,
    output_root: Path = DEFAULT_EXPANSION_STAGING_ROOT,
    stem: str = "pdbbind-expanded-structured-corpus",
) -> dict[str, Any]:
    run_id = f"{stem}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    bundle_root = output_root / run_id
    bundle_root.mkdir(parents=True, exist_ok=True)
    corpus_path = bundle_root / "pdbbind_expanded_structured_corpus.json"
    corpus_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    latest_path = output_root / "LATEST_PDBBIND_EXPANDED.json"
    latest_payload = {
        "run_id": run_id,
        "bundle_root": str(bundle_root).replace("\\", "/"),
        "corpus_path": str(corpus_path).replace("\\", "/"),
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
    }
    latest_path.write_text(json.dumps(latest_payload, indent=2) + "\n", encoding="utf-8")
    return latest_payload


def build_pdb_paper_split_assessment(
    *,
    train_ids: list[str],
    test_ids: list[str],
    corpus_payload: dict[str, Any],
) -> dict[str, Any]:
    structure_rows = {
        str(row.get("payload", {}).get("pdb_id") or "").upper(): row
        for row in corpus_payload.get("rows") or []
        if isinstance(row, dict) and row.get("row_family") == "structure"
    }
    protein_payloads = _protein_payload_by_accession(corpus_payload)
    partner_index = _interaction_partner_index(corpus_payload)

    def _normalize(ids: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in ids:
            token = item.strip().upper()
            if token and token not in seen:
                seen.add(token)
                ordered.append(token)
        return ordered

    train_ids = _normalize(train_ids)
    test_ids = _normalize(test_ids)

    def _clusters_for_accession_set(accessions: set[str], key_name: str) -> list[str]:
        return sorted(
            {
                str(protein_payloads.get(accession, {}).get(key_name) or "").strip()
                for accession in accessions
                if str(protein_payloads.get(accession, {}).get(key_name) or "").strip()
            }
        )

    def _split_summary(ids: list[str]) -> dict[str, Any]:
        found = [pid for pid in ids if pid in structure_rows]
        missing = [pid for pid in ids if pid not in structure_rows]
        proteins = sorted(
            {
                accession
                for pid in found
                for accession in (
                    structure_rows[pid]
                    .get("payload", {})
                    .get("mapped_protein_accessions")
                    or []
                )
            }
        )
        roots = sorted({_accession_root(accession) for accession in proteins})
        uniref100_clusters = _clusters_for_accession_set(set(proteins), "uniref100_cluster")
        uniref90_clusters = _clusters_for_accession_set(set(proteins), "uniref90_cluster")
        uniref50_clusters = _clusters_for_accession_set(set(proteins), "uniref50_cluster")
        class_counts = Counter(
            str(structure_rows[pid].get("payload", {}).get("complex_type") or "unknown")
            for pid in found
        )
        extracted_file_missing = [
            pid
            for pid in found
            if not structure_rows[pid].get("payload", {}).get("structure_file_path")
        ]
        return {
            "structure_count": len(ids),
            "found_count": len(found),
            "missing_count": len(missing),
            "found_structure_ids": found,
            "missing_structure_ids": missing,
            "complex_type_counts": dict(sorted(class_counts.items())),
            "unique_protein_accession_count": len(proteins),
            "unique_protein_accessions": proteins,
            "unique_accession_root_count": len(roots),
            "unique_accession_roots": roots,
            "uniref100_clusters": uniref100_clusters,
            "uniref90_clusters": uniref90_clusters,
            "uniref50_clusters": uniref50_clusters,
            "direct_partner_accession_count": len(
                {
                    partner
                    for accession in proteins
                    for partner in partner_index.get(accession, set())
                }
            ),
            "direct_partner_accession_sample": sorted(
                {
                    partner
                    for accession in proteins
                    for partner in partner_index.get(accession, set())
                }
            )[:20],
            "missing_local_structure_files": extracted_file_missing,
        }

    train_summary = _split_summary(train_ids)
    test_summary = _split_summary(test_ids)
    train_proteins = set(train_summary["unique_protein_accessions"])
    test_proteins = set(test_summary["unique_protein_accessions"])
    train_roots = set(train_summary["unique_accession_roots"])
    test_roots = set(test_summary["unique_accession_roots"])
    train_clusters = train_summary["uniref100_clusters"]
    test_clusters = test_summary["uniref100_clusters"]
    train_uniref90 = train_summary["uniref90_clusters"]
    test_uniref90 = test_summary["uniref90_clusters"]
    train_uniref50 = train_summary["uniref50_clusters"]
    test_uniref50 = test_summary["uniref50_clusters"]
    direct_overlap = sorted(train_proteins & test_proteins)
    root_overlap = sorted(train_roots & test_roots)
    uniref100_overlap = sorted(set(train_clusters) & set(test_clusters))
    uniref90_overlap = sorted(set(train_uniref90) & set(test_uniref90))
    uniref50_overlap = sorted(set(train_uniref50) & set(test_uniref50))

    def _structures_with_accession(ids: list[str], accession: str) -> list[str]:
        return [
            pid
            for pid in ids
            if accession
            in (
                structure_rows[pid]
                .get("payload", {})
                .get("mapped_protein_accessions")
                or []
            )
        ]

    direct_overlap_rows = []
    for accession in direct_overlap:
        payload = protein_payloads.get(accession, {})
        direct_overlap_rows.append(
            {
                "accession": accession,
                "accession_root": payload.get("accession_root"),
                "uniref100_cluster": payload.get("uniref100_cluster"),
                "uniref90_cluster": payload.get("uniref90_cluster"),
                "uniref50_cluster": payload.get("uniref50_cluster"),
                "train_structure_ids": _structures_with_accession(
                    train_summary["found_structure_ids"],
                    accession,
                ),
                "test_structure_ids": _structures_with_accession(
                    test_summary["found_structure_ids"],
                    accession,
                ),
                "direct_partner_sample": sorted(partner_index.get(accession, set()))[:12],
            }
        )

    root_overlap_rows = []
    for accession_root in root_overlap:
        train_accessions = sorted(
            accession
            for accession in train_proteins
            if _accession_root(accession) == accession_root
        )
        test_accessions = sorted(
            accession for accession in test_proteins if _accession_root(accession) == accession_root
        )
        root_overlap_rows.append(
            {
                "accession_root": accession_root,
                "train_accessions": train_accessions,
                "test_accessions": test_accessions,
            }
        )

    def _cluster_overlap_rows(cluster_ids: list[str], key_name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for cluster_id in cluster_ids:
            train_accessions = sorted(
                accession
                for accession in train_proteins
                if str(
                    protein_payloads.get(accession, {}).get(key_name) or ""
                ).strip()
                == cluster_id
            )
            test_accessions = sorted(
                accession
                for accession in test_proteins
                if str(
                    protein_payloads.get(accession, {}).get(key_name) or ""
                ).strip()
                == cluster_id
            )
            rows.append(
                {
                    "cluster_id": cluster_id,
                    "train_accessions": train_accessions,
                    "test_accessions": test_accessions,
                }
            )
        return rows

    structure_pair_overlap_rows = []
    for train_id in train_summary["found_structure_ids"]:
        train_payload = structure_rows[train_id].get("payload", {})
        train_accessions = set(train_payload.get("mapped_protein_accessions") or [])
        train_roots_local = {_accession_root(accession) for accession in train_accessions}
        train_u100 = _clusters_for_accession_set(train_accessions, "uniref100_cluster")
        train_u90 = _clusters_for_accession_set(train_accessions, "uniref90_cluster")
        train_u50 = _clusters_for_accession_set(train_accessions, "uniref50_cluster")
        for test_id in test_summary["found_structure_ids"]:
            test_payload = structure_rows[test_id].get("payload", {})
            test_accessions = set(test_payload.get("mapped_protein_accessions") or [])
            shared_accessions = sorted(train_accessions & test_accessions)
            test_roots_local = {
                _accession_root(accession)
                for accession in test_accessions
            }
            shared_roots = sorted(train_roots_local & test_roots_local)
            test_u100 = _clusters_for_accession_set(
                test_accessions,
                "uniref100_cluster",
            )
            test_u90 = _clusters_for_accession_set(
                test_accessions,
                "uniref90_cluster",
            )
            test_u50 = _clusters_for_accession_set(
                test_accessions,
                "uniref50_cluster",
            )
            shared_u100 = sorted(set(train_u100) & set(test_u100))
            shared_u90 = sorted(set(train_u90) & set(test_u90))
            shared_u50 = sorted(set(train_u50) & set(test_u50))
            if not (shared_accessions or shared_roots or shared_u100 or shared_u90 or shared_u50):
                continue
            structure_pair_overlap_rows.append(
                {
                    "train_structure_id": train_id,
                    "test_structure_id": test_id,
                    "shared_accessions": shared_accessions,
                    "shared_accession_roots": shared_roots,
                    "shared_uniref100_clusters": shared_u100,
                    "shared_uniref90_clusters": shared_u90,
                    "shared_uniref50_clusters": shared_u50,
                }
            )

    shared_partner_overlap = sorted(
        {
            partner
            for accession in train_proteins
            for partner in partner_index.get(accession, set())
        }
        & {
            partner
            for accession in test_proteins
            for partner in partner_index.get(accession, set())
        }
    )

    if direct_overlap:
        verdict = "high_direct_protein_overlap"
    elif root_overlap:
        verdict = "root_level_overlap_review_needed"
    elif uniref100_overlap or uniref90_overlap:
        verdict = "close_sequence_cluster_overlap_review_needed"
    elif uniref50_overlap:
        verdict = "remote_cluster_overlap_review_needed"
    elif train_summary["missing_count"] or test_summary["missing_count"]:
        verdict = "coverage_gap_review_needed"
    else:
        verdict = "ready_for_deeper_sequence_leakage_assessment"

    return {
        "artifact_id": "pdb_paper_split_assessment",
        "schema_id": "proteosphere-pdb-paper-split-assessment-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "train_structure_count": len(train_ids),
            "test_structure_count": len(test_ids),
            "total_structure_count": len(train_ids) + len(test_ids),
            "covered_structure_count": (
                train_summary["found_count"] + test_summary["found_count"]
            ),
            "missing_structure_count": (
                train_summary["missing_count"] + test_summary["missing_count"]
            ),
            "direct_protein_overlap_count": len(direct_overlap),
            "accession_root_overlap_count": len(root_overlap),
            "uniref100_cluster_overlap_count": len(uniref100_overlap),
            "uniref90_cluster_overlap_count": len(uniref90_overlap),
            "uniref50_cluster_overlap_count": len(uniref50_overlap),
            "shared_partner_overlap_count": len(shared_partner_overlap),
            "flagged_structure_pair_count": len(structure_pair_overlap_rows),
            "verdict": verdict,
        },
        "train_split": train_summary,
        "test_split": test_summary,
        "overlap": {
            "direct_protein_accession_overlap": direct_overlap,
            "accession_root_overlap": root_overlap,
            "uniref100_cluster_overlap": uniref100_overlap,
            "uniref90_cluster_overlap": uniref90_overlap,
            "uniref50_cluster_overlap": uniref50_overlap,
            "shared_partner_overlap": shared_partner_overlap,
        },
        "evidence_rows": {
            "direct_protein_overlap_rows": direct_overlap_rows,
            "accession_root_overlap_rows": root_overlap_rows,
            "uniref100_cluster_overlap_rows": _cluster_overlap_rows(
                uniref100_overlap,
                "uniref100_cluster",
            ),
            "uniref90_cluster_overlap_rows": _cluster_overlap_rows(
                uniref90_overlap,
                "uniref90_cluster",
            ),
            "uniref50_cluster_overlap_rows": _cluster_overlap_rows(
                uniref50_overlap,
                "uniref50_cluster",
            ),
            "structure_pair_overlap_rows": structure_pair_overlap_rows,
        },
        "truth_boundary": {
            "summary": (
                "This is a structure/protein coverage and leakage preflight "
                "over the local PDBbind-backed expansion corpus. It checks "
                "direct protein overlap, accession-root overlap, UniRef 100/90/50 "
                "cluster overlap, and flagged train/test structure-pair reuse patterns, "
                "but it is not yet a full alignment- or mutation-aware leakage audit."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_split_leakage_matrix(
    assessment_payload: dict[str, Any],
) -> dict[str, Any]:
    summary = dict(assessment_payload.get("summary") or {})
    overlap = dict(assessment_payload.get("overlap") or {})
    evidence_rows = dict(assessment_payload.get("evidence_rows") or {})

    category_rows = [
        {
            "category": "direct_protein_overlap",
            "count": int(summary.get("direct_protein_overlap_count") or 0),
            "severity": "critical",
            "blocking": bool(summary.get("direct_protein_overlap_count")),
            "sample": list(overlap.get("direct_protein_accession_overlap") or [])[:12],
            "notes": [
                "Exact protein reuse across train and test is the strongest leakage signal."
            ],
        },
        {
            "category": "accession_root_overlap",
            "count": int(summary.get("accession_root_overlap_count") or 0),
            "severity": (
                "high" if int(summary.get("accession_root_overlap_count") or 0) else "clear"
            ),
            "blocking": False,
            "sample": list(overlap.get("accession_root_overlap") or [])[:12],
            "notes": [
                "Accession-root reuse can indicate isoform/root-level overlap even when exact "
                "accession reuse is absent."
            ],
        },
        {
            "category": "uniref100_cluster_overlap",
            "count": int(summary.get("uniref100_cluster_overlap_count") or 0),
            "severity": (
                "high" if int(summary.get("uniref100_cluster_overlap_count") or 0) else "clear"
            ),
            "blocking": False,
            "sample": list(overlap.get("uniref100_cluster_overlap") or [])[:12],
            "notes": [
                "UniRef100 overlap is a close sequence-family proxy and should trigger review."
            ],
        },
        {
            "category": "uniref90_cluster_overlap",
            "count": int(summary.get("uniref90_cluster_overlap_count") or 0),
            "severity": (
                "medium" if int(summary.get("uniref90_cluster_overlap_count") or 0) else "clear"
            ),
            "blocking": False,
            "sample": list(overlap.get("uniref90_cluster_overlap") or [])[:12],
            "notes": [
                "UniRef90 overlap captures broader close-sequence reuse beyond exact accession "
                "matches."
            ],
        },
        {
            "category": "uniref50_cluster_overlap",
            "count": int(summary.get("uniref50_cluster_overlap_count") or 0),
            "severity": (
                "review" if int(summary.get("uniref50_cluster_overlap_count") or 0) else "clear"
            ),
            "blocking": False,
            "sample": list(overlap.get("uniref50_cluster_overlap") or [])[:12],
            "notes": [
                "UniRef50 overlap is a coarse family-level signal and should be interpreted "
                "alongside exact/90-level overlap."
            ],
        },
        {
            "category": "shared_partner_overlap",
            "count": int(summary.get("shared_partner_overlap_count") or 0),
            "severity": (
                "contextual" if int(summary.get("shared_partner_overlap_count") or 0) else "clear"
            ),
            "blocking": False,
            "sample": list(overlap.get("shared_partner_overlap") or [])[:12],
            "notes": [
                "Shared interaction partners do not automatically block usage, but they reveal "
                "network-context coupling between train and test."
            ],
        },
        {
            "category": "flagged_structure_pair_overlap",
            "count": int(summary.get("flagged_structure_pair_count") or 0),
            "severity": (
                "high" if int(summary.get("flagged_structure_pair_count") or 0) else "clear"
            ),
            "blocking": False,
            "sample": [
                f"{row.get('train_structure_id')}->{row.get('test_structure_id')}"
                for row in list(evidence_rows.get("structure_pair_overlap_rows") or [])[:12]
            ],
            "notes": [
                "Flagged train/test structure pairs summarize concrete reuse patterns at the "
                "complex level."
            ],
        },
    ]

    blocked_categories = [
        row["category"]
        for row in category_rows
        if row["blocking"]
    ]
    review_categories = [
        row["category"]
        for row in category_rows
        if row["count"] and not row["blocking"]
    ]

    return {
        "artifact_id": "pdb_paper_split_leakage_matrix_preview",
        "schema_id": "proteosphere-pdb-paper-split-leakage-matrix-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "verdict": summary.get("verdict"),
            "blocked_category_count": len(blocked_categories),
            "review_category_count": len(review_categories),
            "blocked_categories": blocked_categories,
            "review_categories": review_categories,
            "total_structure_count": int(summary.get("total_structure_count") or 0),
            "flagged_structure_pair_count": int(summary.get("flagged_structure_pair_count") or 0),
        },
        "category_rows": category_rows,
        "truth_boundary": {
            "summary": (
                "This matrix turns the staged PDB paper split assessment into a category-by-"
                "category leakage review. It is a decision-support surface, not a replacement "
                "for sequence alignment or mutation-aware auditing."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_split_acceptance_gate(
    assessment_payload: dict[str, Any],
    leakage_matrix_payload: dict[str, Any],
) -> dict[str, Any]:
    summary = dict(assessment_payload.get("summary") or {})
    train_split = dict(assessment_payload.get("train_split") or {})
    test_split = dict(assessment_payload.get("test_split") or {})
    matrix_summary = dict(leakage_matrix_payload.get("summary") or {})

    missing_structures = int(summary.get("missing_structure_count") or 0)
    missing_local_files = len(train_split.get("missing_local_structure_files") or []) + len(
        test_split.get("missing_local_structure_files") or []
    )
    direct_overlap = int(summary.get("direct_protein_overlap_count") or 0)

    gate_rows = [
        {
            "gate_name": "coverage",
            "status": "attention_needed" if missing_structures else "ok",
            "blocking": False,
            "details": {
                "missing_structure_count": missing_structures,
                "train_missing": list(train_split.get("missing_structure_ids") or []),
                "test_missing": list(test_split.get("missing_structure_ids") or []),
            },
        },
        {
            "gate_name": "local_structure_files",
            "status": "attention_needed" if missing_local_files else "ok",
            "blocking": False,
            "details": {
                "missing_local_structure_file_count": missing_local_files,
                "train_missing_local_files": list(
                    train_split.get("missing_local_structure_files") or []
                ),
                "test_missing_local_files": list(
                    test_split.get("missing_local_structure_files") or []
                ),
            },
        },
        {
            "gate_name": "direct_protein_leakage",
            "status": "blocked" if direct_overlap else "ok",
            "blocking": bool(direct_overlap),
            "details": {
                "direct_protein_overlap_count": direct_overlap,
                "blocked_categories": list(matrix_summary.get("blocked_categories") or []),
            },
        },
        {
            "gate_name": "sequence_family_review",
            "status": (
                "attention_needed"
                if int(summary.get("uniref90_cluster_overlap_count") or 0)
                or int(summary.get("uniref50_cluster_overlap_count") or 0)
                else "ok"
            ),
            "blocking": False,
            "details": {
                "uniref100_cluster_overlap_count": int(
                    summary.get("uniref100_cluster_overlap_count") or 0
                ),
                "uniref90_cluster_overlap_count": int(
                    summary.get("uniref90_cluster_overlap_count") or 0
                ),
                "uniref50_cluster_overlap_count": int(
                    summary.get("uniref50_cluster_overlap_count") or 0
                ),
            },
        },
    ]

    blocked_gate_names = [row["gate_name"] for row in gate_rows if row["blocking"]]
    attention_gate_names = [
        row["gate_name"]
        for row in gate_rows
        if row["status"] == "attention_needed"
    ]

    if blocked_gate_names:
        decision = "blocked"
        recommended_action = (
            "Do not treat this paper split as training-ready. Re-split to remove direct protein "
            "reuse before deeper evaluation."
        )
    elif attention_gate_names:
        decision = "usable_with_caveats"
        recommended_action = (
            "Coverage and family-level overlap need review before this split is trusted as a "
            "clean benchmark."
        )
    else:
        decision = "ready_for_deeper_sequence_review"
        recommended_action = (
            "No blocking leakage signals were found in the current staged audit. Proceed to a "
            "deeper sequence/mutation-aware review."
        )

    return {
        "artifact_id": "pdb_paper_split_acceptance_gate_preview",
        "schema_id": "proteosphere-pdb-paper-split-acceptance-gate-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "decision": decision,
            "verdict": summary.get("verdict"),
            "blocked_gate_count": len(blocked_gate_names),
            "attention_gate_count": len(attention_gate_names),
            "blocked_gates": blocked_gate_names,
            "attention_gates": attention_gate_names,
            "recommended_action": recommended_action,
        },
        "gate_rows": gate_rows,
        "truth_boundary": {
            "summary": (
                "This acceptance gate is a fail-closed decision surface over the staged PDB "
                "paper split assessment. It blocks direct protein reuse and records other "
                "coverage/family-level issues as review-needed."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_split_sequence_signature_audit(
    assessment_payload: dict[str, Any],
    *,
    cache_root: Path = DEFAULT_SEQUENCE_CACHE_ROOT,
) -> dict[str, Any]:
    train_split = dict(assessment_payload.get("train_split") or {})
    test_split = dict(assessment_payload.get("test_split") or {})
    overlap = dict(assessment_payload.get("overlap") or {})
    evidence_rows = dict(assessment_payload.get("evidence_rows") or {})

    train_accessions = set(train_split.get("unique_protein_accessions") or [])
    test_accessions = set(test_split.get("unique_protein_accessions") or [])
    all_accessions = train_accessions | test_accessions
    cache_entries = ensure_uniprot_sequence_cache(all_accessions, cache_root=cache_root)

    cache_summary = {
        "requested_accession_count": len(all_accessions),
        "sequence_present_count": sum(
            1 for payload in cache_entries.values() if payload.get("sequence_present")
        ),
        "sequence_missing_count": sum(
            1 for payload in cache_entries.values() if not payload.get("sequence_present")
        ),
    }

    exact_hash_overlap_rows = []
    train_hash_to_accessions: dict[str, list[str]] = defaultdict(list)
    test_hash_to_accessions: dict[str, list[str]] = defaultdict(list)
    for accession in train_accessions:
        sequence_hash = str(cache_entries.get(accession, {}).get("sequence_sha256") or "").strip()
        if sequence_hash:
            train_hash_to_accessions[sequence_hash].append(accession)
    for accession in test_accessions:
        sequence_hash = str(cache_entries.get(accession, {}).get("sequence_sha256") or "").strip()
        if sequence_hash:
            test_hash_to_accessions[sequence_hash].append(accession)
    for sequence_hash in sorted(set(train_hash_to_accessions) & set(test_hash_to_accessions)):
        exact_hash_overlap_rows.append(
            {
                "sequence_sha256": sequence_hash,
                "train_accessions": sorted(train_hash_to_accessions[sequence_hash]),
                "test_accessions": sorted(test_hash_to_accessions[sequence_hash]),
            }
        )

    candidate_pair_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row_group_name in (
        "uniref100_cluster_overlap_rows",
        "uniref90_cluster_overlap_rows",
        "uniref50_cluster_overlap_rows",
    ):
        for row in list(evidence_rows.get(row_group_name) or []):
            train_group = list(row.get("train_accessions") or [])
            test_group = list(row.get("test_accessions") or [])
            group_id = str(row.get("cluster_id") or "")
            for train_accession in train_group:
                for test_accession in test_group:
                    pair_key = (train_accession, test_accession)
                    candidate_pair_index.setdefault(
                        pair_key,
                        {
                            "train_accession": train_accession,
                            "test_accession": test_accession,
                            "source_clusters": [],
                        },
                    )
                    candidate_pair_index[pair_key]["source_clusters"].append(group_id)

    near_sequence_rows = []
    for pair in sorted(
        candidate_pair_index.values(),
        key=lambda item: (item["train_accession"], item["test_accession"]),
    ):
        train_payload = cache_entries.get(pair["train_accession"], {})
        test_payload = cache_entries.get(pair["test_accession"], {})
        train_sequence = str(train_payload.get("fasta_sequence") or "")
        test_sequence = str(test_payload.get("fasta_sequence") or "")
        metrics = _sequence_similarity_metrics(train_sequence, test_sequence)
        near_sequence_rows.append(
            {
                "train_accession": pair["train_accession"],
                "test_accession": pair["test_accession"],
                "source_clusters": sorted(set(pair["source_clusters"])),
                "sequence_present": bool(train_sequence and test_sequence),
                "sequence_sha256_equal": train_payload.get("sequence_sha256")
                and train_payload.get("sequence_sha256") == test_payload.get("sequence_sha256"),
                "length_delta": metrics["length_delta"],
                "length_ratio": metrics["length_ratio"],
                "shared_kmer_jaccard": metrics["shared_kmer_jaccard"],
                "near_sequence_flag": bool(
                    metrics["exact_sequence_match"]
                    or (
                        metrics["shared_kmer_jaccard"] is not None
                        and metrics["shared_kmer_jaccard"] >= 0.85
                    )
                ),
            }
        )

    exact_sequence_overlap_count = len(exact_hash_overlap_rows)
    near_sequence_flagged_count = sum(
        1 for row in near_sequence_rows if row.get("near_sequence_flag")
    )

    if exact_sequence_overlap_count:
        sequence_decision = "blocked_on_exact_sequence_reuse"
    elif near_sequence_flagged_count:
        sequence_decision = "review_needed_for_near_sequence_overlap"
    elif cache_summary["sequence_missing_count"]:
        sequence_decision = "partial_sequence_coverage"
    else:
        sequence_decision = "no_sequence_level_blockers_detected"

    return {
        "artifact_id": "pdb_paper_split_sequence_signature_audit_preview",
        "schema_id": "proteosphere-pdb-paper-split-sequence-signature-audit-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "sequence_decision": sequence_decision,
            "requested_accession_count": cache_summary["requested_accession_count"],
            "sequence_present_count": cache_summary["sequence_present_count"],
            "sequence_missing_count": cache_summary["sequence_missing_count"],
            "exact_sequence_overlap_count": exact_sequence_overlap_count,
            "near_sequence_flagged_count": near_sequence_flagged_count,
            "direct_accession_overlap_count": len(
                overlap.get("direct_protein_accession_overlap") or []
            ),
        },
        "sequence_cache_summary": cache_summary,
        "exact_sequence_overlap_rows": exact_hash_overlap_rows,
        "near_sequence_rows": near_sequence_rows[:250],
        "truth_boundary": {
            "summary": (
                "This audit uses accession-scoped UniProt FASTA retrieval to cache sequence "
                "signatures for the proteins present in a paper split. It upgrades the paper "
                "assessment from cluster-only proxies to exact-sequence and near-sequence "
                "evidence, but it is still not a substitution-aware alignment engine."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_split_mutation_audit(
    assessment_payload: dict[str, Any],
    *,
    cache_root: Path = DEFAULT_SEQUENCE_CACHE_ROOT,
) -> dict[str, Any]:
    train_split = dict(assessment_payload.get("train_split") or {})
    test_split = dict(assessment_payload.get("test_split") or {})
    evidence_rows = dict(assessment_payload.get("evidence_rows") or {})

    train_accessions = set(train_split.get("unique_protein_accessions") or [])
    test_accessions = set(test_split.get("unique_protein_accessions") or [])
    cache_entries = ensure_uniprot_sequence_cache(
        train_accessions | test_accessions,
        cache_root=cache_root,
    )

    candidate_pair_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row_group_name in (
        "uniref100_cluster_overlap_rows",
        "uniref90_cluster_overlap_rows",
        "uniref50_cluster_overlap_rows",
    ):
        for row in list(evidence_rows.get(row_group_name) or []):
            for train_accession in list(row.get("train_accessions") or []):
                for test_accession in list(row.get("test_accessions") or []):
                    if train_accession == test_accession:
                        continue
                    pair_key = (train_accession, test_accession)
                    candidate_pair_index.setdefault(
                        pair_key,
                        {
                            "train_accession": train_accession,
                            "test_accession": test_accession,
                            "source_clusters": [],
                        },
                    )
                    cluster_id = str(row.get("cluster_id") or "")
                    if cluster_id:
                        candidate_pair_index[pair_key]["source_clusters"].append(cluster_id)

    mutation_rows = []
    for pair in sorted(
        candidate_pair_index.values(),
        key=lambda item: (item["train_accession"], item["test_accession"]),
    ):
        train_payload = cache_entries.get(pair["train_accession"], {})
        test_payload = cache_entries.get(pair["test_accession"], {})
        train_sequence = str(train_payload.get("fasta_sequence") or "")
        test_sequence = str(test_payload.get("fasta_sequence") or "")
        if not train_sequence or not test_sequence:
            continue

        metrics = _sequence_similarity_metrics(train_sequence, test_sequence)
        same_length = len(train_sequence) == len(test_sequence)
        mismatch_count = (
            sum(
                1
                for left, right in zip(train_sequence, test_sequence, strict=False)
                if left != right
            )
            if same_length
            else None
        )
        bounded_distance = _bounded_levenshtein_distance(
            train_sequence,
            test_sequence,
            max_distance=12,
        )

        if mismatch_count == 1:
            relation = "single_substitution_variant"
        elif mismatch_count is not None and mismatch_count <= 5:
            relation = "few_substitutions_variant"
        elif bounded_distance is not None and bounded_distance <= 5:
            relation = "small_edit_variant"
        elif bounded_distance is not None:
            relation = "mutation_like_overlap"
        else:
            relation = "family_overlap_not_mutation_like"

        mutation_rows.append(
            {
                "train_accession": pair["train_accession"],
                "test_accession": pair["test_accession"],
                "source_clusters": sorted(set(pair["source_clusters"])),
                "same_length": same_length,
                "mismatch_count": mismatch_count,
                "bounded_edit_distance_le_12": bounded_distance,
                "length_delta": metrics["length_delta"],
                "length_ratio": metrics["length_ratio"],
                "shared_kmer_jaccard": metrics["shared_kmer_jaccard"],
                "relation": relation,
            }
        )

    relation_counts = Counter(str(row["relation"]) for row in mutation_rows)
    mutation_like_count = sum(
        count
        for relation, count in relation_counts.items()
        if relation != "family_overlap_not_mutation_like"
    )
    if mutation_like_count:
        decision = "mutation_like_overlap_present"
    elif mutation_rows:
        decision = "family_overlap_without_small_edit_evidence"
    else:
        decision = "no_non_identical_overlap_pairs_to_review"

    return {
        "artifact_id": "pdb_paper_split_mutation_audit_preview",
        "schema_id": "proteosphere-pdb-paper-split-mutation-audit-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "decision": decision,
            "candidate_pair_count": len(mutation_rows),
            "mutation_like_pair_count": mutation_like_count,
            "relation_counts": dict(sorted(relation_counts.items())),
        },
        "rows": mutation_rows[:250],
        "truth_boundary": {
            "summary": (
                "This audit looks for small-edit or substitution-like sequence reuse between "
                "non-identical train/test proteins drawn from overlapping UniRef groups. It is "
                "still a bounded approximation rather than a full biological alignment engine."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_split_structure_state_audit(
    assessment_payload: dict[str, Any],
    corpus_payload: dict[str, Any],
) -> dict[str, Any]:
    structure_index = {
        str(row.get("payload", {}).get("pdb_id") or "").upper(): row.get("payload", {})
        for row in corpus_payload.get("rows") or []
        if isinstance(row, dict) and row.get("row_family") == "structure"
    }
    evidence_rows = dict(assessment_payload.get("evidence_rows") or {})

    relation_rows = []
    relation_counts: Counter[str] = Counter()
    risk_level_counts: Counter[str] = Counter()

    for pair_row in list(evidence_rows.get("structure_pair_overlap_rows") or []):
        train_id = str(pair_row.get("train_structure_id") or "").upper()
        test_id = str(pair_row.get("test_structure_id") or "").upper()
        train_payload = structure_index.get(train_id, {})
        test_payload = structure_index.get(test_id, {})
        train_accessions = sorted(train_payload.get("mapped_protein_accessions") or [])
        test_accessions = sorted(test_payload.get("mapped_protein_accessions") or [])
        train_roots = sorted(train_payload.get("mapped_protein_accession_roots") or [])
        test_roots = sorted(test_payload.get("mapped_protein_accession_roots") or [])
        train_complex_type = str(train_payload.get("complex_type") or "")
        test_complex_type = str(test_payload.get("complex_type") or "")

        shared_accessions = list(pair_row.get("shared_accessions") or [])
        shared_roots = list(pair_row.get("shared_accession_roots") or [])
        shared_u90 = list(pair_row.get("shared_uniref90_clusters") or [])
        shared_u50 = list(pair_row.get("shared_uniref50_clusters") or [])

        if train_accessions and test_accessions and train_accessions == test_accessions:
            relation = "exact_protein_set_reuse"
            risk_level = "critical"
        elif train_roots and test_roots and train_roots == test_roots:
            relation = "accession_root_set_reuse"
            risk_level = "high"
        elif train_complex_type == test_complex_type and shared_accessions:
            relation = "shared_protein_different_context"
            risk_level = "high"
        elif train_complex_type == test_complex_type and shared_roots:
            relation = "shared_root_different_context"
            risk_level = "medium"
        elif shared_u90:
            relation = "close_family_context_overlap"
            risk_level = "medium"
        elif shared_u50:
            relation = "broad_family_context_overlap"
            risk_level = "review"
        else:
            relation = "shared_partner_or_context_only"
            risk_level = "review"

        relation_counts[relation] += 1
        risk_level_counts[risk_level] += 1
        relation_rows.append(
            {
                "train_structure_id": train_id,
                "test_structure_id": test_id,
                "train_complex_type": train_complex_type,
                "test_complex_type": test_complex_type,
                "train_accession_count": len(train_accessions),
                "test_accession_count": len(test_accessions),
                "shared_accessions": shared_accessions,
                "shared_accession_roots": shared_roots,
                "shared_uniref90_clusters": shared_u90,
                "shared_uniref50_clusters": shared_u50,
                "relation": relation,
                "risk_level": risk_level,
            }
        )

    decision = (
        "critical_structure_state_reuse_present"
        if risk_level_counts.get("critical")
        else (
            "high_risk_structure_context_overlap_present"
            if risk_level_counts.get("high")
            else (
                "review_structure_context_overlap_present"
                if relation_rows
                else "no_structure_state_overlap_rows"
            )
        )
    )

    return {
        "artifact_id": "pdb_paper_split_structure_state_audit_preview",
        "schema_id": "proteosphere-pdb-paper-split-structure-state-audit-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "decision": decision,
            "flagged_pair_count": len(relation_rows),
            "relation_counts": dict(sorted(relation_counts.items())),
            "risk_level_counts": dict(sorted(risk_level_counts.items())),
        },
        "rows": relation_rows[:250],
        "truth_boundary": {
            "summary": (
                "This audit classifies flagged train/test structure pairs by whether they look "
                "like exact protein-set reuse, same-root reuse, or broader family/context reuse. "
                "It is intended for structure-state review, not for automatic governing decisions."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_dataset_quality_verdict(
    assessment_payload: dict[str, Any],
    leakage_matrix_payload: dict[str, Any],
    acceptance_gate_payload: dict[str, Any],
    sequence_audit_payload: dict[str, Any],
    mutation_audit_payload: dict[str, Any],
    structure_state_audit_payload: dict[str, Any],
) -> dict[str, Any]:
    assessment_summary = dict(assessment_payload.get("summary") or {})
    leakage_summary = dict(leakage_matrix_payload.get("summary") or {})
    acceptance_summary = dict(acceptance_gate_payload.get("summary") or {})
    sequence_summary = dict(sequence_audit_payload.get("summary") or {})
    mutation_summary = dict(mutation_audit_payload.get("summary") or {})
    structure_summary = dict(structure_state_audit_payload.get("summary") or {})

    blocked_reasons: list[str] = []
    review_reasons: list[str] = []

    if str(acceptance_summary.get("decision") or "") == "blocked":
        blocked_reasons.extend(list(acceptance_summary.get("blocked_gates") or []))
        review_reasons.extend(list(acceptance_summary.get("attention_gates") or []))
    if str(sequence_summary.get("sequence_decision") or "") == "blocked_on_exact_sequence_reuse":
        blocked_reasons.append("exact_sequence_reuse")
    if str(structure_summary.get("decision") or "").startswith("critical_"):
        blocked_reasons.append("critical_structure_state_reuse")
    elif str(structure_summary.get("decision") or "").startswith("high_risk_"):
        blocked_reasons.append("high_risk_structure_context_overlap")
    if int(assessment_summary.get("missing_structure_count") or 0):
        review_reasons.append("missing_structure_coverage")
    if int(mutation_summary.get("mutation_like_pair_count") or 0):
        review_reasons.append("mutation_like_overlap_review")
    if int(leakage_summary.get("review_category_count") or 0):
        review_reasons.append("cluster_or_partner_overlap_review")

    blocked_reasons = sorted(set(reason for reason in blocked_reasons if reason))
    review_reasons = sorted(set(reason for reason in review_reasons if reason))

    if blocked_reasons:
        overall_decision = "blocked"
        readiness = "not_training_ready"
    elif review_reasons:
        overall_decision = "review_required"
        readiness = "needs_manual_review"
    else:
        overall_decision = "pass"
        readiness = "training_ready_candidate"

    coverage_fraction = (
        float(assessment_summary.get("covered_structure_count") or 0)
        / max(1, int(assessment_summary.get("total_structure_count") or 0))
    )
    evidence_strength = "high" if coverage_fraction >= 0.95 else "partial"

    return {
        "artifact_id": "pdb_paper_dataset_quality_verdict_preview",
        "schema_id": "proteosphere-pdb-paper-dataset-quality-verdict-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "overall_decision": overall_decision,
            "readiness": readiness,
            "blocked_reason_count": len(blocked_reasons),
            "review_reason_count": len(review_reasons),
            "blocked_reasons": blocked_reasons,
            "review_reasons": review_reasons,
            "coverage_fraction": round(coverage_fraction, 4),
            "evidence_strength": evidence_strength,
            "covered_structure_count": int(assessment_summary.get("covered_structure_count") or 0),
            "total_structure_count": int(assessment_summary.get("total_structure_count") or 0),
            "direct_protein_overlap_count": int(
                assessment_summary.get("direct_protein_overlap_count") or 0
            ),
            "exact_sequence_overlap_count": int(
                sequence_summary.get("exact_sequence_overlap_count") or 0
            ),
            "mutation_like_pair_count": int(
                mutation_summary.get("mutation_like_pair_count") or 0
            ),
            "flagged_structure_pair_count": int(
                structure_summary.get("flagged_pair_count") or 0
            ),
            "top_recommendation": (
                "Re-split the dataset before training use."
                if blocked_reasons
                else (
                    "Run manual family/context review before treating as training-ready."
                    if review_reasons
                    else "Dataset passes the current automated paper-split gates."
                )
            ),
        },
        "decision_inputs": {
            "paper_split_assessment_verdict": assessment_summary.get("verdict"),
            "acceptance_gate_decision": acceptance_summary.get("decision"),
            "sequence_decision": sequence_summary.get("sequence_decision"),
            "mutation_decision": mutation_summary.get("decision"),
            "structure_state_decision": structure_summary.get("decision"),
            "leakage_matrix_verdict": leakage_summary.get("verdict"),
        },
        "truth_boundary": {
            "summary": (
                "This surface combines automated coverage, leakage, sequence, mutation, "
                "and structure-state checks into a fail-closed paper-dataset quality verdict."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }


def build_pdb_paper_split_remediation_plan(
    assessment_payload: dict[str, Any],
    quality_verdict_payload: dict[str, Any],
    structure_state_audit_payload: dict[str, Any],
) -> dict[str, Any]:
    train_split = dict(assessment_payload.get("train_split") or {})
    test_split = dict(assessment_payload.get("test_split") or {})
    verdict_summary = dict(quality_verdict_payload.get("summary") or {})
    structure_summary = dict(structure_state_audit_payload.get("summary") or {})
    structure_rows = list(structure_state_audit_payload.get("rows") or [])

    train_structures = set(train_split.get("found_structure_ids") or [])
    test_structures = set(test_split.get("found_structure_ids") or [])
    blocking_edges = [
        row
        for row in structure_rows
        if str(row.get("risk_level") or "") in {"critical", "high"}
    ]

    structure_metrics: dict[str, dict[str, Any]] = {}
    for structure_id in sorted(train_structures | test_structures):
        split = "train" if structure_id in train_structures else "test"
        structure_metrics[structure_id] = {
            "structure_id": structure_id,
            "split": split,
            "conflict_edge_count": 0,
            "critical_edge_count": 0,
            "high_edge_count": 0,
            "relation_counts": Counter(),
        }

    normalized_edges = []
    for row in blocking_edges:
        train_id = str(row.get("train_structure_id") or "").upper()
        test_id = str(row.get("test_structure_id") or "").upper()
        risk_level = str(row.get("risk_level") or "")
        relation = str(row.get("relation") or "")
        normalized_edges.append((train_id, test_id, risk_level, relation))
        for structure_id in (train_id, test_id):
            structure_metrics.setdefault(
                structure_id,
                {
                    "structure_id": structure_id,
                    "split": "unknown",
                    "conflict_edge_count": 0,
                    "critical_edge_count": 0,
                    "high_edge_count": 0,
                    "relation_counts": Counter(),
                },
            )
            structure_metrics[structure_id]["conflict_edge_count"] += 1
            structure_metrics[structure_id]["relation_counts"][relation] += 1
            if risk_level == "critical":
                structure_metrics[structure_id]["critical_edge_count"] += 1
            elif risk_level == "high":
                structure_metrics[structure_id]["high_edge_count"] += 1

    def _serialize_rows(ids: list[str]) -> list[dict[str, Any]]:
        serialized = []
        for structure_id in ids:
            metrics = dict(structure_metrics.get(structure_id) or {})
            relation_counts = metrics.pop("relation_counts", Counter())
            metrics["relation_counts"] = dict(sorted(dict(relation_counts).items()))
            serialized.append(metrics)
        return serialized

    def _greedy_cover() -> list[str]:
        remaining = set((train_id, test_id) for train_id, test_id, _, _ in normalized_edges)
        selected: list[str] = []
        while remaining:
            score_rows = []
            for structure_id, metrics in structure_metrics.items():
                incident = sum(
                    1
                    for train_id, test_id in remaining
                    if structure_id == train_id or structure_id == test_id
                )
                if not incident:
                    continue
                score_rows.append(
                    (
                        incident,
                        metrics.get("critical_edge_count", 0),
                        1 if metrics.get("split") == "test" else 0,
                        structure_id,
                    )
                )
            if not score_rows:
                break
            _, _, _, chosen = max(score_rows)
            selected.append(chosen)
            remaining = {
                edge
                for edge in remaining
                if chosen not in edge
            }
        return selected

    hybrid_holdout = _greedy_cover()
    test_only_holdout = sorted({test_id for _, test_id, _, _ in normalized_edges})
    train_only_holdout = sorted({train_id for train_id, _, _, _ in normalized_edges})

    missing_source_fix_rows = [
        {
            "split": "train",
            "issue": "missing_structure_coverage",
            "structure_ids": sorted(train_split.get("missing_structure_ids") or []),
        },
        {
            "split": "test",
            "issue": "missing_structure_coverage",
            "structure_ids": sorted(test_split.get("missing_structure_ids") or []),
        },
        {
            "split": "test",
            "issue": "missing_local_structure_files",
            "structure_ids": sorted(test_split.get("missing_local_structure_files") or []),
        },
    ]
    missing_source_fix_rows = [
        row for row in missing_source_fix_rows if row["structure_ids"]
    ]

    preferred_plan = "hybrid_greedy_holdout"
    if len(test_only_holdout) <= len(hybrid_holdout):
        preferred_plan = "test_only_holdout"

    return {
        "artifact_id": "pdb_paper_split_remediation_plan_preview",
        "schema_id": "proteosphere-pdb-paper-split-remediation-plan-2026-04-06",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "overall_decision": verdict_summary.get("overall_decision"),
            "preferred_plan": preferred_plan,
            "blocking_edge_count": len(normalized_edges),
            "hybrid_holdout_count": len(hybrid_holdout),
            "test_only_holdout_count": len(test_only_holdout),
            "train_only_holdout_count": len(train_only_holdout),
            "missing_source_fix_count": len(missing_source_fix_rows),
            "critical_structure_state_reuse_count": int(
                (structure_summary.get("risk_level_counts") or {}).get("critical") or 0
            ),
            "high_structure_state_reuse_count": int(
                (structure_summary.get("risk_level_counts") or {}).get("high") or 0
            ),
        },
        "plans": {
            "hybrid_greedy_holdout": {
                "summary": (
                    "Greedy minimal-ish holdout plan that covers the blocking "
                    "train/test structure-conflict graph while preferring test removals on ties."
                ),
                "structure_ids": hybrid_holdout,
                "rows": _serialize_rows(hybrid_holdout),
            },
            "test_only_holdout": {
                "summary": (
                    "Remove or reassign only the test-side structures that "
                    "participate in blocking edges."
                ),
                "structure_ids": test_only_holdout,
                "rows": _serialize_rows(test_only_holdout),
            },
            "train_only_holdout": {
                "summary": (
                    "Remove or reassign only the train-side structures that "
                    "participate in blocking edges."
                ),
                "structure_ids": train_only_holdout,
                "rows": _serialize_rows(train_only_holdout),
            },
        },
        "missing_source_fix_rows": missing_source_fix_rows,
        "truth_boundary": {
            "summary": (
                "This remediation plan is a fail-closed resplitting aid. "
                "It suggests holdout or reassignment candidates and source-fix tasks, "
                "but does not mutate any dataset automatically."
            ),
            "report_only": True,
            "non_governing": True,
        },
    }
