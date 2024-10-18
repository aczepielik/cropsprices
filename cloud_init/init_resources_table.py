from google.cloud import bigquery
from google.cloud import logging as cloud_logging

# Initialize Google Cloud Logging client
logging_client = cloud_logging.Client()

# Get the default logger
logger = logging_client.logger('resources_table_creation')

# Initialize a BigQuery client
client = bigquery.Client()

# Define the schema for the table
schema = [
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("type", "STRING"),
    bigquery.SchemaField("format", "STRING"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("is_chart_creation_blocked", "BOOLEAN"),
    bigquery.SchemaField("openness_score", "INTEGER"),
    bigquery.SchemaField("contains_protected_data", "BOOLEAN"),
    bigquery.SchemaField("data_date", "DATE"),
    bigquery.SchemaField("link", "STRING"),
    bigquery.SchemaField("modified", "TIMESTAMP"),
    bigquery.SchemaField("verified", "TIMESTAMP"),
    bigquery.SchemaField("media_type", "STRING"),
    bigquery.SchemaField("downloads_count", "INTEGER"),
    bigquery.SchemaField("description", "STRING"),
    bigquery.SchemaField("regions", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("region_id", "STRING"),
        bigquery.SchemaField("hierarchy_label", "STRING"),
        bigquery.SchemaField("name", "STRING"),
    ]),
    bigquery.SchemaField("download_url", "STRING"),
    bigquery.SchemaField("file_size", "INTEGER"),
    bigquery.SchemaField("views_count", "INTEGER"),
    bigquery.SchemaField("files", "RECORD", mode="REPEATED", fields=[
        bigquery.SchemaField("file_size", "INTEGER"),
        bigquery.SchemaField("format", "STRING"),
        bigquery.SchemaField("openness_score", "INTEGER"),
        bigquery.SchemaField("download_url", "STRING"),
    ]),
    bigquery.SchemaField("language", "STRING"),
    bigquery.SchemaField("created", "TIMESTAMP"),
    bigquery.SchemaField("file_url", "STRING"),
    bigquery.SchemaField("institution", "RECORD", fields=[
        bigquery.SchemaField("id", "STRING"),
        bigquery.SchemaField("type", "STRING"),
    ]),
    bigquery.SchemaField("dataset", "RECORD", fields=[
        bigquery.SchemaField("id", "STRING"),
        bigquery.SchemaField("type", "STRING"),
    ]),
]

# Set up the table reference
table_id = "cropsprices.your_dataset.resources"
table = bigquery.Table(table_id, schema=schema)

# Create the table
table = client.create_table(table)

# Log the table creation
logger.log_text(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
