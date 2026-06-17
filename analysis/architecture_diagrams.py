"""Architecture diagrams for the board presentation (Aufgabe 1).

Renders two presentation-grade figures with the TH Koeln brand look:
- system_architecture.png : the six-phase data pipeline (data flow)
- code_architecture.png   : the code layers, kept deliberately shallow

Pure matplotlib (the engine seaborn sits on) so the diagrams match the
data charts' colours and logo. No database needed.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

OUT_DIR = os.path.join(config.OUTPUT_DIR, "presentation")
C = config.CHART_COLORS

# "Bare" mode (PRES_BARE=1): drop title/logo for native PPT titles.
BARE = os.getenv("PRES_BARE") == "1"
AX_H = 0.92 if BARE else 0.80


def _style():
    """Brand fonts for every diagram."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    })


def _logo(fig):
    """Transparent TH Koeln logo, top-right corner."""
    if BARE:
        return
    if not os.path.isfile(config.LOGO_PATH):
        return
    ax = fig.add_axes([0.865, 0.875, 0.10, 0.10], anchor="NE", zorder=20)
    ax.imshow(mpimg.imread(config.LOGO_PATH))
    ax.axis("off")
    fig.text(0.915, 0.865, "Group 01 - IT for Finance",
             fontsize=7, color=C["subtitle"], ha="center", va="top")


def _titles(fig, title, subtitle):
    """Headline + grey subtitle, consistent with the data charts."""
    if BARE:
        return
    fig.text(0.06, 0.93, title, fontsize=20, fontweight="bold", color=C["text"])
    fig.text(0.06, 0.875, subtitle, fontsize=12, color=C["subtitle"])


def _box(ax, cx, cy, w, h, title, sub, edge, fill, num=None):
    """One rounded node with a bold title and a small descriptor line."""
    box = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=2, edgecolor=edge, facecolor=fill, zorder=3,
    )
    ax.add_patch(box)
    label = f"{num}  {title}" if num else title
    ax.text(cx, cy + h * 0.16, label, ha="center", va="center",
            fontsize=12.5, fontweight="bold", color=C["text"], zorder=4)
    ax.text(cx, cy - h * 0.22, sub, ha="center", va="center",
            fontsize=9.5, color=C["subtitle"], zorder=4)


def _arrow(ax, x1, y1, x2, y2):
    """Light connector arrow between two nodes."""
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=22,
        linewidth=2.4, color=green_arrow(), zorder=5,
    ))


def green_arrow():
    """Arrow colour - the brand green, so connectors read as 'flow'."""
    return C["purchase"]


def system_architecture():
    """Six-phase pipeline as a clean left-to-right snake of nodes."""
    _style()
    fig = plt.figure(figsize=(13.5, 7))
    fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0.02, 0.04, 0.96, AX_H])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    green, red = C["purchase"], C["sale"]
    light = "#eef4f2"
    w, h = 0.18, 0.21
    top, bot = 0.66, 0.27
    xs = [0.13, 0.38, 0.63, 0.88]

    # top row, left -> right
    _box(ax, xs[0], top, w, h, "SEC EDGAR", "Form 4 ZIPs, 2020-2025", C["text"], "#f0eef0")
    _box(ax, xs[1], top, w, h, "Download", "fetch quarterly ZIPs", green, light, "1")
    _box(ax, xs[2], top, w, h, "Parse", "ZIP -> TSV -> DataFrame", green, light, "2")
    _box(ax, xs[3], top, w, h, "Prepare", "clean - merge - enrich", green, light, "3")
    # bottom row, right -> left (snake)
    _box(ax, xs[3], bot, w, h, "Load", "Django ORM, idempotent", green, light, "4")
    _box(ax, xs[2], bot, w, h, "Validate", "8 data-quality checks", green, light, "5")
    _box(ax, xs[1], bot, w, h, "Evaluate", "charts - tables - PDF", green, light, "6")
    _box(ax, xs[0], bot, w, h, "Output", "output/<year>/...", C["text"], "#f0eef0")

    _arrow(ax, xs[0] + w / 2, top, xs[1] - w / 2, top)
    _arrow(ax, xs[1] + w / 2, top, xs[2] - w / 2, top)
    _arrow(ax, xs[2] + w / 2, top, xs[3] - w / 2, top)
    _arrow(ax, xs[3], top - h / 2, xs[3], bot + h / 2)   # down connector
    _arrow(ax, xs[3] - w / 2, bot, xs[2] + w / 2, bot)
    _arrow(ax, xs[2] - w / 2, bot, xs[1] + w / 2, bot)
    _arrow(ax, xs[1] - w / 2, bot, xs[0] + w / 2, bot)

    ax.text(0.5, 0.025,
            "One idempotent pipeline (delete-then-insert)  -  4.6M rows  -  "
            "7 tables  -  Django ORM on PostgreSQL / SQLite",
            ha="center", va="center", fontsize=10.5, color=C["text"])

    _titles(fig, "System Architecture",
            "SEC Form 4 insider-trading data pipeline - six phases, one command")
    _logo(fig)
    _save(fig, "system_architecture.png")


def code_architecture():
    """Code layers as four stacked bands - intentionally high-level."""
    _style()
    fig = plt.figure(figsize=(13.5, 7))
    fig.patch.set_facecolor(C["bg"])
    ax = fig.add_axes([0.04, 0.04, 0.92, AX_H])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    green = C["purchase"]
    light = "#eef4f2"
    bands = [
        ("Orchestration", "main.py  -  runs the 6 phases, CLI flags (--year / --years)"),
        ("Pipeline logic (modules/)",
         "downloader   parser   data_preparation   db_manager   validation   evaluation"),
        ("Persistence (Django)", "pipeline/models.py  -  7 models   |   migrations   |   secpipeline/settings.py"),
        ("Foundation", "config.py + .env  (no hardcoded values)        30 unit tests (SQLite)"),
    ]
    y0, gap, bh = 0.72, 0.025, 0.155
    for i, (title, sub) in enumerate(bands):
        cy = y0 - i * (bh + gap)
        box = FancyBboxPatch(
            (0.04, cy - bh / 2), 0.92, bh,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            linewidth=2, edgecolor=green, facecolor=light, zorder=3,
        )
        ax.add_patch(box)
        ax.text(0.075, cy + bh * 0.18, title, ha="left", va="center",
                fontsize=14, fontweight="bold", color=C["text"])
        ax.text(0.075, cy - bh * 0.24, sub, ha="left", va="center",
                fontsize=11, color=C["subtitle"])
        if i < len(bands) - 1:
            _arrow(ax, 0.5, cy - bh / 2, 0.5, cy - bh / 2 - gap)

    _titles(fig, "Code Architecture",
            "Clear layers: orchestration on top, a swappable database underneath")
    _logo(fig)
    _save(fig, "code_architecture.png")


def _save(fig, name):
    """Write a diagram at presentation resolution."""
    os.makedirs(OUT_DIR, exist_ok=True)
    if BARE:
        name = name[:-4] + "_bare.png"
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved {path}")


def main():
    """Render both architecture diagrams."""
    system_architecture()
    code_architecture()


if __name__ == "__main__":
    main()
