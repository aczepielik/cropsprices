import logging
from functools import reduce
from typing import Any, Dict, List

import requests
from google.cloud import bigquery, secretmanager, storage
from google.cloud import logging as cloud_logging
from pydantic import ValidationError
from tqdm import tqdm

from cropsprices.apiquery import query_paged_api
from cropsprices.models import Resource


class ResourceManager:
    def __init__(self):
        self.logging_client = cloud_logging.Client()
        self.logging_client.setup_logging()
        self.logger = logging.getLogger("Bulk Data Load")
        self.bq_client = bigquery.Client()
        self.storage_client = storage.Client()
        self.secret_client = secretmanager.SecretManagerServiceClient()

        self.dataset_id = "cropsprices_core"
        self.table_id = "resources"
        self.dataset_ref = self.bq_client.dataset(self.dataset_id)
        self.table_ref = self.dataset_ref.table(self.table_id)

        self.bucket = self._get_gcs_bucket()

    def _get_gcs_bucket(self):
        secret_name = "projects/cropsprices/secrets/bucket-name/versions/latest"
        response = self.secret_client.access_secret_version(
            request={"name": secret_name}
        )
        bucket_name = response.payload.data.decode("UTF-8")
        return self.storage_client.bucket(bucket_name)

    def extract_data(self, responses: List[Dict[str, Any]]):
        return reduce(
            lambda x, y: x + y, map(lambda page: page.get("data", []), responses), []
        )

    def filter_and_validate_resources(
        self, resources: List[Dict[str, Any]]
    ) -> List[Resource]:
        filtered_resources = []
        for resource in resources:
            try:
                r = Resource(**resource)
                filtered_resources.append(r)
            except ValidationError as e:
                self.logger.error(f"Validation error for resource: {e}")
        return filtered_resources

    def write_to_bigquery(self, resources: List[Resource]):
        rows_to_insert = [resource.model_dump(mode="json") for resource in resources]
        self.logger.info(f"Planned to insert {len(rows_to_insert)} rows.")
        errors = self.bq_client.insert_rows_json(self.table_ref, rows_to_insert)
        if errors:
            self.logger.error(f"Encountered errors while inserting rows: {errors}")
            exit(-1)
        else:
            self.logger.info(
                f"Successfully inserted {len(rows_to_insert)} rows into BigQuery"
            )

    def upload_xlsx_to_gcs(self, resources: List[Resource]):
        xlsx_files = [
            file
            for resource in resources
            for file in resource.attributes.files
            if file.format.lower() == "xlsx"
        ]

        with tqdm(total=len(xlsx_files), desc="Uploading XLSX files to GCS") as pbar:
            for file in xlsx_files:
                self._process_xlsx_file(file, pbar)

    def _process_xlsx_file(self, file, pbar):
        try:
            response = self._download_file(file.download_url)
            self._upload_to_gcs(file, response.content)
        except Exception as e:
            self.logger.error(f"Error processing file {file.download_url}: {str(e)}")
        finally:
            pbar.update(1)

    def _download_file(self, url):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response

    def _upload_to_gcs(self, file, content):
        blob_name = (
            f"wholesale_prices_workbooks/{str(file.download_url).split('/')[-2]}.xlsx"
        )
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(content)
        self.logger.info(f"Uploaded {file.download_url} to GCS at {blob.public_url}")

    def process_resources(self, url: str, params: Dict[str, str]):
        all_responses = query_paged_api(url, params)
        all_resources = self.extract_data(all_responses)
        filtered_resources = self.filter_and_validate_resources(all_resources)

        self.write_to_bigquery(filtered_resources)
        self.upload_xlsx_to_gcs(filtered_resources)


def main():
    url = "https://api.dane.gov.pl/1.4/datasets/912,zintegrowany-system-rolniczej-informacji-rynkowej-biuletyny-informacyjne-rynek-owocow-i-warzyw-swiezych/resources"
    params = {
        "sort": "modified",
        "title[prefix]": "ceny hurtowe i targowiskowe",
    }
    resource_manager = ResourceManager()
    resource_manager.process_resources(url, params)


if __name__ == "__main__":
    main()
