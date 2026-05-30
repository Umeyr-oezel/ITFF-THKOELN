# SEC Form 4 Data Pipeline

Automated pipeline that downloads, processes, and analyzes SEC Form 4 insider transaction data for the year 2025.

Built for the IT for Finance course (Group 01).

The database layer uses the **Django ORM with PostgreSQL**. Django is used purely as an ORM here - there is no web frontend, login, or admin panel.

## Setup

1. Make sure you have Python 3.12+ installed.

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your PostgreSQL credentials:
   ```
   cp .env.example .env
   ```
   Then edit `.env` with your actual DB name, host, port, user, and password.

4. Create the database schema (runs the Django migrations):
   ```
   python manage.py migrate
   ```

5. Run the pipeline:
   ```
   python main.py
   ```

The pipeline handles everything automatically - downloading the data from SEC, parsing, cleaning, importing into PostgreSQL, running validation checks, and generating the evaluation charts + PDF report.

## What it does

- Downloads all available 2025 quarterly ZIP files from the SEC website
- Parses the TSV files and prepares them for the database
- Imports everything through the Django ORM (idempotent - safe to re-run)
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
manage.py              Django management commands (migrate, makemigrations, ...)
config.py              Non-sensitive pipeline configuration (SEC URL, paths, batch size)
main.py                Entry point (calls django.setup() before anything else)
secpipeline/
  settings.py          Django settings - PostgreSQL connection read from .env
pipeline/
  models.py            The 7 database tables as Django models
  migrations/          Schema migrations (0001_initial.py)
modules/
  downloader.py        SEC ZIP download with retry logic
  parser.py            ZIP extraction + TSV/JSON parsing
  data_preparation.py  Data cleaning, type conversion, owner merge
  db_manager.py        Idempotent import via the Django ORM
  validation.py        8 plausibility checks (4 mandatory + 4 bonus)
  evaluation.py        Charts, CSV export, PDF report
docs/                  Documentation for each major task (German)
```

## Notes

- The pipeline needs a PostgreSQL server. Connection details go in `.env`, never in the code.
- First run downloads ~80 MB of ZIP files from SEC. Subsequent runs skip existing files.
- Re-running the pipeline deletes and re-imports all data (delete-then-insert), so the database always reflects the latest processing. The `pipeline_log` table is never deleted to keep a full audit trail.

## Current status

- **Task 1 (Setup):** done, except entering the real PostgreSQL credentials (placeholders in `.env` for now).
- **Task 2 (Django migration):** the full code migration from SQLAlchemy/MySQL to Django ORM/PostgreSQL is complete and passes all offline checks (`manage.py check`, `makemigrations`, imports). The remaining step is the end-to-end run against a real PostgreSQL database (`migrate` + full pipeline + validation/charts), which is blocked until the credentials are available. See `docs/django_migration.md`.
- **Task 3 (Docstrings):** done. See `docs/docstring_guidelines.md`.

Other tasks (flexible config, multi-year history, code review) are handled by the other team / scheduled for later - see `Plan.md`.
