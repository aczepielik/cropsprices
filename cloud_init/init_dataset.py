import logging

from google.cloud import bigquery
from google.cloud import logging as cloud_logging

# Initialize Google Cloud Logging client
logging_client = cloud_logging.Client()

# Get the default logger
logger = logging_client.logger("Cloud Init")
logger.level = logging.INFO

# Initialize a BigQuery client
client = bigquery.Client()

# Initialize dataset
dataset = client.create_dataset("cropsprices_core")

# Log dataset creation
logger.info(f"Created dataset {dataset.project}.{dataset.dataset_id}")
