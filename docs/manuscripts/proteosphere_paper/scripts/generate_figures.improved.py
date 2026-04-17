"""Regenerate the six ProteoSphere manuscript figures with a consistent,
journal-grade style. Writes PNGs into
`output/pdf/proteosphere_paper_assets/` alongside the prior versions.

The script is self-contained and depends only on matplotlib + numpy.
It does not embed any external raster that may carry a rendering-tool
watermark; the Struct2Graph panel is rendered schematically from the
recovered overlap counts rather than from a third-party structure image.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------

OUT_DIR = Path(
    r"D:\documents\ProteoSphereV2\output\pdf\proteosphere_paper_assets"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# A muted, print-safe palette.
C_PRIMARY = "#2F4B7C"      # deep blue
C_SECONDARY = "#665191"    # plum
C_ACCENT = "#D45087"       # magenta
C_WARN = "#F95D6A"         # coral red
C_OK = "#2B8C5A"           # forest green
C_NEUTRAL = "#6B7280"      # slate
C_LIGHT = "#E7ECF3"        # light blue-grey
C_PAPER = "#FFFFFF"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#222222",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "figure.facecolor": C_PAPER,
    "axes.facecolor": C_PAPER,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def _save(fig: plt.Figure, name: str) -> None:
    path = OUT_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------
# Figure 1. System overview
# ---------------------------------------------------------------------------

def figure_1() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.5)
    ax.axis("off")

    def box(x, y, w, h, label, color, text_color="white", fontsize=10):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=0, facecolor=color,
        ))
        ax.text(x + w / 2, y + h / 2, label,
                ha="center", va="center",
                color=text_color, fontsize=fontsize, weight="bold")

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#444"))

    # Layer 1: raw estate
    box(0.3, 4.3, 9.4, 0.9,
        "Raw source estate  |  UniProt  RCSB  PDBe  AlphaFold  BindingDB  IntAct  BioGRID  InterPro  Reactome",
        C_NEUTRAL, fontsize=9)

    # Layer 2: release contract
    box(0.3, 3.1, 9.4, 0.9,
        "Release-pinned source contract  |  registry anchored  |  STRING internal_only  |  PDBbind restricted",
        C_SECONDARY, fontsize=9)

    # Layer 3: warehouse families (as tiles)
    families = [
        "proteins", "variants", "pdb_entries", "structure_units",
        "ligands", "pl_edges", "pp_edges", "annotations",
        "pathway_roles", "provenance", "routes", "leakage_groups",
        "similarity",
    ]
    n = len(families)
    tile_w = 9.4 / n
    for i, f in enumerate(families):
        box(0.3 + i * tile_w + 0.03, 1.85, tile_w - 0.06, 0.75,
            f, C_PRIMARY, fontsize=7)
    ax.text(5, 2.8, "Compact warehouse  (best_evidence default view)",
            ha="center", fontsize=10, color="#222", weight="bold")

    # Layer 4: audit runtime + outcomes
    box(0.3, 0.5, 4.5, 1.0,
        "Audit runtime\npolicy resolution  ·  overlap\nreason codes  ·  verdict",
        C_ACCENT, fontsize=9)
    box(5.2, 0.5, 4.5, 1.0,
        "Outcomes\nusable  ·  caveats  ·  audit_only\nblocked  ·  unsafe",
        C_OK, fontsize=9)

    arrow(5, 4.3, 5, 4.0)
    arrow(5, 3.1, 5, 2.6)
    arrow(5, 1.85, 2.55, 1.5)
    arrow(5, 1.85, 7.45, 1.5)
    arrow(4.8, 1.0, 5.2, 1.0)

    ax.set_title("Figure 1.  ProteoSphere system overview",
                 loc="left", fontsize=13)
    _save(fig, "figure_1_system_overview.png")


# ---------------------------------------------------------------------------
# Figure 2. Storage footprint
# ---------------------------------------------------------------------------

def figure_2() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6),
                                   gridspec_kw={"width_ratios": [1.2, 1]})

    # Left: log-scale bar chart of footprints.
    labels = ["Warehouse\nroot", "Tracked\nsource estate",
              "data/raw\n(local)", "Incoming\nmirror"]
    sizes_gb = [74.2, 324.76, 1600, 1500]
    colors = [C_PRIMARY, C_SECONDARY, C_NEUTRAL, C_NEUTRAL]

    bars = ax1.bar(labels, sizes_gb, color=colors, edgecolor="none", width=0.62)
    ax1.set_yscale("log")
    ax1.set_ylabel("Footprint (GB, log scale)")
    ax1.set_ylim(10, 3000)
    ax1.grid(axis="y", linestyle=":", color="#BBB", alpha=0.7)
    ax1.set_axisbelow(True)
    for b, s in zip(bars, sizes_gb):
        ax1.text(b.get_x() + b.get_width() / 2, s * 1.08,
                 f"{s:,.1f} GB" if s < 1000 else f"{s/1000:.1f} TB",
                 ha="center", va="bottom", fontsize=9, color="#222")
    ax1.set_title("Measured local footprints")

    # Right: the logical idea - small hot surface in front of a large estate.
    ax2.axis("off")
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 6)
    # Large rectangle (estate)
    ax2.add_patch(mpatches.FancyBboxPatch(
        (0.3, 0.5), 9.4, 5.0,
        boxstyle="round,pad=0.02,rounding_size=0.15",
        linewidth=0, facecolor=C_LIGHT))
    ax2.text(5, 5.1, "Raw + mirrored source estate (multi-TB)",
             ha="center", fontsize=10, color="#444")
    # Small rectangle (warehouse)
    ax2.add_patch(mpatches.FancyBboxPatch(
        (3.2, 1.4), 3.6, 1.6,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=0, facecolor=C_PRIMARY))
    ax2.text(5, 2.2, "Warehouse\n(best_evidence,\n~74 GB hot)",
             ha="center", va="center", color="white",
             fontsize=10, weight="bold")
    ax2.text(5, 0.75,
             "Routine audits query the hot surface; deep forensics fall back to the estate.",
             ha="center", fontsize=9, color="#444", style="italic")
    ax2.set_title("Warehouse-first review surface")

    fig.suptitle("Figure 2.  Source estate vs. warehouse-first evidence surface",
                 x=0.02, ha="left", fontsize=13, weight="bold", y=1.02)
    _save(fig, "figure_2_storage_footprint.png")


# ---------------------------------------------------------------------------
# Figure 3. Audit decision ladder
# ---------------------------------------------------------------------------

def figure_3() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    stages = [
        ("1. Recover\nsplit artifact", C_PRIMARY),
        ("2. Resolve\npolicy", C_PRIMARY),
        ("3. Measure\noverlap", C_SECONDARY),
        ("4. Apply\nreason codes", C_SECONDARY),
        ("5. Assign\nverdict", C_ACCENT),
    ]
    x0, y0, w, h, gap = 0.3, 3.6, 1.9, 1.4, 0.35
    for i, (label, color) in enumerate(stages):
        x = x0 + i * (w + gap)
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y0), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=0, facecolor=color))
        ax.text(x + w / 2, y0 + h / 2, label,
                ha="center", va="center", color="white",
                fontsize=9.5, weight="bold")
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + w + gap, y0 + h / 2),
                        xytext=(x + w, y0 + h / 2),
                        arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#444"))

    # Verdicts along bottom
    verdicts = [
        ("usable", C_OK),
        ("usable_with_caveats", C_OK),
        ("audit_only", "#C69214"),
        ("blocked_pending_mapping", C_WARN),
        ("blocked_pending_cleanup", C_WARN),
        ("unsafe_for_training", "#7A1F2B"),
    ]
    vw = 1.85
    vy = 1.2
    total = len(verdicts) * vw + (len(verdicts) - 1) * 0.1
    vx0 = (12 - total) / 2
    for i, (label, color) in enumerate(verdicts):
        x = vx0 + i * (vw + 0.1)
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, vy), vw, 0.85,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=0, facecolor=color))
        ax.text(x + vw / 2, vy + 0.425, label,
                ha="center", va="center", color="white",
                fontsize=8.5, weight="bold")

    # Connector from stage 5 down to verdicts band
    ax.annotate("", xy=(6, vy + 0.85),
                xytext=(x0 + 4 * (w + gap) + w / 2, y0),
                arrowprops=dict(arrowstyle="-|>", lw=1.4, color="#444"))

    ax.set_title("Figure 3.  ProteoSphere audit decision ladder",
                 loc="left", fontsize=13, y=1.02)
    _save(fig, "figure_3_review_logic.png")


# ---------------------------------------------------------------------------
# Figure 4. Tier 1 landscape
# ---------------------------------------------------------------------------

def figure_4() -> None:
    fig = plt.figure(figsize=(12, 5.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.3, 0.9], wspace=0.38)

    # Year histogram — pulled from the Tier 1 master summary's year_counts block.
    ax_y = fig.add_subplot(gs[0, 0])
    years = list(range(2018, 2026))
    # Source: literature_hunt_tier1_master_summary.json → summary.year_counts
    counts = [2, 1, 1, 4, 3, 10, 5, 3]  # 18 of 29 published in 2023 or later
    ax_y.bar(years, counts, color=C_PRIMARY, edgecolor="none", width=0.72)
    for y, c in zip(years, counts):
        ax_y.text(y, c + 0.2, str(c), ha="center", va="bottom",
                  fontsize=9, color="#222")
    ax_y.set_xlabel("Publication year")
    ax_y.set_ylabel("Tier 1 papers")
    ax_y.set_title("Year of publication")
    ax_y.set_xticks(years)
    ax_y.set_ylim(0, max(counts) + 1.8)
    ax_y.grid(axis="y", linestyle=":", color="#BBB", alpha=0.6)
    ax_y.set_axisbelow(True)

    # Issue families
    ax_i = fig.add_subplot(gs[0, 1])
    families = [
        "Warm-start benchmark family",
        "Protein-overlapped external family",
        "Paper-specific direct reuse",
        "Invalid external validation",
        "Paper-specific random-CV leakage",
    ]
    fcounts = [14, 12, 1, 1, 1]
    colors = [C_PRIMARY, C_SECONDARY, C_ACCENT, C_WARN, "#C69214"]
    ypos = np.arange(len(families))
    ax_i.barh(ypos, fcounts, color=colors, edgecolor="none", height=0.68)
    ax_i.set_yticks(ypos)
    ax_i.set_yticklabels(families, fontsize=9)
    ax_i.invert_yaxis()
    for y, c in zip(ypos, fcounts):
        ax_i.text(c + 0.25, y, str(c), va="center", fontsize=9, color="#222")
    ax_i.set_xlabel("Tier 1 papers")
    ax_i.set_xlim(0, max(fcounts) + 2.5)
    ax_i.set_title("Issue family")
    ax_i.grid(axis="x", linestyle=":", color="#BBB", alpha=0.6)
    ax_i.set_axisbelow(True)

    # Domain donut
    ax_d = fig.add_subplot(gs[0, 2])
    sizes = [27, 2]
    labels = ["Protein–ligand / DTA  93%", "Protein–protein  7%"]
    wedges, _ = ax_d.pie(
        sizes, startangle=90, colors=[C_PRIMARY, C_ACCENT],
        wedgeprops=dict(width=0.38, edgecolor="white", linewidth=2))
    ax_d.text(0, 0.05, "29", ha="center", va="center",
              fontsize=22, weight="bold", color="#222")
    ax_d.text(0, -0.22, "Tier 1", ha="center", va="center",
              fontsize=9, color="#555")
    ax_d.set_title("Domain")
    ax_d.legend(wedges, labels, loc="lower center",
                bbox_to_anchor=(0.5, -0.12), frameon=False, fontsize=8)

    fig.suptitle(
        "Figure 4.  Tier 1 landscape: 29 hard-failure papers, 18 in 2023 or later",
        x=0.02, ha="left", fontsize=13, weight="bold", y=1.02,
    )
    _save(fig, "figure_4_tier1_landscape.png")


# ---------------------------------------------------------------------------
# Figure 5. Flagship case studies (no watermarked assets)
# ---------------------------------------------------------------------------

def figure_5() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    (ax_a, ax_b), (ax_c, ax_d) = axes

    # Panel A: Struct2Graph — reproduced split counts
    cats = ["Shared PDB IDs\n(train ∩ test)",
            "4EQ6 in train", "4EQ6 in test"]
    vals = [643, 78, 9]
    colors = [C_WARN, C_PRIMARY, C_OK]
    bars = ax_a.bar(cats, vals, color=colors, edgecolor="none", width=0.55)
    for b, v in zip(bars, vals):
        ax_a.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02,
                  str(v), ha="center", va="bottom", fontsize=10,
                  weight="bold", color="#222")
    ax_a.set_ylabel("Count")
    ax_a.set_title("A.  Struct2Graph — reproduced pair-level split leakage")
    ax_a.set_ylim(0, max(vals) * 1.18)
    ax_a.grid(axis="y", linestyle=":", color="#BBB", alpha=0.6)
    ax_a.set_axisbelow(True)
    ax_a.text(0.02, 0.95,
              "Released create_examples.py · seed 1337\n"
              "8,003 train / 1,000 test rows",
              transform=ax_a.transAxes, fontsize=8.5, va="top",
              color="#555", style="italic")

    # Panel B: D2CP05644E — three panels, overlap types
    panels = ["PDBbind\n(50)", "Nanobody\n(47)", "Metadynamics\n(19)"]
    direct = [4, 1, 26]
    exact = [4, 1, 26]
    partner = [110, 16, 75]
    x = np.arange(len(panels))
    w = 0.26
    ax_b.bar(x - w, direct, w, color=C_WARN, label="Direct protein")
    ax_b.bar(x,       exact, w, color=C_ACCENT, label="Exact sequence")
    ax_b.bar(x + w, partner, w, color=C_SECONDARY, label="Shared partner")
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(panels)
    ax_b.set_ylabel("Overlap count")
    ax_b.set_title("B.  Silva et al. 2023 — external panels contaminated")
    ax_b.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax_b.grid(axis="y", linestyle=":", color="#BBB", alpha=0.6)
    ax_b.set_axisbelow(True)

    # Panel C: Warm-start benchmark family — test entities shared with training
    datasets = ["DeepDTA\nDavis drugs", "DeepDTA\nDavis targets",
                "DeepDTA\nKIBA drugs", "DeepDTA\nKIBA targets"]
    test_totals = [68, 442, 2027, 229]
    shared = [68, 442, 2027, 229]
    xd = np.arange(len(datasets))
    ax_c.bar(xd, test_totals, color=C_LIGHT, edgecolor="none",
             label="Test pool size")
    ax_c.bar(xd, shared, color=C_WARN, edgecolor="none",
             label="Shared with training")
    ax_c.set_yscale("log")
    ax_c.set_ylim(10, 5000)
    ax_c.set_xticks(xd)
    ax_c.set_xticklabels(datasets, fontsize=8.5)
    for i, (t, s) in enumerate(zip(test_totals, shared)):
        ax_c.text(i, s * 1.1, f"{s}/{t}", ha="center", va="bottom",
                  fontsize=8.5, color="#222", weight="bold")
    ax_c.set_ylabel("Count (log)")
    ax_c.set_title("C.  DeepDTA setting-1 — every test entity shared")
    ax_c.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax_c.grid(axis="y", linestyle=":", color="#BBB", alpha=0.6)
    ax_c.set_axisbelow(True)

    # Panel D: PDBbind core + AttentionDTA
    groups = ["PDBbind v2013\ncore overlap",
              "PDBbind v2016\ncore overlap",
              "AttentionDTA\nDavis targets",
              "AttentionDTA\nKIBA drugs"]
    values = [108, 288, 367, 2054]
    totals = [108, 290, 367, 2054]
    colors_d = [C_SECONDARY, C_SECONDARY, C_ACCENT, C_ACCENT]
    bars = ax_d.bar(groups, values, color=colors_d, edgecolor="none", width=0.6)
    for b, v, t in zip(bars, values, totals):
        ax_d.text(b.get_x() + b.get_width() / 2, v + max(values) * 0.02,
                  f"{v}/{t}", ha="center", va="bottom",
                  fontsize=9, weight="bold", color="#222")
    ax_d.set_ylabel("Overlap count")
    ax_d.set_title("D.  PDBbind core family + AttentionDTA random-CV")
    ax_d.grid(axis="y", linestyle=":", color="#BBB", alpha=0.6)
    ax_d.set_axisbelow(True)
    ax_d.set_ylim(0, max(values) * 1.18)

    fig.suptitle("Figure 5.  Flagship case studies",
                 x=0.02, ha="left", fontsize=14, weight="bold", y=1.00)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    _save(fig, "figure_5_flagship_cases.png")


# ---------------------------------------------------------------------------
# Figure 6. Controls
# ---------------------------------------------------------------------------

def figure_6() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def column(x, title, color, items):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, 4.6), 3.6, 0.9,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=0, facecolor=color))
        ax.text(x + 1.8, 5.05, title, ha="center", va="center",
                color="white", fontsize=11, weight="bold")
        for i, it in enumerate(items):
            y = 3.9 - i * 0.55
            ax.add_patch(mpatches.FancyBboxPatch(
                (x + 0.1, y - 0.22), 3.4, 0.44,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                linewidth=0, facecolor="#F5F7FA"))
            ax.text(x + 0.3, y, "·  " + it, va="center", fontsize=9,
                    color="#222")

    column(0.3, "Certify as usable",
           C_OK,
           ["RAPPPID (UniRef-grouped)",
            "GraphPPIS (cold target)",
            "BatchDTA (time-split)",
            "HGRL-DTA, NHGNN-DTA"])

    column(4.2, "Downgrade with caveats",
           "#C69214",
           ["PotentialNet (scope narrowed)",
            "Deep Fusion Inference",
            "DTA-OM, TEFDTA",
            "DCGAN-DTA, HAC-Net"])

    column(8.1, "Block as unsafe",
           C_WARN,
           ["Struct2Graph",
            "Silva 2023 (3 panels)",
            "DeepDTA setting-1 family",
            "AttentionDTA random-CV"])

    ax.text(6, 0.4,
            "ProteoSphere validates mitigation-aware designs as well as "
            "flagging unsafe ones — a reviewer, not a filter.",
            ha="center", fontsize=10, color="#444", style="italic")

    ax.set_title("Figure 6.  Constructive use of the reviewer",
                 loc="left", fontsize=13, y=1.02)
    _save(fig, "figure_6_controls.png")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    figure_1()
    figure_2()
    figure_3()
    figure_4()
    figure_5()
    figure_6()


if __name__ == "__main__":
    main()
