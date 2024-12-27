import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TableType = Literal["fruits", "vegetables"]
EnvironmentType = Literal["dev", "staging", "prod"]


@dataclass
class DatabaseConfig:
    dev = {"type": "duckdb", "path": ".data/local.db"}
    staging = {
        "type": "bigquery",
        "project": os.getenv("STAGING_PROJECT_ID"),
        "dataset": os.getenv("STAGING_DATASET"),
    }
    prod = {
        "type": "bigquery",
        "project": os.getenv("PROD_PROJECT_ID"),
        "dataset": os.getenv("PROD_DATASET"),
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
