"""
Handles all MySQL interactions: schema setup, table creation,
and idempotent data import (delete-then-insert strategy).

The university's shared DB server doesn't grant REFERENCES privilege,
so FK integrity is enforced in code: delete children first, insert
parent first. Not ideal but it works.
"""
import logging
import time

from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

import config

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    """Return a cached SQLAlchemy engine (creates one on first call)."""
    global _engine
    if _engine is None:
        db = config.DB_CONFIG
        url = (
            f"mysql+pymysql://{quote_plus(db['user'])}:{quote_plus(db['password'])}"
            f"@{db['host']}:{db['port']}/{config.SCHEMA_NAME}"
        )
        _engine = create_engine(
            url, pool_pre_ping=True, pool_recycle=280,
            pool_size=3, max_overflow=2,
        )
    return _engine


# --- Table definitions ---

CREATE_TABLES = [
    # submissions is the parent table - everything references it
    """
    CREATE TABLE IF NOT EXISTS submissions (
        accession_number VARCHAR(30) PRIMARY KEY,
        filing_date DATE,
        issuer_cik BIGINT,
        issuer_name VARCHAR(255),
        issuer_ticker VARCHAR(20),
        rptowner_cik BIGINT,
        rptowner_name VARCHAR(255),
        is_director TINYINT(1),
        is_officer TINYINT(1),
        is_ten_percent TINYINT(1),
        is_other TINYINT(1),
        officer_title VARCHAR(255),
        created_by VARCHAR(50) NOT NULL,
        source_quarter VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_issuer_cik (issuer_cik),
        INDEX idx_source_quarter (source_quarter),
        INDEX idx_filing_date (filing_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # nonderiv transactions - FK to submissions handled in app code
    """
    CREATE TABLE IF NOT EXISTS nonderiv_trans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        accession_number VARCHAR(30) NOT NULL,
        trans_date DATE,
        trans_code VARCHAR(5),
        equity_swap VARCHAR(5),
        shares DECIMAL(20,4),
        price_per_share DECIMAL(20,4),
        shares_owned_following DECIMAL(20,4),
        nominal_volume DECIMAL(24,4),
        is_valid TINYINT(1) DEFAULT NULL,
        validation_flags VARCHAR(500) DEFAULT NULL,
        created_by VARCHAR(50) NOT NULL,
        source_quarter VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_trans_code (trans_code),
        INDEX idx_trans_date (trans_date),
        INDEX idx_source_quarter (source_quarter),
        INDEX idx_accession (accession_number)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # nonderiv holdings
    """
    CREATE TABLE IF NOT EXISTS nonderiv_holdings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        accession_number VARCHAR(30) NOT NULL,
        shares_owned DECIMAL(20,4),
        created_by VARCHAR(50) NOT NULL,
        source_quarter VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_source_quarter (source_quarter)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # derivative transactions
    """
    CREATE TABLE IF NOT EXISTS deriv_trans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        accession_number VARCHAR(30) NOT NULL,
        trans_date DATE,
        trans_code VARCHAR(5),
        equity_swap VARCHAR(5),
        shares DECIMAL(20,4),
        price_per_share DECIMAL(20,4),
        shares_owned_following DECIMAL(20,4),
        nominal_volume DECIMAL(24,4),
        is_valid TINYINT(1) DEFAULT NULL,
        validation_flags VARCHAR(500) DEFAULT NULL,
        created_by VARCHAR(50) NOT NULL,
        source_quarter VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_trans_date (trans_date),
        INDEX idx_source_quarter (source_quarter)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # derivative holdings
    """
    CREATE TABLE IF NOT EXISTS deriv_holdings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        accession_number VARCHAR(30) NOT NULL,
        shares_owned DECIMAL(20,4),
        created_by VARCHAR(50) NOT NULL,
        source_quarter VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_source_quarter (source_quarter)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # validation results - one row per failed check
    """
    CREATE TABLE IF NOT EXISTS validation_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        accession_number VARCHAR(30),
        table_name VARCHAR(50) NOT NULL,
        record_id INT,
        check_name VARCHAR(100) NOT NULL,
        is_passed TINYINT(1) NOT NULL,
        details TEXT,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source_quarter VARCHAR(10) NOT NULL,
        INDEX idx_accession (accession_number),
        INDEX idx_source_quarter (source_quarter)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    # pipeline audit trail - this table is NEVER deleted
    """
    CREATE TABLE IF NOT EXISTS pipeline_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        quarter_processed VARCHAR(10),
        table_name VARCHAR(50),
        records_imported INT DEFAULT 0,
        records_invalid INT DEFAULT 0,
        status VARCHAR(20) NOT NULL,
        duration_seconds DECIMAL(10,2),
        error_message TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def setup_database():
    """Create the schema and all 7 tables if they don't exist yet."""
    db = config.DB_CONFIG
    root_url = (
        f"mysql+pymysql://{quote_plus(db['user'])}:{quote_plus(db['password'])}"
        f"@{db['host']}:{db['port']}/"
    )
    root_engine = create_engine(root_url)
    with root_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {config.SCHEMA_NAME}"))
        conn.commit()
    root_engine.dispose()

    engine = get_engine()
    with engine.connect() as conn:
        for ddl in CREATE_TABLES:
            conn.execute(text(ddl))
        conn.commit()

    # try adding foreign keys - the university server often lacks
    # the REFERENCES privilege, so we catch and move on
    _try_add_foreign_keys(engine)

    logger.info(f"Database '{config.SCHEMA_NAME}' ready with all 7 tables")


def _try_add_foreign_keys(engine):
    """Attempt to create FK constraints linking child tables to submissions.

    The shared university MySQL server typically doesn't grant REFERENCES,
    so this will fail silently. We keep insertion/deletion order in code
    as the actual safety net regardless.
    """
    fk_statements = [
        "ALTER TABLE nonderiv_trans ADD CONSTRAINT fk_nd_trans_sub "
        "FOREIGN KEY (accession_number) REFERENCES submissions(accession_number) "
        "ON DELETE CASCADE",
        "ALTER TABLE nonderiv_holdings ADD CONSTRAINT fk_nd_hold_sub "
        "FOREIGN KEY (accession_number) REFERENCES submissions(accession_number) "
        "ON DELETE CASCADE",
        "ALTER TABLE deriv_trans ADD CONSTRAINT fk_d_trans_sub "
        "FOREIGN KEY (accession_number) REFERENCES submissions(accession_number) "
        "ON DELETE CASCADE",
        "ALTER TABLE deriv_holdings ADD CONSTRAINT fk_d_hold_sub "
        "FOREIGN KEY (accession_number) REFERENCES submissions(accession_number) "
        "ON DELETE CASCADE",
    ]
    with engine.connect() as conn:
        for stmt in fk_statements:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                # expected on servers without REFERENCES privilege -
                # order-based integrity in import/delete code handles it
                conn.rollback()
                break

    logger.info("FK constraints: applied if server permits, skipped otherwise")


# --- Idempotent import ---

# insert order matters: parent first so children can reference it
IMPORT_ORDER = [
    "submissions",
    "nonderiv_trans",
    "nonderiv_holdings",
    "deriv_trans",
    "deriv_holdings",
]


def _delete_quarter(engine, quarter):
    """Wipe all data for a quarter before re-importing.

    Each table in its own transaction to avoid lock timeouts
    on the shared university server. Children first, then parent.
    Retries on lock timeout since other groups might be running too.
    """
    for table in ["deriv_holdings", "deriv_trans", "nonderiv_holdings",
                  "nonderiv_trans", "submissions", "validation_log"]:
        _execute_with_retry(
            engine,
            text(f"DELETE FROM {table} WHERE source_quarter = :q"),
            {"q": quarter},
        )
    logger.info(f"Deleted existing data for {quarter}")


def _execute_with_retry(engine, stmt, params=None, max_retries=3):
    """Run a SQL statement with retry on lock timeout.

    The shared university server can timeout when multiple groups
    are running pipelines simultaneously.
    """
    for attempt in range(max_retries):
        try:
            with engine.begin() as conn:
                conn.execute(text("SET innodb_lock_wait_timeout = 120"))
                conn.execute(stmt, params or {})
            return
        except Exception as e:
            err_str = str(e)
            if "Lock wait timeout" in err_str and attempt < max_retries - 1:
                wait = 3 * (attempt + 1)
                logger.warning(
                    f"Lock timeout, retry {attempt + 1}/{max_retries} in {wait}s"
                )
                time.sleep(wait)
            else:
                raise


def import_quarter(prepared_quarter, quarter):
    """Import one quarter using delete-then-insert.

    Each table gets its own transaction to avoid holding locks
    too long on the shared server. Not a single atomic operation
    anymore, but the pipeline can be re-run safely if it fails
    mid-way (idempotent by design).
    """
    engine = get_engine()
    start = time.time()

    try:
        _delete_quarter(engine, quarter)

        for table_name in IMPORT_ORDER:
            df = prepared_quarter[table_name]
            if df.empty:
                logger.info(f"  {quarter}/{table_name}: empty, skipping")
                continue

            # DB generates the id column itself
            if "id" in df.columns:
                df = df.drop(columns=["id"])

            with engine.begin() as conn:
                conn.execute(text("SET innodb_lock_wait_timeout = 120"))
                df.to_sql(
                    table_name, conn,
                    if_exists="append", index=False,
                    chunksize=config.BATCH_SIZE
                )
            logger.info(f"  {quarter}/{table_name}: {len(df)} rows imported")

        elapsed = time.time() - start
        log_pipeline_run(quarter, "all", len(prepared_quarter["submissions"]),
                         0, "success", elapsed)
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
    """Append to pipeline_log. This table persists across re-runs."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO pipeline_log
                (quarter_processed, table_name, records_imported,
                 records_invalid, status, duration_seconds, error_message)
            VALUES (:q, :t, :ri, :rv, :s, :d, :e)
        """), {
            "q": quarter, "t": table_name,
            "ri": records_imported, "rv": records_invalid,
            "s": status, "d": round(duration, 2), "e": error_msg
        })
