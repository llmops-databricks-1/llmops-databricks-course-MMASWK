# Databricks notebook source
# Job: mdpi_scraper_job

# test notebook for week 3

import asyncio
from uuid import uuid4

import nest_asyncio
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import DatabaseInstance, DatabaseInstanceState
from databricks_mcp import DatabricksMCPClient
from loguru import logger

from filteredNotFrenzied.agent import MdpiAgent
from filteredNotFrenzied.config import load_config
from filteredNotFrenzied.custom_tools import (
    COFFEE_RATIO_BREWING_TOOL,
    KASUYA_4_6_SPLIT_TOOL,
)
from filteredNotFrenzied.mcp import create_mcp_tools
from filteredNotFrenzied.memory import LakebaseMemory
from filteredNotFrenzied.tool_registry import ToolRegistry

nest_asyncio.apply()

cfg = load_config(
    "/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/project_config.yml"
)
w = WorkspaceClient()
instance_name = "mdpi-agent-instance"

# COMMAND ----------
registry = ToolRegistry()
registry.register(COFFEE_RATIO_BREWING_TOOL)
registry.register(KASUYA_4_6_SPLIT_TOOL)


# COMMAND ----------
host = w.config.host
vector_search_mcp_url = f"{host}/api/2.0/mcp/vector-search/{cfg.catalog}/{cfg.schema}"

vs_mcp_client = DatabricksMCPClient(server_url=vector_search_mcp_url, workspace_client=w)


# COMMAND ----------
mcp_urls = [f"{host}/api/2.0/mcp/vector-search/{cfg.catalog}/{cfg.schema}"]
mcp_tools = asyncio.run(create_mcp_tools(w, mcp_urls))

# COMMAND ----------

all_tools = mcp_tools + registry.get_all_tools()

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
    system_prompt="You are a witty and clever research assistant talking like "
    "Pierce Brosnan James Bond. "
    "Use the available tools to search for papers and answer questions. ",
    tools=all_tools,
    memory=memory,
    session_id=session_id,
)


# COMMAND ----------

response = agent.chat(
    "I want to brew a coffe with a 1:16 ratio and 320g of water. "
    "How much coffee do i need?"
)
logger.info(f"Agent response: {response}")

response = agent.chat("Find papers about coffee health benefits")
logger.info(f"Agent response: {response}")

response = agent.chat(
    "I want to brew a coffe with the 4:6 method and have 287g of water. "
    "What is the amount of water for the first and second pour?"
)
logger.info(f"Agent response: {response}")
