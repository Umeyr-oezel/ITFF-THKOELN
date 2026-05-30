"""
Generates all evaluations: monthly Top-5/Bottom-5 bar charts,
overview charts (trend, sentiment, heatmap), CSV exports,
and an auto-generated PDF report.
"""
import os
import logging
import time

import matplotlib
matplotlib.use("Agg")  # no GUI needed
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402
import seaborn as sns  # noqa: E402, F401
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import text  # noqa: E402

from modules import get_engine  # noqa: E402
import config  # noqa: E402

logger = logging.getLogger(__name__)


def _retry_query(engine, query_func, max_retries=3):
    """Retry a DB query if the connection drops (shared server issue)."""
    import modules as dbm
    last_error = None
    for attempt in range(max_retries):
        try:
            return query_func(engine)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(f"DB query failed (attempt {attempt + 1}): {e}")
                dbm._engine = None
                engine = dbm.get_engine()
                time.sleep(1)
            else:
                raise
    raise last_error

# chart color scheme
COLOR_PURCHASE = "#1a6b54"
COLOR_SALE = "#8b2f3a"
COLOR_BG = "#fafafa"
COLOR_TEXT = "#2d2d2d"
COLOR_GRID = "#e0e0e0"
COLOR_SUBTITLE = "#666666"

# TH Köln logo for branding
LOGO_PATH = os.path.join(os.path.dirname(__file__), os.pardir,
                         "assets", "th_koeln_logo.png")

# each tuple: (trans_code, metric_col, order_col, label, file_tag)
EVALUATIONS = [
    ("P", "total_shares", "total_shares", "Shares Traded", "purchases_by_shares"),
    ("P", "num_transactions", "num_transactions",
     "Number of Transactions", "purchases_by_transactions"),
    ("P", "total_volume", "total_volume",
     "USD Nominal Volume", "purchases_by_volume"),
    ("S", "total_shares", "total_shares",
     "Shares Traded", "sales_by_shares"),
    ("S", "num_transactions", "num_transactions",
     "Number of Transactions", "sales_by_transactions"),
    ("S", "total_volume", "total_volume", "USD Nominal Volume", "sales_by_volume"),
]

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


# --- DB queries ---

def _get_available_months(engine):
    """Which months in TARGET_YEAR actually have valid P or S data?"""
    def _query(eng):
        with eng.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT MONTH(trans_date) AS m
                FROM nonderiv_trans
                WHERE is_valid = 1
                  AND trans_code IN ('P', 'S')
                  AND YEAR(trans_date) = :yr
                ORDER BY m
            """), {"yr": config.TARGET_YEAR}).fetchall()
        return [r[0] for r in rows]
    return _retry_query(engine, _query)


def query_monthly_ranking(engine, trans_code, order_col, month):
    """Top-5 companies for a given metric in one month.

    GROUP BY issuer_cik with MAX() on name/ticker because the
    server has ONLY_FULL_GROUP_BY enabled.
    """
    # ORDER BY needs f-string - MySQL won't accept params there
    sql = f"""
        SELECT
            s.issuer_cik,
            MAX(s.issuer_name) AS issuer_name,
            MAX(s.issuer_ticker) AS issuer_ticker,
            SUM(t.shares) AS total_shares,
            COUNT(*) AS num_transactions,
            SUM(t.nominal_volume) AS total_volume
        FROM nonderiv_trans t
        JOIN submissions s ON t.accession_number = s.accession_number
        WHERE t.trans_code = :code
            AND t.is_valid = 1
            AND YEAR(t.trans_date) = :yr
            AND MONTH(t.trans_date) = :month
        GROUP BY s.issuer_cik
        ORDER BY {order_col} DESC
        LIMIT 5
    """
    def _query(eng):
        with eng.connect() as conn:
            return pd.read_sql(text(sql), conn, params={
                "code": trans_code, "yr": config.TARGET_YEAR, "month": month
            })
    return _retry_query(engine, _query)


# --- Chart helpers ---

def _format_value(val):
    """Turn big numbers into something readable (1.2M, 340K, etc.)."""
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:,.2f}B"
    if val >= 1_000_000:
        return f"{val / 1_000_000:,.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:,.1f}K"
    return f"{val:,.0f}"


def _add_logo(fig):
    """Stick the TH Köln logo + group name in the top-right corner."""
    if not os.path.isfile(LOGO_PATH):
        return
    logo = mpimg.imread(LOGO_PATH)
    logo_x, logo_w = 0.855, 0.09
    logo_y, logo_h = 0.89, 0.09
    ax_logo = fig.add_axes(
        [logo_x, logo_y, logo_w, logo_h], anchor="NE",
    )
    ax_logo.imshow(logo, alpha=0.55)
    ax_logo.axis("off")
    fig.text(
        logo_x + logo_w / 2 + 0.02, logo_y - 0.005,
        "Group 01 - IT for Finance",
        fontsize=6.5, color=COLOR_SUBTITLE, ha="center", va="top",
    )


def _setup_chart_style():
    """Common font settings for all charts."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial"],
    })


# --- Monthly bar charts ---

def create_bar_chart(data, month_num, metric_col, metric_label,
                     trans_type, output_dir):
    """Horizontal bar chart for one top-5 ranking."""
    if data.empty:
        return None

    month_str = f"{config.TARGET_YEAR}-{month_num:02d}"
    month_dir = os.path.join(output_dir, month_str)
    os.makedirs(month_dir, exist_ok=True)
    display_month = f"{MONTH_NAMES[month_num]} {config.TARGET_YEAR}"

    # "TICKER - Company Name" labels
    labels = []
    for _, row in data.iterrows():
        name = row["issuer_name"] or "Unknown"
        ticker = row["issuer_ticker"] or "N/A"
        if len(name) > 30:
            name = name[:27] + "..."
        labels.append(f"{ticker}  -  {name}")

    color = COLOR_PURCHASE if trans_type == "Purchases" else COLOR_SALE
    values = data[metric_col].fillna(0)

    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    bars = ax.barh(
        labels, values, color=color, height=0.55,
        edgecolor="none", zorder=3,
    )

    # annotate values next to each bar
    max_val = values.max() if len(values) else 1
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + max_val * 0.015,
            bar.get_y() + bar.get_height() / 2,
            _format_value(val),
            va="center", fontsize=9.5, color=COLOR_TEXT,
            fontweight="medium",
        )

    # clean look: no frames, no x-axis, subtle grid
    ax.set_xlim(0, max_val * 1.18)
    ax.xaxis.set_visible(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="y", length=0, labelsize=10, labelcolor=COLOR_TEXT)
    ax.grid(axis="x", color=COLOR_GRID, linewidth=0.5, zorder=0)
    ax.invert_yaxis()

    title_prefix = "Top 5 Insider" if trans_type == "Purchases" else "Bottom 5 Insider"
    fig.text(
        0.06, 0.96,
        f"{title_prefix} {trans_type}  |  {metric_label}",
        fontsize=14, fontweight="bold", color=COLOR_TEXT, va="top",
    )
    fig.text(
        0.06, 0.91, display_month,
        fontsize=11, color=COLOR_SUBTITLE, va="top",
    )

    plt.subplots_adjust(top=0.84, left=0.28, right=0.92, bottom=0.06)

    _add_logo(fig)

    filename = (
        f"{trans_type.lower()}_by_"
        f"{metric_label.lower().replace(' ', '_')}.png"
    )
    filepath = os.path.join(month_dir, filename)
    plt.savefig(filepath, dpi=200, facecolor=COLOR_BG)
    plt.close()

    return filepath


# --- Overview charts (year-level) ---

def _query_monthly_totals(engine):
    """Aggregated P/S totals per month - used by trend + sentiment charts."""
    sql = text("""
        SELECT
            MONTH(t.trans_date) AS month_num,
            t.trans_code,
            SUM(t.shares) AS total_shares,
            COUNT(*) AS num_transactions,
            SUM(t.nominal_volume) AS total_volume
        FROM nonderiv_trans t
        WHERE t.is_valid = 1
          AND t.trans_code IN ('P', 'S')
          AND YEAR(t.trans_date) = :yr
        GROUP BY MONTH(t.trans_date), t.trans_code
        ORDER BY month_num
    """)
    def _query(eng):
        with eng.connect() as conn:
            return pd.read_sql(sql, conn, params={"yr": config.TARGET_YEAR})
    return _retry_query(engine, _query)


def create_trend_chart(engine, output_dir):
    """Line chart comparing monthly purchase vs sale volume."""
    df = _query_monthly_totals(engine)
    if df.empty:
        return None

    purchases = df[df["trans_code"] == "P"].set_index("month_num")
    sales = df[df["trans_code"] == "S"].set_index("month_num")

    months = sorted(df["month_num"].unique())
    month_labels = [MONTH_NAMES[m][:3] for m in months]

    p_vals = [purchases.loc[m, "total_volume"] if m in purchases.index else 0
              for m in months]
    s_vals = [sales.loc[m, "total_volume"] if m in sales.index else 0
              for m in months]

    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    x_pos = list(range(len(month_labels)))

    ax.plot(x_pos, [v / 1e9 for v in p_vals],
            color=COLOR_PURCHASE, linewidth=2.5, marker="o",
            markersize=7, label="Purchases", zorder=3)
    ax.plot(x_pos, [v / 1e9 for v in s_vals],
            color=COLOR_SALE, linewidth=2.5, marker="s",
            markersize=7, label="Sales", zorder=3)

    # subtle fill under the lines
    ax.fill_between(x_pos, [v / 1e9 for v in p_vals],
                    alpha=0.08, color=COLOR_PURCHASE, zorder=2)
    ax.fill_between(x_pos, [v / 1e9 for v in s_vals],
                    alpha=0.08, color=COLOR_SALE, zorder=2)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(month_labels)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.5, zorder=0)
    ax.tick_params(axis="both", length=0, labelsize=10, labelcolor=COLOR_TEXT)
    ax.set_ylabel("Volume (Billion USD)", fontsize=10, color=COLOR_TEXT)

    ax.legend(frameon=False, fontsize=10, loc="upper right")

    fig.text(
        0.06, 0.96,
        f"Monthly Insider Transaction Volume  |  {config.TARGET_YEAR}",
        fontsize=14, fontweight="bold", color=COLOR_TEXT, va="top",
    )
    fig.text(
        0.06, 0.91, "Purchases vs Sales - USD Nominal Volume",
        fontsize=11, color=COLOR_SUBTITLE, va="top",
    )

    plt.subplots_adjust(top=0.84, left=0.10, right=0.92, bottom=0.10)
    _add_logo(fig)

    filepath = os.path.join(output_dir, f"{config.TARGET_YEAR}_trend_volume.png")
    plt.savefig(filepath, dpi=200, facecolor=COLOR_BG)
    plt.close()
    logger.info(f"  Created trend chart: {filepath}")
    return filepath


def create_sentiment_chart(engine, output_dir):
    """P/S ratio per month - above 1.0 means more buying than selling."""
    df = _query_monthly_totals(engine)
    if df.empty:
        return None

    purchases = df[df["trans_code"] == "P"].set_index("month_num")
    sales = df[df["trans_code"] == "S"].set_index("month_num")

    months = sorted(df["month_num"].unique())
    month_labels = [MONTH_NAMES[m][:3] for m in months]

    ratios = []
    for m in months:
        p_vol = purchases.loc[m, "total_volume"] if m in purchases.index else 0
        s_vol = sales.loc[m, "total_volume"] if m in sales.index else 0
        ratios.append(p_vol / s_vol if s_vol > 0 else 0)

    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    # green = bullish (ratio >= 1), red = bearish
    x_pos = list(range(len(month_labels)))
    colors = [COLOR_PURCHASE if r >= 1.0 else COLOR_SALE for r in ratios]
    bars = ax.bar(x_pos, ratios, color=colors, width=0.5,
                  edgecolor="none", zorder=3)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(month_labels)

    ax.axhline(y=1.0, color=COLOR_TEXT, linewidth=1, linestyle="--",
               alpha=0.4, zorder=2)
    ax.text(len(months) - 0.5, 1.02, "Neutral (1.0)",
            fontsize=8, color=COLOR_SUBTITLE, ha="right", va="bottom")

    for bar, ratio in zip(bars, ratios):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{ratio:.2f}", ha="center", va="bottom",
                fontsize=9, color=COLOR_TEXT, fontweight="medium")

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.5, zorder=0)
    ax.tick_params(axis="both", length=0, labelsize=10, labelcolor=COLOR_TEXT)
    ax.set_ylabel("P/S Ratio", fontsize=10, color=COLOR_TEXT)
    ax.set_ylim(0, max(ratios) * 1.25 if ratios else 2)

    fig.text(
        0.06, 0.96,
        f"Insider Sentiment Index  |  {config.TARGET_YEAR}",
        fontsize=14, fontweight="bold", color=COLOR_TEXT, va="top",
    )
    fig.text(
        0.06, 0.91,
        "Purchase / Sale Volume Ratio - above 1.0 = bullish signal",
        fontsize=11, color=COLOR_SUBTITLE, va="top",
    )

    plt.subplots_adjust(top=0.84, left=0.10, right=0.92, bottom=0.10)
    _add_logo(fig)

    filepath = os.path.join(output_dir,
                            f"{config.TARGET_YEAR}_sentiment_index.png")
    plt.savefig(filepath, dpi=200, facecolor=COLOR_BG)
    plt.close()
    logger.info(f"  Created sentiment chart: {filepath}")
    return filepath


def create_heatmap(engine, output_dir):
    """Heatmap of companies that keep showing up in Top-5 sales.

    Only shows companies present in at least 2 different months.
    Cells show rank position (#1-#5), darker = higher rank.
    """
    months = _get_available_months(engine)
    if not months:
        return None

    # grab top-5 sales (by volume) for each month
    all_rankings = []
    for month in months:
        df = query_monthly_ranking(engine, "S", "total_volume", month)
        if df.empty:
            continue
        df["month_num"] = month
        df["rank"] = range(1, len(df) + 1)
        all_rankings.append(df[["issuer_cik", "issuer_name",
                                "issuer_ticker", "month_num", "rank"]])

    if not all_rankings:
        return None

    combined = pd.concat(all_rankings, ignore_index=True)

    # filter: at least 2 months
    appearance_counts = combined.groupby("issuer_cik").size()
    repeat_ciks = appearance_counts[appearance_counts >= 2].index
    repeat_df = combined[combined["issuer_cik"].isin(repeat_ciks)]

    if repeat_df.empty:
        return None

    labels = {}
    for _, row in repeat_df.iterrows():
        cik = row["issuer_cik"]
        if cik not in labels:
            name = row["issuer_name"] or "Unknown"
            ticker = row["issuer_ticker"] or "N/A"
            if len(name) > 25:
                name = name[:22] + "..."
            labels[cik] = f"{ticker} - {name}"

    # pivot into a matrix: companies x months
    pivot = repeat_df.pivot_table(
        index="issuer_cik", columns="month_num",
        values="rank", aggfunc="first",
    )
    pivot = pivot.reindex(columns=months)

    # most frequent sellers on top
    pivot["count"] = pivot.notna().sum(axis=1)
    pivot = pivot.sort_values("count", ascending=False).drop(
        columns="count",
    )

    # cap at 15 rows so it stays readable
    pivot = pivot.head(15)

    month_labels = [MONTH_NAMES[m][:3] for m in months]
    company_labels = [labels.get(cik, str(cik)) for cik in pivot.index]

    _setup_chart_style()
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    data_matrix = pivot.values.astype(float)

    # rank 1 = darkest, rank 5 = lightest
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(
        "rank", [COLOR_SALE, "#e8b4b8", "#f5e6e8"], N=5,
    )
    cmap.set_bad(color=COLOR_BG)

    masked = np.ma.masked_invalid(data_matrix)
    ax.imshow(masked, cmap=cmap, aspect="auto", vmin=1, vmax=5)

    # show rank numbers in each cell
    for i in range(data_matrix.shape[0]):
        for j in range(data_matrix.shape[1]):
            val = data_matrix[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"#{int(val)}", ha="center", va="center",
                        fontsize=9, color="white" if val <= 2 else COLOR_TEXT,
                        fontweight="bold")

    ax.set_xticks(range(len(month_labels)))
    ax.set_xticklabels(month_labels, fontsize=10)
    ax.set_yticks(range(len(company_labels)))
    ax.set_yticklabels(company_labels, fontsize=9)
    ax.tick_params(length=0, labelcolor=COLOR_TEXT)

    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.text(
        0.06, 0.96,
        f"Repeat Insider Sellers  |  {config.TARGET_YEAR}",
        fontsize=14, fontweight="bold", color=COLOR_TEXT, va="top",
    )
    fig.text(
        0.06, 0.91,
        "Companies appearing in Top-5 Sales (by Volume) across "
        "multiple months",
        fontsize=11, color=COLOR_SUBTITLE, va="top",
    )

    plt.subplots_adjust(
        top=0.84, left=0.25, right=0.92, bottom=0.06,
    )
    _add_logo(fig)

    filepath = os.path.join(
        output_dir, f"{config.TARGET_YEAR}_repeat_sellers_heatmap.png",
    )
    plt.savefig(filepath, dpi=200, facecolor=COLOR_BG)
    plt.close()
    logger.info(f"  Created heatmap: {filepath}")
    return filepath


# --- CSV export ---

def export_table(data, month_num, metric_label, trans_type, output_dir):
    """Dump a ranking result to CSV."""
    if data.empty:
        return None

    month_str = f"{config.TARGET_YEAR}-{month_num:02d}"
    month_dir = os.path.join(output_dir, month_str)
    os.makedirs(month_dir, exist_ok=True)
    filename = (
        f"{trans_type.lower()}_by_"
        f"{metric_label.lower().replace(' ', '_')}.csv"
    )
    filepath = os.path.join(month_dir, filename)
    data.to_csv(filepath, index=False)
    return filepath


# --- PDF report ---

def generate_pdf_report(engine, monthly_charts_dir,
                        overview_charts_dir, output_dir):
    """Build a PDF with title page, stats, overview charts, and monthly charts."""
    from fpdf import FPDF

    year = config.TARGET_YEAR
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # title page
    pdf.add_page()
    if os.path.isfile(LOGO_PATH):
        pdf.image(LOGO_PATH, x=220, y=10, w=50)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_y(60)
    pdf.cell(0, 15, "SEC Form 4 Insider Transactions", align="C", ln=True)
    pdf.set_font("Helvetica", "", 18)
    pdf.cell(0, 12, f"Annual Report {year}", align="C", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Group 01 - IT for Finance", align="C", ln=True)
    pdf.cell(0, 10, "TH Koeln", align="C", ln=True)
    pdf.set_text_color(0, 0, 0)

    # pipeline stats
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Pipeline Summary", ln=True)
    pdf.ln(5)

    stats = _get_pipeline_stats(engine)
    pdf.set_font("Helvetica", "", 12)
    for label, value in stats:
        pdf.cell(120, 8, label, ln=False)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, str(value), ln=True)
        pdf.set_font("Helvetica", "", 12)

    # overview charts
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"Year Overview {year}", ln=True)
    pdf.ln(3)

    overview_files = [
        f"{year}_trend_volume.png",
        f"{year}_sentiment_index.png",
        f"{year}_repeat_sellers_heatmap.png",
    ]
    for fname in overview_files:
        fpath = os.path.join(overview_charts_dir, fname)
        if os.path.isfile(fpath):
            pdf.image(fpath, x=10, w=270)
            pdf.ln(5)

    # monthly breakdown
    months = _get_available_months(engine)
    for month in months:
        month_str = f"{year}-{month:02d}"
        display = f"{MONTH_NAMES[month]} {year}"

        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, display, ln=True)
        pdf.ln(2)

        metrics = [
            "shares_traded", "number_of_transactions",
            "usd_nominal_volume",
        ]
        for trans in ["purchases", "sales"]:
            for metric in metrics:
                fname = f"{trans}_by_{metric}.png"
                fpath = os.path.join(
                    monthly_charts_dir, month_str, fname,
                )
                if os.path.isfile(fpath):
                    if pdf.get_y() > 140:
                        pdf.add_page()
                        pdf.set_font("Helvetica", "B", 18)
                        pdf.cell(
                            0, 12, f"{display} (continued)", ln=True,
                        )
                        pdf.ln(2)
                    pdf.image(fpath, x=10, w=270)
                    pdf.ln(3)

    pdf_path = os.path.join(output_dir, f"{year}_evaluation_report.pdf")
    pdf.output(pdf_path)
    logger.info(f"  Created PDF report: {pdf_path}")
    return pdf_path


def _get_pipeline_stats(engine):
    """Pull key numbers from the DB for the PDF summary page."""
    def _query(eng):
        return _get_pipeline_stats_inner(eng)
    return _retry_query(engine, _query)


def _get_pipeline_stats_inner(engine):
    """Actually runs the stats queries (separated for retry wrapper)."""
    stats = []
    with engine.connect() as conn:
        n_sub = conn.execute(
            text("SELECT COUNT(*) FROM submissions")
        ).scalar()
        stats.append(("Total Submissions (Filings)", f"{n_sub:,}"))

        n_nd = conn.execute(
            text("SELECT COUNT(*) FROM nonderiv_trans")
        ).scalar()
        stats.append(("Non-Derivative Transactions", f"{n_nd:,}"))

        n_dt = conn.execute(
            text("SELECT COUNT(*) FROM deriv_trans")
        ).scalar()
        stats.append(("Derivative Transactions", f"{n_dt:,}"))

        n_valid_nd = conn.execute(
            text("SELECT COUNT(*) FROM nonderiv_trans WHERE is_valid = 1")
        ).scalar()
        pct_nd = (n_valid_nd / n_nd * 100) if n_nd else 0
        stats.append((
            "Valid Non-Deriv Transactions",
            f"{n_valid_nd:,} ({pct_nd:.1f}%)",
        ))

        n_valid_dt = conn.execute(
            text("SELECT COUNT(*) FROM deriv_trans WHERE is_valid = 1")
        ).scalar()
        pct_dt = (n_valid_dt / n_dt * 100) if n_dt else 0
        stats.append((
            "Valid Deriv Transactions",
            f"{n_valid_dt:,} ({pct_dt:.1f}%)",
        ))

        n_vlog = conn.execute(
            text("SELECT COUNT(*) FROM validation_log")
        ).scalar()
        stats.append(("Validation Log Entries", f"{n_vlog:,}"))

        quarters = conn.execute(text(
            "SELECT DISTINCT source_quarter FROM submissions "
            "ORDER BY source_quarter"
        )).fetchall()
        q_list = ", ".join(r[0] for r in quarters)
        stats.append(("Quarters Loaded", q_list))

        n_companies = conn.execute(text(
            "SELECT COUNT(DISTINCT issuer_cik) FROM submissions"
        )).scalar()
        stats.append(("Unique Companies (Issuers)", f"{n_companies:,}"))

        n_insiders = conn.execute(text(
            "SELECT COUNT(DISTINCT rptowner_cik) FROM submissions"
        )).scalar()
        stats.append(("Unique Insiders (Reporters)", f"{n_insiders:,}"))

    return stats


# --- Main orchestration ---

def generate_all_evaluations():
    """Run everything: monthly charts + CSVs, overview charts, PDF.

    For each month with data: 6 bar charts (3 purchase metrics,
    3 sale metrics) plus matching CSV tables.
    """
    engine = get_engine()

    os.makedirs(config.CHARTS_DIR, exist_ok=True)
    os.makedirs(config.CHARTS_OVERVIEW_DIR, exist_ok=True)
    os.makedirs(config.TABLES_DIR, exist_ok=True)

    months = _get_available_months(engine)
    logger.info(f"Generating evaluations for {len(months)} months...")

    chart_count = 0
    csv_count = 0

    for month in months:
        for trans_code, metric_col, order_col, metric_label, file_tag in EVALUATIONS:
            trans_type = "Purchases" if trans_code == "P" else "Sales"

            df = query_monthly_ranking(engine, trans_code, order_col, month)

            if df.empty:
                logger.info(
                    f"  {config.TARGET_YEAR}-{month:02d} {trans_type}/{metric_label}: "
                    f"no data, skipping"
                )
                continue

            chart_path = create_bar_chart(
                df, month, metric_col, metric_label,
                trans_type, config.CHARTS_DIR
            )
            if chart_path:
                chart_count += 1

            csv_path = export_table(
                df, month, metric_label, trans_type, config.TABLES_DIR
            )
            if csv_path:
                csv_count += 1

        logger.info(f"  {config.TARGET_YEAR}-{month:02d}: done")

    # year-level overview
    create_trend_chart(engine, config.CHARTS_OVERVIEW_DIR)
    create_sentiment_chart(engine, config.CHARTS_OVERVIEW_DIR)
    create_heatmap(engine, config.CHARTS_OVERVIEW_DIR)

    generate_pdf_report(
        engine, config.CHARTS_DIR,
        config.CHARTS_OVERVIEW_DIR, config.OUTPUT_DIR,
    )

    logger.info(
        f"Evaluation complete: {chart_count + 3} charts, {csv_count} CSVs "
        f"for {len(months)} months"
    )
