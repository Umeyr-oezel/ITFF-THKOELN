"""
Parses the downloaded SEC Form 4 ZIP archives.
Extracts them into quarter-specific folders and reads TSV/JSON
files into pandas DataFrames.
"""
import os
import json
import zipfile
import logging
import pandas as pd

import config

logger = logging.getLogger(__name__)

# only these files are relevant for our pipeline
RELEVANT_TSVS = [
    "SUBMISSION.tsv",
    "NONDERIV_TRANS.tsv",
    "NONDERIV_HOLDING.tsv",
    "DERIV_TRANS.tsv",
    "DERIV_HOLDING.tsv",
    "REPORTINGOWNER.tsv",
]


def extract_zip(zip_path, quarter_label):
    """Unzip into a quarter-specific subfolder. Returns the folder path."""
    target_dir = os.path.join(config.EXTRACTED_DIR, quarter_label)
    os.makedirs(target_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target_dir)

    files = os.listdir(target_dir)
    logger.info(f"Extracted {quarter_label}: {len(files)} files")
    return target_dir


def read_tsv(filepath):
    """Read a TSV into a DataFrame.

    Falls back to latin-1 if UTF-8 chokes. ACCESSION_NUMBER is
    forced to string - otherwise pandas might mangle it.
    """
    if not os.path.isfile(filepath):
        logger.warning(f"File not found: {filepath}")
        return pd.DataFrame()

    if os.path.getsize(filepath) == 0:
        logger.warning(f"Empty file: {filepath}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(
            filepath, sep="\t", encoding="utf-8",
            low_memory=False, on_bad_lines="warn",
            dtype={"ACCESSION_NUMBER": str}
        )
    except UnicodeDecodeError:
        logger.info(f"UTF-8 failed for {filepath}, trying latin-1")
        df = pd.read_csv(
            filepath, sep="\t", encoding="latin-1",
            low_memory=False, on_bad_lines="warn",
            dtype={"ACCESSION_NUMBER": str}
        )

    logger.debug(f"Read {os.path.basename(filepath)}: {df.shape[0]} rows, {df.shape[1]} cols")
    return df


def read_json(filepath):
    """Load a JSON metadata file if it exists."""
    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Read JSON: {os.path.basename(filepath)}")
        return data
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Could not parse {filepath}: {e}")
        return None


def parse_quarter(quarter_dir):
    """Read all relevant TSVs from one quarter folder.

    Returns dict: table_name -> DataFrame (+ optional JSON metadata).
    """
    result = {}

    for tsv_name in RELEVANT_TSVS:
        path = os.path.join(quarter_dir, tsv_name)
        table_key = tsv_name.replace(".tsv", "")
        df = read_tsv(path)
        result[table_key] = df
        if not df.empty:
            logger.info(f"  {table_key}: {len(df)} rows")

    # some ZIPs also contain metadata JSON
    json_path = os.path.join(quarter_dir, "FORM_345_metadata.json")
    metadata = read_json(json_path)
    if metadata:
        result["_metadata"] = metadata

    return result


def parse_all_quarters(zip_list):
    """Extract and parse all downloaded ZIPs.

    Args:
        zip_list: list of (quarter_label, zip_path) from downloader

    Returns dict: quarter_label -> parsed data dict.
    """
    os.makedirs(config.EXTRACTED_DIR, exist_ok=True)
    all_data = {}

    for quarter_label, zip_path in zip_list:
        logger.info(f"Parsing {quarter_label}...")
        quarter_dir = extract_zip(zip_path, quarter_label)
        all_data[quarter_label] = parse_quarter(quarter_dir)

    logger.info(f"Parsing complete: {len(all_data)} quarter(s)")
    return all_data
