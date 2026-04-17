from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
DOC_DIR = REPO_ROOT / "docs" / "manuscripts" / "proteosphere_paper"
ASSET_DIR = OUTPUT_DIR / "proteosphere_audit_supplement_assets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOC_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUTPUT_DIR / "proteosphere_audit_supplement_catalog.pdf"
MD_PATH = DOC_DIR / "proteosphere_audit_supplement_catalog.md"
ASSET_MANIFEST = OUTPUT_DIR / "proteosphere_audit_supplement_catalog.assets.json"

DEEP_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_review"
RECENT_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion"
DEEP_REPORT = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_review.json"
RECENT_REPORT = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion.json"
MASTER_SUMMARY = REPO_ROOT / "artifacts" / "status" / "literature_hunt_tier1_master_summary.json"

DTA_PROOF = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_proofs" / "dta_setting1_family_audit.json"
PDBBIND_PROOF = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_proofs" / "pdbbind_core_family_audit.json"
ATTENTION_PROOF = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion_proofs" / "attentiondta_random_cv_family_audit.json"
STRUCT2GRAPH_PROOF = REPO_ROOT / "artifacts" / "status" / "struct2graph_overlap" / "struct2graph_reproduced_split_overlap.json"
D2CP_PROOF = REPO_ROOT / "artifacts" / "status" / "paper_d2cp05644e_detailed_audit.json"
STRUCT2GRAPH_IMAGE = REPO_ROOT / "artifacts" / "status" / "struct2graph_overlap" / "4EQ6_train_test_overlay.png"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def ptext(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "")
    )


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(ptext(text), style)


def make_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "Title",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=colors.HexColor("#102542"),
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#102542"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=13.8,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=7,
            spaceAfter=4,
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.2,
            leading=12.2,
            textColor=colors.HexColor("#334155"),
            spaceBefore=5,
            spaceAfter=3,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=11.8,
            textColor=colors.HexColor("#24303d"),
            spaceAfter=4,
        ),
        "Small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.0,
            leading=9.8,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=3,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.9,
            leading=11.5,
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=0,
            textColor=colors.HexColor("#24303d"),
            spaceAfter=2,
        ),
        "Caption": ParagraphStyle(
            "Caption",
            parent=sample["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.0,
            leading=9.8,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=4,
        ),
    }


def table(data: list[list[str]], widths: list[float]) -> LongTable:
    sample = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "THead",
        parent=sample["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.0,
        leading=8.4,
        textColor=colors.HexColor("#102542"),
    )
    body_style = ParagraphStyle(
        "TBody",
        parent=sample["BodyText"],
        fontName="Helvetica",
        fontSize=6.9,
        leading=8.3,
        textColor=colors.HexColor("#24303d"),
    )
    rows: list[list[Any]] = []
    for idx, row in enumerate(data):
        style = header_style if idx == 0 else body_style
        rows.append([p(cell, style) if isinstance(cell, str) else cell for cell in row])
    tbl = LongTable(rows, colWidths=[w * inch for w in widths], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102542")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return tbl


def flatten_notes(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        notes = []
        for key, item in value.items():
            if isinstance(item, list):
                joined = "; ".join(str(x) for x in item if str(x).strip())
                if joined:
                    notes.append(f"{key}: {joined}")
            elif str(item).strip():
                notes.append(f"{key}: {item}")
        return notes
    return [str(value)]


def mitigation_text(value: Any) -> str:
    if isinstance(value, dict):
        status = str(value.get("status") or "").strip()
        notes = flatten_notes(value.get("notes"))
        text = status.replace("_", " ") if status else ""
        if notes:
            note_text = " ".join(notes)
            return f"{text}. {note_text}".strip(". ")
        return text or "No detailed mitigation audit note preserved."
    return str(value)


def load_papers() -> list[dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for directory in (DEEP_DIR, RECENT_DIR):
        for path in sorted(directory.glob("*.json")):
            payload = read_json(path)
            payload["_artifact_path"] = rel(path)
            items[payload["paper_id"]] = payload
    return list(items.values())


def status_order(status: str) -> int:
    return {
        "tier1_hard_failure": 0,
        "tier2_strong_supporting_case": 1,
        "control_nonfailure": 2,
        "candidate_needs_more_recovery": 3,
    }.get(status, 9)


def family_proof_lookup() -> dict[str, dict[str, Any]]:
    return {
        "deepdta_setting1_family": read_json(DTA_PROOF),
        "pdbbind_core_family": read_json(PDBBIND_PROOF),
        "attentiondta_random_row_cv": read_json(ATTENTION_PROOF),
        "struct2graph_public_pairs": read_json(STRUCT2GRAPH_PROOF),
        "prodigy78_plus_external_panels": read_json(D2CP_PROOF),
    }


def manuscript_role(status: str) -> str:
    mapping = {
        "tier1_hard_failure": "Flagship or primary proof-set paper",
        "tier2_strong_supporting_case": "Supporting breadth paper retained below Tier 1",
        "control_nonfailure": "Fairness control showing that ProteoSphere does not over-flag",
        "candidate_needs_more_recovery": "Transparency-only recovery backlog entry",
    }
    return mapping.get(status, "Reviewed paper")


def family_note(paper: dict[str, Any], proofs: dict[str, dict[str, Any]]) -> list[str]:
    family = str(paper.get("benchmark_family") or "")
    out: list[str] = []
    if family == "deepdta_setting1_family":
        proof = proofs[family]
        davis = proof["datasets"]["davis"]
        kiba = proof["datasets"]["kiba"]
        out.append(
            "Underlying family proof: DeepDTA setting1 releases warm-start folds. "
            f"Davis reuses {davis['shared_drug_count']}/{davis['test_unique_drug_count']} test drugs and "
            f"{davis['shared_target_count']}/{davis['test_unique_target_count']} test targets across train/test."
        )
        out.append(
            f"KIBA reuses {kiba['shared_drug_count']}/{kiba['test_unique_drug_count']} test drugs and "
            f"{kiba['shared_target_count']}/{kiba['test_unique_target_count']} test targets."
        )
        out.append(
            "Sample shared entity indices preserved in the proof artifact: "
            f"Davis drugs {davis['sample_shared_drug_indices']}, Davis targets {davis['sample_shared_target_indices']}, "
            f"KIBA drugs {kiba['sample_shared_drug_indices']}, KIBA targets {kiba['sample_shared_target_indices']}."
        )
        out.append(f"Benchmark-family proof artifact: {rel(DTA_PROOF)}")
    elif family == "pdbbind_core_family":
        proof = proofs[family]
        v2016 = proof["core_sets"]["v2016_core"]
        v2013 = proof["core_sets"]["v2013_core"]
        out.append(
            "Underlying family proof: the PDBbind core-set evaluation lineage preserves direct protein overlap against the training pool."
        )
        out.append(
            f"v2016 core: {v2016['test_complexes_with_direct_protein_overlap']}/{v2016['test_count']} test complexes retain direct protein overlap with training."
        )
        out.append(
            f"v2013 core: {v2013['test_complexes_with_direct_protein_overlap']}/{v2013['test_count']} test complexes retain direct protein overlap with training."
        )
        sample_bits = []
        for sample in v2016["sample_overlaps"][:3]:
            sample_bits.append(
                f"{sample['test_pdb_id'].upper()} shares {', '.join(sample['shared_accessions'])} with train-side examples "
                f"{', '.join(item.upper() for item in sample['sample_train_ids'][:4])}"
            )
        out.append("Illustrative v2016 conflicts: " + "; ".join(sample_bits) + ".")
        out.append(f"Benchmark-family proof artifact: {rel(PDBBIND_PROOF)}")
    elif family == "attentiondta_random_row_cv":
        proof = proofs[family]
        davis = proof["datasets"]["davis"]
        kiba = proof["datasets"]["kiba"]
        metz = proof["datasets"]["metz"]
        out.append(
            "Underlying family proof: AttentionDTA shuffles full interaction rows and slices folds by row index, preserving drug and target reuse across folds."
        )
        out.append(
            f"Davis: {davis['shared_drug_count']}/{davis['test_unique_drug_count']} test drugs and "
            f"{davis['shared_target_count']}/{davis['test_unique_target_count']} test targets also appear in training."
        )
        out.append(
            f"KIBA: {kiba['shared_drug_count']}/{kiba['test_unique_drug_count']} test drugs and "
            f"{kiba['shared_target_count']}/{kiba['test_unique_target_count']} test targets also appear in training."
        )
        out.append(
            f"Metz: {metz['shared_drug_count']}/{metz['test_unique_drug_count']} test drugs and "
            f"{metz['shared_target_count']}/{metz['test_unique_target_count']} test targets also appear in training."
        )
        out.append(f"Benchmark-family proof artifact: {rel(ATTENTION_PROOF)}")
    return out


def d2cp_lines() -> list[str]:
    proof = read_json(D2CP_PROOF)
    lines: list[str] = []
    mapping = [
        ("benchmark_vs_pdbbind50", "PDBbind-derived 50-complex panel"),
        ("benchmark_vs_nanobody47", "Nanobody 47-complex panel"),
        ("benchmark_vs_metadynamics19", "Metadynamics 19-complex panel"),
    ]
    for key, label in mapping:
        section = proof[key]
        summary = section["assessment"]["summary"]
        lines.append(
            f"{label}: direct protein overlap {summary['direct_protein_overlap_count']}, accession-root overlap {summary['accession_root_overlap_count']}, "
            f"UniRef100 overlap {summary['uniref100_cluster_overlap_count']}, shared partner overlap {summary['shared_partner_overlap_count']}, "
            f"flagged structure-pair count {summary['flagged_structure_pair_count']}, verdict {summary['verdict']}."
        )
        overlap_map = section.get("direct_overlap_map") or []
        if overlap_map:
            details = []
            for row in overlap_map:
                details.append(
                    f"{row['name']} ({row['accession']}): train {', '.join(row['train_structures'])}; test {', '.join(row['test_structures'])}"
                )
            lines.append("Exact direct-overlap map: " + " | ".join(details) + ".")
    lines.append(f"Detailed flagship proof artifact: {rel(D2CP_PROOF)}")
    return lines


def struct2graph_lines() -> list[str]:
    proof = read_json(STRUCT2GRAPH_PROOF)
    sample = ", ".join(proof["shared_pdb_sample"][:25])
    chains = []
    for row in proof["highlight_structure"]["structure_unit_rows"]:
        chains.append(f"chain {row['chain_id']} -> {row['protein_ref']}")
    return [
        f"ProteoSphere reproduced the released example-shuffle split logic with seed {proof['reproduction_seed']} and found {proof['shared_pdb_count']} shared PDB IDs between train and test.",
        f"Representative shared-PDB sample: {sample}.",
        f"Highlight structure {proof['highlight_structure']['structure_id']} was reused in {proof['highlight_structure']['train_example_count']} reproduced train examples and {proof['highlight_structure']['test_example_count']} reproduced test examples.",
        "Highlight chain grounding: " + "; ".join(chains) + ".",
        f"Detailed flagship proof artifact: {rel(STRUCT2GRAPH_PROOF)}",
    ]


def corpus_summary_table(papers: list[dict[str, Any]]) -> list[list[str]]:
    rows = [["Paper", "Year", "Status", "Benchmark family", "Main manuscript role"]]
    for paper in sorted(papers, key=lambda x: (status_order(str(x.get("final_status") or "")), -int(x.get("year") or 0), str(x.get("title") or ""))):
        rows.append(
            [
                f"{paper.get('title')} ({paper.get('paper_id')})",
                str(paper.get("year") or ""),
                str(paper.get("final_status") or ""),
                str(paper.get("benchmark_family") or ""),
                manuscript_role(str(paper.get("final_status") or "")),
            ]
        )
    return rows


def family_index_table(papers: list[dict[str, Any]]) -> list[list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for paper in papers:
        grouped[str(paper.get("benchmark_family") or "unassigned")].append(str(paper.get("paper_id")))
    rows = [["Benchmark family", "Reviewed papers in this supplement"]]
    for family, paper_ids in sorted(grouped.items()):
        rows.append([family, ", ".join(sorted(paper_ids))])
    return rows


def paper_detail_lines(paper: dict[str, Any], proofs: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    links = [str(item) for item in paper.get("official_evidence_links") or []]
    if links:
        lines.append("Official evidence links: " + " | ".join(links))
    lines.append(f"Claimed split or evaluation design: {paper.get('claimed_split_description') or 'Not preserved.'}")
    recovered = flatten_notes(paper.get("recovered_split_evidence"))
    if recovered:
        lines.append("Recovered evidence: " + " ".join(recovered))
    mitigation_claims = flatten_notes(paper.get("mitigation_claims"))
    if mitigation_claims:
        lines.append("What the paper said it did about bias, leakage, or split safety: " + " ".join(mitigation_claims))
    else:
        lines.append("What the paper said it did about bias, leakage, or split safety: no explicit mitigation claim was recovered.")
    lines.append("ProteoSphere mitigation reading: " + mitigation_text(paper.get("mitigation_audit_result")))
    failure_class = paper.get("exact_failure_class")
    if isinstance(failure_class, list):
        lines.append("Exact failure class: " + ", ".join(str(item) for item in failure_class))
    elif str(failure_class).strip():
        lines.append("Exact failure class: " + str(failure_class))
    overlap = paper.get("overlap_findings") or {}
    if overlap:
        overlap_notes = flatten_notes(overlap.get("notes"))
        if overlap_notes:
            lines.append("Overlap findings: " + " ".join(overlap_notes))
        extra_parts = []
        for key, value in overlap.items():
            if key == "notes":
                continue
            if isinstance(value, dict):
                scalar_bits = []
                for inner_key, inner_value in value.items():
                    if isinstance(inner_value, (str, int, float, bool)):
                        scalar_bits.append(f"{inner_key}={inner_value}")
                if scalar_bits:
                    extra_parts.append(f"{key}: {', '.join(scalar_bits)}")
            elif isinstance(value, list):
                scalar_items = [str(item) for item in value if isinstance(item, (str, int, float, bool))]
                if scalar_items:
                    extra_parts.append(f"{key}: {', '.join(scalar_items[:12])}")
            elif value not in ("", None):
                extra_parts.append(f"{key}: {value}")
        if extra_parts:
            lines.append("Overlap detail fields: " + " | ".join(extra_parts))
    contamination = paper.get("contamination_findings") or {}
    cont_notes = flatten_notes(contamination.get("notes")) if isinstance(contamination, dict) else flatten_notes(contamination)
    if cont_notes:
        lines.append("Contamination or control reading: " + " ".join(cont_notes))
    block = flatten_notes(paper.get("blockers"))
    if block:
        lines.append("Blockers or remaining uncertainties: " + " ".join(block))
    lines.extend(family_note(paper, proofs))
    if paper["paper_id"] == "baranwal2022struct2graph":
        lines.extend(struct2graph_lines())
    if paper["paper_id"] == "d2cp05644e_2023":
        lines.extend(d2cp_lines())
    lines.append("Recommended ProteoSphere treatment: " + str(paper.get("recommended_proteosphere_treatment") or "Not recorded."))
    provenance = flatten_notes(paper.get("provenance_notes"))
    if provenance:
        lines.append("Provenance notes: " + " ".join(provenance))
    lines.append(
        "Raw or archive fallback required in this paper-level artifact: "
        + ("yes" if bool(paper.get("raw_archive_fallback_required")) else "no")
        + "."
    )
    lines.append("Primary per-paper artifact: " + str(paper.get("_artifact_path") or ""))
    return lines


def write_markdown(
    papers: list[dict[str, Any]],
    summary: dict[str, Any],
    proofs: dict[str, dict[str, Any]],
) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        grouped[str(paper.get("final_status") or "unknown")].append(paper)

    lines: list[str] = []
    lines.append("# ProteoSphere Supplementary Literature Audit Catalog")
    lines.append("")
    lines.append(
        "This supplement backs the manuscript's literature-hunt claims with the full reviewed manuscript corpus."
    )
    lines.append("")
    lines.append("## Corpus scope")
    lines.append("")
    lines.append(
        f"- Reviewed manuscript corpus: `{summary['candidate_count']}` papers"
    )
    for status, count in summary["tier_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.append("")
    lines.append("## Benchmark-family proof artifacts")
    lines.append("")
    lines.append(f"- DeepDTA setting1 family: `{rel(DTA_PROOF)}`")
    lines.append(f"- PDBbind core family: `{rel(PDBBIND_PROOF)}`")
    lines.append(f"- AttentionDTA random-row CV: `{rel(ATTENTION_PROOF)}`")
    lines.append(f"- Struct2Graph direct reuse: `{rel(STRUCT2GRAPH_PROOF)}`")
    lines.append(f"- D2CP05644E external-panel audit: `{rel(D2CP_PROOF)}`")
    lines.append("")
    for status in (
        "tier1_hard_failure",
        "tier2_strong_supporting_case",
        "control_nonfailure",
        "candidate_needs_more_recovery",
    ):
        entries = sorted(grouped.get(status, []), key=lambda x: (-int(x.get("year") or 0), str(x.get("title") or "")))
        if not entries:
            continue
        lines.append(f"## {status}")
        lines.append("")
        for paper in entries:
            lines.append(f"### {paper['title']} ({paper['paper_id']})")
            lines.append("")
            lines.append(f"- DOI: `{paper.get('doi','')}`")
            lines.append(f"- Journal/year: `{paper.get('journal','')}` / `{paper.get('year','')}`")
            lines.append(f"- Benchmark family: `{paper.get('benchmark_family','')}`")
            lines.append(f"- Manuscript role: `{manuscript_role(str(paper.get('final_status') or ''))}`")
            for item in paper_detail_lines(paper, proofs):
                lines.append(f"- {item}")
            lines.append("")
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_story(
    papers: list[dict[str, Any]],
    summary: dict[str, Any],
    proofs: dict[str, dict[str, Any]],
) -> list[Any]:
    s = make_styles()
    story: list[Any] = []

    def bullet(text: str) -> None:
        story.append(p("- " + text, s["Bullet"]))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        grouped[str(paper.get("final_status") or "unknown")].append(paper)

    story.append(p("ProteoSphere Supplementary Literature Audit Catalog", s["Title"]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        p(
            "This supplement is intended to make the manuscript's literature-hunt claims fully inspectable. It covers the full reviewed manuscript corpus, preserves the benchmark-family proofs that underlie many later-paper calls, and records what each paper said about split quality or mitigation alongside what ProteoSphere found.",
            s["Body"],
        )
    )
    story.append(p("1. Scope and reading guide", s["H1"]))
    bullet(
        f"Manuscript-reviewed corpus size: {summary['candidate_count']} papers."
    )
    for status, count in summary["tier_counts"].items():
        bullet(f"{status}: {count} papers.")
    bullet(
        "Tier 1 means proof-backed hard failure under ProteoSphere logic; Tier 2 means strong supporting case held below Tier 1; control means mitigation-aware or materially better-designed comparison case; recovery backlog means reviewed but not promoted."
    )
    bullet(
        "Where a later paper inherited a previously released benchmark family, the supplement cites both the later paper and the earlier family-level proof so that the manuscript does not rely on any unbacked summarized claim."
    )
    bullet(
        "All interpretations are intentionally constructive. A flagged benchmark claim is not treated as proof that a paper is scientifically worthless; it is treated as evidence that the paper's evaluation scope is narrower than the headline framing may imply."
    )

    story.append(Spacer(1, 0.05 * inch))
    story.append(table(corpus_summary_table(papers), [2.2, 0.55, 1.2, 1.3, 1.65]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(table(family_index_table(papers), [1.9, 5.0]))
    story.append(PageBreak())

    story.append(p("2. Benchmark-family and flagship proof sections", s["H1"]))
    story.append(
        p(
            "These sections preserve the exact proof objects that are reused throughout the per-paper catalog. When a later paper inherits one of these benchmark families without adding a successful mitigation layer, the per-paper entry references the relevant proof below rather than pretending that the later paper shipped a brand-new independent split.",
            s["Body"],
        )
    )

    story.append(p("2.1 Struct2Graph direct train/test structure reuse", s["H2"]))
    for line in struct2graph_lines():
        bullet(line)
    if STRUCT2GRAPH_IMAGE.exists():
        story.append(Image(str(STRUCT2GRAPH_IMAGE), width=5.5 * inch, height=3.25 * inch))
        story.append(p("Struct2Graph overlay generated by ProteoSphere from the reused 4EQ6 structure.", s["Caption"]))

    story.append(p("2.2 D2CP05644E external-panel contamination audit", s["H2"]))
    for line in d2cp_lines():
        bullet(line)

    story.append(p("2.3 DeepDTA setting1 warm-start family", s["H2"]))
    for line in family_note({"benchmark_family": "deepdta_setting1_family"}, proofs):
        bullet(line)

    story.append(p("2.4 PDBbind core-family external-evaluation problem", s["H2"]))
    for line in family_note({"benchmark_family": "pdbbind_core_family"}, proofs):
        bullet(line)

    story.append(p("2.5 AttentionDTA row-level random CV", s["H2"]))
    for line in family_note({"benchmark_family": "attentiondta_random_row_cv"}, proofs):
        bullet(line)

    for status in (
        "tier1_hard_failure",
        "tier2_strong_supporting_case",
        "control_nonfailure",
        "candidate_needs_more_recovery",
    ):
        entries = sorted(grouped.get(status, []), key=lambda x: (-int(x.get("year") or 0), str(x.get("title") or "")))
        if not entries:
            continue
        story.append(PageBreak())
        story.append(p(f"3. {status}", s["H1"]))
        story.append(
            p(
                "Each entry below states what the paper claimed, what official or recovered evidence was used, whether the authors described any mitigation, what ProteoSphere concluded, and what exact concrete conflicts were preserved in the current evidence bundle.",
                s["Body"],
            )
        )
        for idx, paper in enumerate(entries, start=1):
            story.append(
                p(
                    f"3.{idx} {paper['title']} ({paper['paper_id']})",
                    s["H2"],
                )
            )
            story.append(
                p(
                    f"Citation context: {paper.get('journal','')} ({paper.get('year','')}), DOI {paper.get('doi','')}. "
                    f"Domain={paper.get('domain','')}; task family={paper.get('task_family','')}; benchmark family={paper.get('benchmark_family','')}; manuscript role={manuscript_role(str(paper.get('final_status') or ''))}.",
                    s["Body"],
                )
            )
            for line in paper_detail_lines(paper, proofs):
                bullet(line)
            story.append(Spacer(1, 0.06 * inch))

    story.append(PageBreak())
    story.append(p("4. Closing note on transparency", s["H1"]))
    story.append(
        p(
            "The manuscript intentionally separates hard failures, supporting cases, controls, and unresolved recovery cases because the supplement shows that these categories are genuinely different. Some papers are code-proven split failures. Some inherit benchmark families that are already unsafe for the claim being made. Some explicitly attempt to mitigate leakage and therefore serve as fairness controls. Others remain under-recovered and are included here precisely so that the manuscript does not quietly blur suspicion into proof.",
            s["Body"],
        )
    )
    return story


def main() -> None:
    papers = load_papers()
    papers.sort(key=lambda x: (status_order(str(x.get("final_status") or "")), -int(x.get("year") or 0), str(x.get("title") or "")))

    recent = read_json(RECENT_REPORT)
    combined_summary = recent["combined_summary"]
    proofs = family_proof_lookup()

    write_markdown(papers, combined_summary, proofs)

    story = build_story(papers, combined_summary, proofs)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.68 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
    )
    doc.build(story)

    manifest = {
        "pdf": str(PDF_PATH),
        "markdown": str(MD_PATH),
        "source_reports": [
            rel(DEEP_REPORT),
            rel(RECENT_REPORT),
            rel(MASTER_SUMMARY),
        ],
        "proof_artifacts": [
            rel(DTA_PROOF),
            rel(PDBBIND_PROOF),
            rel(ATTENTION_PROOF),
            rel(STRUCT2GRAPH_PROOF),
            rel(D2CP_PROOF),
        ],
        "paper_count": len(papers),
    }
    ASSET_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
