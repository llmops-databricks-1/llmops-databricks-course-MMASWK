# Databricks notebook source
from databricks import agents
from databricks.sdk import WorkspaceClient
from databricks.sdk.runtime import dbutils
from loguru import logger
from mlflow import MlflowClient

from filteredNotFrenzied.config import ProjectConfig

# COMMAND ----------

# Get parameters (passed via base_parameters in job YAML)
git_sha = dbutils.widgets.get("git_sha")
env = dbutils.widgets.get("env")
secret_scope = "mdpi-agent-scope"

# Load configuration
cfg = ProjectConfig.from_yaml(
    "/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/project_config.yml",
    env=env,
)

# Get model details
model_name = f"{cfg.catalog}.{cfg.schema}.mdpi_agent"
endpoint_name = f"mdpi-agent-endpoint-{env}-course"

client = MlflowClient()
model_version = client.get_model_version_by_alias(model_name, "latest-model").version

# Get experiment ID
experiment = client.get_experiment_by_name(cfg.experiment_name)

logger.info("Deploying agent:")
logger.info(f"  Model: {model_name}")
logger.info(f"  Version: {model_version}")
logger.info(f"  Endpoint: {endpoint_name}")


# COMMAND ----------
client_id = dbutils.secrets.get("dev_SPN", "client_id")
client_secret = dbutils.secrets.get("dev_SPN", "client_secret")

# COMMAND ----------

# Deploy agent to serving endpoint
agents.deploy(
    model_name=model_name,
    model_version=int(model_version),
    endpoint_name=endpoint_name,
    # usage_policy_id=cfg.usage_policy_id,
    scale_to_zero=True,
    workload_size="Small",
    deploy_feedback_model=False,
    environment_vars={
        "GIT_SHA": git_sha,
        "MODEL_VERSION": model_version,
        "MODEL_SERVING_ENDPOINT_NAME": endpoint_name,
        "MLFLOW_EXPERIMENT_ID": experiment.experiment_id,
        "LAKEBASE_SP_CLIENT_ID": client_id,
        "LAKEBASE_SP_CLIENT_SECRET": client_secret,
        "LAKEBASE_SP_HOST": WorkspaceClient().config.host,
    },
)

logger.info("✓ Deployment complete!")
