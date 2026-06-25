"""v2 findings chart: insider buy-share vs. the market.

Monthly insider buy-share (purchases / (purchases + sales), by count)
plotted against the S&P 500 drawdown from its trailing peak. Bars are
green above the median buy-share and red below it; the market drawdown
runs as an orange line on the right axis. The relationship is quantified
by the correlation printed on the chart.

Rendered title-less with large fonts for a native PowerPoint title.
S&P 500 monthly closes: analysis/sp500_monthly.csv (Yahoo Finance).
"""
import csv
import os
import sys

import django

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "secpipeline.settings")
django.setup()

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from django.db.models import Count  # noqa: E402
from django.db.models.functions import TruncMonth  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

import config  # noqa: E402
from pipeline.models import NonderivTrans  # noqa: E402

OUT_DIR = os.path.join(config.OUTPUT_DIR, "presentation")
C = config.CHART_COLORS
BELOW = C["sale"]  # below-median buy-share: brand red, clear contrast vs green
MKT = "#e8801a"  # market line: orange, clear contrast vs green bars


def buy_share():
    """Monthly purchase share (count) joined with the S&P 500 drawdown."""
    qs = (
        NonderivTrans.objects
        .filter(is_valid=True, trans_code__in=["P", "S"],
                trans_date__year__gte=config.START_YEAR,
                trans_date__year__lte=config.END_YEAR)
        .annotate(m=TruncMonth("trans_date"))
        .values("m", "trans_code").annotate(n=Count("id"))
    )
    df = pd.DataFrame(list(qs))
    df["ym"] = pd.to_datetime(df["m"]).dt.strftime("%Y-%m")
    w = df.pivot(index="ym", columns="trans_code", values="n").fillna(0)
    w["bs"] = w["P"] / (w["P"] + w["S"]) * 100

    sp = pd.read_csv(os.path.join(ROOT, "analysis", "sp500_monthly.csv")).set_index("month")
    sp["dd"] = (sp["close"] / sp["close"].cummax() - 1) * 100
    w = w.join(sp)
    w.index = pd.to_datetime(w.index + "-01")
    return w.sort_index()


def main():
    """Render the title-less hero chart with the market overlay."""
    w = buy_share()
    med = w["bs"].median()
    r = w["bs"].corr(w["dd"])
    rtxt = f"{r:.2f}"
    # robustness: the link is not a single-episode (COVID) artefact
    ex20 = w[w.index.year != 2020]
    y22 = w[w.index.year == 2022]
    r_ex, r_22, n = ex20["bs"].corr(ex20["dd"]), y22["bs"].corr(y22["dd"]), len(w)

    plt.rcParams.update({"font.family": "sans-serif",
                         "font.sans-serif": ["DejaVu Sans"]})
    # wider/shorter so it fills the slide width -> larger effective fonts
    fig, ax = plt.subplots(figsize=(12.5, 4.7))
    fig.subplots_adjust(top=0.93, bottom=0.25, left=0.085, right=0.915)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    # bars: insider buy-share - green above the median, red below
    colors = [C["purchase"] if v >= med else BELOW for v in w["bs"]]
    ax.bar(w.index, w["bs"], width=22, color=colors, zorder=3)
    ax.axhline(med, color=C["text"], lw=1.2, ls="--", zorder=2)
    ax.text(w.index[-1], med + 1.2, f" median {med:.0f}%", ha="right",
            fontsize=15, color=C["text"])
    ax.set_ylim(0, 80)  # headroom at the top for the callout band
    ax.set_ylabel("Insider buy-share, % (by count)", fontsize=16)
    ax.tick_params(axis="both", labelsize=15)
    for sp_ in ("top", "right", "left"):
        ax.spines[sp_].set_visible(False)
    ax.margins(x=0.01)

    # overlay line: S&P 500 drawdown from peak (right axis)
    ax2 = ax.twinx()
    ax2.plot(w.index, w["dd"], color=MKT, lw=3.0, zorder=4)
    ax2.set_ylim(-38, 16)  # headroom so the line stays clear of the callout band
    ax2.set_ylabel("S&P 500 drawdown from peak (%)", fontsize=15, color=MKT)
    ax2.tick_params(axis="y", labelsize=15, labelcolor=MKT)
    for sp_ in ("top", "left"):
        ax2.spines[sp_].set_visible(False)
    ax2.spines["right"].set_color(MKT)

    # correlation callout in the empty band at the top - drawn on the twin
    # axis (above the line) and clear of the bars thanks to the headroom
    ax2.text(0.012, 0.99,
             f"Buy-share vs. S&P 500 drawdown:   r = {rtxt}",
             transform=ax2.transAxes, ha="left", va="top", fontsize=16,
             fontweight="bold", color=C["text"], zorder=6,
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=C["purchase"], lw=1.5))
    ax2.text(0.99, 0.97,
             "buy-share = purchases / (purchases + sales)",
             transform=ax2.transAxes, ha="right", va="top", fontsize=12.5,
             color=C["subtitle"], zorder=6)
    ax2.text(0.012, 0.81,
             f"robust: excl. 2020  r = {r_ex:.2f}    -    2022 alone  r = {r_22:.2f}"
             f"    -    n = {n} months (descriptive)",
             transform=ax2.transAxes, ha="left", va="top", fontsize=11.5,
             color=C["subtitle"], zorder=6,
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"))

    legend = [
        mpatches.Patch(color=C["purchase"], label="insider buy-share, above median"),
        mpatches.Patch(color=BELOW, label="insider buy-share, below median"),
        Line2D([0], [0], color=MKT, lw=3.0, label="S&P 500 drawdown (right axis)"),
    ]
    ax.legend(handles=legend, loc="upper center", ncol=3, frameon=False,
              fontsize=14, bbox_to_anchor=(0.5, -0.16))

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "v2_buyshare_crashes.png")
    fig.savefig(path, dpi=200, facecolor=C["bg"])
    plt.close(fig)
    print(f"saved {path}  (r={r:.2f}, median={med:.1f}%)")


if __name__ == "__main__":
    main()
