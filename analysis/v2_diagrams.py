"""v2 schematic diagrams for the board deck (no database needed).

Title-less, large-font figures:
- v2_form4_intro.png    : what a Form 4 is (who / what / when / why)
- v2_form4_example.png  : the anatomy of a filing, with the fields we use
- v2_architecture.png   : the six-phase pipeline merged with the code modules
- v2_data_funnel.png    : how the raw filings narrow to the analyzed trades

Pure matplotlib, brand colours, sized for projection.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

OUT_DIR = os.path.join(config.OUTPUT_DIR, "presentation")
C = config.CHART_COLORS
GREEN, SALE, TEXT, SUB, BG = (C["purchase"], C["sale"], C["text"],
                              C["subtitle"], C["bg"])
LIGHT = "#eef4f2"
ACCENTS = ["#1a6b54", "#2a9d8f", "#3d5a80", "#ee9b00"]


def _canvas(w=13.5, h=6.6):
    """A blank brand-coloured canvas with 0..1 axes."""
    # DejaVu Sans has full glyph coverage (arrows, check marks) - avoids tofu.
    plt.rcParams.update({"font.family": "sans-serif",
                         "font.sans-serif": ["DejaVu Sans"]})
    fig = plt.figure(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=200, facecolor=BG)
    plt.close(fig)
    print(f"saved {path}")


def _rbox(ax, x, y, w, h, edge, fill, lw=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.004,rounding_size=0.02",
                 linewidth=lw, edgecolor=edge, facecolor=fill, zorder=3))


# --- Slide 2: what is a Form 4 -------------------------------------------

def form4_intro():
    """Four rows: WHO / WHAT / WHEN / WHY, large type."""
    fig, ax = _canvas(13.5, 5.4)
    rows = [
        ("WHO", "Section 16 insiders: directors, officers & beneficial owners > 10%"),
        ("WHAT", "Every change in their holdings of their own company's stock\n(buys, sells, grants, option exercises)"),
        ("WHEN", "Filed with the SEC within 2 business days of the transaction\n(since the Sarbanes-Oxley Act, 2002)"),
        ("WHY", "A public, near-real-time record of insider activity,\nmandated for market transparency"),
    ]
    h = 0.17
    y = 0.90
    for i, (key, txt) in enumerate(rows):
        _rbox(ax, 0.04, y - h, 0.20, h, ACCENTS[i], ACCENTS[i])
        ax.text(0.14, y - h / 2, key, ha="center", va="center",
                fontsize=23, fontweight="bold", color="white", zorder=4)
        ax.text(0.28, y - h / 2, txt, ha="left", va="center",
                fontsize=19, color=TEXT, zorder=4)
        y -= h + 0.035
    _save(fig, "v2_form4_intro.png")


# --- Slide 3: anatomy of a Form 4 ----------------------------------------

def form4_example():
    """A simplified, annotated Form 4; the fields we use are highlighted."""
    fig, ax = _canvas(13.5, 5.7)

    # header band
    _rbox(ax, 0.03, 0.84, 0.94, 0.11, TEXT, TEXT)
    ax.text(0.06, 0.895, "FORM 4", ha="left", va="center", fontsize=22,
            fontweight="bold", color="white")
    ax.text(0.20, 0.895, "Statement of Changes in Beneficial Ownership",
            ha="left", va="center", fontsize=15, color="white")

    # issuer / person / relationship row
    cells = [
        ("Issuer", "TransDigm Group Inc.  (TDG)"),
        ("Reporting person", "Robert J. Small"),
        ("Relationship", "✓  Director"),
    ]
    cw = 0.305
    for i, (lab, val) in enumerate(cells):
        x = 0.03 + i * (cw + 0.0075)
        _rbox(ax, x, 0.70, cw, 0.11, "#cccccc", "white")
        ax.text(x + 0.015, 0.775, lab, ha="left", va="center", fontsize=13, color=SUB)
        ax.text(x + 0.015, 0.735, val, ha="left", va="center", fontsize=16,
                fontweight="bold", color=TEXT)

    # Table I
    ax.text(0.03, 0.665, "Table I - Non-Derivative Securities", ha="left",
            va="center", fontsize=14, fontweight="bold", color=TEXT)
    headers = ["Security", "Date", "Code", "Shares", "Price", "Owned after"]
    row = ["Common Stock", "2020-03-10", "P", "2,111", "$495.71", "1,486,197"]
    widths = [0.24, 0.16, 0.10, 0.14, 0.14, 0.16]
    used = {1, 2, 3, 4}  # date, code, shares, price -> what we extract
    x = 0.03
    yh, yr = 0.54, 0.42
    for j, (head, val, wj) in enumerate(zip(headers, row, widths)):
        fill = LIGHT if j in used else "white"
        edge = GREEN if j in used else "#cccccc"
        _rbox(ax, x, yh, wj, 0.08, "#cccccc", "#f0f0f0", lw=1)   # header cell
        ax.text(x + wj / 2, yh + 0.04, head, ha="center", va="center",
                fontsize=14, fontweight="bold", color=TEXT)
        _rbox(ax, x, yr, wj, 0.10, edge, fill, lw=2 if j in used else 1)  # value cell
        ax.text(x + wj / 2, yr + 0.05, val, ha="center", va="center",
                fontsize=16, color=TEXT,
                fontweight="bold" if j in used else "normal")
        x += wj + 0.004

    # callout for the highlighted fields
    ax.text(0.03, 0.32,
            "Highlighted = the fields we extract from 4.6M records:  "
            "date, code (P/S), shares, price  →  nominal volume",
            ha="left", va="center", fontsize=15, color=GREEN, fontweight="bold")
    ax.text(0.03, 0.20,
            "Real filing: a TransDigm director buying during the COVID crash  -  "
            "SEC EDGAR, accession 0000919574-20-002398.",
            ha="left", va="center", fontsize=13, color=SUB)
    ax.text(0.03, 0.10,
            "(Table II - derivative securities: options, warrants, convertibles - "
            "is parsed the same way.)",
            ha="left", va="center", fontsize=12, color=SUB)
    _save(fig, "v2_form4_example.png")


# --- Slide 4: merged processing + code architecture ----------------------

def _arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=22, linewidth=2.4, color=GREEN, zorder=5))


def _phase(ax, cx, cy, w, h, num, name, action, module):
    _rbox(ax, cx - w / 2, cy - h / 2, w, h, GREEN, LIGHT)
    ax.text(cx, cy + h * 0.28, f"{num}  {name}", ha="center", va="center",
            fontsize=17, fontweight="bold", color=TEXT)
    ax.text(cx, cy + h * 0.02, action, ha="center", va="center",
            fontsize=14, color=SUB)
    ax.text(cx, cy - h * 0.28, module, ha="center", va="center",
            fontsize=14, color=GREEN, fontstyle="italic")


def architecture():
    """Six phases (data flow) merged with their code module each."""
    fig, ax = _canvas(13.5, 5.4)
    ax.text(0.5, 0.95, "main.py  -  orchestrates all six phases",
            ha="center", va="center", fontsize=16, color=TEXT, fontweight="bold")

    w, hh = 0.29, 0.24
    top, bot = 0.66, 0.30
    xs = [0.19, 0.50, 0.81]
    phases = [
        ("1", "Download", "fetch quarterly ZIPs", "downloader.py"),
        ("2", "Parse", "ZIP → TSV → DataFrame", "parser.py"),
        ("3", "Prepare", "clean - merge - enrich", "data_preparation.py"),
        ("4", "Load", "Django ORM → PostgreSQL / SQLite", "db_manager.py"),
        ("5", "Validate", "8 data-quality checks", "validation.py"),
        ("6", "Evaluate", "charts - tables - PDF", "evaluation.py"),
    ]
    # top row L->R (1,2,3), bottom row R->L (4,5,6) = snake
    pos = [(xs[0], top), (xs[1], top), (xs[2], top),
           (xs[2], bot), (xs[1], bot), (xs[0], bot)]
    for (cx, cy), p in zip(pos, phases):
        _phase(ax, cx, cy, w, hh, *p)
    _arrow(ax, xs[0] + w / 2, top, xs[1] - w / 2, top)
    _arrow(ax, xs[1] + w / 2, top, xs[2] - w / 2, top)
    _arrow(ax, xs[2], top - hh / 2, xs[2], bot + hh / 2)
    _arrow(ax, xs[2] - w / 2, bot, xs[1] + w / 2, bot)
    _arrow(ax, xs[1] - w / 2, bot, xs[0] + w / 2, bot)

    # foundation strip
    _rbox(ax, 0.03, 0.04, 0.94, 0.09, "#ee9b00", "#fdf3e0", lw=2)
    ax.text(0.5, 0.085,
            "Foundation:  config.py + .env  -  7 tables  -  "
            "idempotent (delete-then-insert)  -  1.2M filings → 4.6M rows  -  36 unit tests",
            ha="center", va="center", fontsize=13, color=TEXT)
    _save(fig, "v2_architecture.png")


# --- Slide 5: data funnel (how much data survives each step) -------------

def data_funnel():
    """How the raw filings narrow down to the trades behind our signal.

    Real counts from the loaded database (2020-2025). The big drops are
    deliberate focus, not data loss - validation itself keeps 99.98%.
    Each level shows the count and a short label inside the box; the
    longer detail sits to the right, clear of the box.
    """
    fig, ax = _canvas(13.5, 5.7)

    # (count, short label, relative width) - label kept short to fit the box
    levels = [
        ("4.6M", "records parsed (1.21M filings)", 0.74),
        ("1.84M", "non-derivative transactions", 0.60),
        ("715K", "open-market buys & sells (P/S)", 0.48),
        ("715K", "valid - 99.98% pass 8 checks", 0.48),
    ]
    top, h, gap = 0.93, 0.16, 0.065
    edges = [ACCENTS[0], ACCENTS[1], "#ee9b00", GREEN]
    fills = [LIGHT, LIGHT, "#fdf3e0", LIGHT]
    y = top
    for i, (cnt, label, bw) in enumerate(levels):
        x = 0.5 - bw / 2
        _rbox(ax, x, y - h, bw, h, edges[i], fills[i], lw=2.5)
        ax.text(0.5, y - h * 0.36, cnt, ha="center", va="center",
                fontsize=25, fontweight="bold", color=edges[i], zorder=4)
        ax.text(0.5, y - h * 0.74, label, ha="center", va="center",
                fontsize=13.5, color=TEXT, zorder=4)
        if i < len(levels) - 1:
            ax.add_patch(FancyArrowPatch((0.5, y - h), (0.5, y - h - gap),
                         arrowstyle="-|>", mutation_scale=22, linewidth=2.4,
                         color=GREEN, zorder=5))
        y -= h + gap

    ax.text(0.5, 0.03,
            "The big drops are deliberate focus on open-market trades - not lost data.",
            ha="center", va="center", fontsize=12.5, color=SUB, fontstyle="italic")
    _save(fig, "v2_data_funnel.png")


def main():
    """Render all v2 diagrams."""
    form4_intro()
    form4_example()
    architecture()
    data_funnel()


if __name__ == "__main__":
    main()
