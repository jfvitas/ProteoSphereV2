from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import fitz
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_review.json"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "literature_hunt_deep_review"
PDF_PATH = OUTPUT_DIR / "proteosphere_literature_hunt_deep_review.pdf"
ASSET_MANIFEST = OUTPUT_DIR / "proteosphere_literature_hunt_deep_review.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_literature_hunt_deep_review.preview.page1.png"

STATUS_COLORS = {
    "tier1_hard_failure": "#9f1d35",
    "tier2_strong_supporting_case": "#1d4e89",
    "control_nonfailure": "#117733",
    "candidate_needs_more_recovery": "#6b7280",
}


def load_report() -> dict[str, Any]:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def sanitize(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def build_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#14213d")),
        "H1": ParagraphStyle("H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#14213d")),
        "H2": ParagraphStyle("H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#1f2937")),
        "Body": ParagraphStyle("Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.8, leading=13.0, textColor=colors.HexColor("#24303d")),
        "Small": ParagraphStyle("Small", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.4, leading=10.8, textColor=colors.HexColor("#5b6472")),
    }


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text), style)


def chart_status_counts(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["tier_counts"]
    labels = list(counts.keys())
    values = [counts[key] for key in labels]
    colors_list = [STATUS_COLORS[key] for key in labels]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.bar(labels, values, color=colors_list)
    ax.set_ylabel("Paper count")
    ax.set_title("Tier distribution")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def chart_domain_counts(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["domain_counts"]
    labels = list(counts.keys())
    values = [counts[key] for key in labels]
    fig, ax = plt.subplots(figsize=(8.2, 3.4))
    ax.bar(labels, values, color="#3a86ff")
    ax.set_ylabel("Paper count")
    ax.set_title("Domain coverage")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def callout(title: str, body: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[para(title, styles["H2"])], [para(body, styles["Body"])]], colWidths=[6.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eef7")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_document(report: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    styles = build_styles()
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    chart1 = chart_status_counts(report, TMP_DIR / "tier_counts.png")
    chart2 = chart_domain_counts(report, TMP_DIR / "domain_counts.png")
    assets: dict[str, Any] = {
        "charts": [str(chart1), str(chart2)],
        "embedded_images": [],
    }

    tier1 = [row for row in report["papers"] if row["final_status"] == "tier1_hard_failure"]
    tier2 = [row for row in report["papers"] if row["final_status"] == "tier2_strong_supporting_case"]
    controls = [row for row in report["papers"] if row["final_status"] == "control_nonfailure"]
    backlog = [row for row in report["papers"] if row["final_status"] == "candidate_needs_more_recovery"]
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in tier1:
        by_domain[row["domain"]].append(row)

    story: list[Any] = []
    story.extend(
        [
            para("Deep ProteoSphere Literature Hunt", styles["Title"]),
            Spacer(1, 0.12 * inch),
            para("Tier 1 ML Dataset Failures Across Biomolecular Interaction Papers", styles["H1"]),
            Spacer(1, 0.18 * inch),
            para(
                f"This review package identifies {len(tier1)} proof-backed Tier 1 hard failures, {len(tier2)} Tier 2 supporting cases, {len(controls)} mitigation-aware controls, and {len(backlog)} unresolved backlog papers. The core narrative is that respected peer-reviewed papers can still overstate generalization when their released split family is leaky, warm-started, or only weakly external.",
                styles["Body"],
            ),
            Spacer(1, 0.2 * inch),
            Image(str(chart1), width=6.9 * inch, height=3.0 * inch),
            Spacer(1, 0.1 * inch),
            Image(str(chart2), width=6.9 * inch, height=2.8 * inch),
            Spacer(1, 0.14 * inch),
            callout(
                "Methodological stance",
                "ProteoSphere kept the warehouse as the governing evidence surface, then escalated to official split artifacts or registry-mediated local benchmark fallback only when the condensed warehouse could not resolve the split truth directly. Papers were promoted to Tier 1 only when the split failure itself was proven and no mitigation strong enough to neutralize it was found.",
                styles,
            ),
            PageBreak(),
            para("Benchmark-Family Proofs", styles["H1"]),
            Spacer(1, 0.08 * inch),
        ]
    )

    deepdta = report["benchmark_family_proofs"]["deepdta_setting1"]
    pdbbind = report["benchmark_family_proofs"]["pdbbind_core"]
    story.extend(
        [
            callout(
                "DeepDTA setting1 family",
                f"Davis shares {deepdta['datasets']['davis']['shared_drug_count']}/{deepdta['datasets']['davis']['test_unique_drug_count']} test drugs and {deepdta['datasets']['davis']['shared_target_count']}/{deepdta['datasets']['davis']['test_unique_target_count']} test targets with training. KIBA shares {deepdta['datasets']['kiba']['shared_drug_count']}/{deepdta['datasets']['kiba']['test_unique_drug_count']} test drugs and {deepdta['datasets']['kiba']['shared_target_count']}/{deepdta['datasets']['kiba']['test_unique_target_count']} test targets with training. This is a hard warm-start failure for unseen-entity claims.",
                styles,
            ),
            Spacer(1, 0.12 * inch),
            callout(
                "PDBbind core-set family",
                f"The v2016 core set retains direct protein overlap for {pdbbind['core_sets']['v2016_core']['test_complexes_with_direct_protein_overlap']}/{pdbbind['core_sets']['v2016_core']['test_count']} test complexes against the remaining general pool, and the v2013 core set retains overlap for {pdbbind['core_sets']['v2013_core']['test_complexes_with_direct_protein_overlap']}/{pdbbind['core_sets']['v2013_core']['test_count']}. This means refined/general-to-core evaluation is not a clean unseen-protein test.",
                styles,
            ),
            Spacer(1, 0.16 * inch),
            para("Flagship Tier 1 examples", styles["H1"]),
            Spacer(1, 0.06 * inch),
        ]
    )

    for row in report["best_examples"]:
        story.extend(
            [
                para(f"{row['title']} ({row['journal']}, {row['year']})", styles["H2"]),
                para(
                    f"DOI: {row['doi']}<br/>Benchmark family: {row['benchmark_family']}<br/>Why it matters: {row['contamination_findings']['notes'][0]}",
                    styles["Body"],
                ),
                para(f"ProteoSphere treatment: {row['recommended_proteosphere_treatment']}", styles["Small"]),
                Spacer(1, 0.09 * inch),
            ]
        )
        if row["paper_id"] == "baranwal2022struct2graph":
            overlay = report["benchmark_family_proofs"]["struct2graph"].get("overlay_image_path")
            if overlay and Path(overlay).exists():
                story.append(Image(overlay, width=4.8 * inch, height=3.2 * inch))
                story.append(Spacer(1, 0.08 * inch))
                assets["embedded_images"].append(overlay)

    story.append(PageBreak())
    story.append(para("Tier 1 by Domain", styles["H1"]))
    story.append(Spacer(1, 0.08 * inch))
    for domain, rows in sorted(by_domain.items()):
        story.append(para(domain.replace("_", " ").title(), styles["H2"]))
        table_rows = [["Paper", "Benchmark", "Why Blocked"]]
        for row in sorted(rows, key=lambda item: (-item["scores"]["publication_utility"], item["paper_id"])):
            table_rows.append([row["paper_id"], row["benchmark_family"], row["contamination_findings"]["notes"][0]])
        table = Table(table_rows, colWidths=[1.55 * inch, 1.5 * inch, 3.9 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                    ("LEADING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.12 * inch))

    story.append(PageBreak())
    story.append(para("Tier 2, Controls, and Backlog", styles["H1"]))
    story.append(Spacer(1, 0.08 * inch))
    for section_title, rows in [
        ("Tier 2 supporting cases", tier2),
        ("Mitigation-aware controls", controls),
        ("Backlog needing more recovery", backlog),
    ]:
        story.append(para(section_title, styles["H2"]))
        for row in rows:
            body = row["recovered_split_evidence"][0] if row["recovered_split_evidence"] else (row["blockers"][0] if row["blockers"] else "")
            story.append(para(f"{row['title']} ({row['journal']}, {row['year']})", styles["Body"]))
            if body:
                story.append(para(body, styles["Small"]))
            story.append(Spacer(1, 0.06 * inch))
        story.append(Spacer(1, 0.06 * inch))

    story.append(PageBreak())
    story.append(para("Adoption Argument", styles["H1"]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        para(
            "The strongest contribution of this analyzer is not only that it catches spectacular mistakes like direct train/test structure reuse. It also formalizes two other high-value behaviors that the field needs: first, proving when a benchmark family is intrinsically warm-started or protein-overlapped even though it is widely reused; second, refusing to over-claim when split provenance is incomplete. That combination makes the tool useful as a reviewer, a benchmark curator, and a design aid for future datasets.",
            styles["Body"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        callout(
            "Bottom line",
            "This package is strong enough to support a review-paper narrative about why biomolecular interaction ML needs an explicit dataset analyzer. The safest publication framing is to lead with the local forensic failures, extend with the DeepDTA and PDBbind benchmark-family proofs, then use the controls to show the analyzer is fair rather than indiscriminately negative.",
            styles,
        )
    )
    return story, assets


def render_preview(pdf_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    page = document.load_page(0)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    pixmap.save(output_path)


def main() -> int:
    report = load_report()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    story, assets = build_document(report)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )
    doc.build(story)
    render_preview(PDF_PATH, PREVIEW_PATH)
    manifest = {
        "pdf_path": str(PDF_PATH),
        "preview_path": str(PREVIEW_PATH),
        **assets,
    }
    ASSET_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote PDF: {PDF_PATH}")
    print(f"Wrote asset manifest: {ASSET_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
