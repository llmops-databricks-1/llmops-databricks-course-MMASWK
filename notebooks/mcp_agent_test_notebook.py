# Databricks notebook source
# Job: mdpi_scraper_job

# test notebook for week 3

from uuid import uuid4

import nest_asyncio
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import DatabaseInstance, DatabaseInstanceState
from loguru import logger

from filteredNotFrenzied.agent import MdpiAgent, log_register_agent
from filteredNotFrenzied.config import load_config
from filteredNotFrenzied.custom_tools import (
    COFFEE_RATIO_BREWING_TOOL,
    KASUYA_4_6_SPLIT_TOOL,
)
from filteredNotFrenzied.evaluation import evaluate_agent
from filteredNotFrenzied.memory import LakebaseMemory
from filteredNotFrenzied.tool_registry import ToolRegistry
from filteredNotFrenzied.utils.common import get_widget

nest_asyncio.apply()

env = get_widget("env", "dev")
git_sha = get_widget("git_sha", "local")
run_id = get_widget("run_id", "local")

cfg = load_config(
    "/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/project_config.yml"
)

model_name = f"{cfg.catalog}.{cfg.schema}.mdpi_agent"

w = WorkspaceClient()
instance_name = "mdpi-agent-instance"

# COMMAND ----------
registry = ToolRegistry()
registry.register(COFFEE_RATIO_BREWING_TOOL)
registry.register(KASUYA_4_6_SPLIT_TOOL)


# COMMAND ----------
host = w.config.host
vector_search_mcp_url = f"{host}/api/2.0/mcp/vector-search/{cfg.catalog}/{cfg.schema}"

# COMMAND ----------

try:
    instance = w.database.get_database_instance(instance_name)
    logger.info(f"Using existing instance: {instance_name}")
    if instance.state == DatabaseInstanceState.STOPPED:
        logger.info("Instance is stopped, starting...")
        instance = w.database.update_database_instance(
            name=instance_name,
            database_instance=DatabaseInstance(name=instance_name, stopped=False),
            update_mask="stopped",
        )
        instance = w.database.wait_get_database_instance_database_available(instance_name)
        logger.info("Instance started")
    lakebase_host = instance.read_write_dns
except Exception:
    logger.info(f"Creating new instance: {instance_name}")
    instance = w.database.create_database_instance(
        DatabaseInstance(
            name=instance_name,
            capacity="CU_1",
        ),
    )
    lakebase_host = instance.response.read_write_dns


# COMMAND ----------
# Use the correct Lakehouse project_id from your Databricks instance
# You can get the correct project_id from your database instance object (see Cell 55)
memory = LakebaseMemory(
    project_id=instance.name  # Use the actual instance name, not a hardcoded string
)

memory._get_connection_string()
session_id = f"test-session-{uuid4()}"

# COMMAND ----------

agent = MdpiAgent(
    llm_endpoint=cfg.llm_endpoint,
    system_prompt="You are the James Bond of coffee brewing. Be witty and "
    "talk like Pierce Brosnan James Bond. "
    "Support the user to find great papers about coffee. Q gave you vector search "
    "to find papers, "
    "Kasuya 4:6 method and appropriate coffee brewing tools to support the user "
    "to brew delicious coffee. "
    "Do not mention the tools in the response.",
    catalog=cfg.catalog,
    schema=cfg.schema,
    lakebase_project_id="mdpi-agent-instance",
    custom_tools=registry.get_all_tools(),
)


# COMMAND ----------
results = evaluate_agent(
    cfg,
    "/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/eval_inputs.txt",
    agent,
)

# COMMAND ----------
registered_model = log_register_agent(
    cfg=cfg,
    git_sha=git_sha,
    run_id=run_id,
    agent_code_path="/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/mdpi_agent.py",
    model_name=model_name,
    evaluation_metrics=results.metrics,
)
