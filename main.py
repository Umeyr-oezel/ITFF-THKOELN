"""
Entry point for the SEC Form 4 data pipeline.
Runs all six phases in order - can be executed multiple times
without creating duplicates (idempotent).
"""
import argparse
import logging
import os
import sys
import time

import django

# Django must be configured before importing anything that touches the
# ORM, so this runs before the pipeline module imports below.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "secpipeline.settings")
django.setup()

from django.conf import settings  # noqa: E402

from modules import (  # noqa: E402
    data_preparation,
    db_manager,
    downloader,
    evaluation,
    parser,
    validation,
)
import config  # noqa: E402


def parse_args():
    """Handle command-line flags for flexible pipeline runs."""
    p = argparse.ArgumentParser(
        description="SEC Form 4 Insider Transaction Pipeline"
    )
    p.add_argument(
        "--skip-download", action="store_true",
        help="use existing ZIPs instead of fetching from SEC"
    )
    p.add_argument(
        "--skip-import", action="store_true",
        help="skip DB import, useful when re-running evaluation"
    )
    p.add_argument(
        "--only-evaluate", action="store_true",
        help="jump straight to validation + evaluation (phases 5-6)"
    )
    return p.parse_args()


def preflight_checks(skip_sec=False):
    """Catch config problems before we're 3 minutes into an import.

    Checks: .env credentials present, DB reachable, SEC website up.
    """
    issues = []

    db = settings.DATABASES["default"]
    if not db.get("USER"):
        issues.append(
            "DB_USER is empty - did you create a .env file? "
            "(copy .env.example and fill in your credentials)"
        )
    if not db.get("PASSWORD"):
        issues.append("DB_PASSWORD is empty - check your .env file")

    # try the DB connection
    if not issues:
        try:
            from django.db import connection
            connection.ensure_connection()
            logging.info("Pre-flight: DB connection OK")
        except Exception as e:
            issues.append(f"Cannot connect to PostgreSQL: {e}")

    # SEC reachable? (skip when we only need DB data)
    if not skip_sec:
        try:
            import requests
            resp = requests.head(
                config.SEC_BASE_URL,
                headers={"User-Agent": config.USER_AGENT},
                timeout=10
            )
            logging.info(f"Pre-flight: SEC website OK (HTTP {resp.status_code})")
        except Exception as e:
            issues.append(f"Cannot reach SEC website: {e}")

    if issues:
        for msg in issues:
            logging.error(f"PREFLIGHT FAILED: {msg}")
        logging.error("Fix the above and try again.")
        sys.exit(1)

    logging.info("All pre-flight checks passed")


def print_summary(prepared, elapsed):
    """Show what the pipeline did - useful for the demo video."""
    logging.info("")
    logging.info("=" * 55)
    logging.info("  PIPELINE SUMMARY")
    logging.info("=" * 55)

    total_rows = 0
    for quarter in sorted(prepared.keys()):
        q_data = prepared[quarter]
        q_total = sum(len(df) for df in q_data.values())
        total_rows += q_total

        sub_count = len(q_data["submissions"])
        nd_count = len(q_data["nonderiv_trans"])
        dt_count = len(q_data["deriv_trans"])
        logging.info(
            f"  {quarter}: {sub_count:,} filings, "
            f"{nd_count:,} nonderiv, {dt_count:,} deriv"
        )

    logging.info("-" * 55)
    logging.info(f"  Total rows:  {total_rows:,}")
    logging.info(f"  Quarters:    {len(prepared)}")
    logging.info(f"  Duration:    {elapsed:.1f}s")

    # count generated output files
    chart_count = sum(
        len(files) for _, _, files in os.walk(config.CHARTS_DIR)
    ) + sum(
        len(files) for _, _, files in os.walk(config.CHARTS_OVERVIEW_DIR)
    )
    csv_count = sum(
        len(files) for _, _, files in os.walk(config.TABLES_DIR)
    )
    logging.info(f"  Charts:      {chart_count}")
    logging.info(f"  CSV tables:  {csv_count}")
    logging.info("=" * 55)


# ---


def main():
    """Kick off the full pipeline, start to finish."""
    args = parse_args()
    setup_logging()
    setup_directories()

    start = time.time()
    logging.info("=== Pipeline started ===")

    preflight_checks(skip_sec=args.only_evaluate)

    # shortcut: only re-run evaluation on existing DB data
    if args.only_evaluate:
        logging.info("--only-evaluate: jumping to phases 5+6")
        validation.run_validation()
        evaluation.generate_all_evaluations()
        elapsed = time.time() - start
        logging.info(f"=== Pipeline finished in {elapsed:.1f}s ===")
        return

    # phase 1 - grab ZIPs from SEC
    if args.skip_download:
        logging.info("--skip-download: using existing ZIP files")
        zip_files = downloader.list_existing_quarters()
    else:
        zip_files = downloader.download_all_quarters()

    # phase 2 - extract TSVs into DataFrames
    raw_data = parser.parse_all_quarters(zip_files)

    # phase 3 - clean, merge, enrich
    prepared = data_preparation.prepare_all_data(raw_data)

    # phase 4 - push into PostgreSQL (schema is managed by Django migrations)
    if not args.skip_import:
        db_manager.import_all_data(prepared)
    else:
        logging.info("--skip-import: skipping DB import")

    # phase 5 - run validation checks
    validation.run_validation()

    # phase 6 - charts, CSVs, PDF
    evaluation.generate_all_evaluations()

    elapsed = time.time() - start
    print_summary(prepared, elapsed)
    logging.info(f"=== Pipeline finished in {elapsed:.1f}s ===")


def setup_logging():
    """Set up dual logging: file + console."""
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )


def setup_directories():
    """Make sure all output folders exist before we start writing."""
    dirs = [
        config.RAW_DIR, config.EXTRACTED_DIR,
        config.CHARTS_DIR, config.CHARTS_OVERVIEW_DIR,
        config.TABLES_DIR, os.path.dirname(config.LOG_FILE),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


if __name__ == "__main__":
    main()
