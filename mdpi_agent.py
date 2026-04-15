import mlflow
from mlflow.models import ModelConfig

from filteredNotFrenzied.agent import MdpiAgent

config = ModelConfig(
    development_config={
        "catalog": "mlops_dev",
        "schema": "mdpi",
        "system_prompt": "prompt placeholder",
        "llm_endpoint": "databricks-gpt-oss-120b",
        "lakebase_project_id": "mdpi-agent-lakebase",
    }
)

agent = MdpiAgent(
    llm_endpoint=config.get("llm_endpoint"),
    system_prompt=config.get("system_prompt"),
    catalog=config.get("catalog"),
    schema=config.get("schema"),
    lakebase_project_id=config.get("lakebase_project_id"),
)
mlflow.models.set_model(agent)
