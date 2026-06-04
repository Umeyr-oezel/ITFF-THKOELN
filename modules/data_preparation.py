"""
Transforms raw SEC data into clean, DB-ready DataFrames.
Handles type conversions, column renaming, owner-merge for
submissions, and adds pipeline metadata to every table.
"""
import logging
from datetime import datetime
import pandas as pd

import config

logger = logging.getLogger(__name__)


def _clean_columns(df):
    """Lowercase column names and strip whitespace."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower()
    return df


def _parse_date(series):
    """SEC dates come as DD-MON-YYYY (e.g. 15-JAN-2025)."""
    return pd.to_datetime(series, format="%d-%b-%Y", errors="coerce")


def add_metadata(df, quarter):
    """Stamp each row with who created it and when."""
    df["created_by"] = config.CREATED_BY
    df["source_quarter"] = quarter
    df["created_at"] = datetime.now()
    return df


# ---


def prepare_submissions(sub_df, owner_df, quarter):
    """Merge submissions with reporting-owner data.

    SEC stores owner info separately in REPORTINGOWNER.tsv, but
    our DB schema wants it all in one table. We take the first
    owner's CIK/name per filing and OR-combine the role flags.
    """
    sub = _clean_columns(sub_df)
    owners = _clean_columns(owner_df)

    # figure out each owner's relationship from the combined string
    rel = owners["rptowner_relationship"].fillna("")
    owners["is_director"] = rel.str.contains("Director", case=False).astype(int)
    owners["is_officer"] = rel.str.contains("Officer", case=False).astype(int)
    owners["is_ten_percent"] = rel.str.contains("TenPercent", case=False).astype(int)
    owners["is_other"] = rel.str.contains(r"\bOther\b", case=False).astype(int)

    # one row per filing: first owner CIK/name, max of boolean flags
    owner_agg = owners.groupby("accession_number").agg(
        rptowner_cik=("rptownercik", "first"),
        rptowner_name=("rptownername", "first"),
        officer_title=("rptowner_title", "first"),
        is_director=("is_director", "max"),
        is_officer=("is_officer", "max"),
        is_ten_percent=("is_ten_percent", "max"),
        is_other=("is_other", "max"),
    ).reset_index()

    merged = sub.merge(owner_agg, on="accession_number", how="left")

    merged["filing_date"] = _parse_date(merged["filing_date"])

    # match SEC column names to our DB schema
    col_map = {
        "issuercik": "issuer_cik",
        "issuername": "issuer_name",
        "issuertradingsymbol": "issuer_ticker",
    }
    merged.rename(columns=col_map, inplace=True)

    keep = [
        "accession_number", "filing_date",
        "issuer_cik", "issuer_name", "issuer_ticker",
        "rptowner_cik", "rptowner_name",
        "is_director", "is_officer", "is_ten_percent", "is_other",
        "officer_title",
    ]
    result = merged[[c for c in keep if c in merged.columns]].copy()

    dupes = result.duplicated(subset=["accession_number"]).sum()
    if dupes > 0:
        logger.warning(f"Submissions: {dupes} duplicate accession_numbers, dropping")
        result = result.drop_duplicates(subset=["accession_number"], keep="first")

    result = add_metadata(result, quarter)

    logger.info(f"Prepared submissions: {len(result)} rows")
    return result


def prepare_transactions(df, quarter, table_name="nonderiv_trans"):
    """Clean transaction data - works for both nonderiv and deriv tables."""
    if df.empty:
        logger.info(f"{table_name}: empty, skipping")
        return df

    trans = _clean_columns(df)

    trans["trans_date"] = _parse_date(trans["trans_date"])

    for col in ["trans_shares", "trans_pricepershare", "shrs_ownd_folwng_trans"]:
        if col in trans.columns:
            trans[col] = pd.to_numeric(trans[col], errors="coerce")

    # calculate nominal volume (shares * price)
    if "trans_shares" in trans.columns and "trans_pricepershare" in trans.columns:
        trans["nominal_volume"] = trans["trans_shares"] * trans["trans_pricepershare"]

    col_map = {
        "trans_shares": "shares",
        "trans_pricepershare": "price_per_share",
        "equity_swap_involved": "equity_swap",
        "shrs_ownd_folwng_trans": "shares_owned_following",
    }
    trans.rename(columns={k: v for k, v in col_map.items() if k in trans.columns}, inplace=True)

    keep = ["accession_number", "trans_date", "trans_code", "equity_swap",
            "shares", "price_per_share", "shares_owned_following", "nominal_volume"]
    result = trans[[c for c in keep if c in trans.columns]].copy()

    dupes = result.duplicated().sum()
    if dupes > 0:
        logger.info(f"{table_name}: {dupes} full duplicate rows in raw data")

    result = add_metadata(result, quarter)

    logger.info(f"Prepared {table_name}: {len(result)} rows")
    return result


def prepare_holdings(df, quarter, table_name="nonderiv_holdings"):
    """Clean holdings data. Pretty simple since there's only one relevant column."""
    if df.empty:
        logger.info(f"{table_name}: empty, skipping")
        return df

    hold = _clean_columns(df)

    if "shrs_ownd_folwng_trans" in hold.columns:
        hold["shrs_ownd_folwng_trans"] = pd.to_numeric(
            hold["shrs_ownd_folwng_trans"], errors="coerce"
        )

    col_map = {"shrs_ownd_folwng_trans": "shares_owned"}
    hold.rename(columns={k: v for k, v in col_map.items() if k in hold.columns}, inplace=True)

    keep = ["accession_number", "shares_owned"]
    result = hold[[c for c in keep if c in hold.columns]].copy()

    dupes = result.duplicated().sum()
    if dupes > 0:
        logger.info(f"{table_name}: {dupes} full duplicate rows in raw data")

    result = add_metadata(result, quarter)

    logger.info(f"Prepared {table_name}: {len(result)} rows")
    return result


# ---


def prepare_all_data(raw_data):
    """Run all transformations on every quarter.

    Takes the raw dict from parser, returns a dict of
    DB-ready DataFrames grouped by quarter.
    """
    prepared = {}

    for quarter, tables in raw_data.items():
        logger.info(f"Preparing {quarter}...")

        q_data = {}

        # submissions need the owner merge
        q_data["submissions"] = prepare_submissions(
            tables["SUBMISSION"], tables["REPORTINGOWNER"], quarter
        )

        q_data["nonderiv_trans"] = prepare_transactions(
            tables["NONDERIV_TRANS"], quarter, "nonderiv_trans"
        )

        q_data["nonderiv_holdings"] = prepare_holdings(
            tables["NONDERIV_HOLDING"], quarter, "nonderiv_holdings"
        )

        q_data["deriv_trans"] = prepare_transactions(
            tables["DERIV_TRANS"], quarter, "deriv_trans"
        )

        q_data["deriv_holdings"] = prepare_holdings(
            tables["DERIV_HOLDING"], quarter, "deriv_holdings"
        )

        prepared[quarter] = q_data

    logger.info(f"Data preparation complete: {len(prepared)} quarter(s)")

    log_data_quality(prepared)

    return prepared


def log_data_quality(prepared):
    """Print a data quality overview after all preparation is done.

    Helps catch issues early - NULL counts, missing values, etc.
    """
    logger.info("--- Data Quality Report ---")

    for quarter in sorted(prepared.keys()):
        p = prepared[quarter]

        sub = p["submissions"]
        null_cik = sub["issuer_cik"].isna().sum()
        null_ticker = sub["issuer_ticker"].isna().sum()
        null_owner = sub["rptowner_cik"].isna().sum()
        logger.info(
            f"  {quarter} submissions ({len(sub)} rows): "
            f"missing issuer_cik={null_cik}, ticker={null_ticker}, "
            f"owner_cik={null_owner}"
        )

        for tbl in ["nonderiv_trans", "deriv_trans"]:
            df = p[tbl]
            if df.empty:
                continue
            nulls = {
                "date": df["trans_date"].isna().sum(),
                "shares": df["shares"].isna().sum() if "shares" in df.columns else 0,
                "price": (df["price_per_share"].isna().sum()
                          if "price_per_share" in df.columns else 0),
            }
            vol_null = df["nominal_volume"].isna().sum() if "nominal_volume" in df.columns else 0
            logger.info(
                f"  {quarter} {tbl} ({len(df)} rows): "
                f"NULL date={nulls['date']}, shares={nulls['shares']}, "
                f"price={nulls['price']}, volume={vol_null}"
            )

    logger.info("--- End Data Quality Report ---")
