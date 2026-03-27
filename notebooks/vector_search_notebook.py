# Databricks notebook source
# Job: mdpi_paper_parser
# COMMAND ----------
import sys
from pathlib import Path

from pyspark.sql import SparkSession

from filteredNotFrenzied.config import get_env, load_config
from filteredNotFrenzied.vector_search import VectorSearchManager

src_path = Path.cwd().parent / "src"
if src_path not in sys.path:
    sys.path.insert(0, str(src_path))

# COMMAND ----------
spark = SparkSession.builder.getOrCreate()

env = get_env(spark)
cfg = load_config("../project_config.yml", env)

vs_manager = VectorSearchManager(
    config=cfg,
    endpoint_name=cfg.vector_search_endpoint,
    embedding_model=cfg.embedding_endpoint,
)

index = vs_manager.create_or_get_index()
