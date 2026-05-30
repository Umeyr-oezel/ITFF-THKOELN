"""
Central config for the whole pipeline.
All credentials come from .env so nothing sensitive is hardcoded here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# where we scrape available quarters from
SEC_BASE_URL = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
USER_AGENT = "University Group01 group01@student.university.edu"

# DB credentials from .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
}
SCHEMA_NAME = "group01"

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
