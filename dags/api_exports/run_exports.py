
from os.path import expanduser
from tools.api_exports.agents import fetch_agents
from tools.api_exports.customers import fetch_customers
from tools.api_exports.conversations import fetch_conversations
from tools.utils.time_util import get_n_days_from_now_string, get_current_utc_string, get_localized_date
from aiqdynamo.tables.agents import AgentsTable
from aiqdynamo.tables.customers import CustomersTable
from aiqdynamo.tables.conversations import ConversationsTable

import json
import argparse


def split_into_batches(records, batch_split_size):
    if not records:
        return []
    for i in range(0, len(records), batch_split_size):
        yield records[i:i + batch_split_size]


default_batch_split_size = 15

def batch_write(file_path, batch_func, batch_split_size=default_batch_split_size):

    if not batch_split_size:
        raise Exception('batch_split_size is missing')

    with open(file_path, 'r') as records_file:
        records = json.load(records_file)

        for batch in split_into_batches(records, batch_split_size):
            batch_func(batch)
            time.sleep(2)


def export_conversations_to_dynamo(start_date, end_date):
    conversations_file_path = fetch_conversations(start_date, end_date)
    batch_write(conversations_file_path, ConversationsTable.batch_write_conversation_records)


def export_customers_to_dynamo(start_date, end_date):
    customers_file_path = fetch_customers(start_date, end_date)
    batch_write(customers_file_path, CustomersTable.batch_write_customer_records)


def export_agents_to_dynamo(start_date, end_date):
    agents_file_path = fetch_agents(start_date, end_date)
    batch_write(agents_file_path, AgentsTable.batch_write_agent_records)


def run_exports(start_date=None, end_date=None):

    if not end_date:
        end_date = get_current_utc_string()

    if not start_date:
        start_date = get_n_days_from_now_string(1, past=True)

    end_date = get_localized_date(end_date)
    start_date = get_localized_date(start_date)

    export_agents_to_dynamo(start_date, end_date)
    export_customers_to_dynamo(start_date, end_date)
    export_conversations_to_dynamo(start_date, end_date)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=str, help='Start date - format YYYY-MM-DD %H:%m:%s', default=None)
    parser.add_argument('--end_date', type=str, help='End date - format YYYY-MM-DD %H:%m:%s', default=None)

    args = parser.parse_args()
    run_exports(args.start_date, args.end_date)
