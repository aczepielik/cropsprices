import json
import logging
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List

import requests
from pydantic import ValidationError
from tqdm import tqdm

from cropsprices.apiquery import query_paged_api
from cropsprices.models import Resource

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Bulk Data Load")


VALID_PREFIXES = [
    "ceny hurtowe i targowiskowe",
    "Rynek owoców i warzyw",
]


class ResourceManager:
    def __init__(self, output_dir: str = "data/raw", overrides_dir: str = "data/overrides"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.overrides_dir = Path(overrides_dir)
        self.overrides_dir.mkdir(parents=True, exist_ok=True)

    def extract_data(self, responses: List[Dict[str, Any]]):
        return reduce(
            lambda x, y: x + y, map(lambda page: page.get("data", []), responses), []
        )

    def filter_and_validate_resources(
        self, resources: List[Dict[str, Any]]
    ) -> List[Resource]:
        filtered_resources = []
        for resource in resources:
            title = resource.get("attributes", {}).get("title", "")
            if not any(title.startswith(p) for p in VALID_PREFIXES):
                continue
            try:
                r = Resource(**resource)
                filtered_resources.append(r)
            except ValidationError as e:
                logger.error(f"Validation error for resource: {e}")
        return filtered_resources

    def download_xlsx_files(self, resources: List[Resource]):
        xlsx_files = [
            file
            for resource in resources
            for file in resource.attributes.files
            if file.format.lower() == "xlsx"
        ]

        manifest = []
        with tqdm(total=len(xlsx_files), desc="Downloading XLSX files") as pbar:
            for file in xlsx_files:
                self._download_and_save(file, manifest, pbar)

        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, default=str)
        logger.info(f"Saved manifest with {len(manifest)} files to {manifest_path}")

    def _download_and_save(self, file, manifest: list, pbar):
        try:
            file_id = str(file.download_url).split("/")[-2]
            filename = f"{file_id}.xlsx"
            filepath = self.output_dir / filename

            if filepath.exists():
                logger.info(f"Already exists: {filename}")
                manifest.append({"file_id": file_id, "filename": filename, "url": str(file.download_url)})
                pbar.update(1)
                return

            # Check for manual override before downloading
            override_path = self.overrides_dir / filename
            if override_path.exists():
                import shutil
                shutil.copy2(override_path, filepath)
                logger.info(f"Applied override: {filename}")
                manifest.append({"file_id": file_id, "filename": filename, "url": str(file.download_url), "source": "override"})
                pbar.update(1)
                return

            response = self._download_file(file.download_url)
            filepath.write_bytes(response.content)
            logger.info(f"Downloaded: {filename}")
            manifest.append({"file_id": file_id, "filename": filename, "url": str(file.download_url)})
        except Exception as e:
            logger.error(f"Error downloading {file.download_url}: {str(e)}")
        finally:
            pbar.update(1)

    def _download_file(self, url):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response

    def process_resources(self, url: str, params: Dict[str, str]):
        all_responses = query_paged_api(url, params)
        all_resources = self.extract_data(all_responses)
        filtered_resources = self.filter_and_validate_resources(all_resources)

        logger.info(f"Validated {len(filtered_resources)} resources")
        self.download_xlsx_files(filtered_resources)


def main():
    url = "https://api.dane.gov.pl/1.4/datasets/912,zintegrowany-system-rolniczej-informacji-rynkowej-biuletyny-informacyjne-rynek-owocow-i-warzyw-swiezych/resources"
    params = {
        "sort": "modified",
    }
    resource_manager = ResourceManager()
    resource_manager.process_resources(url, params)


if __name__ == "__main__":
    main()
