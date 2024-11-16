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
    bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("type", "STRING"),
    bigquery.SchemaField(
        "attributes",
        "RECORD",
        fields=[
            bigquery.SchemaField("format", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("is_chart_creation_blocked", "BOOLEAN"),
            bigquery.SchemaField("has_research_data", "BOOLEAN"),
            bigquery.SchemaField("openness_score", "INTEGER"),
            bigquery.SchemaField("contains_protected_data", "BOOLEAN"),
            bigquery.SchemaField("supplements", "STRING", mode="REPEATED"),
            bigquery.SchemaField("data_date", "TIMESTAMP"),
            bigquery.SchemaField("has_high_value_data", "BOOLEAN"),
            bigquery.SchemaField("has_dynamic_data", "BOOLEAN"),
            bigquery.SchemaField("link", "STRING"),
            bigquery.SchemaField("csv_download_url", "STRING"),
            bigquery.SchemaField("csv_file_url", "STRING"),
            bigquery.SchemaField("modified", "TIMESTAMP"),
            bigquery.SchemaField("visualization_types", "STRING", mode="REPEATED"),
            bigquery.SchemaField("verified", "TIMESTAMP"),
            bigquery.SchemaField("media_type", "STRING"),
            bigquery.SchemaField("special_signs", "STRING", mode="REPEATED"),
            bigquery.SchemaField("downloads_count", "INTEGER"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField(
                "regions",
                "RECORD",
                mode="REPEATED",
                fields=[
                    bigquery.SchemaField("region_id", "STRING"),
                    bigquery.SchemaField("hierarchy_label", "STRING"),
                    bigquery.SchemaField("name", "STRING"),
                ],
            ),
            bigquery.SchemaField("download_url", "STRING"),
            bigquery.SchemaField("jsonld_download_url", "STRING"),
            bigquery.SchemaField("file_size", "INTEGER"),
            bigquery.SchemaField("jsonld_file_size", "INTEGER"),
            bigquery.SchemaField("views_count", "INTEGER"),
            bigquery.SchemaField("jsonld_file_url", "STRING"),
            bigquery.SchemaField("csv_file_size", "INTEGER"),
            bigquery.SchemaField(
                "files",
                "RECORD",
                mode="REPEATED",
                fields=[
                    bigquery.SchemaField("file_size", "INTEGER"),
                    bigquery.SchemaField("format", "STRING"),
                    bigquery.SchemaField("openness_score", "INTEGER"),
                    bigquery.SchemaField("download_url", "STRING"),
                ],
            ),
            bigquery.SchemaField("language", "STRING"),
            bigquery.SchemaField("created", "TIMESTAMP"),
            bigquery.SchemaField("file_url", "STRING"),
        ],
    ),
    bigquery.SchemaField(
        "relationships",
        "RECORD",
        fields=[
            bigquery.SchemaField(
                "institution",
                "RECORD",
                fields=[
                    bigquery.SchemaField(
                        "data",
                        "RECORD",
                        fields=[
                            bigquery.SchemaField("type", "STRING"),
                            bigquery.SchemaField("id", "STRING"),
                        ],
                    ),
                    bigquery.SchemaField(
                        "links",
                        "RECORD",
                        fields=[
                            bigquery.SchemaField("related", "STRING"),
                        ],
                    ),
                ],
            ),
            bigquery.SchemaField(
                "dataset",
                "RECORD",
                fields=[
                    bigquery.SchemaField(
                        "data",
                        "RECORD",
                        fields=[
                            bigquery.SchemaField("type", "STRING"),
                            bigquery.SchemaField("id", "STRING"),
                        ],
                    ),
                    bigquery.SchemaField(
                        "links",
                        "RECORD",
                        fields=[
                            bigquery.SchemaField("related", "STRING"),
                        ],
                    ),
                ],
            ),
        ],
    ),
    bigquery.SchemaField(
        "links",
        "RECORD",
        fields=[
            bigquery.SchemaField("self", "STRING"),
        ],
    ),
]

# Set up the table reference
table_id = "cropsprices.cropsprices_core.resources"
table = bigquery.Table(table_id, schema=schema)

# Create the table
table = client.create_table(table)

# Log the table creation
logger.info(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
