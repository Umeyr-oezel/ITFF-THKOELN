"""
Central config for the whole pipeline.

Database credentials live in .env and are read by Django in
secpipeline/settings.py. Everything here is non-sensitive pipeline
configuration: the SEC URL, file paths, and batch/timing settings.
"""

# where we scrape available quarters from
SEC_BASE_URL = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
USER_AGENT = "University Group01 group01@student.university.edu"

# directory layout
DATA_DIR = "data/"
RAW_DIR = "data/raw/"
EXTRACTED_DIR = "data/extracted/"
OUTPUT_DIR = "output/"
CHARTS_DIR = "output/charts/monthly/"
CHARTS_OVERVIEW_DIR = "output/charts/overview/"
TABLES_DIR = "output/tables/monthly/"
LOG_FILE = "logs/pipeline.log"

# pipeline settings
TARGET_YEAR = 2025
BATCH_SIZE = 5000
REQUEST_DELAY = 0.2   # SEC asks for at least 100ms between requests
CREATED_BY = "group01"
