"""Seaborn architecture visuals for the board slides (Aufgabe 1).

Seaborn draws statistical plots, not box-and-arrow diagrams, so here
"architecture" means the *quantitative shape* of the system:

- system_pipeline.png : rows imported per quarter - the pipeline at work
- code_layers.png     : lines of code per module, coloured by layer

Both read presentation-grade: a modern gradient palette, the transparent
TH Koeln logo, bold titles. The system chart needs the database; the code
chart just measures the source files.
"""
import os
import sys
from collections import defaultdict

import django

matplotlib_backend = "Agg"
import matplotlib  # noqa: E402

matplotlib.use(matplotlib_backend)
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "secpipeline.settings")
django.setup()

from django.db.models import Count  # noqa: E402

import config  # noqa: E402
from pipeline.models import (  # noqa: E402
    DerivHolding, DerivTrans, NonderivHolding, NonderivTrans, Submission,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(config.OUTPUT_DIR, "presentation")
C = config.CHART_COLORS

# Modern, on-brand palette: TH Koeln green anchors it, the rest harmonises.
LAYER_COLORS = {
    "Orchestration": "#1a6b54",
    "Pipeline modules": "#2a9d8f",
    "Persistence": "#3d5a80",
    "Foundation": "#ee9b00",
}

# "Bare" mode (PRES_BARE=1): drop title/logo/source for native PPT titles.
BARE = os.getenv("PRES_BARE") == "1"


def _style():
    """Seaborn whitegrid + brand fonts."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "axes.labelcolor": C["text"],
        "text.color": C["text"],
        "xtick.color": C["subtitle"],
        "ytick.color": C["subtitle"],
    })


def _logo(fig):
    """Transparent TH Koeln logo, top-right."""
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
    """Bold headline + grey subtitle + SEC/source note."""
    if BARE:
        return
    fig.text(0.065, 0.94, title, fontsize=20, fontweight="bold", color=C["text"])
    fig.text(0.065, 0.89, subtitle, fontsize=12, color=C["subtitle"])


def _quarter_key(q):
    """Sort key for '2020Q1' style strings."""
    year, qtr = q.split("Q")
    return int(year) * 10 + int(qtr)


def system_pipeline():
    """Rows imported per quarter - a gradient bar chart of throughput."""
    counts = defaultdict(int)
    for model in (Submission, NonderivTrans, NonderivHolding, DerivTrans, DerivHolding):
        for row in model.objects.values("source_quarter").annotate(
                n=Count("source_quarter")):
            counts[row["source_quarter"]] += row["n"]

    df = pd.DataFrame(
        sorted(counts.items(), key=lambda kv: _quarter_key(kv[0])),
        columns=["quarter", "rows"],
    )
    total = df["rows"].sum()

    # gradient: deeper green = more rows that quarter
    order = df["rows"].rank().astype(int) - 1
    palette = sns.color_palette("crest", len(df))
    colors = [palette[i] for i in order]

    _style()
    fig, ax = plt.subplots(figsize=(13.5, 7))
    fig.subplots_adjust(top=(0.95 if BARE else 0.80), bottom=0.14, left=0.085, right=0.96)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    x = range(len(df))
    ax.bar(x, df["rows"], color=colors, width=0.78, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["quarter"], rotation=45, ha="right", fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1000:.0f}K"))
    ax.set_ylabel("Rows imported")
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.margins(x=0.01)

    ax.text(0.5, 0.93,
            f"{total / 1e6:.1f}M rows  -  24 quarters  -  7 tables  -  one idempotent run",
            transform=ax.transAxes, ha="center", fontsize=11,
            color=C["text"], fontweight="medium")

    _titles(fig, "System Architecture - the pipeline at work",
            "Rows imported per quarter (2020-2025) through the six-phase pipeline")
    if not BARE:
        fig.text(0.065, 0.02, "Source: SEC EDGAR Form 4 - Group 01",
                 fontsize=8, color=C["subtitle"])
    _logo(fig)
    _save(fig, "system_pipeline.png")


def _loc(rel_path):
    """Line count of a source file, 0 if missing."""
    path = os.path.join(ROOT, rel_path)
    if not os.path.isfile(path):
        return 0
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def code_layers():
    """Lines of code per module, coloured by architectural layer."""
    files = [
        ("main.py", "main.py", "Orchestration"),
        ("modules/downloader.py", "downloader", "Pipeline modules"),
        ("modules/parser.py", "parser", "Pipeline modules"),
        ("modules/data_preparation.py", "data_preparation", "Pipeline modules"),
        ("modules/db_manager.py", "db_manager", "Pipeline modules"),
        ("modules/validation.py", "validation", "Pipeline modules"),
        ("modules/evaluation.py", "evaluation", "Pipeline modules"),
        ("pipeline/models.py", "models (Django)", "Persistence"),
        ("secpipeline/settings.py", "settings", "Persistence"),
        ("config.py", "config", "Foundation"),
    ]
    df = pd.DataFrame(
        [(name, _loc(p), layer) for p, name, layer in files],
        columns=["module", "loc", "layer"],
    ).sort_values("loc", ascending=True)
    total = df["loc"].sum()
    colors = [LAYER_COLORS[l] for l in df["layer"]]

    _style()
    fig, ax = plt.subplots(figsize=(13.5, 7))
    fig.subplots_adjust(top=(0.95 if BARE else 0.80), bottom=0.10, left=0.20, right=0.94)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    y = range(len(df))
    ax.barh(y, df["loc"], color=colors, height=0.66, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(df["module"], fontsize=11)
    for i, v in enumerate(df["loc"]):
        ax.text(v + total * 0.004, i, f"{v}", va="center",
                fontsize=10, fontweight="medium", color=C["text"])
    ax.set_xlim(0, df["loc"].max() * 1.12)
    ax.xaxis.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(axis="y", length=0)

    # legend = the layers
    handles = [plt.Rectangle((0, 0), 1, 1, color=col) for col in LAYER_COLORS.values()]
    ax.legend(handles, LAYER_COLORS.keys(), frameon=False, fontsize=10,
              loc="lower right", title="Layer", title_fontsize=10)

    _titles(fig, "Code Architecture - by layer",
            f"Lines of code per module ({total:,} lines, four clean layers)")
    _logo(fig)
    _save(fig, "code_layers.png")


def _save(fig, name):
    """Write a chart at presentation resolution."""
    os.makedirs(OUT_DIR, exist_ok=True)
    if BARE:
        name = name[:-4] + "_bare.png"
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved {path}")


def main():
    """Render both seaborn architecture charts."""
    system_pipeline()
    code_layers()


if __name__ == "__main__":
    main()
