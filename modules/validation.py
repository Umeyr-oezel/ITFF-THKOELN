"""
Runs plausibility checks on imported transaction data.
4 mandatory checks + 4 bonus checks. Results go into two places:
the is_valid/validation_flags columns on the main table AND
the separate validation_log table for traceability.
"""
import logging
from datetime import date

import pandas as pd
from sqlalchemy import text

from modules import get_engine
import config

logger = logging.getLogger(__name__)

# all known SEC Form 4 transaction codes
KNOWN_TRANS_CODES = {
    "P", "S", "A", "M", "F", "G", "J", "D", "C",
    "L", "U", "X", "I", "W", "Z", "O", "E", "K", "H",
}

MAX_REASONABLE_PRICE = 1_000_000


# --- Individual checks ---

def _check_mandatory_fields(df):
    """accession_number and trans_date must not be NULL."""
    mask = df["accession_number"].isna() | df["trans_date"].isna()
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "MISSING_MANDATORY;"
    return df


def _check_no_negative_prices(df):
    """Negative prices don't make sense. NaN is fine though."""
    mask = df["price_per_share"].notna() & (df["price_per_share"] < 0)
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "NEGATIVE_PRICE;"
    return df


def _check_no_negative_shares(df):
    """Same logic as prices - shares can't go below zero."""
    mask = df["shares"].notna() & (df["shares"] < 0)
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "NEGATIVE_SHARES;"
    return df


def _check_date_logic(df):
    """Transaction can't happen after the filing date (needs JOIN data)."""
    mask = (
        df["trans_date"].notna()
        & df["filing_date"].notna()
        & (df["trans_date"] > df["filing_date"])
    )
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "DATE_AFTER_FILING;"
    return df


def _check_valid_trans_code(df):
    """Flag any trans_code we haven't seen in the SEC docs."""
    mask = df["trans_code"].notna() & ~df["trans_code"].isin(KNOWN_TRANS_CODES)
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "UNKNOWN_TRANS_CODE;"
    return df


def _check_future_date(df):
    """Transactions in the future are almost certainly data errors."""
    today = pd.Timestamp(date.today())
    mask = df["trans_date"].notna() & (df["trans_date"] > today)
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "FUTURE_DATE;"
    return df


def _check_reasonable_price(df):
    """Anything at or above $1M per share is suspicious enough to flag."""
    mask = (
        df["price_per_share"].notna()
        & (df["price_per_share"] >= MAX_REASONABLE_PRICE)
    )
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "UNREASONABLE_PRICE;"
    return df


def _check_orphan_records(df):
    """Transaction without a matching submission - shouldn't happen but does."""
    mask = df["_has_submission"] == 0
    df.loc[mask, "is_valid"] = 0
    df.loc[mask, "flags"] += "ORPHAN_RECORD;"
    return df


# --- Writing results back ---

def _update_main_table(engine, table_name, df):
    """Set is_valid and validation_flags on the transaction table.

    Resets valid rows per quarter (to avoid locking the whole table),
    then marks invalid rows individually.
    """
    invalid = df[df["is_valid"] == 0]
    quarters = df["source_quarter"].unique()

    with engine.begin() as conn:
        # reset per quarter so we don't lock 285k rows at once
        for q in quarters:
            conn.execute(
                text(f"UPDATE {table_name} SET is_valid = 1, "
                     f"validation_flags = '' "
                     f"WHERE source_quarter = :q"),
                {"q": q},
            )

        if not invalid.empty:
            ids = invalid["id"].astype(int).tolist()
            flag_vals = invalid["flags"].tolist()
            params = [
                {"id": rid, "v": 0, "f": f}
                for rid, f in zip(ids, flag_vals)
            ]
            conn.execute(
                text(f"UPDATE {table_name} SET is_valid = :v, "
                     f"validation_flags = :f WHERE id = :id"),
                params,
            )

    logger.info(
        f"  Updated {table_name}: {len(df)} total, {len(invalid)} marked invalid"
    )


def _write_validation_log(engine, table_name, df):
    """Write one log row per failed check per record."""
    failed = df[df["is_valid"] == 0]

    if failed.empty:
        logger.info(f"  {table_name}: all records passed validation")
        return

    log_rows = []
    for _, row in failed.iterrows():
        checks = [c for c in row["flags"].split(";") if c]
        for check in checks:
            log_rows.append({
                "accession_number": row["accession_number"],
                "table_name": table_name,
                "record_id": int(row["id"]),
                "check_name": check,
                "is_passed": 0,
                "details": _describe_failure(row, check),
                "source_quarter": row["source_quarter"],
            })

    log_df = pd.DataFrame(log_rows)
    with engine.begin() as conn:
        log_df.to_sql(
            "validation_log", conn,
            if_exists="append", index=False,
            chunksize=config.BATCH_SIZE,
        )

    logger.info(f"  Wrote {len(log_rows)} entries to validation_log for {table_name}")


def _describe_failure(row, check_name):
    """Short human-readable explanation of what went wrong."""
    if check_name == "MISSING_MANDATORY":
        missing = []
        if pd.isna(row["accession_number"]):
            missing.append("accession_number")
        if pd.isna(row["trans_date"]):
            missing.append("trans_date")
        return f"NULL fields: {', '.join(missing)}"

    if check_name == "NEGATIVE_PRICE":
        return f"price_per_share={row['price_per_share']}"

    if check_name == "NEGATIVE_SHARES":
        return f"shares={row['shares']}"

    if check_name == "DATE_AFTER_FILING":
        return f"trans_date={row['trans_date']} > filing_date={row['filing_date']}"

    if check_name == "UNKNOWN_TRANS_CODE":
        return f"trans_code='{row['trans_code']}'"

    if check_name == "FUTURE_DATE":
        return f"trans_date={row['trans_date']} is after today"

    if check_name == "UNREASONABLE_PRICE":
        return f"price_per_share={row['price_per_share']}"

    if check_name == "ORPHAN_RECORD":
        return f"accession_number={row['accession_number']} not in submissions"

    return check_name


# --- Main validation logic ---

def _validate_table(engine, table_name):
    """Run all 8 checks on one transaction table, store results.

    LEFT JOIN against submissions so we also catch orphan records.
    """
    logger.info(f"Validating {table_name}...")

    query = text(f"""
        SELECT t.id, t.accession_number, t.trans_date, t.trans_code,
               t.shares, t.price_per_share, t.source_quarter,
               s.filing_date,
               CASE WHEN s.accession_number IS NOT NULL THEN 1 ELSE 0
               END AS _has_submission
        FROM {table_name} t
        LEFT JOIN submissions s ON t.accession_number = s.accession_number
    """)
    df = pd.read_sql(query, engine)

    if df.empty:
        logger.info(f"  {table_name}: no data to validate")
        return

    # make sure comparison works properly
    df["trans_date"] = pd.to_datetime(df["trans_date"], errors="coerce")
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")

    df["is_valid"] = 1
    df["flags"] = ""

    # mandatory (1-4)
    df = _check_mandatory_fields(df)
    df = _check_no_negative_prices(df)
    df = _check_no_negative_shares(df)
    df = _check_date_logic(df)

    # bonus
    df = _check_valid_trans_code(df)
    df = _check_future_date(df)
    df = _check_reasonable_price(df)
    df = _check_orphan_records(df)

    valid_count = (df["is_valid"] == 1).sum()
    invalid_count = len(df) - valid_count
    logger.info(
        f"  {table_name}: {valid_count} valid, {invalid_count} invalid "
        f"({len(df)} total)"
    )

    # dual storage: inline flags + separate log table
    _update_main_table(engine, table_name, df)
    _write_validation_log(engine, table_name, df)


def run_validation():
    """Validate nonderiv_trans and deriv_trans, then print a summary."""
    engine = get_engine()

    # clean old validation_log so re-runs don't cause duplicates
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM validation_log"))
    logger.info("Cleared validation_log for fresh run")

    _validate_table(engine, "nonderiv_trans")
    _validate_table(engine, "deriv_trans")

    with engine.connect() as conn:
        for tbl in ["nonderiv_trans", "deriv_trans"]:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            valid = conn.execute(
                text(f"SELECT COUNT(*) FROM {tbl} WHERE is_valid = 1")
            ).scalar()
            pct = (valid / total * 100) if total else 0
            logger.info(f"  {tbl}: {valid}/{total} valid ({pct:.1f}%)")

        vlog = conn.execute(
            text("SELECT COUNT(*) FROM validation_log")
        ).scalar()
        logger.info(f"  validation_log: {vlog} entries")

    logger.info("Validation complete")
