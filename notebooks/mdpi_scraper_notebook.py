# Databricks notebook source
# Job: mdpi_scraper_job

# COMMAND ----------

import sys
from pathlib import Path

from loguru import logger

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType

from filteredNotFrenzied.mdpi_scraper import MDPIScraper
from filteredNotFrenzied.config import get_env, load_config

src_path = Path.cwd().parent / "src"
if src_path not in sys.path:
    sys.path.insert(0, str(src_path))

# COMMAND ----------
spark = SparkSession.builder.getOrCreate()

# COMMAND ----------
# Load config
env = get_env(spark)
cfg = load_config("../project_config.yml", env)

CATALOG = cfg.catalog
SCHEMA = cfg.schema
TABLE_NAME = "arxiv_papers"

# COMMAND ----------

# Create schema if it doesn't exist
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
logger.info(f"Schema {CATALOG}.{SCHEMA} ready")


# COMMAND ----------

# Configuration
search_queries = [
    "coffee+brew",
]

output_table = f"{CATALOG}.{SCHEMA}.mdpi_papers"
pdf_storage_path = "/Volumes/mlops_dev/maximili/mmaswk_volume/mdpi_paper/"

# COMMAND ----------

# Define schema
schema = StructType([
    StructField("id", StringType(), False),
    StructField("title", StringType(), False),
    StructField("authors", StringType(), False),
    StructField("summary", StringType(), True),
    StructField("published", StringType(), True),
    StructField("pdf_url", StringType(), False),
    StructField("journal", StringType(), True),
    StructField("ingestion_timestamp", StringType(), False),
])

# COMMAND ----------

# Fetch papers for each query
all_papers = []
scraper = MDPIScraper(output_directory=pdf_storage_path)

for query in search_queries:
    logger.info(f"Fetching papers for: {query}")
    papers = scraper.fetch_papers(max_results=20)
    all_papers.extend(papers)
    logger.info(f"  Found {len(papers)} papers")

logger.info(f"\nTotal papers fetched: {len(all_papers)}")

# COMMAND ----------

# Create and write DataFrame
df = spark.createDataFrame(all_papers, schema=schema)

df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable(output_table)

logger.info(f"Saved {len(all_papers)} papers to table: {output_table}")

# COMMAND ----------

total, downloaded = scraper.download_papers(all_papers, pdf_storage_path)
logger.info(f"Downloaded {downloaded}/{total} PDFs")

# COMMAND ----------

# Verify data
display(spark.table(output_table))