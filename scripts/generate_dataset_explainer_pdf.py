from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DIR = REPO_ROOT / "artifacts" / "status"
FINAL_BUNDLE_DIR = (
    REPO_ROOT
    / "data"
    / "reports"
    / "final_structured_datasets"
    / "final-structured-dataset-20260406T025042Z"
)
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
OUTPUT_PATH = OUTPUT_DIR / "proteosphere_dataset_explainer_2026-04-06.pdf"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dir_stats(path: Path) -> tuple[int, int]:
    if not path.exists():
        return (0, 0)
    file_count = 0
    total_bytes = 0
    for child in path.rglob("*"):
        if child.is_file():
            file_count += 1
            total_bytes += child.stat().st_size
    return (file_count, total_bytes)


def human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def source_status_map() -> dict[str, dict[str, Any]]:
    matrix = read_json(STATUS_DIR / "source_coverage_matrix.json")
    return {
        str(row.get("source_name") or row.get("normalized_name") or ""): row
        for row in matrix.get("matrix", [])
        if isinstance(row, dict)
    }


@dataclass(frozen=True)
class SourceSection:
    key: str
    title: str
    raw_dir: str | None
    role: str
    contains: list[str]
    ids_and_labels: list[str]
    parameters: list[str]
    used_for: list[str]
    caveats: list[str]


SOURCE_SECTIONS: list[SourceSection] = [
    SourceSection(
        key="uniprot",
        title="UniProt",
        raw_dir="uniprot",
        role="Canonical protein identity backbone",
        contains=[
            "protein-centric records rather than protein-bound complexes",
            "canonical sequence, isoforms, accession history, and curated feature annotations",
            "functional context such as catalytic activity, pathways, disease notes, and external cross-references",
        ],
        ids_and_labels=[
            "primary accession is the main join key",
            "secondary accessions are kept as aliases and replacement history",
            "isoform IDs stay distinct from the base accession",
            "features are span-aware and typed, for example Binding site, Active site, Domain, Modified residue",
        ],
        parameters=[
            "sequence length and sequence version",
            "organism and NCBI taxonomy",
            "reviewed status and protein existence evidence",
            "cross-references to PDB, Reactome, InterPro, BioGRID, IntAct, and related resources",
        ],
        used_for=[
            "anchoring every protein-bearing object to a stable protein spine",
            "feeding motif/domain extraction and variant lineage",
            "providing the safest accession-first normalization into other datasets",
        ],
        caveats=[
            "gene names are not treated as unique IDs",
            "reviewed and unreviewed entries have different quality levels",
            "replacement history and isoforms must not be flattened away",
        ],
    ),
    SourceSection(
        key="bindingdb",
        title="BindingDB",
        raw_dir="bindingdb",
        role="Primary protein-ligand assay and measurement source",
        contains=[
            "protein bound to ligands rather than proteins alone",
            "measurement-level rows with one assay result per row",
            "ligand chemistry, target identifiers, assay metadata, and publication provenance",
        ],
        ids_and_labels=[
            "BindingDB Reactant_set_id identifies a measurement interaction row",
            "BindingDB MonomerID identifies ligand monomers",
            "UniProt IDs, PDB IDs, and assay names label the target side",
            "measurement types include Ki, Kd, IC50, EC50, kon, koff",
        ],
        parameters=[
            "pH and temperature when reported",
            "affinity relation operators such as = or >",
            "SMILES, InChI, and InChIKey for chemistry normalization",
            "PMID, DOI, patents, and entry titles for provenance",
        ],
        used_for=[
            "creating the largest slice of the current structured corpus",
            "building ligand support rows plus measurement rows",
            "supplying direct supervision for affinity and assay tasks",
        ],
        caveats=[
            "target sequence text may not exactly match the assayed construct",
            "many values are sparse or censored, so missingness and inequality direction are preserved",
            "this is not used as a protein-protein interaction authority",
        ],
    ),
    SourceSection(
        key="biogrid",
        title="BioGRID",
        raw_dir="biogrid",
        role="Broad pairwise interaction evidence layer",
        contains=[
            "protein and gene interaction records, not standalone protein profiles",
            "physical and genetic interactions in the same download family",
            "publication-grounded interaction rows with interactor aliases and namespaces",
        ],
        ids_and_labels=[
            "BioGRID Interaction ID labels an evidence row",
            "BioGRID IDs, Entrez Gene IDs, UniProt accessions, and symbols label interactors",
            "experimental system type explicitly labels physical versus genetic evidence",
        ],
        parameters=[
            "throughput",
            "taxon IDs",
            "score, tags, qualifiers, and ontology terms",
            "publication source and PubMed ID",
        ],
        used_for=[
            "protein-neighborhood evidence and interaction context",
            "pairwise supervision once protein identity is normalized",
            "supporting interaction similarity and partner summaries",
        ],
        caveats=[
            "aliases and symbols are lookup aids only",
            "physical and genetic interactions must remain separate",
            "splice/background context is not fully captured",
        ],
    ),
    SourceSection(
        key="intact",
        title="IntAct",
        raw_dir="intact",
        role="Curated PSI-MI interaction and complex evidence layer",
        contains=[
            "protein-protein interaction records and native complexes",
            "participant features such as mutations, modifications, and binding regions",
            "publication-linked evidence with detection methods and interaction types",
        ],
        ids_and_labels=[
            "Interaction AC and IMEx ID label the evidence object",
            "UniProtKB and RefSeq label participants",
            "feature spans and PSI-MI terms label sub-record detail",
        ],
        parameters=[
            "interaction type",
            "detection method",
            "confidence score",
            "expanded_from_complex style lineage",
        ],
        used_for=[
            "high-confidence curated PPI evidence",
            "variant-associated interaction context",
            "native complex lineage where simple pair edges would be lossy",
        ],
        caveats=[
            "binary portal views can be projections from n-ary complexes",
            "negative interactions are out of scope",
            "gene names are not canonical keys",
        ],
    ),
    SourceSection(
        key="reactome",
        title="Reactome",
        raw_dir="reactome",
        role="Pathway and reaction context layer",
        contains=[
            "pathways, reactions, complexes, compartments, and reference entities",
            "proteins alone in pathway context plus small molecules and complex members",
            "human-first curation with inferred events for other species and some inferred human mappings",
        ],
        ids_and_labels=[
            "stable IDs and versioned stable IDs label pathways and reactions",
            "UniProt and ChEBI cross-references label proteins and small molecules",
            "event type labels pathway, reaction, complex, and related entity classes",
        ],
        parameters=[
            "species",
            "review status",
            "inputs, outputs, catalysts, and regulators",
            "pathway ancestry and compartment context",
        ],
        used_for=[
            "weak functional labels and grouping context",
            "pathway-aware split design",
            "reaction and compartment annotations around proteins",
        ],
        caveats=[
            "not treated as assay authority",
            "inferred events are contextual evidence rather than direct experimental truth",
            "entity sets and modified forms must not be collapsed into one protein row",
        ],
    ),
    SourceSection(
        key="rcsb_pdbe",
        title="RCSB PDB / PDBe / SIFTS",
        raw_dir="sifts",
        role="Experimental structure and chain-mapping authority",
        contains=[
            "protein structures, complexes, ligands, assemblies, chains, and residue spans",
            "proteins both alone and bound to ligands or partner chains",
            "entry metadata plus residue-level UniProt mappings through SIFTS",
        ],
        ids_and_labels=[
            "PDB ID labels the entry",
            "entity ID, assembly ID, and chain IDs label substructures",
            "CCD component IDs label bound chemicals",
            "UniProt mapping spans connect chains back to proteins",
        ],
        parameters=[
            "experimental method",
            "resolution",
            "assembly count and composition",
            "observed residue coverage and validation signals",
        ],
        used_for=[
            "grounding experimental structures onto the protein spine",
            "distinguishing ligand-bound structure context from purely sequence-based records",
            "carrying chain and assembly provenance into downstream examples",
        ],
        caveats=[
            "biological assembly and asymmetric unit are not interchangeable",
            "chain renumbering and missing residues must remain explicit",
            "ligands may be solvent-like, partial, or covalent",
        ],
    ),
    SourceSection(
        key="alphafold",
        title="AlphaFold DB",
        raw_dir="alphafold_db",
        role="Predicted structure companion layer",
        contains=[
            "predicted protein structures and some predicted complexes",
            "proteins alone by default, with complex predictions as a newer companion surface",
            "coordinate assets plus confidence and sequence-placement metadata",
        ],
        ids_and_labels=[
            "UniProt accession labels the protein anchor",
            "entryId and modelEntityId label the predicted structure instance",
            "sequenceChecksum and sequenceStart/End label exact sequence placement",
        ],
        parameters=[
            "average pLDDT and confidence bucket summaries",
            "PAE and MSA asset links",
            "complex confidence metrics such as ipTM and pDockQ",
            "provider ID and version lineage",
        ],
        used_for=[
            "filling structure coverage gaps when no experimental structure is available",
            "keeping a predicted geometry companion attached to the same protein",
            "supporting sequence-complete context without claiming experimental truth",
        ],
        caveats=[
            "never merged into experimental structures",
            "confidence metrics are model-quality indicators, not ground truth",
            "fragmented long proteins and complex-provider differences remain visible",
        ],
    ),
    SourceSection(
        key="interpro",
        title="InterPro / PROSITE / ELM motif systems",
        raw_dir="interpro",
        role="Domain, motif, and site enrichment layer",
        contains=[
            "protein annotations rather than whole-complex measurements",
            "families, domains, repeats, sites, profiles, and short linear motifs",
            "mostly proteins alone, with partner-aware context for some ELM motifs and structure-linked motifs",
        ],
        ids_and_labels=[
            "IPRxxxxx labels InterPro entries",
            "PSxxxxx, PDOCxxxxx, and PRUxxxxx label PROSITE motifs and rules",
            "ELME##### labels ELM motif classes",
            "all of these are span-aware on UniProt proteins",
        ],
        parameters=[
            "residue spans",
            "entry type and integrated versus unintegrated status",
            "taxonomic scope",
            "evidence count and partner/domain hints for ELM",
        ],
        used_for=[
            "compact motif/domain/site support rows in the structured corpus",
            "family-aware grouping and leakage control",
            "hard-negative construction and functional-site context",
        ],
        caveats=[
            "motif degeneracy is high and many motifs need context",
            "absence of a motif hit is not evidence of absence",
            "member-database provenance must be kept because not all signatures are equally reliable",
        ],
    ),
    SourceSection(
        key="sabio_rk",
        title="SABIO-RK",
        raw_dir="sabio_rk",
        role="Kinetics support and future enrichment lane",
        contains=[
            "kinetic-law and enzyme reaction metadata when verified",
            "currently a support surface rather than a heavily populated training layer",
            "query metadata and accession overlaps more than complete kinetic-law corpora in the current repo state",
        ],
        ids_and_labels=[
            "accession-scoped search fields and support markers",
            "planned kinetic-law IDs once verified",
        ],
        parameters=[
            "enzyme/reaction identifiers",
            "query scope metadata",
            "support status and blocker state",
        ],
        used_for=[
            "pathway_kinetics support rows",
            "future upgrade path for enzyme kinetics supervision",
        ],
        caveats=[
            "current state is partial and degraded",
            "the structured corpus marks this as support, not governing truth",
            "live kinetic-law IDs are still unverified in the current build",
        ],
    ),
]


def build_context() -> dict[str, Any]:
    source_map = source_status_map()
    final_manifest = read_json(FINAL_BUNDLE_DIR / "bundle_manifest.json")
    corpus = read_json(FINAL_BUNDLE_DIR / "seed_plus_neighbors_structured_corpus.json")
    baseline = read_json(FINAL_BUNDLE_DIR / "training_set_baseline_sidecar.json")
    multimodal = read_json(FINAL_BUNDLE_DIR / "training_set_multimodal_sidecar.json")
    packet_summary = read_json(FINAL_BUNDLE_DIR / "training_packet_summary.json")
    lite_manifest = read_json(STATUS_DIR / "lightweight_bundle_manifest.json")
    leakage_audit = read_json(STATUS_DIR / "external_dataset_leakage_audit_preview.json")
    completeness_matrix = read_json(STATUS_DIR / "training_packet_completeness_matrix_preview.json")
    source_matrix = read_json(STATUS_DIR / "source_coverage_matrix.json")

    raw_seed_root = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
    selected_source_stats: dict[str, dict[str, Any]] = {}
    for section in SOURCE_SECTIONS:
        stats_path = raw_seed_root / section.raw_dir if section.raw_dir else None
        file_count, total_bytes = dir_stats(stats_path) if stats_path else (0, 0)
        row = source_map.get(section.key, {})
        selected_source_stats[section.key] = {
            "effective_status": row.get("effective_status", "unknown"),
            "snapshot_state": row.get("snapshot_state", "unknown"),
            "present_file_count": row.get("counts", {}).get("present_file_count"),
            "present_total_bytes": row.get("counts", {}).get("present_total_bytes"),
            "repo_local_file_count": file_count,
            "repo_local_total_bytes": total_bytes,
        }

    rows = corpus.get("rows", [])
    sample_measurement = next(
        (row for row in rows if isinstance(row, dict) and row.get("row_family") == "measurement"),
        {},
    )
    sample_structure = next(
        (row for row in rows if isinstance(row, dict) and row.get("row_family") == "structure"),
        {},
    )
    sample_variant = next(
        (
            row
            for row in read_json(STATUS_DIR / "protein_variant_summary_library.json").get("records", [])
            if isinstance(row, dict)
        ),
        {},
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "final_manifest": final_manifest,
        "corpus": corpus,
        "baseline": baseline,
        "multimodal": multimodal,
        "packet_summary": packet_summary,
        "lite_manifest": lite_manifest,
        "leakage_audit": leakage_audit,
        "completeness_matrix": completeness_matrix,
        "source_matrix": source_matrix,
        "selected_source_stats": selected_source_stats,
        "sample_measurement": sample_measurement,
        "sample_structure": sample_structure,
        "sample_variant": sample_variant,
    }


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            spaceAfter=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324d"),
        ),
        "subtitle": ParagraphStyle(
            "CustomSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#45617a"),
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#17324d"),
            spaceBefore=10,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#244866"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.8,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.5,
            textColor=colors.HexColor("#4a4a4a"),
            spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.4,
            leftIndent=8,
            rightIndent=8,
            textColor=colors.HexColor("#0f3252"),
            backColor=colors.HexColor("#eef5fb"),
            borderPadding=8,
            spaceAfter=8,
        ),
    }


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def bullet_list(items: list[str], style: ParagraphStyle, bullet_color: str = "#17324d") -> list[Paragraph]:
    bullet_style = ParagraphStyle(
        "BulletBody",
        parent=style,
        leftIndent=12,
        firstLineIndent=0,
        spaceBefore=1,
        spaceAfter=3,
    )
    return [
        Paragraph(f'<font color="{bullet_color}">&#8226;</font> {item}', bullet_style)
        for item in items
    ]


def summary_table(context: dict[str, Any]) -> Table:
    corpus_summary = context["corpus"]["summary"]
    packet_summary = context["packet_summary"]["summary"]
    baseline_summary = context["baseline"]["summary"]
    leakage = context["leakage_audit"]
    source_summary = context["source_matrix"]["summary"]
    data = [
        ["Metric", "Current value"],
        ["Versioned final bundle", context["final_manifest"]["run_id"]],
        ["Corpus rows", f"{corpus_summary['row_count']:,}"],
        ["Resolved vs unresolved entities", f"{corpus_summary['resolved_entity_count']:,} resolved / {corpus_summary['unresolved_entity_count']:,} unresolved"],
        ["Seed accessions", f"{corpus_summary['seed_accession_count']:,}"],
        ["One-hop neighbors", f"{corpus_summary['one_hop_neighbor_accession_count']:,}"],
        ["Packet count", f"{packet_summary['packet_count']:,}"],
        ["Visible training candidates", f"{baseline_summary['all_visible_training_candidates_view_count']:,}"],
        ["Strict governing examples", f"{corpus_summary['strict_governing_training_view_count']:,}"],
        ["Downloaded sources in coverage registry", f"{source_summary['present_source_count']:,} present, {source_summary['partial_source_count']:,} partial, {source_summary['missing_source_count']:,} missing"],
        ["Leakage duplicates across splits", str(len(leakage.get("cross_split_duplicates") or []))],
        ["Split policy in audit", str(leakage.get("split_policy") or "unknown")],
    ]
    table = Table(data, colWidths=[2.45 * inch, 4.55 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fbff"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b5c8d8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def source_inventory_table(context: dict[str, Any]) -> Table:
    data = [["Source", "Role", "Coverage status", "Repo-local mirror"]]
    for section in SOURCE_SECTIONS:
        stats = context["selected_source_stats"][section.key]
        mirror = "not repo-local"
        if section.raw_dir:
            mirror = f"{stats['repo_local_file_count']} files / {human_bytes(stats['repo_local_total_bytes'])}"
        data.append(
            [
                section.title,
                section.role,
                f"{stats['effective_status']} ({stats['snapshot_state']})",
                mirror,
            ]
        )
    table = Table(data, colWidths=[1.35 * inch, 2.35 * inch, 1.35 * inch, 2.25 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244866")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fbff"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b5c8d8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def family_counts_table(context: dict[str, Any]) -> Table:
    family_counts = context["corpus"]["summary"]["row_family_counts"]
    meanings = {
        "measurement": "BindingDB-derived assay rows; this is the dominant current supervision family.",
        "protein": "Seed proteins and neighbor protein placeholders.",
        "interaction": "STRING/BioGRID/IntAct-style interaction context rows, currently non-governing.",
        "ligand": "Per-accession ligand support summaries.",
        "motif_site": "Motif/domain/site summaries from protein annotation layers.",
        "pathway_kinetics": "SABIO/kinetics support summaries.",
        "structure": "Experimental structure support rows.",
        "page_support": "Targeted supplemental pages to scrape or hydrate later.",
    }
    data = [["Row family", "Count", "Interpretation"]]
    for family, count in sorted(family_counts.items()):
        data.append([family, f"{count:,}", meanings.get(family, "Structured row family")])
    table = Table(data, colWidths=[1.2 * inch, 0.7 * inch, 4.8 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244866")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fbff"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b5c8d8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def packet_table(context: dict[str, Any]) -> Table:
    data = [["Accession", "Packet lane", "Present", "Missing"]]
    for row in context["packet_summary"]["rows"]:
        data.append(
            [
                row["accession"],
                row["packet_lane"],
                ", ".join(row.get("present_modalities") or []),
                ", ".join(row.get("missing_modalities") or []) or "none",
            ]
        )
    table = Table(data, colWidths=[0.9 * inch, 1.85 * inch, 2.1 * inch, 2.15 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244866")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("LEADING", (0, 0), (-1, -1), 9.4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f7fbff"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b5c8d8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def add_source_section(story: list[Any], section: SourceSection, context: dict[str, Any], styles: dict[str, ParagraphStyle]) -> None:
    stats = context["selected_source_stats"][section.key]
    present_bytes = stats.get("present_total_bytes")
    coverage_line = f"<b>Current registry state:</b> {stats['effective_status']} ({stats['snapshot_state']})."
    if isinstance(present_bytes, int):
        coverage_line += f" Registry-tracked bytes: {human_bytes(present_bytes)}."
    if section.raw_dir:
        coverage_line += f" Repo-local seed mirror: {stats['repo_local_file_count']} files, {human_bytes(stats['repo_local_total_bytes'])}."

    story.append(p(section.title, styles["h2"]))
    story.append(p(f"<b>Role:</b> {section.role}", styles["body"]))
    story.append(p(coverage_line, styles["small"]))
    story.append(p("<b>What it contains</b>", styles["body"]))
    story.extend(bullet_list(section.contains, styles["body"]))
    story.append(p("<b>How rows are labeled and keyed</b>", styles["body"]))
    story.extend(bullet_list(section.ids_and_labels, styles["body"]))
    story.append(p("<b>Important fields and parameters</b>", styles["body"]))
    story.extend(bullet_list(section.parameters, styles["body"]))
    story.append(p("<b>How it is used in ProteoSphere</b>", styles["body"]))
    story.extend(bullet_list(section.used_for, styles["body"]))
    story.append(p("<b>Main caveats</b>", styles["body"]))
    story.extend(bullet_list(section.caveats, styles["body"], bullet_color="#8a3c1a"))


def build_story(context: dict[str, Any]) -> list[Any]:
    styles = make_styles()
    story: list[Any] = []

    corpus_summary = context["corpus"]["summary"]
    lite_counts = context["lite_manifest"]["record_counts"]
    sample_measurement = context["sample_measurement"].get("payload", {})
    sample_structure = context["sample_structure"].get("payload", {})
    sample_variant = context["sample_variant"]
    leakage = context["leakage_audit"]
    raw_registries = context["corpus"]["raw_scrape_registries"]

    story.append(p("ProteoSphere V2 Dataset Explainer", styles["title"]))
    story.append(p("Downloaded datasets, merge strategy, identity resolution, variant lineage, scrape scope, and training-set quality assessment.", styles["subtitle"]))
    story.append(p(f"Generated from the repo state at <b>{datetime.fromisoformat(context['generated_at']).strftime('%Y-%m-%d %H:%M UTC')}</b>.", styles["small"]))

    story.append(p("1. Executive Summary", styles["h1"]))
    story.append(p(f"The current versioned final bundle is a <b>report-only, one-hop-bounded structured corpus</b> with <b>{corpus_summary['row_count']:,}</b> rows over <b>{corpus_summary['seed_accession_count']}</b> seed proteins and <b>{corpus_summary['one_hop_neighbor_accession_count']}</b> direct neighbors.", styles["body"]))
    story.append(p("The data model is anchored to a conservative protein spine: UniProt first, then attach measurements, structures, interactions, motifs, pathways, kinetics support, and packet artifacts without collapsing source-native evidence classes.", styles["body"]))
    story.append(summary_table(context))
    story.append(Spacer(1, 0.14 * inch))
    story.append(p("<b>Truth boundary:</b> the bundle is explicitly marked report-only and non-mutating. It is suitable for auditing and planning, but not proof that every planned modality is equally complete.", styles["callout"]))

    story.append(p("2. Downloaded Dataset Inventory", styles["h1"]))
    story.append(p("The coverage registry currently reports 48 present, 2 partial, and 3 missing source families. The table below focuses on the core sources that materially affect the current structured dataset.", styles["body"]))
    story.append(source_inventory_table(context))
    for section in SOURCE_SECTIONS:
        add_source_section(story, section, context, styles)

    story.append(PageBreak())
    story.append(p("3. How The Sources Are Combined", styles["h1"]))
    story.extend(bullet_list([
        "Seed accessions define the initial protein cohort.",
        "UniProt establishes the canonical protein identity and feature backbone.",
        "BindingDB contributes ligand-support summaries and the majority of current measurement rows.",
        "RCSB/PDBe/SIFTS contribute experimental structure rows; AlphaFold contributes parallel predicted structures.",
        "BioGRID, IntAct, and STRING-derived partner materialization add interaction context without forcing uncertain joins into governing truth.",
        "InterPro, PROSITE, ELM-style motif/domain/site signals, Reactome context, and SABIO support rows attach as enrichment layers.",
        "The resulting corpus is converted into a baseline sidecar and a multimodal sidecar that point to packet artifacts and canonical records.",
    ], styles["body"]))
    story.append(p("The row-family distribution makes the current bias obvious: this slice is overwhelmingly measurement-heavy because BindingDB is the deepest executed source in the present cohort.", styles["body"]))
    story.append(family_counts_table(context))
    story.append(p(f"<b>Example measurement row:</b> type <b>{sample_measurement.get('measurement_type', 'unknown')}</b>, target <b>{sample_measurement.get('accession', 'unknown')}</b>, assay <b>{sample_measurement.get('bindingdb_assay_name', 'unknown')}</b>, record ID <b>{sample_measurement.get('source_record_id', 'unknown')}</b>, with raw affinity text, normalization fields, assay context, ligand refs, and provenance preserved.", styles["small"]))
    story.append(p(f"<b>Example structure row:</b> PDB <b>{sample_structure.get('structure_id', 'unknown')}</b>, mapped proteins <b>{', '.join(sample_structure.get('mapped_uniprot_accessions') or [])}</b>, chains <b>{', '.join(sample_structure.get('mapped_chain_ids') or [])}</b>, method <b>{sample_structure.get('experimental_method', 'unknown')}</b>, bound components <b>{', '.join(sample_structure.get('nonpolymer_bound_components') or []) or 'none'}</b>.", styles["small"]))

    story.append(p("4. How Identity Matching Is Confirmed", styles["h1"]))
    story.extend(bullet_list([
        "Protein-bearing records normalize to UniProt accession first; secondary accessions remain aliases, not alternate primaries.",
        "Sequence version, checksum/hash, taxon, residue span, chain, and assembly context are used to validate source-to-source mappings when available.",
        "Experimental structures join via PDB plus entity/chain/assembly and SIFTS spans; AlphaFold joins via UniProt plus checksum/model identifiers.",
        "BindingDB keeps both measurement IDs and chemistry IDs, so target identity and ligand identity are validated separately.",
        "BioGRID and IntAct preserve their native interaction IDs and evidence lineage even after protein normalization.",
        "Many-to-many or ambiguous cases are left unresolved or candidate-only instead of silently coerced.",
    ], styles["body"]))
    story.append(p("Current entity-resolution preview totals 5,223 rows: 5,150 joined, 70 candidate-only, and 3 partial. That behavior is a good sign for label hygiene because it means uncertainty is preserved rather than hidden.", styles["body"]))

    story.append(p("5. Variants, Merged Records, And Split Governance", styles["h1"]))
    story.append(p("Variant handling is lineage-first. The live protein-variant summary library contains 1,874 protein_variant records grouped into 11 linked protein-spine groups.", styles["body"]))
    story.extend(bullet_list([
        "Each variant carries both protein_ref and parent_protein_ref.",
        "variant_signature and sequence_delta_signature preserve the amino-acid delta explicitly.",
        "Source-specific variant feature IDs are retained for provenance.",
        "Heavy construct metadata is deferred until a candidate is selected.",
        "Split simulation groups records by protein_spine_group, which helps keep related mutations of the same base protein in the same split.",
    ], styles["body"]))
    story.append(p(f"A representative variant record is <b>{sample_variant.get('summary_id', 'unknown')}</b>, linked to <b>{sample_variant.get('parent_protein_ref', 'unknown')}</b> with signature <b>{sample_variant.get('variant_signature', 'unknown')}</b>.", styles["small"]))
    story.append(p("For broader accession replacement or merged/split record history, the current posture is conservative. Secondary accessions, replacement history, isoform boundaries, and taxon remain visible, but the repo does not appear to implement a separate gene-merger graph that would aggressively rewrite one identity into another. Ambiguous cases stay unresolved.", styles["body"]))

    story.append(p("6. What Is Being Scraped Or Hydrated", styles["h1"]))
    story.extend(bullet_list([
        f"Interaction registry: {raw_registries['interaction']['row_count']} rows.",
        f"Structure registry: {raw_registries['structure']['row_count']} rows for structures such as {', '.join(raw_registries['structure'].get('structure_ids') or [])}.",
        f"BindingDB registry: {raw_registries['bindingdb']['profile_row_count']} ligand-support profiles and {raw_registries['bindingdb']['measurement_row_count']} measurement rows.",
        f"Motif registry: {raw_registries['motif']['row_count']} support rows.",
        f"SABIO support registry: {raw_registries['sabio']['row_count']} support rows.",
        f"Page-support registry: {raw_registries['page_support']['row_count']} targeted pages queued for supplemental hydration.",
    ], styles["body"]))
    story.append(p("This is robust for accession-scoped enrichment because every added row is labeled with governing status, training admissibility, provenance refs, payload refs, and a plain-language inclusion rationale. It is not yet robust as a claim of broad, modality-balanced coverage.", styles["body"]))
    story.append(packet_table(context))

    story.append(PageBreak())
    story.append(p("7. What The Current Final Structured Dataset Contains", styles["h1"]))
    story.extend(bullet_list([
        "seed_plus_neighbors_structured_corpus.json: row-level structured corpus",
        "seed_plus_neighbors_entity_resolution.json: join-state surface",
        "training_set_baseline_sidecar.json: baseline examples with feature pointers, labels, lineage, and split",
        "training_set_multimodal_sidecar.json: multimodal packaging surface pointing to packet artifacts and canonical records",
        "training_packet_summary.json: packet completeness by accession",
        "bundle_manifest.json: run identity, counts, file paths, readiness state, and truth-boundary notes",
    ], styles["body"]))
    story.append(p("The baseline sidecar stores protein references plus optional structure, ligand, and observation refs, then points to concrete artifacts such as FASTA, CIF, ligand JSON, and PPI evidence text. This is good for auditability because the training example retains a path back to the exact packet and source lineage.", styles["body"]))
    story.append(p(f"The compact ProteoSphere Lite bundle is even narrower: {lite_counts['proteins']} proteins, {lite_counts['protein_variants']} protein variants, {lite_counts['structures']} structures, {lite_counts['ligands']} ligands, {lite_counts['motif_annotations']} motif annotations, {lite_counts['pathway_annotations']} pathway annotations, and {lite_counts['provenance_records']} provenance records. Interaction families are still reserved there.", styles["body"]))

    story.append(p("8. How Complete And Trustworthy Is It Right Now?", styles["h1"]))
    story.extend(bullet_list([
        "7 packets are complete enough to materialize non-governing multimodal examples with sequence, structure, ligand, and PPI.",
        "2 accessions are governing-ready at the protein level but still package-blocked because a modality is absent.",
        "3 accessions remain blocked pending acquisition, including one case that currently has only sequence available.",
        "The corpus is much stronger for protein-ligand measurements than for balanced multimodal supervision.",
        "Procurement is still incomplete for some sources, especially STRING, ELM, and SABIO-RK.",
    ], styles["body"]))
    story.append(p("So the current bundle is already useful for quality auditing and small-cohort training-set construction, but it is not yet a broad, modality-balanced benchmark corpus.", styles["body"]))

    story.append(p("9. Bias, Leakage, And Data-Quality Assessment", styles["h1"]))
    story.append(p("<b>Strengths already present</b>", styles["body"]))
    story.extend(bullet_list([
        f"Cross-split duplicate audit currently reports {len(leakage.get('cross_split_duplicates') or [])} accession collisions.",
        "Variants are grouped by shared protein spine.",
        "Ambiguous joins remain unresolved instead of being forced.",
        "Source-native IDs and packet lineage are preserved for auditing.",
        "Predicted and experimental structures are explicitly separated.",
    ], styles["body"]))
    story.append(p("<b>Biases and risks that remain</b>", styles["body"]))
    story.extend(bullet_list([
        "Measurement dominance: the current row mix is overwhelmingly BindingDB-heavy.",
        "Coverage bias toward famous proteins, disease genes, model organisms, and experimentally tractable systems.",
        "Annotation bias because curated sources are much richer for popular proteins than for the long tail.",
        "Family leakage risk if split governance is only accession-level and not family-level.",
        "Construct mismatch risk because BindingDB warns target sequence text may differ from the assayed construct.",
        "Support-only context rows should not be treated as the same evidence class as measured assays or experimental structures.",
    ], styles["body"]))
    story.append(p("<b>Recommended checks before training</b>", styles["body"]))
    story.extend(bullet_list([
        "Enforce split grouping at protein-spine and family/cluster level, not just accession level.",
        "Keep measured assays, curated annotations, pathway context, predicted structures, and scrape-only support rows in separate evidence classes.",
        "Exclude candidate-only and support-only rows from gold benchmarks unless weak supervision is explicitly intended.",
        "Audit censored and missing affinity values before regression training.",
        "Measure model performance separately by completeness tier and modality coverage.",
        "Pin source snapshots and packet manifests so the same example can be rebuilt later.",
    ], styles["body"]))

    story.append(p("10. Bottom-Line Assessment", styles["h1"]))
    story.append(p("ProteoSphere already shows a careful data-engineering posture: a stable protein spine, conservative join rules, explicit truth boundaries, packet-level provenance, and real leakage controls. The main weakness right now is imbalance, not lack of rigor. The live slice is much more mature for protein-ligand measurements than for a balanced multimodal benchmark.", styles["body"]))
    story.append(p("For auditing training-set quality, this bundle is already valuable because it clearly distinguishes governing rows, support-only rows, candidate rows, blocked accessions, and incomplete modalities. For a larger training push, the next priority should be finishing missing acquisitions, hardening family-level leakage controls, and rebalancing the evidence mix.", styles["body"]))

    return story


def add_page_number(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7f90"))
    canvas.drawRightString(7.25 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.drawString(0.75 * inch, 0.45 * inch, "ProteoSphere V2 dataset explainer")
    canvas.restoreState()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    context = build_context()
    story = build_story(context)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="ProteoSphere V2 Dataset Explainer",
        author="OpenAI Codex",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
