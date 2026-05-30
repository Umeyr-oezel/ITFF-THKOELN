# SEC Form 4 Data Pipeline

Automated pipeline that downloads, processes, and analyzes SEC Form 4 insider transaction data for the year 2025.

Built for the IT for Finance course (Group 01).

## Setup

1. Make sure you have Python 3.10+ installed.

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your MySQL credentials:
   ```
   cp .env.example .env
   ```
   Then edit `.env` with your actual DB host, port, user, and password.

4. Run the pipeline:
   ```
   python main.py
   ```

That's it. The pipeline handles everything automatically - downloading the data from SEC, parsing, cleaning, importing into MySQL, running validation checks, and generating the evaluation charts + PDF report.

## What it does

- Downloads all available 2025 quarterly ZIP files from the SEC website
- Parses the TSV files and prepares them for the database
- Creates the MySQL schema and imports everything (idempotent - safe to re-run)
- Validates transactions (mandatory field checks, price/quantity checks, date logic, etc.)
- Generates monthly Top-5 / Bottom-5 insider trading charts, CSV tables, and a summary PDF

## Output

After running, you'll find:
- `output/charts/monthly/` - bar charts per month (purchases + sales, 3 metrics each)
- `output/charts/overview/` - trend, sentiment, and heatmap charts
- `output/tables/monthly/` - CSV exports of the ranking data
- `output/2025_evaluation_report.pdf` - full report with all charts
- `logs/pipeline.log` - detailed log of the pipeline run

## Project structure

```
config.py              Central configuration (.env loader)
main.py                Entry point
modules/
  downloader.py        SEC ZIP download with retry logic
  parser.py            ZIP extraction + TSV/JSON parsing
  data_preparation.py  Data cleaning, type conversion, owner merge
  db_manager.py        MySQL schema setup + idempotent import
  validation.py        8 plausibility checks (4 mandatory + 4 bonus)
  evaluation.py        Charts, CSV export, PDF report
```

## Notes

- The pipeline needs a MySQL server. Connection details go in `.env`, never in the code.
- First run downloads ~80 MB of ZIP files from SEC. Subsequent runs skip existing files.
- Re-running the pipeline deletes and re-imports all data (delete-then-insert), so the database always reflects the latest processing. The `pipeline_log` table is never deleted to keep a full audit trail.