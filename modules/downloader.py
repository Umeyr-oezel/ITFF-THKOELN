"""
Downloads SEC Form 4 ZIP files for the configured year.
Figures out which quarters are available by scraping the SEC page,
then downloads them with rate limiting so we don't get blocked.
"""
import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


def get_available_quarters():
    """Scrape the SEC page to find which quarters have data for all TARGET_YEARS.

    Returns list of (quarter_label, download_url) tuples across all configured years.
    No hardcoding - discovers dynamically what's online.
    """
    headers = {"User-Agent": config.USER_AGENT}
    resp = requests.get(config.SEC_BASE_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    quarters = []

    years_pattern = "|".join(str(y) for y in config.TARGET_YEARS)

    for link in soup.find_all("a", href=True):
        href = link["href"]

        # looking for links like "2025q1_form345.zip" across all target years
        match = re.search(
            rf"(({years_pattern})q(\d))_form345\.zip", href, re.IGNORECASE
        )
        if match:
            year = match.group(2)
            quarter_num = match.group(3)
            quarter_label = f"{year}Q{quarter_num}"
            if href.startswith("/"):
                full_url = f"https://www.sec.gov{href}"
            else:
                full_url = href
            quarters.append((quarter_label, full_url))
            logger.info(f"Found: {quarter_label} -> {full_url}")

    if not quarters:
        logger.warning(f"No quarters found for years {config.TARGET_YEARS}")

    return sorted(quarters, key=lambda x: x[0])


def is_already_downloaded(filename):
    """Quick check if we already have this file."""
    path = os.path.join(config.RAW_DIR, filename)
    return os.path.isfile(path)


def download_quarter(url, filename, max_retries=3):
    """Download one ZIP from SEC, with retry on server errors.

    Streams the response so large files don't blow up memory.
    Backs off exponentially on 429/500/503.
    """
    filepath = os.path.join(config.RAW_DIR, filename)
    headers = {"User-Agent": config.USER_AGENT}

    for attempt in range(max_retries):
        try:
            time.sleep(config.REQUEST_DELAY)  # be nice to SEC servers
            resp = requests.get(url, headers=headers, stream=True, timeout=60)

            if resp.status_code in (429, 500, 503):
                wait = 2 ** (attempt + 1)
                logger.warning(
                    f"HTTP {resp.status_code} for {filename}, "
                    f"retry {attempt + 1}/{max_retries} in {wait}s"
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            size_mb = os.path.getsize(filepath) / 1024 / 1024
            logger.info(f"Downloaded {filename} ({size_mb:.1f} MB)")
            return filepath

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Error downloading {filename}: {e}, retrying in {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"Failed to download {filename} after {max_retries} attempts: {e}")
                raise

    logger.error(f"Gave up on {filename} after {max_retries} retries (rate-limited)")
    return None


def list_existing_quarters():
    """Find already-downloaded ZIPs without hitting SEC.

    Useful with --skip-download so we don't need internet access.
    Scans for all TARGET_YEARS, not just one.
    """
    results = []
    if not os.path.isdir(config.RAW_DIR):
        return results

    years_pattern = "|".join(str(y) for y in config.TARGET_YEARS)

    for fname in sorted(os.listdir(config.RAW_DIR)):
        match = re.match(
            rf"(({years_pattern})q(\d))_form345\.zip", fname, re.IGNORECASE
        )
        if match:
            year = match.group(2)
            quarter_num = match.group(3)
            label = f"{year}Q{quarter_num}"
            results.append((label, os.path.join(config.RAW_DIR, fname)))
            logger.info(f"Found existing: {label}")

    logger.info(f"{len(results)} existing quarter(s) in {config.RAW_DIR}")
    return results


def download_all_quarters():
    """Download all quarters for TARGET_YEAR. Skips existing files.

    Returns list of (quarter_label, zip_path) tuples.
    """
    os.makedirs(config.RAW_DIR, exist_ok=True)
    quarters = get_available_quarters()

    if not quarters:
        logger.error("No quarters to download!")
        return []

    results = []
    for label, url in quarters:
        filename = url.split("/")[-1]

        if is_already_downloaded(filename):
            logger.info(f"{label} already exists, skipping.")
            results.append((label, os.path.join(config.RAW_DIR, filename)))
            continue

        logger.info(f"Downloading {label}...")
        path = download_quarter(url, filename)
        if path:
            results.append((label, path))

    logger.info(f"Download complete: {len(results)} quarter(s) available")
    return results
