import psycopg2 

import streamlit as st

# Credentials
proddb_credentials = {
    'user': st.secrets.get('DB_USER'),
    'password': st.secrets.get('DB_PASS'),
    'host': st.secrets.get('DB_HOST'),
    'port': st.secrets.get('DB_PORT'),
    'database': st.secrets.get('DB_NAME')
}

def get_sql_connection():
    connection = psycopg2.connect(user=proddb_credentials['user'],
                              password=proddb_credentials['password'],
                              host=proddb_credentials['host'],
                              port=proddb_credentials['port'],
                              database=proddb_credentials['database'])

    cursor = connection.cursor()

    return cursor 