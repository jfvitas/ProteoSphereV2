from __future__ import annotations

import json
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz
import matplotlib.pyplot as plt
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = REPO_ROOT / "artifacts" / "status" / "literature_hunt_confirmed_dataset_issues.json"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "literature_hunt_review"
ASSET_DIR = TMP_DIR / "paper_assets"
PDF_PATH = OUTPUT_DIR / "proteosphere_literature_hunt_review.pdf"
MANIFEST_PATH = OUTPUT_DIR / "proteosphere_literature_hunt_review.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_literature_hunt_review.preview.page1.png"

STATUS_ORDER = [
    "confirmed_red_flag",
    "confirmed_blocked_external",
    "confirmed_audit_only_noncanonical",
    "candidate_needs_more_recovery",
]

STATUS_TITLES = {
    "confirmed_red_flag": "Confirmed Red Flags",
    "confirmed_blocked_external": "Blocked External Validation",
    "confirmed_audit_only_noncanonical": "Confirmed Audit-Only / Non-Canonical Cases",
    "candidate_needs_more_recovery": "Candidate Cases Needing More Recovery",
}

STATUS_COLORS = {
    "confirmed_red_flag": "#9f1d35",
    "confirmed_blocked_external": "#bf5b17",
    "confirmed_audit_only_noncanonical": "#1d4e89",
    "candidate_needs_more_recovery": "#6b7280",
}

CLUSTER_TITLES = {
    "direct_split_failure": "Direct split failure",
    "blocked_external_validation": "Blocked external validation",
    "benchmark_family_dependence": "Benchmark-family dependence",
    "legacy_benchmark_dependence": "Legacy benchmark dependence",
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


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text), style)


def build_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1f2d3d"),
            spaceAfter=12,
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#14213d"),
            spaceAfter=8,
        ),
        "SubTitle": ParagraphStyle(
            "SubTitle",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15.5,
            textColor=colors.HexColor("#1f2d3d"),
            spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=10.2,
            leading=13.6,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#28323f"),
        ),
        "BodySmall": ParagraphStyle(
            "BodySmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.4,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#586174"),
        ),
        "Label": ParagraphStyle(
            "Label",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.3,
            leading=11.5,
            textColor=colors.HexColor("#0f172a"),
        ),
        "Caption": ParagraphStyle(
            "Caption",
            parent=sample["Italic"],
            fontName="Helvetica-Oblique",
            fontSize=8.2,
            leading=10.5,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#667085"),
        ),
    }


def make_bullet_list(items: list[str], style: ParagraphStyle) -> list[Any]:
    flowables: list[Any] = []
    for item in items:
        flowables.append(Paragraph(f'&bull; {sanitize(item)}', style))
        flowables.append(Spacer(1, 0.04 * inch))
    return flowables


def callout_box(title: str, body: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[paragraph(title, styles["Label"])], [paragraph(body, styles["Body"])]],
        colWidths=[6.85 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7f9fc")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#c7d2e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(font_name, size=size)
    except OSError:
        return ImageFont.load_default()


def build_paper_card(row: dict[str, Any]) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ASSET_DIR / f"{row['paper_id']}.png"
    width, height = 1100, 760
    image = PILImage.new("RGB", (width, height), "#f8fafc")
    draw = ImageDraw.Draw(image)

    color = STATUS_COLORS[row["final_status"]]
    draw.rectangle([(0, 0), (width, height)], fill="#f8fafc")
    draw.rounded_rectangle([(28, 28), (width - 28, height - 28)], radius=26, outline=color, width=8, fill="#ffffff")
    draw.rounded_rectangle([(60, 60), (width - 60, 140)], radius=18, fill=color)

    draw.text((84, 82), row["journal"], font=_font(34, bold=True), fill="#ffffff")
    draw.text((width - 360, 82), str(row["year"]), font=_font(34, bold=True), fill="#ffffff")

    y = 185
    for line in textwrap.wrap(row["title"], width=34)[:4]:
        draw.text((82, y), line, font=_font(42, bold=True), fill="#14213d")
        y += 58

    y += 10
    for line in textwrap.wrap(f"Status: {row['final_status'].replace('_', ' ')}", width=48)[:2]:
        draw.text((82, y), line, font=_font(28, bold=False), fill="#334155")
        y += 38

    for line in textwrap.wrap(f"Benchmark family: {row['benchmark_family']}", width=52)[:2]:
        draw.text((82, y), line, font=_font(28, bold=False), fill="#334155")
        y += 38

    y += 14
    for line in textwrap.wrap(row["confirmed_issue_summary"], width=56)[:5]:
        draw.text((82, y), line, font=_font(25, bold=False), fill="#475569")
        y += 33

    image.save(output_path)
    return output_path


def create_status_chart(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["status_counts"]
    labels = [STATUS_TITLES[key] for key in STATUS_ORDER if key in counts]
    values = [counts[key] for key in STATUS_ORDER if key in counts]
    colors_list = [STATUS_COLORS[key] for key in STATUS_ORDER if key in counts]
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    ax.bar(labels, values, color=colors_list)
    ax.set_ylabel("Paper count")
    ax.set_title("Confirmed literature-hunt outcomes", fontsize=13)
    ax.set_ylim(0, max(values) + 2)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def create_cluster_chart(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["issue_cluster_counts"]
    labels = [CLUSTER_TITLES.get(key, key.replace("_", " ")) for key in counts]
    values = [counts[key] for key in counts]
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    ax.bar(labels, values, color="#3a86ff")
    ax.set_ylabel("Paper count")
    ax.set_title("Failure modes in the literature hunt", fontsize=13)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def create_benchmark_chart(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(report["summary"]["benchmark_family_counts"])
    top_items = counts.most_common(6)
    labels = [label for label, _ in top_items]
    values = [value for _, value in top_items]
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    ax.barh(labels, values, color="#577590")
    ax.set_xlabel("Paper count")
    ax.set_title("Most reused benchmark families", fontsize=13)
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)
    return output_path


def render_pdf_first_page(pdf_path: Path, output_path: Path) -> None:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(output_path)
    doc.close()


def build_assets(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for row in rows:
        card_path = build_paper_card(row)
        assets[row["paper_id"]] = {
            "image_path": str(card_path),
            "image_kind": "citation_card",
            "image_source": row["doi"],
        }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(assets, indent=2) + "\n", encoding="utf-8")
    return assets


def build_story(report: dict[str, Any], assets: dict[str, dict[str, Any]]) -> list[Any]:
    styles = build_styles()
    rows = sorted(report["papers"], key=lambda item: (-item["publication_score"], item["paper_id"]))
    status_chart = create_status_chart(report, TMP_DIR / "status_chart.png")
    cluster_chart = create_cluster_chart(report, TMP_DIR / "cluster_chart.png")
    benchmark_chart = create_benchmark_chart(report, TMP_DIR / "benchmark_chart.png")

    story: list[Any] = []
    story.extend(
        [
            Spacer(1, 0.32 * inch),
            paragraph("ProteoSphere Literature Hunt for Dataset-Quality Failures", styles["CoverTitle"]),
            paragraph(
                "A warehouse-first review of peer-reviewed protein papers whose train/test design shows leakage, blocked external validation, or benchmark-family dependence.",
                styles["Body"],
            ),
            Spacer(1, 0.14 * inch),
            callout_box(
                "What this report is trying to prove",
                (
                    "The point is not that every paper here is bad science. The point is that respected, reproducible, peer-reviewed papers can still make weaker dataset claims than they appear to make. "
                    "ProteoSphere turns those differences into explicit review buckets instead of treating all published benchmarks as equally trustworthy."
                ),
                styles,
            ),
            Spacer(1, 0.16 * inch),
            paragraph(
                f"Primary warehouse root: {report['warehouse_root']}. Default logical view: {report['default_view']}. "
                "The hunt used the local library and existing ProteoSphere audit artifacts first, then added web-verified benchmark-family candidates where the library could confirm dependence but not yet mirror the exact roster.",
                styles["BodySmall"],
            ),
            Spacer(1, 0.18 * inch),
            Image(str(status_chart), width=6.9 * inch, height=3.2 * inch),
            Spacer(1, 0.06 * inch),
            paragraph("Figure 1. Final status distribution across the literature-hunt candidate set.", styles["Caption"]),
            Spacer(1, 0.10 * inch),
            Image(str(cluster_chart), width=6.9 * inch, height=3.2 * inch),
            Spacer(1, 0.06 * inch),
            paragraph("Figure 2. Failure modes captured by the hunt.", styles["Caption"]),
            Spacer(1, 0.10 * inch),
            Image(str(benchmark_chart), width=6.9 * inch, height=3.15 * inch),
            Spacer(1, 0.06 * inch),
            paragraph("Figure 3. Benchmark-family concentration across the candidate papers.", styles["Caption"]),
            PageBreak(),
            paragraph("Executive Summary", styles["SectionTitle"]),
        ]
    )

    summary = report["summary"]
    bullets = [
        f"The hunt reviewed {summary['candidate_count']} candidate papers and promoted {summary['confirmed_main_shortlist_count']} to the confirmed shortlist.",
        f"Two papers are especially strong negative examples: Struct2Graph because the released split logic itself leaks, and D2CP05644E because its external validation panels overlap biologically with the recovered training benchmark.",
        f"The biggest cluster is not blatant leakage but benchmark-family dependence: {summary['benchmark_family_counts'].get('ppis_train335_family', 0)} papers stay inside the GraphPPIS Train_335/Test_60 lineage.",
        "That still matters scientifically. Within-family gains are useful, but they are weaker evidence for generalization than papers often imply.",
        "The report also keeps a backlog of partially recovered legacy-benchmark papers that are suspicious but not yet strong enough for the confirmed shortlist.",
    ]
    story.extend(make_bullet_list(bullets, styles["Body"]))
    story.extend(
        [
            Spacer(1, 0.10 * inch),
            paragraph("Best Examples For A Review Paper", styles["SubTitle"]),
        ]
    )
    story.extend(
        make_bullet_list(
            [
                f"{row['title']} ({row['journal']}, {row['year']}) - {row['confirmed_issue_summary']}"
                for row in report["best_examples"]
            ],
            styles["Body"],
        )
    )
    story.extend(
        [
            Spacer(1, 0.12 * inch),
            callout_box(
                "How to read the shortlist",
                (
                    "Confirmed red flag means the split itself fails independence. Confirmed blocked external means the supposed external panel is not external enough. "
                    "Confirmed audit-only means the paper is still useful, but the evaluation stays inside a reused benchmark family and should not carry the full weight of a fresh external benchmark."
                ),
                styles,
            ),
            PageBreak(),
        ]
    )

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["final_status"]].append(row)

    for status in STATUS_ORDER:
        section_rows = grouped.get(status)
        if not section_rows:
            continue
        story.append(paragraph(STATUS_TITLES[status], styles["SectionTitle"]))
        story.append(Spacer(1, 0.06 * inch))
        for row in section_rows:
            asset = assets[row["paper_id"]]
            image = Image(asset["image_path"], width=2.42 * inch, height=1.67 * inch)
            left_col = [
                paragraph(row["title"], styles["SubTitle"]),
                paragraph(f"{row['journal']} ({row['year']})", styles["BodySmall"]),
                Spacer(1, 0.03 * inch),
                paragraph(row["confirmed_issue_summary"], styles["Body"]),
                Spacer(1, 0.03 * inch),
                paragraph(f"Benchmark family: {row['benchmark_family']}", styles["BodySmall"]),
            ]
            top_table = Table(
                [[left_col, image]],
                colWidths=[4.45 * inch, 2.4 * inch],
            )
            top_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            evidence_notes = (row.get("leakage_findings") or {}).get("notes") or []
            bullets = [
                f"DOI: {row['doi']}",
                f"Task family: {row['task_family']}",
                f"Issue classes: {', '.join(row['issue_classes'])}",
                f"Claimed split: {row['claimed_split_description']}",
            ]
            if evidence_notes:
                bullets.append(f"Key evidence: {evidence_notes[0]}")
            if len(evidence_notes) > 1:
                bullets.append(f"Extra evidence: {evidence_notes[1]}")
            if row.get("consequences"):
                bullets.append(f"Consequence: {row['consequences'][0]}")
            if row.get("recommended_canonical_treatment"):
                bullets.append(f"ProteoSphere treatment: {row['recommended_canonical_treatment']}")
            if row.get("blockers"):
                bullets.append(f"Blockers: {'; '.join(row['blockers'])}")

            story.extend(
                [
                    KeepTogether(
                        [
                            top_table,
                            Spacer(1, 0.06 * inch),
                            paragraph(
                                f"Final status: {row['final_status']} | Severity: {row['severity']} | Publication score: {row['publication_score']}",
                                styles["Label"],
                            ),
                            Spacer(1, 0.04 * inch),
                        ]
                    )
                ]
            )
            story.extend(make_bullet_list(bullets, styles["Body"]))
            story.extend(
                [
                    Spacer(1, 0.06 * inch),
                    HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d6dbe4")),
                    Spacer(1, 0.12 * inch),
                ]
            )
        story.append(PageBreak())

    story.append(paragraph("Controls And Closing Interpretation", styles["SectionTitle"]))
    story.append(Spacer(1, 0.05 * inch))
    control_lines = [
        f"{control['title']} ({control['journal']}, {control['year']}) - {control['reason_for_control']} Current ProteoSphere verdict: {control['verdict']}."
        for control in report["controls"]
    ]
    story.extend(make_bullet_list(control_lines, styles["Body"]))
    story.extend(
        [
            Spacer(1, 0.12 * inch),
            callout_box(
                "Reviewer takeaway",
                (
                    "A dataset reviewer earns its place when it can separate very different kinds of weakness: direct leakage, blocked external validation, under-disclosed split membership, and benchmark-family dependence. "
                    "Those are not interchangeable problems, and treating them as interchangeable hides real differences in scientific risk."
                ),
                styles,
            ),
            Spacer(1, 0.10 * inch),
            paragraph("Primary sources", styles["SubTitle"]),
        ]
    )
    for row in report["papers"]:
        story.append(paragraph(f"{row['title']} - {row['doi']}", styles["BodySmall"]))
    return story


def add_page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#5f6775"))
    canvas.drawRightString(7.4 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.drawString(0.75 * inch, 0.45 * inch, "ProteoSphere literature-hunt review")
    canvas.restoreState()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    report = load_report()
    assets = build_assets(report["papers"])
    story = build_story(report, assets)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.6 * inch,
        title="ProteoSphere Literature Hunt for Dataset-Quality Failures",
        author="Codex for ProteoSphere",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    render_pdf_first_page(PDF_PATH, PREVIEW_PATH)
    print(f"Wrote {PDF_PATH}")
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Wrote {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
