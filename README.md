# SEC Form 4 Data Pipeline

Automated pipeline that downloads, processes, and analyzes SEC Form 4 insider transaction data for the years 2020–2025.

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

   No PostgreSQL server yet? There is a local SQLite fallback - set
   `DB_ENGINE=django.db.backends.sqlite3` and `DB_NAME=local.sqlite3` in
   `.env` and everything below works against a single local file (no
   server, no credentials). See `docs/sqlite_fallback_und_tests.md`.

4. Run the pipeline:
   ```
   python main.py                    # all years (2020-2025)
   python main.py --year 2024        # single year
   python main.py --years 2022-2024  # year range
   ```
   That's the only command you need - `main.py` applies the database
   migrations automatically on startup, so a fresh checkout works in one
   step. (You can still run `python manage.py migrate` by hand if you want.)

The pipeline handles everything automatically - downloading the data from SEC, parsing, cleaning, importing into PostgreSQL, running validation checks, and generating the evaluation charts + PDF report.

## What it does

- Downloads all available quarterly ZIP files from the SEC website (2020–2025 by default, configurable via `START_YEAR`/`END_YEAR` in `.env`)
- Parses the TSV files and prepares them for the database
- Imports everything through the Django ORM (idempotent - safe to re-run)
- Validates transactions (mandatory field checks, price/quantity checks, date logic, etc.)
- Generates monthly Top-5 / Bottom-5 insider trading charts, CSV tables, and a summary PDF

## Output

After running, the output is grouped per year under `output/<year>/`:
- `output/<year>/<year>_evaluation_report.pdf` - full report for that year
- `output/<year>/charts/monthly/<MM>/` - bar charts per month (purchases + sales, 3 metrics each)
- `output/<year>/charts/overview/` - trend, sentiment, and heatmap charts
- `output/<year>/tables/monthly/<MM>/` - CSV exports of the ranking data
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

## Testing

The pipeline ships with a unit-test suite (Django's built-in test runner -
no extra package). Tests run against a throwaway SQLite database, so they
need neither the PostgreSQL server nor internet access:

```
python manage.py test
```

Make sure the SQLite fallback is active in `.env` (see setup step 3). The
suite covers data preparation, all eight validation checks, the parser,
the downloader (network mocked), and the idempotent import. See
`docs/sqlite_fallback_und_tests.md`.

## Current status

- **Task 1 (Setup):** done, except entering the real PostgreSQL credentials (placeholders in `.env` for now).
- **Task 2 (Django migration):** the full code migration from SQLAlchemy/MySQL to Django ORM/PostgreSQL is complete and passes all offline checks (`manage.py check`, `makemigrations`, imports). The remaining step is the end-to-end run against a real PostgreSQL database (`migrate` + full pipeline + validation/charts), which is blocked until the credentials are available. See `docs/django_migration.md`.
- **Task 3 (Docstrings):** done. See `docs/docstring_guidelines.md`.
- **Task 4 (Flexible config):** done. All hardcoded values moved to `config.py` or `.env`. See `docs/configuration.md`.
- **Task 5 (Multi-year history):** done. Pipeline now covers 2020–2025 by default. CLI flags `--year` and `--years` added. See `docs/multi_year_extension.md`.
- **Task 6 (Code review):** done. File-by-file review of the root files, `modules/`, and the Django layer — efficiency, hardcoded values, and bugs fixed; the test suite stays green (34 tests). See `docs/code_review.md`.

The project has since moved into a follow-up phase (presentation, Plan-B server research, and the final PostgreSQL migration) — see `Plan.md` for the current task list.
