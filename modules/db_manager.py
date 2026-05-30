"""Idempotent data import on top of the Django ORM.

Each quarter is imported with a delete-then-insert strategy so the
pipeline can be re-run safely. submissions go in first; the four child
tables reference them via a real foreign key, so any transaction or
holding whose filing is missing gets dropped (and logged) before the
insert instead of blowing up the whole batch.

The whole import of a quarter runs in one transaction now - PostgreSQL
on our own database doesn't have the lock-contention problem the old
shared MySQL server did, so there's no reason to split it up anymore.

pipeline_log is an audit trail and is never deleted.
"""
import logging
import time

import pandas as pd
from django.db import transaction

from pipeline.models import (
    DerivHolding,
    DerivTrans,
    NonderivHolding,
    NonderivTrans,
    PipelineLog,
    Submission,
    ValidationLog,
)
import config

logger = logging.getLogger(__name__)


def _records(df):
    """Turn a prepared DataFrame into row dicts, NaN/NaT replaced by None.

    pandas marks missing values with NaN (floats) and NaT (dates); the
    ORM needs real None so those columns end up as SQL NULL. Casting to
    object first lets a single where() catch both kinds at once.
    """
    if df.empty:
        return []
    clean = df.astype(object).where(pd.notnull(df), None)
    return clean.to_dict("records")


def _drop_orphans(df, valid_accessions, table_name):
    """Drop child rows whose filing isn't in this quarter's submissions.

    The foreign key would reject them anyway; filtering up front keeps
    one bad row from failing the entire bulk insert. Dropped rows are
    logged so they don't vanish silently.
    """
    if df.empty:
        return df
    keep = df["accession_number"].isin(valid_accessions)
    dropped = int((~keep).sum())
    if dropped:
        logger.warning(
            f"  {table_name}: dropping {dropped} orphan row(s) "
            f"without a matching submission"
        )
    return df[keep]


# --- building model instances from prepared DataFrames ---

def _build_submissions(records):
    """Map submission dicts onto Submission instances for bulk_create."""
    return [
        Submission(
            accession_number=r["accession_number"],
            filing_date=r.get("filing_date"),
            issuer_cik=r.get("issuer_cik"),
            issuer_name=r.get("issuer_name"),
            issuer_ticker=r.get("issuer_ticker"),
            rptowner_cik=r.get("rptowner_cik"),
            rptowner_name=r.get("rptowner_name"),
            is_director=r.get("is_director"),
            is_officer=r.get("is_officer"),
            is_ten_percent=r.get("is_ten_percent"),
            is_other=r.get("is_other"),
            officer_title=r.get("officer_title"),
            created_by=r["created_by"],
            source_quarter=r["source_quarter"],
        )
        for r in records
    ]


def _build_transactions(model, records):
    """Map transaction dicts onto model instances (nonderiv or deriv).

    submission_id carries the accession_number straight into the FK
    column. is_valid/validation_flags stay unset - the validation phase
    fills them in later.
    """
    return [
        model(
            submission_id=r["accession_number"],
            trans_date=r.get("trans_date"),
            trans_code=r.get("trans_code"),
            equity_swap=r.get("equity_swap"),
            shares=r.get("shares"),
            price_per_share=r.get("price_per_share"),
            shares_owned_following=r.get("shares_owned_following"),
            nominal_volume=r.get("nominal_volume"),
            created_by=r["created_by"],
            source_quarter=r["source_quarter"],
        )
        for r in records
    ]


def _build_holdings(model, records):
    """Map holding dicts onto model instances (nonderiv or deriv)."""
    return [
        model(
            submission_id=r["accession_number"],
            shares_owned=r.get("shares_owned"),
            created_by=r["created_by"],
            source_quarter=r["source_quarter"],
        )
        for r in records
    ]


# --- idempotent import ---

def _delete_quarter(quarter):
    """Remove a quarter's data before re-import (children first).

    Deleting submissions would cascade to the children, but we clear
    them explicitly first so the intent is obvious and so validation_log
    (which has no foreign key) gets wiped for the quarter too.
    """
    for model in (DerivHolding, DerivTrans, NonderivHolding,
                  NonderivTrans, Submission):
        model.objects.filter(source_quarter=quarter).delete()
    ValidationLog.objects.filter(source_quarter=quarter).delete()
    logger.info(f"Deleted existing data for {quarter}")


def import_quarter(prepared_quarter, quarter):
    """Import one quarter using delete-then-insert, all in one transaction.

    If anything fails the transaction rolls back and the quarter is left
    exactly as it was, so a re-run always lands on a clean slate.
    """
    sub_df = prepared_quarter["submissions"]
    start = time.time()

    children = [
        ("nonderiv_trans", NonderivTrans, _build_transactions),
        ("nonderiv_holdings", NonderivHolding, _build_holdings),
        ("deriv_trans", DerivTrans, _build_transactions),
        ("deriv_holdings", DerivHolding, _build_holdings),
    ]

    try:
        with transaction.atomic():
            _delete_quarter(quarter)

            Submission.objects.bulk_create(
                _build_submissions(_records(sub_df)),
                batch_size=config.BATCH_SIZE,
            )
            logger.info(f"  {quarter}/submissions: {len(sub_df)} rows imported")

            valid_accessions = set(sub_df["accession_number"])
            for table_name, model, builder in children:
                df = _drop_orphans(
                    prepared_quarter[table_name], valid_accessions, table_name
                )
                if df.empty:
                    logger.info(f"  {quarter}/{table_name}: empty, skipping")
                    continue
                model.objects.bulk_create(
                    builder(model, _records(df)),
                    batch_size=config.BATCH_SIZE,
                )
                logger.info(f"  {quarter}/{table_name}: {len(df)} rows imported")

        elapsed = time.time() - start
        log_pipeline_run(quarter, "all", len(sub_df), 0, "success", elapsed)
        logger.info(f"Import {quarter} complete in {elapsed:.1f}s")

    except Exception as e:
        elapsed = time.time() - start
        log_pipeline_run(quarter, "all", 0, 0, "error", elapsed, str(e))
        logger.error(f"Import {quarter} failed: {e}")
        raise


def import_all_data(prepared_data):
    """Import every quarter we have data for."""
    for quarter in sorted(prepared_data.keys()):
        logger.info(f"Importing {quarter}...")
        import_quarter(prepared_data[quarter], quarter)

    logger.info(f"All {len(prepared_data)} quarter(s) imported")


def log_pipeline_run(quarter, table_name, records_imported,
                     records_invalid, status, duration, error_msg=None):
    """Append one row to pipeline_log. This table persists across re-runs.

    Runs outside the import transaction so the audit entry survives even
    when the import it describes was rolled back.
    """
    PipelineLog.objects.create(
        quarter_processed=quarter,
        table_name=table_name,
        records_imported=records_imported,
        records_invalid=records_invalid,
        status=status,
        duration_seconds=round(duration, 2),
        error_message=error_msg,
    )
