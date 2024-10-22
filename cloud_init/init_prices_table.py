import logging

from google.cloud import bigquery
from google.cloud import logging as cloud_logging

# Initialize Google Cloud Logging client
logging_client = cloud_logging.Client()
logging_client.setup_logging()
logger = logging.getLogger("Cloud Init")

# Initialize a BigQuery client
client = bigquery.Client()

# Define the schema for the table
schema = [
    bigquery.SchemaField("Product", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("Unit", "STRING"),
    bigquery.SchemaField("Place", "STRING"),
    bigquery.SchemaField("Date", "DATE"),
    bigquery.SchemaField("Statistic", "STRING"),
    bigquery.SchemaField("Price", "FLOAT"),
    bigquery.SchemaField("Origin", "STRING"),
]

# Set up the table reference
table_id = "cropsprices.cropsprices_core.prices"
table = bigquery.Table(table_id, schema=schema)

# Create the table
table = client.create_table(table)

# Log the table creation
logger.info(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
