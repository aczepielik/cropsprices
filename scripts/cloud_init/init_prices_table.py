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
# Set up the table references
fruit_table_id = "cropsprices.cropsprices_core.wholesale_prices_fruits"
vegetable_table_id = "cropsprices.cropsprices_core.wholesale_prices_vegetables"
fruit_table = bigquery.Table(fruit_table_id, schema=schema)
vegetable_table = bigquery.Table(vegetable_table_id, schema=schema)

# Create the tables
fruit_table = client.create_table(fruit_table)
vegetable_table = client.create_table(vegetable_table)

# Log the table creations
logger.info(
    f"Created fruit prices table {fruit_table.project}.{fruit_table.dataset_id}.{fruit_table.table_id}"
)
logger.info(
    f"Created vegetable prices table {vegetable_table.project}.{vegetable_table.dataset_id}.{vegetable_table.table_id}"
)
