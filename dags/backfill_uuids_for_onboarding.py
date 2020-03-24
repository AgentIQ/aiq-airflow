
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook
from datetime import datetime, timedelta


params = {}  # TODO (Akshay) start and end date could be used here and for insert query

default_args = {
    'owner': 'Airflow',
    'depends_on_past': False,
    'start_date': datetime(2019, 12, 4),
    'email': ['software_engineering@agentiq.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)}

dag = DAG('backfill_uuids_for_onboarding',
          default_args=default_args,
          schedule_interval='10 02 * * 1-7',
          params=params)


NUM_ANALYTICS_ROWS = 200


def get_analytics_stats_conn_cursors():
    analytics_conn = PostgresHook(postgres_conn_id='ANALYTICS_DB').get_conn()
    stats_conn = PostgresHook(postgres_conn_id='STATS_DB').get_conn()

    analytics_server_cursor = analytics_conn.cursor("analytics_server_cursor")
    # providing an argument makes this a server cursor, which wouldn't hold
    # all records in the memory
    # https://www.psycopg.org/docs/usage.html#server-side-cursors
    stats_client_cursor = stats_conn.cursor()
    return (analytics_conn, analytics_server_cursor, stats_conn, stats_client_cursor)


def close_conns_cursors(conns_cursors):
    for c in conns_cursors:
        c.close()


def backfill_uuids():
    (analytics_conn, analytics_server_cursor, stats_conn, stats_client_cursor) = get_analytics_stats_conn_cursors()

    analytics_server_cursor.execute("select uuid, device_id from customer_ids_mapping;")
    while True:
        rows = analytics_server_cursor.fetchmany(NUM_ANALYTICS_ROWS)
        if not rows:
            break
        for row in rows:
            query = """insert into customer_events(uuid)
                                  values(%s) where device_id = %s
                                  on conflict(uuid) do nothing;
                    """
            stats_client_cursor.execute(query, [row[0], row[1]])
            stats_conn.commit()

    close_conns_cursors((analytics_conn, analytics_server_cursor, stats_conn, stats_client_cursor))


t0 = PythonOperator(
    task_id='backfill_uuids',
    python_callable=backfill_uuids,
    dag=dag)
