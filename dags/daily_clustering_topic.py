import os
import nltk
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from airflow.models import Variable
from utils.airflow_helper import get_environments
from tools.config.config import config


default_args = {
    'owner': 'Jaekwan',
    'depends_on_past': False,
    'start_date': datetime(2020, 6, 1),
    'email': ['swe@agentiq.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)}

dag = DAG('Daily_topic_clustering',
          default_args=default_args,
          # run every day at 12:30am PST after conversation closure
          schedule_interval='30 07 * * 1-7')

env = os.environ.copy()
env.update(get_environments())

def download_nltk_data(*args, **kwargs):
    for data_file in config['nltk_models']:
        nltk.download(data_file)


# Dependent nltk data for topic.
download_model = PythonOperator(
    task_id='download_dependent_data',
    python_callable=download_nltk_data,
    dag=dag)



# The time is pinned due to the timezone handling within simple_stats script
# TODO(jaekwan): Come back and align the time arguments
upload_to_s3 = BashOperator(
    task_id='clustering_data_to_s3',
    bash_command='python -m tools.analysis.simple_stats \
            --start_date="{{ execution_date.subtract(days=1).format("%Y-%m-%d") }} 17:00:00" \
            --end_date="{{ execution_date.format("%Y-%m-%d") }} 16:59:59" \
            --message_env_filter={{ var.value.ENVIRONMENT }} \
            --upload_clustering_files \
            --expand_to_full_conversations',
    retries=1,
    env=env,
    dag=dag)

upload_to_db = BashOperator(
    task_id='clustering_data_to_db',
    bash_command='python -m tools.analysis.cluster_management \
            --start_date="{{ execution_date.subtract(days=1).format("%Y-%m-%d") }} 17:00:00" \
            --end_date="{{ execution_date.format("%Y-%m-%d") }} 16:59:59" \
            --upload_to_db',
    retries=1,
    env=env,
    dag=dag)

download_model >> upload_to_s3 >> upload_to_db