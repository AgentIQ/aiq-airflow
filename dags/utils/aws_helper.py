"""
    AWS helpers and constants
"""
import os


def create_etl_daily_key(env, subdir, date_string, file_name=None):
    if file_name:
        return os.path.join(env, subdir, 'daily', date_string, file_name)
    else:
        return os.path.join(env, subdir, 'daily', date_string)
