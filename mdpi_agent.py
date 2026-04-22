import mlflow
from mlflow.models import ModelConfig

from filteredNotFrenzied.agent import MdpiAgent
from filteredNotFrenzied.custom_tools import (
    COFFEE_RATIO_BREWING_TOOL,
    KASUYA_4_6_SPLIT_TOOL,
)
from filteredNotFrenzied.tool_registry import ToolRegistry

config = ModelConfig(
    development_config={
        "catalog": "mlops_dev",
        "schema": "mdpi",
        "system_prompt": "prompt placeholder",
        "llm_endpoint": "databricks-gpt-oss-120b",
        "lakebase_project_id": "mdpi-agent-lakebase",
    }
)

registry = ToolRegistry()
registry.register(COFFEE_RATIO_BREWING_TOOL)
registry.register(KASUYA_4_6_SPLIT_TOOL)

agent = MdpiAgent(
    llm_endpoint=config.get("llm_endpoint"),
    system_prompt=config.get("system_prompt"),
    catalog=config.get("catalog"),
    schema=config.get("schema"),
    lakebase_project_id=config.get("lakebase_project_id"),
    custom_tools=registry.get_all_tools(),
)
mlflow.models.set_model(agent)
