"""
# Suggestions
This dag:

* extracts today's conversations from analytics
* transforms it into format suitable for training
* collects all such training input files from s3
* collects ai_configs from ai-manager to also serve as inputs for training
* trains/ generates models which are used computation of suggestion ranks by ai-engine

"""

import os
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta
from utils.airflow_helper import get_environments


default_args = {
    'owner': 'Akshay',
    'depends_on_past': False,
    'start_date': datetime(2020, 5, 27),
    'email': ['swe@agentiq.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)}

dag = DAG('suggestions',
          default_args=default_args,
          # run every day at 4:30am PST
          schedule_interval='30 11 * * 1-7')
dag.doc_md = __doc__

# It is not recommanded to use Variable with global scope
# but not sure if there is another way to inject airflow variables
# into envionment variables.
env = os.environ.copy()
env.update(get_environments())

extract_conversation = BashOperator(
    task_id='extract_conversation',
    bash_command='python3 -m tools.analysis.simple_stats --daily --upload_to_s3',
    retries=1,
    env=env,
    dag=dag)

transform_conversation = BashOperator(
    task_id='transform_conversation',
    bash_command="python3 -m tools.etl.extract_training_data \
    --bucket_name=agentiq-suggestion-data \
     --download_inputs_from_s3=True \
     --action='upload'",
    retries=1,
    env=env,
    dag=dag)

collect_older_transformed_convos = BashOperator(
    task_id='collect_older_transformed_convos',
    bash_command="python3 -m tools.etl.extract_training_data \
    --bucket_name=agentiq-suggestion-data  \
    --action='clean_training_data'",
    retries=1,
    env=env,
    dag=dag)


collect_ai_configs = BashOperator(
    task_id='collect_ai_configs',
    bash_command='python3 -m tools.suggestions.pull_expressions_actions --upload_to_s3=True',
    retries=1,
    env=env,
    dag=dag)


generate_suggestion_models = BashOperator(
    task_id='generate_suggestion_models',
    bash_command="python3 -m tools.suggestions.generate_model \
    --output=lm,vsm,dm  \
    --mode=generate \
    --upload_to_s3=True \
    --download_inputs_from_s3=True",
    retries=1,
    env=env,
    dag=dag)


extract_conversation >> transform_conversation >> collect_older_transformed_convos >> collect_ai_configs >> generate_suggestion_models
