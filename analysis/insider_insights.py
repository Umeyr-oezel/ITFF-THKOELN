"""Presentation analysis for Aufgabe 1 (Team 1).

Reads the same database the pipeline fills and looks for the story angles
that make an audience sit up: the all-time buy/sell picture across
2020-2025 and, above all, the COVID-19 crash of March 2020, when
corporate insiders bought their own stock into a collapsing market.

This is a standalone presentation tool. It only reads the models, never
writes to them, so it stays clear of the pipeline code Team 2 reviews.
Charts are rendered presentation-grade (TH Koeln logo, brand colours)
into output/presentation/.
"""
import os
import sys

import django

# Run from anywhere: make sure the project root (where secpipeline lives)
# is importable even though this script sits in analysis/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "secpipeline.settings")
django.setup()

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from django.db.models import Count, Sum  # noqa: E402
from django.db.models.functions import TruncMonth  # noqa: E402

import config  # noqa: E402
from pipeline.models import NonderivTrans  # noqa: E402

OUT_DIR = os.path.join(config.OUTPUT_DIR, "presentation")
C = config.CHART_COLORS
COVID = pd.Timestamp("2020-03-01")

# "Bare" mode (PRES_BARE=1): drop the baked-in title/logo/source so the chart
# can sit under a native PowerPoint title. Files get a _bare.png suffix.
BARE = os.getenv("PRES_BARE") == "1"


def usd(val):
    """Compact USD label: $1.2B, $340M, $5K."""
    a = abs(val)
    if a >= 1e9:
        return f"${val / 1e9:,.1f}B"
    if a >= 1e6:
        return f"${val / 1e6:,.0f}M"
    if a >= 1e3:
        return f"${val / 1e3:,.0f}K"
    return f"${val:,.0f}"


def load_monthly():
    """Monthly purchase/sale totals across the configured years.

    Restricted to valid non-derivative P/S rows whose transaction date
    actually falls inside 2020-2025 - late or mis-keyed filing dates would
    otherwise smear the timeline.
    """
    qs = (
        NonderivTrans.objects
        .filter(
            is_valid=True,
            trans_code__in=["P", "S"],
            trans_date__year__gte=config.START_YEAR,
            trans_date__year__lte=config.END_YEAR,
        )
        .annotate(month=TruncMonth("trans_date"))
        .values("month", "trans_code")
        .annotate(volume=Sum("nominal_volume"), n=Count("id"))
        .order_by("month")
    )
    df = pd.DataFrame(list(qs))
    df["month"] = pd.to_datetime(df["month"])
    df["volume"] = pd.to_numeric(df["volume"]).fillna(0)
    return df


def to_wide(df):
    """Pivot the tidy frame to one row per month with P/S columns."""
    vol = df.pivot(index="month", columns="trans_code", values="volume").fillna(0)
    cnt = df.pivot(index="month", columns="trans_code", values="n").fillna(0)
    wide = pd.DataFrame({
        "buy_vol": vol.get("P", 0),
        "sell_vol": vol.get("S", 0),
        "buy_n": cnt.get("P", 0),
        "sell_n": cnt.get("S", 0),
    })
    wide["buy_share"] = wide["buy_n"] / (wide["buy_n"] + wide["sell_n"]) * 100
    return wide.sort_index()


def report(df, wide):
    """Print the count-based facts we can safely quote on stage.

    Dollar volume is deliberately left out of the headline: a handful of
    micro-cap filings carry absurd nominal_volume values (shares x price
    overflow), so USD totals are not trustworthy. Transaction counts are.
    """
    total_buy_n = int(wide["buy_n"].sum())
    total_sell_n = int(wide["sell_n"].sum())
    total_n = total_buy_n + total_sell_n
    avg_buy = total_buy_n / len(wide)

    print("\n" + "=" * 64)
    print("  INSIDER TRADING 2020-2025 - ALL-TIME FACTS (count-based)")
    print("=" * 64)
    print(f"  Valid P/S transactions : {total_n:,}")
    print(f"  Purchases (P)          : {total_buy_n:,}")
    print(f"  Sales (S)              : {total_sell_n:,}")
    print(f"  Sell-to-buy count ratio: {total_sell_n / total_buy_n:,.1f} : 1")
    print(f"  Insider buy share (#)  : {total_buy_n / total_n * 100:,.1f}%")
    print(f"  Avg purchases / month  : {avg_buy:,.0f}")

    print("\n  -- Monthly buy share extremes (by transaction count) --")
    hi = wide["buy_share"].idxmax()
    lo = wide["buy_share"].idxmin()
    print(f"  Most bullish month : {hi:%b %Y}  ->  {wide.loc[hi, 'buy_share']:.1f}% buys")
    print(f"  Most bearish month : {lo:%b %Y}  ->  {wide.loc[lo, 'buy_share']:.1f}% buys")

    if COVID in wide.index:
        med = wide["buy_share"].median()
        c = wide.loc[COVID]
        print("\n  -- COVID shock (March 2020) --")
        print(f"  Buy share Mar 2020 : {c['buy_share']:.1f}%  (median month {med:.1f}%)")
        print(f"  Purchases Mar 2020 : {int(c['buy_n']):,}  "
              f"({c['buy_n'] / avg_buy:.1f}x a normal month)")
        print(f"  Rank of Mar 2020 buy share among all {len(wide)} months: "
              f"#{int((wide['buy_share'] > c['buy_share']).sum()) + 1}")

    print("\n  -- DATA-QUALITY NOTE (relevant fuer Aufgabe 2) --")
    print("  nominal_volume has micro-cap outliers (e.g. WIKISOFT '$34T'),")
    print("  so USD totals are unreliable. Validation checks price < 1M but")
    print("  never sanity-checks shares x price. Count metrics are clean.")
    print("=" * 64 + "\n")


# --- charts ---

def _style():
    """Shared seaborn/matplotlib look for every chart."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "axes.edgecolor": C["grid"],
        "axes.labelcolor": C["text"],
        "text.color": C["text"],
        "xtick.color": C["subtitle"],
        "ytick.color": C["subtitle"],
        "axes.grid.axis": "y",
    })


def _add_logo(fig):
    """Place the transparent TH Koeln logo in the top-right corner."""
    if BARE:
        return
    if not os.path.isfile(config.LOGO_PATH):
        return
    logo = mpimg.imread(config.LOGO_PATH)
    ax = fig.add_axes([0.865, 0.895, 0.10, 0.10], anchor="NE", zorder=20)
    ax.imshow(logo)
    ax.axis("off")
    fig.text(0.915, 0.885, "Group 01 - IT for Finance",
             fontsize=7, color=C["subtitle"], ha="center", va="top")


def _titles(fig, ax, title, subtitle):
    """Left-aligned headline + grey subtitle, with a SEC source note."""
    if BARE:
        return
    fig.text(0.065, 0.95, title, fontsize=19, fontweight="bold", color=C["text"])
    fig.text(0.065, 0.905, subtitle, fontsize=11.5, color=C["subtitle"])
    fig.text(0.065, 0.02, "Source: SEC EDGAR Form 4 (non-derivative) - Group 01",
             fontsize=8, color=C["subtitle"])


def chart_trend(wide):
    """All-time monthly purchase vs sale activity (counts), COVID annotated.

    Counts rather than USD: the dollar figures are corrupted by micro-cap
    outliers, but the number of filed transactions is solid.
    """
    _style()
    fig, ax = plt.subplots(figsize=(13, 6.6))
    fig.subplots_adjust(top=(0.95 if BARE else 0.82), bottom=0.12, left=0.09, right=0.95)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    x = wide.index
    ax.fill_between(x, wide["sell_n"], color=C["sale"], alpha=0.10)
    ax.fill_between(x, wide["buy_n"], color=C["purchase"], alpha=0.16)
    ax.plot(x, wide["sell_n"], color=C["sale"], lw=2.4, label="Sales (S)")
    ax.plot(x, wide["buy_n"], color=C["purchase"], lw=2.4, label="Purchases (P)")

    ax.axvline(COVID, color=C["text"], ls="--", lw=1, alpha=0.5)
    ax.annotate("COVID crash - March 2020\ninsider buying spikes",
                xy=(COVID, wide.loc[COVID, "buy_n"]),
                xytext=(25, 35), textcoords="offset points",
                fontsize=10.5, fontweight="bold", color=C["purchase"],
                arrowprops=dict(arrowstyle="->", color=C["purchase"], alpha=0.7))

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1000:.0f}K"))
    ax.set_ylabel("Insider transactions per month")
    ax.margins(x=0.01)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=11)
    _titles(fig, ax, "Insider Trading Activity 2020-2025",
            "Monthly number of insider purchase vs. sale transactions")
    _add_logo(fig)
    _save(fig, "trend_all_time.png")


def chart_sentiment(wide):
    """Monthly insider buy share (%) - the COVID buying spike is the shock."""
    _style()
    fig, ax = plt.subplots(figsize=(13, 6.6))
    fig.subplots_adjust(top=(0.95 if BARE else 0.82), bottom=0.12, left=0.08, right=0.95)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    colors = [C["purchase"] if m == COVID else
              (C["purchase"] if v >= 50 else C["sale"]) for m, v in
              zip(wide.index, wide["buy_share"])]
    alphas = [1.0 if m == COVID else 0.35 for m in wide.index]
    ax.bar(wide.index, wide["buy_share"], width=22,
           color=colors, alpha=1.0)
    for bar, a in zip(ax.patches, alphas):
        bar.set_alpha(a)

    ax.axhline(50, color=C["text"], lw=1, alpha=0.4)
    ax.text(wide.index[-16], 51.5, "50% = balance (buys = sells)",
            fontsize=9, color=C["subtitle"], ha="left")

    if COVID in wide.index:
        cv = wide.loc[COVID, "buy_share"]
        ax.annotate(f"March 2020: {cv:.0f}% buys\n(#1 of 72 months)",
                    xy=(COVID, cv), xytext=(40, -34),
                    textcoords="offset points", fontsize=11,
                    fontweight="bold", color=C["purchase"],
                    arrowprops=dict(arrowstyle="->", color=C["purchase"]))

    ax.set_ylabel("Share of insider transactions that are purchases (%)")
    ax.set_ylim(0, max(60, wide["buy_share"].max() * 1.15))
    ax.margins(x=0.01)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    _titles(fig, ax, "When the market crashed, insiders bought",
            "Share of insider transactions that are purchases - the March 2020 (COVID) spike")
    _add_logo(fig)
    _save(fig, "sentiment_all_time.png")


def chart_covid_buyers():
    """Who bought the March-2020 panic - top issuers by purchase count.

    Count-based and therefore immune to the dollar-volume data issues.
    """
    qs = (
        NonderivTrans.objects
        .filter(is_valid=True, trans_code="P",
                trans_date__year=2020, trans_date__month=3)
        .values("submission__issuer_ticker", "submission__issuer_name")
        .annotate(n=Count("id"))
        .order_by("-n")[:12]
    )
    labels, vals = [], []
    for r in qs:
        name = r["submission__issuer_name"] or "Unknown"
        if len(name) > 26:
            name = name[:23] + "..."
        labels.append(f"{r['submission__issuer_ticker'] or '?'}  -  {name}")
        vals.append(r["n"])

    _style()
    fig, ax = plt.subplots(figsize=(13, 6.6))
    fig.subplots_adjust(top=(0.95 if BARE else 0.82), bottom=0.10, left=0.32, right=0.94)
    fig.patch.set_facecolor(C["bg"])
    ax.set_facecolor(C["bg"])

    y = range(len(labels))
    # green gradient: the most active buyer gets the deepest colour
    grad = list(reversed(sns.color_palette("crest", len(vals))))
    ax.barh(y, vals, color=grad, height=0.62, zorder=3)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, f"{v}", va="center",
                fontsize=10, fontweight="medium", color=C["text"])
    ax.set_xlim(0, max(vals) * 1.14)
    ax.xaxis.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(axis="y", length=0)
    _titles(fig, ax, "Who bought the crash? (March 2020)",
            "Top companies by number of insider purchases in March 2020")
    _add_logo(fig)
    _save(fig, "covid_buyers.png")


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
    """Run the analysis and render every presentation chart."""
    df = load_monthly()
    wide = to_wide(df)
    report(df, wide)
    chart_trend(wide)
    chart_sentiment(wide)
    chart_covid_buyers()


if __name__ == "__main__":
    main()
