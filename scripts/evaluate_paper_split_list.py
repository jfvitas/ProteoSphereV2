from __future__ import annotations

import json
import os
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from api.model_studio.capabilities import option_reason
    from api.model_studio.reference_library import (
        load_public_reference_manifest,
        load_source_registry,
        normalize_source_family_name,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from model_studio.capabilities import option_reason
    from model_studio.reference_library import (  # type: ignore[no-redef]
        load_public_reference_manifest,
        load_source_registry,
        normalize_source_family_name,
    )

DEFAULT_WAREHOUSE_ROOT = Path(
    os.environ.get("PROTEOSPHERE_WAREHOUSE_ROOT", r"D:\ProteoSphere\reference_library")
)
DEFAULT_OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_split_list_evaluation.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "paper_split_list_evaluation.md"
DEFAULT_PER_PAPER_DIR = REPO_ROOT / "artifacts" / "status" / "paper_split_list"
DEFAULT_EXTERNAL_ARTIFACT_DIR = (
    REPO_ROOT / "artifacts" / "status" / "paper_split_external"
)


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    title: str
    doi: str
    task_group: str
    modality: str
    source_families: tuple[str, ...]
    named_entities: tuple[str, ...]
    claimed_split_description: str
    split_style: str
    notes: tuple[str, ...] = ()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must decode to a JSON object.")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def _count_pair_tsv(path: Path) -> tuple[int, int]:
    pair_count = 0
    proteins: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            parts = text.split("\t")
            if len(parts) < 2:
                continue
            pair_count += 1
            proteins.add(parts[0])
            proteins.add(parts[1])
    return pair_count, len(proteins)


def _struct2graph_reproduction(base_dir: Path) -> dict[str, Any] | None:
    interactions_path = base_dir / "interactions_data.txt"
    if not interactions_path.exists():
        return None
    import random

    examples: list[tuple[str, str, int]] = []
    with interactions_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            p1, p2, label = text.split("\t")
            examples.append((p1, p2, int(label)))
    rng = random.Random(1337)
    shuffled = list(examples)
    rng.shuffle(shuffled)
    rng.shuffle(shuffled)
    rng.shuffle(shuffled)
    train_len = int(0.8 * len(shuffled))
    remaining = len(shuffled) - train_len
    test_len = int(0.5 * remaining)
    train = shuffled[:train_len]
    test = shuffled[train_len : train_len + test_len]
    dev = shuffled[train_len + test_len :]
    train_pdb = {item for row in train for item in row[:2]}
    test_pdb = {item for row in test for item in row[:2]}
    shared = sorted(train_pdb & test_pdb)
    return {
        "reproduction_seed": 1337,
        "interaction_rows": len(shuffled),
        "train_rows": len(train),
        "test_rows": len(test),
        "dev_rows": len(dev),
        "train_unique_pdb_ids": len(train_pdb),
        "test_unique_pdb_ids": len(test_pdb),
        "shared_pdb_count": len(shared),
        "shared_pdb_sample": shared[:25],
    }


def _supplemental_evidence(paper: PaperSpec) -> dict[str, Any]:
    base_dir = DEFAULT_EXTERNAL_ARTIFACT_DIR
    if paper.paper_id == "sledzieski2021dscript":
        human_train = base_dir / "dscript" / "human_train.tsv"
        human_test = base_dir / "dscript" / "human_test.tsv"
        fly_test = base_dir / "dscript" / "fly_test.tsv"
        if not all(path.exists() for path in (human_train, human_test, fly_test)):
            return {}
        train_pairs, train_proteins = _count_pair_tsv(human_train)
        test_pairs, test_proteins = _count_pair_tsv(human_test)
        fly_pairs, fly_proteins = _count_pair_tsv(fly_test)
        return {
            "status": "published_split_located",
            "summary": (
                "Released D-SCRIPT pair files were recovered locally, including human "
                "train/test and a fly transfer cohort."
            ),
            "details": [
                f"`human_train.tsv` contains {train_pairs:,} labeled pairs spanning {train_proteins:,} unique Ensembl proteins.",
                f"`human_test.tsv` contains {test_pairs:,} labeled pairs spanning {test_proteins:,} unique Ensembl proteins.",
                f"`fly_test.tsv` contains {fly_pairs:,} labeled pairs spanning {fly_proteins:,} FlyBase proteins.",
                "The released identifiers are Ensembl/FlyBase protein IDs rather than warehouse-native `protein_ref` or UniProt accessions.",
            ],
            "artifact_paths": [str(human_train), str(human_test), str(fly_test)],
            "source_links": [
                "https://github.com/samsledje/D-SCRIPT/blob/main/docs/source/data.rst",
            ],
        }
    if paper.paper_id == "szymborski2022rapppid":
        archive_path = base_dir / "rapppid" / "rapppid_data.zip"
        if not archive_path.exists():
            return {}
        with zipfile.ZipFile(archive_path) as zf:
            names = zf.namelist()
        c1 = sorted(name for name in names if "/string_c1/" in name and name.endswith(".pkl.gz"))
        c2 = sorted(name for name in names if "/string_c2/" in name and name.endswith(".pkl.gz"))
        c3 = sorted(name for name in names if "/string_c3/" in name and name.endswith(".pkl.gz"))
        return {
            "status": "published_split_located",
            "summary": (
                "A RAPPPID Zenodo release was recovered locally and contains explicit C1/C2/C3 split artifacts."
            ),
            "details": [
                f"The archive includes {len(c1)} `string_c1` pickle members, {len(c2)} `string_c2` members, and {len(c3)} `string_c3` members.",
                "The release packages `train_pairs.pkl.gz`, `val_pairs.pkl.gz`, `test_pairs.pkl.gz`, and `seqs.pkl.gz` for the comparative splits.",
                "The serialized keys are Ensembl protein IDs in STRING-style namespace (for example `9606.ENSP...`), not warehouse-native accessions.",
            ],
            "artifact_paths": [str(archive_path)],
            "source_links": [
                "https://doi.org/10.5281/zenodo.6817258",
            ],
        }
    if paper.paper_id == "baranwal2022struct2graph":
        struct_dir = base_dir / "struct2graph"
        create_examples = struct_dir / "create_examples.py"
        interactions = struct_dir / "interactions_data.txt"
        proteins = struct_dir / "list_of_prots.txt"
        if not all(path.exists() for path in (create_examples, interactions, proteins)):
            return {}
        interaction_rows = sum(
            1
            for line in interactions.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        protein_rows = sum(
            1
            for line in proteins.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        reproduction = _struct2graph_reproduction(struct_dir)
        return {
            "status": "repo_split_logic_located",
            "summary": (
                "The Struct2Graph repository exposes the split-building code and it is example-level randomization rather than accession-grouped separation."
            ),
            "details": [
                f"`interactions_data.txt` contains {interaction_rows:,} labeled PDB-pair examples and `list_of_prots.txt` contains {protein_rows:,} accession-to-PDB-chain rows.",
                "The released `create_examples.py` shuffles merged examples three times and then slices them into 80% train, 10% test, and 10% dev.",
                "That repo logic operates on pair examples, not on proteins, accession roots, UniRef groups, or source-separated components.",
            ],
            "artifact_paths": [str(create_examples), str(interactions), str(proteins)],
            "source_links": [
                "https://github.com/baranwa2/Struct2Graph",
                "https://raw.githubusercontent.com/baranwa2/Struct2Graph/master/create_examples.py",
                "https://raw.githubusercontent.com/baranwa2/Struct2Graph/master/interactions_data.txt",
                "https://raw.githubusercontent.com/baranwa2/Struct2Graph/master/list_of_prots.txt",
            ],
            "reproduction": reproduction,
        }
    return {}


def _project_status_from_verdict(verdict: str) -> str:
    if verdict == "faithful and acceptable as-is":
        return "usable"
    if verdict == "audit-useful but non-canonical":
        return "audit_only"
    if verdict == "misleading / leakage-prone":
        return "unsafe_for_training"
    return "blocked_pending_mapping"


def _recommended_policy(split_style: str) -> str:
    if split_style in {"strict_unseen_protein", "uniref_or_homology_guard"}:
        return "uniref_grouped"
    if split_style in {"external_holdout", "source_held_out", "paper_specific_external"}:
        return "paper_faithful_external"
    return "accession_grouped"


def _source_rows(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, Any]]:
    rows = con.execute(
        """
        SELECT
            source_key,
            source_name,
            availability_status,
            category,
            license_scope,
            public_export_allowed,
            redistributable,
            retrieval_mode,
            scope_tier
        FROM warehouse_sources
        """
    ).fetchall()
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalize_source_family_name(row[0] or row[1] or "")
        indexed[key] = {
            "source_key": row[0],
            "source_name": row[1],
            "availability_status": row[2],
            "category": row[3],
            "license_scope": row[4],
            "public_export_allowed": bool(row[5]),
            "redistributable": bool(row[6]),
            "retrieval_mode": row[7],
            "scope_tier": row[8],
        }
    return indexed


def _warehouse_profile(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    ppi_sources = {
        row[0]: {"row_count": row[1], "resolved_endpoint_count": row[2]}
        for row in con.execute(
            """
            SELECT
                interaction_source,
                COUNT(*) AS row_count,
                COUNT(*) FILTER (
                    WHERE protein_a_ref IS NOT NULL
                      AND protein_b_ref IS NOT NULL
                ) AS resolved_endpoint_count
            FROM protein_protein_edges
            GROUP BY 1
            """
        ).fetchall()
    }
    return {
        "protein_uniref_coverage": dict(
            zip(
                ("proteins", "uniref100", "uniref90", "uniref50"),
                con.execute(
                    """
                    SELECT
                        COUNT(*) AS proteins,
                        COUNT(*) FILTER (WHERE uniref100_cluster IS NOT NULL) AS uniref100,
                        COUNT(*) FILTER (WHERE uniref90_cluster IS NOT NULL) AS uniref90,
                        COUNT(*) FILTER (WHERE uniref50_cluster IS NOT NULL) AS uniref50
                    FROM proteins
                    """
                ).fetchone(),
                strict=True,
            )
        ),
        "connectivity_validation": _load_json(
            DEFAULT_WAREHOUSE_ROOT / "control" / "runtime_validation.latest.json"
        )
        .get("checks", {})
        .get("connectivity_validation", {}),
        "ppi_sources": ppi_sources,
        "variant_rows": int(con.execute("SELECT COUNT(*) FROM protein_variants").fetchone()[0]),
        "joined_variant_rows": int(
            con.execute(
                "SELECT COUNT(*) FROM protein_variants WHERE join_status = 'joined'"
            ).fetchone()[0]
        ),
        "pdb_entry_rows": int(con.execute("SELECT COUNT(*) FROM pdb_entries").fetchone()[0]),
        "structure_unit_rows": int(
            con.execute("SELECT COUNT(*) FROM structure_units").fetchone()[0]
        ),
    }


PAPERS: tuple[PaperSpec, ...] = (
    PaperSpec(
        "zhang2012preppi",
        "Structure-based prediction of protein-protein interactions on a genome-wide scale",
        "https://doi.org/10.1038/nature11503",
        "ppi_prediction",
        "structure_plus_functional",
        ("rcsb_pdbe", "uniprot", "string", "intact"),
        ("yeast", "human", "PrePPI"),
        "Genome-scale discovery workflow in yeast and human; the supplied paper list does not provide an explicit train/test or external holdout roster.",
        "paper_specific_external",
    ),
    PaperSpec("sun2017sequence", "Sequence-based prediction of protein protein interaction using a deep-learning algorithm", "https://doi.org/10.1186/s12859-017-1700-2", "ppi_prediction", "sequence_only", ("intact", "string"), ("10-fold CV benchmark", "external test sets"), "10-fold cross-validation benchmark plus external test sets from the supplied reading list.", "cross_validation"),
    PaperSpec("du2017deepppi", "DeepPPI: Boosting Prediction of Protein-Protein Interactions with Deep Neural Networks", "https://doi.org/10.1021/acs.jcim.7b00028", "ppi_prediction", "sequence_only", ("intact", "string"), ("test set",), "Held-out test set is claimed, but the supplied list does not identify the membership roster or grouping rule.", "held_out_test"),
    PaperSpec("hashemifar2018dppi", "Predicting protein-protein interactions through sequence-based deep learning", "https://doi.org/10.1093/bioinformatics/bty573", "ppi_prediction", "sequence_profile", ("intact", "string"), ("S. cerevisiae core subset", "homodimers"), "Several benchmarks are named, including the S. cerevisiae core subset, but the supplied list does not include explicit split membership evidence.", "held_out_test"),
    PaperSpec("chen2019siamese_rcnn", "Multifaceted protein-protein interaction prediction based on Siamese residual RCNN", "https://doi.org/10.1093/bioinformatics/btz328", "ppi_prediction", "sequence_only", ("intact", "string"), ("SHS27k", "SHS148k"), "Reported train/test evaluation on SHS27k and SHS148k, but the supplied list does not expose the actual roster or separation rule.", "held_out_test"),
    PaperSpec("sledzieski2021dscript", "D-SCRIPT translates genome to phenome with sequence-based, structure-aware, genome-scale predictions of protein-protein interactions", "https://doi.org/10.1016/j.cels.2021.08.010", "ppi_prediction", "sequence_plus_structure_aware", ("intact", "uniprot"), ("38,345 human PPIs", "fly proteins"), "Model trained on 38,345 human PPIs and evaluated for cross-species transfer to fly proteins.", "external_holdout"),
    PaperSpec("szymborski2022rapppid", "RAPPPID: towards generalizable protein interaction prediction with AWD-LSTM twin networks", "https://doi.org/10.1093/bioinformatics/btac429", "ppi_prediction", "sequence_only", ("intact", "string", "uniprot"), ("unseen proteins",), "Strict train/test separation with unseen proteins is claimed in the supplied list.", "strict_unseen_protein"),
    PaperSpec("baranwal2022struct2graph", "Struct2Graph: a graph attention network for structure based predictions of protein-protein interactions", "https://doi.org/10.1186/s12859-022-04910-9", "ppi_prediction", "structure_only", ("rcsb_pdbe", "pdbbind"), ("balanced set", "1:10 unbalanced set", "fivefold CV"), "Balanced-set evaluation and fivefold cross-validation on an unbalanced set are claimed.", "cross_validation"),
    PaperSpec("gainza2020masif", "Deciphering interaction fingerprints from protein molecular surfaces using geometric deep learning", "https://doi.org/10.1038/s41592-019-0666-6", "interface_prediction", "surface_geometry", ("rcsb_pdbe",), ("MaSIF-site", "MaSIF-search", "PD-L1:mouse PD1"), "Benchmarking is described through site/search tasks and a database scan example; the supplied list does not provide explicit train/test membership.", "paper_specific_external"),
    PaperSpec("dai2021geometric_interface", "Protein interaction interface region prediction by geometric deep learning", "https://doi.org/10.1093/bioinformatics/btab154", "interface_prediction", "geometry_plus_complementarity", ("rcsb_pdbe",), ("multiple benchmarks",), "Multiple benchmarks are referenced, but the supplied list does not include membership evidence or a concrete grouping rule.", "paper_specific_external"),
    PaperSpec("xie2022interprotein_contacts", "Deep graph learning of inter-protein contacts", "https://doi.org/10.1093/bioinformatics/btab761", "contact_prediction", "graph_plus_msa_lm", ("rcsb_pdbe", "uniprot"), ("homodimers", "CASP-CAPRI data"), "Evaluation is reported on homodimers and CASP-CAPRI data.", "external_holdout"),
    PaperSpec("tubiana2022scannet", "ScanNet: an interpretable geometric deep learning model for structure-based protein binding site prediction", "https://doi.org/10.1038/s41592-022-01490-7", "binding_site_prediction", "structure_only", ("rcsb_pdbe",), ("unseen folds", "SARS-CoV-2 spike epitopes"), "Unseen-fold generalization is claimed, but no explicit split roster is included in the supplied list.", "uniref_or_homology_guard"),
    PaperSpec("krapp2023pesto", "PeSTo: parameter-free geometric deep learning for accurate prediction of protein binding interfaces", "https://doi.org/10.1038/s41467-023-37701-8", "binding_site_prediction", "structure_only", ("rcsb_pdbe",), ("ScanNet comparison", "PPDB5 example"), "Comparison against prior interface predictors plus an unbound PPDB5 example; no explicit train/test membership evidence in the supplied list.", "paper_specific_external"),
    PaperSpec("yugandhar2014affinity", "Protein-protein binding affinity prediction from amino acid sequence", "https://doi.org/10.1093/bioinformatics/btu580", "affinity_prediction", "sequence_only", ("pdbbind", "uniprot"), ("135 complexes", "jackknife"), "Class-specific regression over 135 complexes with jackknife evaluation.", "cross_validation"),
    PaperSpec("rodrigues2019mcsm_ppi2", "mCSM-PPI2: predicting the effects of mutations on protein-protein interactions", "https://doi.org/10.1093/nar/gkz383", "mutation_effect_prediction", "structure_plus_evolution", ("rcsb_pdbe", "uniprot"), ("CAPRI blind tests",), "Benchmarking includes CAPRI blind tests, which function as an external holdout regime.", "external_holdout"),
    PaperSpec("wang2020nettree", "A topology-based network tree for the prediction of protein-protein binding affinity changes following mutation", "https://doi.org/10.1038/s42256-020-0149-6", "mutation_effect_prediction", "structure_only", ("rcsb_pdbe",), ("AB-Bind S645", "blind homology subset"), "Reported on AB-Bind S645 plus a blind homology subset.", "external_holdout"),
    PaperSpec("zhang2020mutabind2", "MutaBind2: Predicting the Impacts of Single and Multiple Mutations on Protein-Protein Interactions", "https://doi.org/10.1016/j.isci.2020.100939", "mutation_effect_prediction", "structure_plus_conservation", ("rcsb_pdbe", "uniprot"), ("single and multiple mutations",), "Single- and multiple-mutation benchmarking is claimed, but the supplied list does not provide the roster or split construction details.", "held_out_test"),
    PaperSpec("zhou2024ddmut_ppi", "DDMut-PPI: predicting effects of mutations on protein-protein interactions using graph-based deep learning", "https://doi.org/10.1093/nar/gkae412", "mutation_effect_prediction", "graph_plus_plm", ("rcsb_pdbe", "uniprot"), ("SM1124", "single and multiple mutants"), "Evaluation is reported on single- and multiple-mutation sets including SM1124.", "external_holdout"),
    PaperSpec("bryant2022af2_ppi", "Improved prediction of protein-protein interactions using AlphaFold2", "https://doi.org/10.1038/s41467-022-28865-w", "complex_prediction", "structure_prediction", ("alphafold", "rcsb_pdbe"), ("heterodimers", "CAPRI docking baseline"), "Direct heterodimer complex prediction with ranked evaluation against docking baselines.", "external_holdout"),
    PaperSpec("gao2022af2complex", "AF2Complex predicts direct physical interactions in multimeric proteins with deep learning", "https://doi.org/10.1038/s41467-022-29394-2", "complex_prediction", "structure_prediction", ("alphafold", "rcsb_pdbe"), ("multimeric complexes", "E. coli test"), "Large-scale E. coli test for multimeric direct interaction identification.", "external_holdout"),
)


def _source_findings(
    paper: PaperSpec,
    source_lookup: dict[str, dict[str, Any]],
    registry_payload: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    findings: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    registry_rows = registry_payload.get("source_records") or registry_payload.get("records") or []
    for family in paper.source_families:
        normalized = normalize_source_family_name(family)
        source_row = source_lookup.get(normalized)
        registry_count = sum(
            1
            for row in registry_rows
            if normalize_source_family_name(row.get("source_family") or row.get("source_key") or "")
            == normalized
        )
        if source_row is None:
            blockers.append(f"warehouse source family `{family}` is not present in warehouse_sources")
            continue
        findings.append(
            f"{source_row['source_name']} is present in the library with "
            f"license scope `{source_row['license_scope']}` and scope tier `{source_row['scope_tier']}` "
            f"(registry records: {registry_count})."
        )
        if not source_row["public_export_allowed"] or not source_row["redistributable"]:
            warnings.append(
                f"{source_row['source_name']} is non-public or non-redistributable in the condensed library and should remain audit-facing rather than governing."
            )
    if paper.task_group == "ppi_prediction":
        ppi_sources = profile["ppi_sources"]
        findings.append(
            "The current best-evidence `protein_protein_edges` surface only materializes "
            f"{', '.join(sorted(ppi_sources))}; IntAct/STRING are present as sources but not as benchmark roster tables."
        )
    if paper.task_group in {"interface_prediction", "binding_site_prediction", "contact_prediction", "complex_prediction"}:
        findings.append(
            f"`pdb_entries` ({profile['pdb_entry_rows']:,} rows) and `structure_units` ({profile['structure_unit_rows']:,} rows) are available in best_evidence, but paper-specific benchmark membership is not."
        )
    if paper.task_group == "mutation_effect_prediction":
        findings.append(
            f"`protein_variants` contains {profile['variant_rows']:,} rows ({profile['joined_variant_rows']:,} joined), which is enough for mutation-level grounding but not enough to reconstruct named paper cohorts like AB-Bind or SM1124 from the condensed surface alone."
        )
    return findings, blockers, warnings


def _verdict_for_paper(paper: PaperSpec) -> str:
    if paper.split_style == "cross_validation":
        return "misleading / leakage-prone"
    if paper.split_style in {"strict_unseen_protein", "external_holdout", "uniref_or_homology_guard"}:
        return "audit-useful but non-canonical"
    if paper.split_style == "held_out_test":
        return "incomplete because required evidence is missing"
    return "incomplete because required evidence is missing"


def _resolved_policy_payload(paper: PaperSpec) -> dict[str, Any]:
    policy = _recommended_policy(paper.split_style)
    return {
        "policy": policy,
        "reason": option_reason("split_strategies", policy),
        "recommended_for_training": policy in {"accession_grouped", "uniref_grouped"},
        "paper_faithful_only": policy == "paper_faithful_external",
    }


def _overlap_findings(paper: PaperSpec, profile: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    resolved = paper.split_style in {"strict_unseen_protein"}
    notes: list[str] = []
    blockers.append("paper-specific train/test membership roster is absent from the condensed warehouse")
    if resolved:
        notes.append(
            "The claimed split style is compatible with ProteoSphere UniRef-aware grouping, but the paper roster is not present in the condensed warehouse, so no concrete train/test overlap rows could be emitted."
        )
    else:
        notes.append(
            "Direct, accession-root, and UniRef overlap checks require concrete train/test membership. The library exposes UniRef clusters broadly, but not the paper roster needed to apply them."
        )
    notes.append(
        f"The proteins surface includes {profile['protein_uniref_coverage']['uniref90']:,} proteins with UniRef90 assignments, so UniRef-grouped evaluation is generally possible once a roster is mapped."
    )
    return {
        "direct_overlap": {"status": "not_computable", "notes": list(notes)},
        "accession_root_overlap": {"status": "not_computable", "notes": list(notes)},
        "uniref_overlap": {"status": "theoretically_supported", "notes": list(notes)},
    }, blockers, warnings


def _leakage_findings(paper: PaperSpec, profile: dict[str, Any]) -> dict[str, Any]:
    connectivity = profile["connectivity_validation"].get("protein_protein_edges", {})
    notes = [
        "ProteoSphere treats direct accession reuse, accession-root reuse, UniRef reuse, and shared partner/component reuse as leakage axes.",
        "Without a paper roster, partner/component leakage cannot be enumerated concretely from the condensed warehouse.",
    ]
    if paper.split_style == "cross_validation":
        notes.append("Cross-validation over precompiled benchmark pairs is treated as leakage-prone unless accession/UniRef grouping is shown explicitly.")
    if paper.task_group == "ppi_prediction":
        notes.append(
            f"The runtime validation artifact reports {int(connectivity.get('edges_with_null_endpoint') or 0):,} PPI edges with null endpoints, which further limits partner-level leakage analysis for structure-derived rows."
        )
    return {"status": "preflight_only", "notes": notes}


def _governed_eligibility_findings(paper: PaperSpec, blockers: list[str]) -> dict[str, Any]:
    notes = [
        "best_evidence is the governing read view for this evaluation.",
        "Paper-specific benchmark claims remain non-governing until the condensed warehouse can resolve membership and provenance at roster level.",
    ]
    if paper.task_group in {"interface_prediction", "binding_site_prediction", "contact_prediction", "complex_prediction"}:
        notes.append("This paper is better treated as an audit/comparison benchmark than as a release-governing training split in current ProteoSphere surfaces.")
    if paper.task_group == "mutation_effect_prediction":
        notes.append("Mutation-effect papers can be grounded partially through `protein_variants`, but named benchmark splits remain audit-only unless cohort membership is materialized.")
    status = "candidate_only"
    if blockers:
        status = "audit_only"
    return {"status": status, "notes": notes}


def _recommended_treatment(paper: PaperSpec, verdict: str, resolved_policy: dict[str, Any]) -> str:
    policy = resolved_policy["policy"]
    if verdict == "misleading / leakage-prone":
        return f"Do not accept the reported split as training-governing. Re-express the benchmark under `{policy}` before any comparison is treated as meaningful."
    if verdict == "audit-useful but non-canonical":
        if policy == "paper_faithful_external":
            return "Keep the paper split in a `paper_faithful_external` audit lane only; do not treat it as the default canonical split for training or headline benchmarking."
        return f"Keep the paper split as a `paper_faithful_external` audit lane and compare it against a ProteoSphere-native `{policy}` rebuild when roster evidence becomes available."
    return f"Treat the paper as blocked pending roster mapping. If recovered later, canonicalize it under `{policy}` rather than trusting the paper split verbatim."


def _paper_payload(
    paper: PaperSpec,
    *,
    source_lookup: dict[str, dict[str, Any]],
    profile: dict[str, Any],
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    source_findings, source_blockers, source_warnings = _source_findings(
        paper, source_lookup, registry_payload, profile
    )
    overlap_findings, overlap_blockers, overlap_warnings = _overlap_findings(paper, profile)
    resolved_policy = _resolved_policy_payload(paper)
    verdict = _verdict_for_paper(paper)
    blockers = [*source_blockers, *overlap_blockers]
    warnings = [*source_warnings, *overlap_warnings]
    fallback_required = False
    provenance_notes = [
        "Primary evidence came from the condensed warehouse catalog, manifest, source registry, runtime validation artifact, and Model Studio split-policy code.",
        "No raw/archive fallback was used for this paper evaluation.",
    ]
    if paper.named_entities:
        provenance_notes.append(
            "Named entities or benchmark labels from the supplied paper list were mapped only to warehouse-visible source families and summary surfaces, not to raw membership rosters."
        )
    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "doi": paper.doi,
        "task_group": paper.task_group,
        "claimed_split_description": paper.claimed_split_description,
        "resolved_split_policy": resolved_policy,
        "overlap_findings": overlap_findings,
        "leakage_findings": _leakage_findings(paper, profile),
        "source_family_findings": source_findings,
        "governed_eligibility_findings": _governed_eligibility_findings(paper, blockers),
        "verdict": verdict,
        "project_status": _project_status_from_verdict(verdict),
        "blockers": blockers,
        "warnings": warnings,
        "recommended_canonical_treatment": _recommended_treatment(paper, verdict, resolved_policy),
        "provenance_notes": provenance_notes,
        "named_entities": list(paper.named_entities),
        "source_families": list(paper.source_families),
        "raw_archive_fallback_required": fallback_required,
    }


def _apply_supplemental_overrides(payload: dict[str, Any], paper: PaperSpec) -> dict[str, Any]:
    evidence = _supplemental_evidence(paper)
    if not evidence:
        return payload
    payload["supplemental_evidence"] = evidence
    payload["provenance_notes"].append(
        "Supplemental non-warehouse evidence was used from paper release/repository materials to clarify split membership or split-construction logic."
    )
    if paper.paper_id == "sledzieski2021dscript":
        payload["verdict"] = "audit-useful but non-canonical"
        payload["project_status"] = _project_status_from_verdict(payload["verdict"])
        payload["blockers"] = [
            blocker
            for blocker in payload["blockers"]
            if "membership roster is absent" not in blocker
        ]
        payload["blockers"].append(
            "published D-SCRIPT split files are keyed by Ensembl/FlyBase protein identifiers that the condensed warehouse does not currently bridge to `protein_ref` or UniProt accessions"
        )
        for key in ("direct_overlap", "accession_root_overlap", "uniref_overlap"):
            payload["overlap_findings"][key]["status"] = "mapping_blocked_after_roster_recovery"
            payload["overlap_findings"][key]["notes"].append(evidence["summary"])
        payload["leakage_findings"]["notes"].append(
            "The released human-train versus species-test files make the paper split auditable, but overlap and governed-eligibility checks remain blocked until an identifier bridge is materialized."
        )
        payload["governed_eligibility_findings"]["status"] = "audit_only"
        payload["governed_eligibility_findings"]["notes"].append(
            "Because the recovered rosters are not resolvable to warehouse identifiers, the paper can inform audit comparisons but cannot become a governing training split as-is."
        )
        payload["recommended_canonical_treatment"] = (
            "Keep the paper in a `paper_faithful_external` audit lane. Build an Ensembl/FlyBase-to-UniProt bridge before comparing it with ProteoSphere-native accession- or UniRef-grouped evaluations."
        )
    elif paper.paper_id == "szymborski2022rapppid":
        payload["verdict"] = "audit-useful but non-canonical"
        payload["project_status"] = _project_status_from_verdict(payload["verdict"])
        payload["blockers"] = [
            blocker
            for blocker in payload["blockers"]
            if "membership roster is absent" not in blocker
        ]
        payload["blockers"].append(
            "published RAPPPID split artifacts are keyed by STRING/Ensembl protein identifiers that the condensed warehouse does not currently bridge to canonical `protein_ref` rows"
        )
        for key in ("direct_overlap", "accession_root_overlap", "uniref_overlap"):
            payload["overlap_findings"][key]["status"] = "mapping_blocked_after_roster_recovery"
            payload["overlap_findings"][key]["notes"].append(evidence["summary"])
        payload["leakage_findings"]["notes"].append(
            "The recovered C1/C2/C3 artifacts anchor the paper's strict unseen-protein claim, but exact overlap diagnostics are still blocked by missing Ensembl-to-UniProt bridging in best_evidence."
        )
        payload["source_family_findings"].append(
            "Recovered Zenodo artifacts show that the benchmark was packaged explicitly around STRING v11 human comparatives rather than only described narratively."
        )
        payload["governed_eligibility_findings"]["status"] = "audit_only"
        payload["governed_eligibility_findings"]["notes"].append(
            "This split is precise enough to keep as an audit lane, but not admissible as governing training evidence until its identifiers resolve cleanly into the warehouse."
        )
        payload["recommended_canonical_treatment"] = (
            "Keep the released C1/C2/C3 splits as audit lanes and rebuild any governing comparison under `uniref_grouped` once STRING/Ensembl identifiers are bridged into warehouse proteins."
        )
    elif paper.paper_id == "baranwal2022struct2graph":
        reproduction = evidence.get("reproduction") or {}
        payload["blockers"] = [
            blocker
            for blocker in payload["blockers"]
            if "membership roster is absent" not in blocker
        ]
        payload["blockers"].append(
            "the repository exposes split-construction logic, but it does not provide a saved published split roster or seed-stable assignment artifact for the exact paper run"
        )
        direct = payload["overlap_findings"]["direct_overlap"]
        direct["status"] = "reproduced_overlap_demonstrated"
        direct["notes"] = [
            evidence["summary"],
            (
                "A deterministic reproduction of the released split logic over the public interaction table "
                f"yielded {reproduction.get('shared_pdb_count', 0):,} shared PDB IDs between train and test."
            ),
            (
                "This reproduction is not claimed to be the paper's exact saved split, but it demonstrates that the released split mechanism permits direct structure reuse across partitions."
            ),
        ]
        payload["overlap_findings"]["accession_root_overlap"]["status"] = "not_needed_for_failure"
        payload["overlap_findings"]["accession_root_overlap"]["notes"].append(
            "Direct PDB reuse already fails the split under ProteoSphere logic, so accession-root grouping is a downstream rather than primary concern here."
        )
        payload["overlap_findings"]["uniref_overlap"]["status"] = "not_needed_for_failure"
        payload["overlap_findings"]["uniref_overlap"]["notes"].append(
            "UniRef grouping would be stricter still, but the reproduced direct structure overlap is already sufficient to classify the released split logic as leakage-prone."
        )
        payload["leakage_findings"]["status"] = "repo_code_and_reproduction_support_failure"
        payload["leakage_findings"]["notes"].append(
            "The released `create_examples.py` performs random example-level shuffling followed by 80/10/10 slicing, which is incompatible with accession-grouped, structure-grouped, or partner-isolated evaluation."
        )
        if reproduction:
            payload["leakage_findings"]["notes"].append(
                f"Using a deterministic reproduction seed ({reproduction['reproduction_seed']}) on the public interaction table produced {reproduction['shared_pdb_count']:,} overlapping PDB IDs across train and test."
            )
        payload["governed_eligibility_findings"]["status"] = "audit_only"
        payload["governed_eligibility_findings"]["notes"].append(
            "Because direct structure reuse is demonstrated by the released split logic itself, this paper split is not admissible for governing training evaluation."
        )
        payload["recommended_canonical_treatment"] = (
            "Do not use the paper-faithful split for training claims. Rebuild the benchmark under an accession-grouped or stronger structure-aware grouping policy before treating any performance comparison as canonical."
        )
    return payload


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Paper Split Evaluation",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Warehouse root: `{report['warehouse_root']}`",
        f"- Default view: `{report['default_view']}`",
        "",
        "## Summary Table",
        "",
        "| Paper | Verdict | Project status | Recommended policy |",
        "| --- | --- | --- | --- |",
    ]
    for row in report["papers"]:
        lines.append(
            f"| `{row['paper_id']}` | {row['verdict']} | `{row['project_status']}` | `{row['resolved_split_policy']['policy']}` |"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in report["papers"]:
        grouped[row["verdict"]].append(row)
    for verdict in (
        "faithful and acceptable as-is",
        "audit-useful but non-canonical",
        "misleading / leakage-prone",
        "incomplete because required evidence is missing",
    ):
        items = grouped.get(verdict) or []
        if not items:
            continue
        lines.extend(["", f"## {verdict}", ""])
        for row in items:
            blocker_text = "; ".join(row["blockers"][:2]) or "none"
            warning_text = "; ".join(row["warnings"][:2]) or "none"
            lines.append(
                f"- `{row['paper_id']}`: {row['recommended_canonical_treatment']} Blockers: {blocker_text}. Warnings: {warning_text}."
            )
    lines.extend(["", "## Warehouse Sufficiency Notes", ""])
    for note in report["warehouse_sufficiency_notes"]:
        lines.append(f"- {note}")
    lines.extend(["", "## Raw/Archive Fallback", ""])
    for note in report["raw_archive_fallback_notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    os.environ.setdefault("PROTEOSPHERE_WAREHOUSE_ROOT", str(DEFAULT_WAREHOUSE_ROOT))
    manifest_path = DEFAULT_WAREHOUSE_ROOT / "warehouse_manifest.json"
    source_registry_path = DEFAULT_WAREHOUSE_ROOT / "control" / "source_registry.json"
    catalog_path = DEFAULT_WAREHOUSE_ROOT / "catalog" / "reference_library.duckdb"
    manifest_payload = load_public_reference_manifest(manifest_path)
    registry_payload = load_source_registry(source_registry_path)
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        profile = _warehouse_profile(con)
        source_lookup = _source_rows(con)
    papers = [
        _apply_supplemental_overrides(
            _paper_payload(
                paper,
                source_lookup=source_lookup,
                profile=profile,
                registry_payload=registry_payload,
            ),
            paper,
        )
        for paper in PAPERS
    ]
    verdict_counts = dict(sorted(Counter(row["verdict"] for row in papers).items()))
    report = {
        "artifact_id": "paper_split_list_evaluation",
        "schema_id": "proteosphere-paper-split-list-evaluation-2026-04-13",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "warehouse_root": str(DEFAULT_WAREHOUSE_ROOT),
        "catalog_path": str(catalog_path),
        "manifest_path": str(manifest_path),
        "source_registry_path": str(source_registry_path),
        "default_view": "best_evidence",
        "manifest_default_views": manifest_payload.get("default_views", {}),
        "warehouse_profile": profile,
        "summary": {
            "paper_count": len(papers),
            "verdict_counts": verdict_counts,
            "project_status_counts": dict(sorted(Counter(row["project_status"] for row in papers).items())),
        },
        "warehouse_sufficiency_notes": [
            "The condensed warehouse does not expose a DOI-indexed paper benchmark membership surface, so paper-specific train/test rosters could not be reconstructed from best_evidence alone.",
            "IntAct and STRING are present as promoted sources, but the current best_evidence `protein_protein_edges` table only materializes `pdbbind` and `elm_interaction_domains` rows.",
            "Structure families are well represented, but interface/contact benchmark labels such as CASP-CAPRI and PPDB5 are not materialized as paper-membership tables.",
            "Mutation support exists in `protein_variants`, but named cohorts such as AB-Bind S645 and SM1124 are not represented as explicit warehouse splits.",
            "Even when paper supplements were recovered, some released rosters were keyed by Ensembl/FlyBase or other non-warehouse identifiers, so overlap and admissibility checks remain blocked until identifier bridges are materialized.",
        ],
        "raw_archive_fallback_notes": [
            "No raw/archive fallback was required for this report.",
            "If future roster reconstruction is needed, any raw/archive path must be resolved through `source_registry.json` and remain non-governing until validated.",
            "Supplemental GitHub or Zenodo release artifacts were used for selected papers, but these were treated as audit-supporting evidence rather than governing warehouse truth.",
        ],
        "papers": papers,
    }
    _write_json(DEFAULT_OUTPUT_JSON, report)
    for row in papers:
        _write_json(DEFAULT_PER_PAPER_DIR / f"{row['paper_id']}.json", row)
    DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_MD.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Wrote {DEFAULT_OUTPUT_JSON}")
    print(f"Wrote {DEFAULT_OUTPUT_MD}")
    print(f"Wrote {len(papers)} per-paper artifacts to {DEFAULT_PER_PAPER_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
