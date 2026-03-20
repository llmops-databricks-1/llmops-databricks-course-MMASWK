# Databricks notebook source
# COMMAND ----------

import sys
from pathlib import Path

from filteredNotFrenzied.mdpi_scraper import MDPIScraper

# Add src directory to path for imports
src_path = Path.cwd().parent / "src"
if src_path not in sys.path:
    sys.path.insert(0, str(src_path))


# COMMAND ----------

# Initialize scraper with search query for MDPI
scraper = MDPIScraper(
    search_query="coffee+brew",
    output_directory="/Volumes/mlops_dev/maximili/mmaswk_volume/mdpi_paper/",
    request_delay=1.0,
    max_retries=5,
    retry_delay=2,
    timeout=30,
    log_level="INFO",
)

print("MDPI Scraper initialized successfully!")

# COMMAND ----------

# Debug: Inspect page structure
scraper.debug_page()

# COMMAND ----------

# Scrape and download PDFs
found, downloaded = scraper.scrape_and_download()

# COMMAND ----------
