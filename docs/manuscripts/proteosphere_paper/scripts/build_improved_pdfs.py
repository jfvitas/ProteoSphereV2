"""Build PDFs from the improved ProteoSphere manuscript, supplement, and PI
briefing. Resolves `{{FIGURE_N_PATH}}` tokens against
`figure_manifest.json`, replaces `{{TIER1_TABLE}}` in the supplement with a
compact Tier 1 table rendered from `literature_hunt_tier1_master_summary.json`
when available, and emits three PDFs alongside the existing ones:

  output/pdf/proteosphere_manuscript_draft.improved.pdf
  output/pdf/proteosphere_manuscript_supplement.improved.pdf
  output/pdf/proteosphere_pi_briefing.improved.pdf
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)


REPO_ROOT = Path(r"D:\documents\ProteoSphereV2")
MANUSCRIPT_DIR = REPO_ROOT / "docs" / "manuscripts" / "proteosphere_paper"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
STATUS_DIR = REPO_ROOT / "artifacts" / "status"

MAIN_MD = MANUSCRIPT_DIR / "proteosphere_manuscript_draft.improved.md"
SUPP_MD = MANUSCRIPT_DIR / "proteosphere_supplementary_appendix.improved.md"
PI_MD = MANUSCRIPT_DIR / "proteosphere_pi_briefing.improved.md"
FIG_MANIFEST = MANUSCRIPT_DIR / "figure_manifest.json"
TIER1_SUMMARY = STATUS_DIR / "literature_hunt_tier1_master_summary.json"

MAIN_PDF = OUTPUT_DIR / "proteosphere_manuscript_draft.improved.pdf"
SUPP_PDF = OUTPUT_DIR / "proteosphere_manuscript_supplement.improved.pdf"
PI_PDF = OUTPUT_DIR / "proteosphere_pi_briefing.improved.pdf"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

BASE = getSampleStyleSheet()


def make_styles() -> dict[str, ParagraphStyle]:
    body_font = "Helvetica"
    body_bold = "Helvetica-Bold"
    body_italic = "Helvetica-Oblique"
    return {
        "title": ParagraphStyle(
            "title", parent=BASE["Title"],
            fontName=body_bold, fontSize=18, leading=22,
            spaceAfter=14, textColor=colors.HexColor("#1F2937"),
        ),
        "h1": ParagraphStyle(
            "h1", parent=BASE["Heading1"],
            fontName=body_bold, fontSize=14, leading=18,
            spaceBefore=16, spaceAfter=8,
            textColor=colors.HexColor("#1F3A5F"),
        ),
        "h2": ParagraphStyle(
            "h2", parent=BASE["Heading2"],
            fontName=body_bold, fontSize=12, leading=16,
            spaceBefore=12, spaceAfter=6,
            textColor=colors.HexColor("#2F4B7C"),
        ),
        "h3": ParagraphStyle(
            "h3", parent=BASE["Heading3"],
            fontName=body_bold, fontSize=11, leading=14,
            spaceBefore=10, spaceAfter=4,
            textColor=colors.HexColor("#2F4B7C"),
        ),
        "body": ParagraphStyle(
            "body", parent=BASE["BodyText"],
            fontName=body_font, fontSize=10, leading=14,
            spaceAfter=7, textColor=colors.HexColor("#222222"),
            alignment=4,  # justify
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=BASE["BodyText"],
            fontName=body_font, fontSize=10, leading=14,
            leftIndent=14, bulletIndent=2, spaceAfter=3,
            textColor=colors.HexColor("#222222"),
        ),
        "caption": ParagraphStyle(
            "caption", parent=BASE["BodyText"],
            fontName=body_italic, fontSize=9, leading=12,
            spaceBefore=2, spaceAfter=10,
            textColor=colors.HexColor("#555555"),
            alignment=1,
        ),
        "table_header": ParagraphStyle(
            "th", fontName=body_bold, fontSize=9, leading=11,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "td", fontName=body_font, fontSize=9, leading=11,
            textColor=colors.HexColor("#222222"),
        ),
    }


# ---------------------------------------------------------------------------
# Markdown → flowables (narrow subset)
# ---------------------------------------------------------------------------

INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
INLINE_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
INLINE_CODE = re.compile(r"`([^`]+)`")
INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
IMAGE_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)")
TABLE_SEP = re.compile(r"^\s*\|?\s*[-: ]+\s*(\|\s*[-: ]+\s*)+\|?\s*$")


def inline_markdown(text: str) -> str:
    # Escape reportlab-sensitive characters first.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = INLINE_CODE.sub(
        lambda m: f'<font face="Courier" size="9">{m.group(1)}</font>', text
    )
    text = INLINE_BOLD.sub(r"<b>\1</b>", text)
    text = INLINE_ITALIC.sub(r"<i>\1</i>", text)
    text = INLINE_LINK.sub(
        lambda m: f'<link href="{m.group(2)}" color="#2F4B7C">{m.group(1)}</link>',
        text,
    )
    return text


@dataclass
class FigureMap:
    tokens: dict[str, str]
    captions: dict[str, str]


def load_figure_map() -> FigureMap:
    if not FIG_MANIFEST.exists():
        return FigureMap({}, {})
    data = json.loads(FIG_MANIFEST.read_text(encoding="utf-8"))
    tokens = {f["token"]: f["path"] for f in data["figures"]}
    caps = {f["token"]: f.get("caption", "") for f in data["figures"]}
    return FigureMap(tokens, caps)


def resolve_tokens(text: str, figmap: FigureMap, tier1_md: str) -> str:
    for tok, path in figmap.tokens.items():
        text = text.replace("{{" + tok + "}}", path)
    text = text.replace("{{TIER1_TABLE}}", tier1_md)
    return text


def render_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> LongTable:
    rows: list[list[Paragraph]] = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    header = rows[0]
    body_rows = rows[1:]

    data = [[Paragraph(inline_markdown(c), styles["table_header"]) for c in header]]
    for r in body_rows:
        data.append([Paragraph(inline_markdown(c), styles["table_cell"]) for c in r])

    n_cols = len(header)
    usable_width = 6.5 * inch
    col_widths = [usable_width / n_cols] * n_cols

    tbl = LongTable(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F4B7C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#F5F7FA"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
    ]))
    return tbl


def md_to_flowables(md: str, styles: dict[str, ParagraphStyle],
                    figmap: FigureMap) -> list:
    flowables: list = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank line
        if not stripped:
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            flowables.append(Paragraph(inline_markdown(stripped[2:]),
                                       styles["title"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flowables.append(Paragraph(inline_markdown(stripped[3:]),
                                       styles["h1"]))
            i += 1
            continue
        if stripped.startswith("### "):
            flowables.append(Paragraph(inline_markdown(stripped[4:]),
                                       styles["h2"]))
            i += 1
            continue
        if stripped.startswith("#### "):
            flowables.append(Paragraph(inline_markdown(stripped[5:]),
                                       styles["h3"]))
            i += 1
            continue

        # Image line
        m = IMAGE_LINE.match(stripped)
        if m:
            alt = m.group(1)
            path = m.group(2)
            if Path(path).exists():
                img = Image(path, width=6.5 * inch, height=4.2 * inch,
                            kind="proportional")
                flowables.append(img)
                if alt:
                    flowables.append(Paragraph(inline_markdown(alt),
                                               styles["caption"]))
            else:
                flowables.append(Paragraph(f"[missing image: {path}]",
                                           styles["caption"]))
            i += 1
            continue

        # Table
        if stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            tbl_lines = [stripped]
            i += 2  # skip separator
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl_lines.append(lines[i].strip())
                i += 1
            flowables.append(render_table(tbl_lines, styles))
            flowables.append(Spacer(1, 6))
            continue

        # Bulleted list
        if stripped.startswith(("- ", "* ")):
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                item = lines[i].strip()[2:]
                flowables.append(Paragraph(inline_markdown(item),
                                           styles["bullet"], bulletText="•"))
                i += 1
            flowables.append(Spacer(1, 4))
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", stripped):
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                m = re.match(r"^(\d+)\.\s+(.*)", lines[i].strip())
                num, item = m.group(1), m.group(2)
                flowables.append(Paragraph(inline_markdown(item),
                                           styles["bullet"],
                                           bulletText=f"{num}."))
                i += 1
            flowables.append(Spacer(1, 4))
            continue

        # Default paragraph: accumulate until blank
        buf = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not (
            lines[i].startswith("#")
            or lines[i].strip().startswith(("- ", "* ", "|", "!["))
            or re.match(r"^\d+\.\s+", lines[i].strip())
        ):
            buf.append(lines[i].strip())
            i += 1
        flowables.append(Paragraph(inline_markdown(" ".join(buf)),
                                   styles["body"]))

    return flowables


# ---------------------------------------------------------------------------
# Tier 1 table for the supplement
# ---------------------------------------------------------------------------

def build_tier1_table() -> str:
    if not TIER1_SUMMARY.exists():
        return ("*(Tier 1 master summary artifact not found at build time; "
                "see `artifacts/status/literature_hunt_tier1_master_summary.json`.)*")
    try:
        data = json.loads(TIER1_SUMMARY.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"*(Tier 1 table unavailable: {exc})*"

    papers: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for key in ("papers", "tier1_papers", "records", "entries"):
            if isinstance(data.get(key), list):
                papers = data[key]
                break
    if not papers:
        return ("*(Tier 1 papers list not found in summary artifact; inspect "
                "`literature_hunt_tier1_master_summary.json` directly.)*")

    header = "| Paper | Year | Domain | Issue family | Verdict |"
    sep = "|---|---|---|---|---|"
    rows = [header, sep]
    for p in papers:
        pid = str(p.get("paper_id") or p.get("id") or p.get("title", ""))[:60]
        year = str(p.get("year") or p.get("publication_year") or "")
        domain = str(p.get("domain") or p.get("subfield") or "")
        family = str(p.get("issue_family") or p.get("failure_class") or "")
        verdict = str(p.get("verdict") or p.get("status") or "")
        rows.append(f"| {pid} | {year} | {domain} | {family} | {verdict} |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Build entry point
# ---------------------------------------------------------------------------

def build_pdf(md_path: Path, pdf_path: Path, styles: dict[str, ParagraphStyle],
              figmap: FigureMap, tier1_md: str) -> None:
    text = md_path.read_text(encoding="utf-8")
    text = resolve_tokens(text, figmap, tier1_md)
    flowables = md_to_flowables(text, styles, figmap)

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=letter,
        leftMargin=1.0 * inch, rightMargin=1.0 * inch,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        title=md_path.stem, author="ProteoSphere",
    )
    doc.build(flowables)
    print(f"wrote {pdf_path}")


def main() -> None:
    styles = make_styles()
    figmap = load_figure_map()
    tier1_md = build_tier1_table()

    build_pdf(MAIN_MD, MAIN_PDF, styles, figmap, tier1_md)
    build_pdf(SUPP_MD, SUPP_PDF, styles, figmap, tier1_md)
    build_pdf(PI_MD, PI_PDF, styles, figmap, tier1_md)


if __name__ == "__main__":
    main()
