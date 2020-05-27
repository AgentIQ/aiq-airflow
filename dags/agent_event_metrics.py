
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook
from datetime import datetime, timedelta

BATCH_SIZE = 200
default_args = {
    'owner': 'Jaekwan',
    'depends_on_past': False,
    'start_date': datetime(2020, 5, 1),
    'email': ['swe@agentiq.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)}

dag = DAG('agent_event_metrics',
          default_args=default_args,
          schedule_interval=timedelta(days=1))


def get_connection(name):
    return PostgresHook(postgres_conn_id=name).get_conn()


def analytics_select_query(table, interested_events, start_time, end_time):
    print(interested_events)
    return f"""SELECT payload->>'action', payload->>'conversation_id', date
        FROM {table}
        WHERE payload->>'action' in {interested_events}
        AND payload->>'conversation_id' is NOT NULL
        AND date between '{start_time}'::timestamp and '{end_time}'::timestamp;"""


def stats_upsert_query():
    return f"""INSERT INTO agent_events (event_name, conversation_id, time_stamp)
        VALUES (%s, %s, %s)
        ON CONFLICT ON CONSTRAINT uniq_event_per_conversation
        DO NOTHING;"""


def move_data_into_stat(analytics_query):
    print(f'Query: {analytics_query}')

    stats_conn = get_connection('STATS_DB')
    analytics_conn = get_connection('ANALYTICS_DB')

    if (not stats_conn or not analytics_conn):
        raise Exception('Unable to connect to database')

    stats_cursor = stats_conn.cursor()
    analytics_cursor = analytics_conn.cursor()

    analytics_cursor.execute(analytics_query)
    count = 0
    print(f'BATCH SIZE: {BATCH_SIZE}')
    while True:
        rows = analytics_cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break

        print(f'Upserting # {len(rows)}')
        for row in rows:
            stats_cursor.execute(stats_upsert_query(), [row[0], row[1], row[2]])
            stats_conn.commit()
        count += len(rows)

    stats_cursor.close()
    analytics_conn.close()
    return count


def get_config(name):
    conf = {
        'suggestion': {
            'analytics_table': 'suggestions',
            'events': ('conversations.suggest.send',
                       'conversations.suggest.click',
                       'conversations.suggest.edit',
                       'conversations.suggest.show')},
        'asset': {
            'analytics_table': 'assets',
            'events': ('conversations.kb.assets.send',
                       'conversations.kb.assets.click',
                       'conversations.kb.assets.show')},
        'document': {
            'analytics_table': 'documents',
            'events': ('conversations.kb.documents.send',
                       'conversations.kb.documents.click',
                       'conversations.kb.documents.show')}}

    if name not in conf:
        raise Exception(f'Unable to find configuration for {name}')

    return conf[name]


def move_analytics_table_to_stats(name, start_time, end_time):
    print(f'execution_start={start_time} - execution_end={end_time}')
    conf = get_config(name)
    return move_data_into_stat(analytics_select_query(conf['analytics_table'],
                                                      conf['events'],
                                                      start_time,
                                                      end_time))


def move_suggestions_to_stats(*args, **kwargs):
    return move_analytics_table_to_stats('suggestion',
                                         kwargs['execution_date'].subtract(days=1),
                                         kwargs['execution_date'])


def move_documents_to_stats(*args, **kwargs):
    return move_analytics_table_to_stats('document',
                                         kwargs['execution_date'].subtract(days=1),
                                         kwargs['execution_date'])


def move_assets_to_stats(*args, **kwargs):
    return move_analytics_table_to_stats('asset',
                                         kwargs['execution_date'].subtract(days=1),
                                         kwargs['execution_date'])


t0 = PythonOperator(
    task_id='suggestion_to_stats',
    python_callable=move_suggestions_to_stats,
    provide_context=True,
    dag=dag)

t1 = PythonOperator(
    task_id='asset_to_stats',
    python_callable=move_assets_to_stats,
    provide_context=True,
    dag=dag)

t2 = PythonOperator(
    task_id='documents_to_stats',
    python_callable=move_documents_to_stats,
    provide_context=True,
    dag=dag)

t0 >> t1 >> t2
