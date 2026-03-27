# Databricks notebook source
# Job: mdpi_paper_parser
# COMMAND ----------
import sys
from pathlib import Path


from pyspark.sql import SparkSession
from filteredNotFrenzied.data_processor import DataProcessor
from filteredNotFrenzied.config import get_env, load_config


src_path = Path.cwd().parent / "src"
if src_path not in sys.path:
    sys.path.insert(0, str(src_path))

# COMMAND ----------
spark = SparkSession.builder.getOrCreate()

# COMMAND ----------
env = get_env(spark)
cfg = load_config("../project_config.yml", env)


dp = DataProcessor(spark, cfg)
dp.parse_and_process()




