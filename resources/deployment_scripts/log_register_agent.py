# Databricks notebook source

import mlflow

from filteredNotFrenzied.agent import log_register_agent
from filteredNotFrenzied.config import ProjectConfig
from filteredNotFrenzied.evaluation import evaluate_agent
from filteredNotFrenzied.utils.common import get_widget

env = get_widget("env", "dev")
git_sha = get_widget("git_sha", "local")
run_id = get_widget("run_id", "local")

cfg = ProjectConfig.from_yaml(
    config_path="/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/project_config.yml",
    env=env,
)

mlflow.set_experiment(cfg.experiment_name)

# COMMAND ----------
# Run evaluation
results = evaluate_agent(
    cfg,
    "/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/eval_inputs.txt",
)

# COMMAND ----------
# Log and register model
registered_model = log_register_agent(
    cfg=cfg,
    git_sha=git_sha,
    run_id=run_id,
    agent_code_path="/Workspace/Users/maximilian.meisterarendt@swk.de/.bundle/llmops-databricks-course-MMASWK/dev/files/mdpi_agent.py",
    model_name=f"{cfg.catalog}.{cfg.schema}.mdpi_agent",
    evaluation_metrics=results.metrics,
)
