import argparse
import datetime

from google.cloud import bigquery, secretmanager


def export_table_to_parquet(project_id, dataset_id, table_id, gcs_bucket):
    """
    Export a BigQuery table to a Parquet file in Google Cloud Storage

    Args:
        project_id (str): GCP project ID
        dataset_id (str): BigQuery dataset ID
        table_id (str): BigQuery table ID
        gcs_bucket (str): GCS bucket name where parquet file will be stored
    """
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)

    # Get table reference
    table_ref = client.dataset(dataset_id).table(table_id)

    # Configure export job
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    destination_uri = f"gs://{gcs_bucket}/exports/{table_id}_{timestamp}.parquet"

    job_config = bigquery.ExtractJobConfig()
    job_config.destination_format = bigquery.DestinationFormat.PARQUET

    # Start export job
    extract_job = client.extract_table(
        table_ref, destination_uri, job_config=job_config
    )

    # Wait for job to complete
    extract_job.result()

    print(f"Exported {project_id}.{dataset_id}.{table_id} to {destination_uri}")


def main():
    parser = argparse.ArgumentParser(description="Export BigQuery table to Parquet")
    parser.add_argument("--project-id", help="GCP Project ID", default="cropsprices")
    parser.add_argument(
        "--dataset-id",
        help="BigQuery Dataset ID",
        default="cropsprices_core",
    )
    parser.add_argument("--table-id", required=True, help="BigQuery Table ID")

    args = parser.parse_args()

    secret_client = secretmanager.SecretManagerServiceClient()
    secret_name = "projects/cropsprices/secrets/bucket-name/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})
    gcs_bucket = response.payload.data.decode("UTF-8")

    export_table_to_parquet(args.project_id, args.dataset_id, args.table_id, gcs_bucket)


if __name__ == "__main__":
    main()
