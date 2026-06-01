"""
Central config for the whole pipeline.

Database credentials live in .env and are read by Django in
secpipeline/settings.py. Everything here is non-sensitive pipeline
configuration: the SEC URL, file paths, and batch/timing settings.
"""
import os

# where we scrape available quarters from
SEC_BASE_URL = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
USER_AGENT = os.getenv("USER_AGENT", "University Group01 group01@student.university.edu")

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
START_YEAR = int(os.getenv("START_YEAR", 2020))
END_YEAR = int(os.getenv("END_YEAR", 2025))
TARGET_YEARS = list(range(START_YEAR, END_YEAR + 1))
BATCH_SIZE = 5000
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 0.2))
CREATED_BY = os.getenv("CREATED_BY", "group01")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# validation thresholds
KNOWN_TRANS_CODES = {
    "P", "S", "A", "M", "F", "G", "J", "D", "C",
    "L", "U", "X", "I", "W", "Z", "O", "E", "K", "H",
}
MAX_REASONABLE_PRICE = float(os.getenv("MAX_REASONABLE_PRICE", 1_000_000))

# chart appearance
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "th_koeln_logo.png")
CHART_COLORS = {
    "purchase": "#1a6b54",
    "sale":     "#8b2f3a",
    "bg":       "#fafafa",
    "text":     "#2d2d2d",
    "grid":     "#e0e0e0",
    "subtitle": "#666666",
}
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}
