import logging
import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from google.cloud import secretmanager

# Load environment variables from .env file
load_dotenv()

TableType = Literal["fruits", "vegetables"]
EnvironmentType = Literal["dev", "staging", "prod"]


def _get_secret(project_id: str, secret_name: str) -> str:
    """Get secret from Secret Manager"""
    logging.debug(f"Fetching secret: {secret_name}")

    client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

    try:
        response = client.access_secret_version(request={"name": secret_path})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.error(f"Failed to fetch secret {secret_name}: {e}")
        raise


@dataclass
class DatabaseConfig:
    dev = {"type": "duckdb", "args": {"path": ".data/local.db"}}
    staging = {
        "type": "cloudduckdb",
        "args": {
            "bucket": _get_secret(
                project_id=os.getenv("PROJECT_ID", ""),
                secret_name="bucket-name",
            ),
            "path": "exports",
            "materialize": True,
        },
    }
    prod = {
        "type": "cloudduckdb",
        "args": {
            "bucket": _get_secret(
                project_id=os.getenv("PROJECT_ID", ""),
                secret_name="bucket-name",
            ),
            "path": "exports/latest",
            "materialize": True,
        },
    }


@dataclass
class AppConfig:
    """Configuration settings for the application"""

    COLORS = {
        "primary": "#606c38",
        "secondary": "#dda15e",
        "accent": "#bc6c25",
        "positive": "#4caf50",
        "negative": "#b71c1c",
        "info": "#29b6f6",
        "warning": "#f9a825",
        "light": "fffae0",
    }

    TABLE_COLUMNS = [
        {"name": "product", "label": "Produkt", "field": "product"},
        {"name": "price_min", "label": "Cena min", "field": "price_min"},
        {"name": "price_max", "label": "Cena max", "field": "price_max"},
        {"name": "year_ago_min", "label": "Rok temu min", "field": "year_ago_min"},
        {"name": "year_ago_max", "label": "Rok temu max", "field": "year_ago_max"},
    ]

    @staticmethod
    def get_db_config(env: EnvironmentType = "dev") -> dict:
        return getattr(DatabaseConfig, env)
