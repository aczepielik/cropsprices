import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
from google.cloud import bigquery

from .config import AppConfig, EnvironmentType


class DatabaseConnector(ABC):
    """Abstract base class for database connections"""

    @abstractmethod
    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        pass

    @abstractmethod
    def format_date(self, date_column: str, format_str: str) -> str:
        pass

    @abstractmethod
    def concat(self, *args: str) -> str:
        pass

    @abstractmethod
    def case_when(
        self, condition: str, then_value: str, else_value: str = "NULL"
    ) -> str:
        pass

    @abstractmethod
    def escape_column(self, column_name: str) -> str:
        """Escape column name according to database syntax"""
        pass

    @abstractmethod
    def cast_date_to_compare(self, date):
        pass


class DuckDBConnector(DatabaseConnector):
    def __init__(self, db_path: str):
        self.conn = duckdb.connect(db_path, read_only=True)

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        # Replace named parameters with ? placeholders for DuckDB
        if parameters:
            # Create a list to store parameters in order
            param_list = []
            modified_query = query

            # Replace each @param with ? and collect parameters in order
            for param_name, param_value in parameters.items():
                placeholder = f"@{param_name}"
                modified_query = modified_query.replace(placeholder, "?")
                param_list.append(param_value)

            return self.conn.execute(modified_query, param_list).fetchall()
        return self.conn.execute(query).fetchall()

    def format_date(self, date_column: str, format_str: str) -> str:
        return f"strftime({date_column}, '{format_str}')"

    def concat(self, *args: str) -> str:
        return " || ".join(args)

    def case_when(
        self, condition: str, then_value: str, else_value: str = "NULL"
    ) -> str:
        return f"CASE WHEN {condition} THEN {then_value} ELSE {else_value} END"

    def escape_column(self, column_name: str) -> str:
        return f'"{column_name}"'

    def cast_date_to_compare(self, date):
        return date


class CloudDuckDBConnector(DuckDBConnector):
    def __init__(self, bucket: str, path: str, materialize: bool = False):
        self.conn = duckdb.connect(":memory:")
        self._init_views(bucket, path, materialize)

    def _init_views(self, bucket: str, path: str, materialize: bool = False):
        """Initialize views from parquet files"""
        base_path = f"gs://{bucket}/{path}"
        collection_type = "TABLE" if materialize else "VIEW"

        # Load httpfs extension and set credentials
        logging.debug("Installing and loading https.")
        self.conn.execute("INSTALL httpfs;")
        self.conn.execute("LOAD httpfs;")
        logging.debug("Loaded https.")

        logging.debug("Starting authentication to Cloud Strorage")

        credentials: Dict[str, str] = {
            "AccessKey": os.getenv("SA_ACCESS_KEY", "").strip('"'),
            "Secret": os.getenv("SA_SECRET", "").strip('"'),
        }

        logging.debug(credentials["AccessKey"])

        # Create GCS secret with HMAC credentials
        self.conn.execute(f"""
            CREATE SECRET (
                TYPE GCS,
                KEY_ID '{credentials['AccessKey']}',
                SECRET '{credentials['Secret']}'
            );
        """)
        logging.debug("Authenticated to Cloud Storage.")

        logging.debug("Creating local copy of data.")
        self.conn.execute(f"""
            CREATE {collection_type} vegetables AS 
            SELECT * FROM read_parquet('{base_path}/vegetables.parquet');
            
            CREATE {collection_type} fruits AS 
            SELECT * FROM read_parquet('{base_path}/fruits.parquet');
        """)
        sql_path = Path(__file__).parent / "db_views.sql"
        with open(sql_path, "r") as f:
            view_queries = f.read()
            self.conn.execute(view_queries)
        logging.debug("Local copy of data created.")


class BigQueryConnector(DatabaseConnector):
    def __init__(self, project: str, dataset: str):
        self.client = bigquery.Client(project=project)
        self.dataset = dataset

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        job_config = None
        if parameters:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(name, self._get_bq_type(val), val)
                    for name, val in parameters.items()
                ]
            )
        query_job = self.client.query(query, job_config=job_config)
        return list(query_job.result())

    def format_date(self, date_column: str, format_str: str) -> str:
        return f"FORMAT_DATE('{format_str}', {date_column})"

    def concat(self, *args: str) -> str:
        return f"CONCAT({', '.join(args)})"

    def case_when(
        self, condition: str, then_value: str, else_value: str = "NULL"
    ) -> str:
        return f"IF({condition}, {then_value}, {else_value})"

    def escape_column(self, column_name: str) -> str:
        return f"`{column_name}`"

    def cast_date_to_compare(self, date):
        return datetime.strftime(date, "%Y-%m-%d")

    def _get_bq_type(self, value: Any) -> str:
        type_map = {
            str: "STRING",
            int: "INT64",
            float: "FLOAT64",
            datetime: "DATETIME",
            bool: "BOOL",
        }
        return type_map.get(type(value), "STRING")


class DatabaseManager:
    """Handles all database operations"""

    def __init__(self, env: EnvironmentType = "dev", db_config: Optional[dict] = None):
        self.db_config = db_config or AppConfig.get_db_config(env)
        logging.debug(f"Initializing DatabaseManager with environment: {env}")
        logging.debug(f"Database config type: {self.db_config['type']}")
        self.connector = self._create_connector()

    def _create_connector(self) -> DatabaseConnector:
        if self.db_config["type"] == "duckdb":
            return DuckDBConnector(**self.db_config["args"])
        elif self.db_config["type"] == "cloudduckdb":
            return CloudDuckDBConnector(**self.db_config["args"])
        elif self.db_config["type"] == "bigquery":
            return BigQueryConnector(**self.db_config["args"])
        raise ValueError(f"Unsupported database type: {self.db_config['type']}")

    def get_allowed_dates(self, table: str, place: str, origin_type: str) -> List[str]:
        formatted_date = self.connector.format_date("Date", "%Y/%m/%d")
        query = f"""
            SELECT DISTINCT {formatted_date} AS YMD
            FROM {self._get_table_ref(table)}
            WHERE Place = @place
            AND Origin = @origin
            ORDER BY YMD
        """
        results = self.connector.execute_query(
            query, {"place": place, "origin": origin_type}
        )
        return [row[0] for row in results]

    def get_products(self, table: str, origin_type: str, place: str) -> List[str]:
        view_name = f"{table}_year_over_year"
        product_unit = self.connector.concat("Product", "', '", "Unit")
        query = f"""
            SELECT DISTINCT {product_unit} AS ProductUnit
            FROM {self._get_table_ref(view_name)}
            WHERE Origin = @origin AND Place = @place
            ORDER BY ProductUnit
        """
        results = self.connector.execute_query(
            query, {"origin": origin_type, "place": place}
        )
        return [row[0] for row in results]

    def get_markets(self, table: str) -> List[str]:
        query = f"""
            SELECT Place
            FROM (
                SELECT Place, COUNT(*) as freq
                FROM {self._get_table_ref(table)}
                WHERE Place IS NOT NULL
                GROUP BY Place
                ORDER BY freq DESC
            ) sub
        """
        results = self.connector.execute_query(query)
        return [row[0] for row in results]

    def get_prices_data(
        self, table: str, place: str, date: str, origin_type: str
    ) -> List[Dict[str, Any]]:
        view_name = f"{table}_year_over_year"
        product_unit = self.connector.concat("Product", "', '", "Unit")
        current_date_col = self.connector.escape_column("current_date")

        min_case = self.connector.case_when("Statistic = 'Min'", "current_price")
        max_case = self.connector.case_when("Statistic = 'Max'", "current_price")
        min_year_ago = self.connector.case_when("Statistic = 'Min'", "year_ago_price")
        max_year_ago = self.connector.case_when("Statistic = 'Max'", "year_ago_price")

        query = f"""
            SELECT 
                {product_unit} as product,
                MIN({min_case}) as price_min,
                MAX({max_case}) as price_max,
                MIN({min_year_ago}) as year_ago_min,
                MAX({max_year_ago}) as year_ago_max
            FROM {self._get_table_ref(view_name)}
            WHERE Place = @place
            AND {current_date_col} = @date
            AND Origin = @origin
            GROUP BY Product, Unit
            ORDER BY product
        """

        params = {
            "place": place,
            "date": date,
            "origin": origin_type,
        }
        logging.debug(f"Executing get_prices_data with params: {params}")
        logging.debug(f"Using view: {view_name}")
        logging.debug(f"Full query: {query}")

        results = self.connector.execute_query(
            query,
            params,
        )
        logging.debug(f"Query returned {len(results)} results")

        return [
            {
                "product": row[0],
                "price_min": f"{row[1]:.2f}" if row[1] is not None else "N/A",
                "price_max": f"{row[2]:.2f}" if row[2] is not None else "N/A",
                "year_ago_min": f"{row[3]:.2f}" if row[3] is not None else "N/A",
                "year_ago_max": f"{row[4]:.2f}" if row[4] is not None else "N/A",
            }
            for row in results
        ]

    def _get_table_ref(self, table: str) -> str:
        """Get the appropriate table reference based on database type"""
        if self.db_config["type"] == "bigquery":
            return f"`{self.db_config['dataset']}.{table}`"
        return table

    def get_prices_data_for_product(
        self,
        table: str,
        product_unit: str,
        place: str,
        origin_type: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Tuple[List[Any], ...]:
        view_name = f"{table}_year_over_year"
        product_unit_expr = self.connector.concat("Product", "', '", "Unit")
        current_date_col = self.connector.escape_column("current_date")

        min_case = self.connector.case_when("Statistic = 'Min'", "current_price")
        max_case = self.connector.case_when("Statistic = 'Max'", "current_price")
        min_year_ago = self.connector.case_when("Statistic = 'Min'", "year_ago_price")
        max_year_ago = self.connector.case_when("Statistic = 'Max'", "year_ago_price")

        query = f"""
            SELECT 
                {current_date_col} as Date,
                MIN({min_case}) as price_min,
                MAX({max_case}) as price_max,
                MIN({min_year_ago}) as year_ago_min,
                MAX({max_year_ago}) as year_ago_max
            FROM {self._get_table_ref(view_name)}
            WHERE Place = @place
            AND {product_unit_expr} = @product_unit
            AND Origin = @origin
            AND {current_date_col} BETWEEN @start_date AND @end_date
            GROUP BY Date
            ORDER BY Date
        """
        params = {
            "place": place,
            "product_unit": product_unit,
            "origin": origin_type,
            "start_date": self.connector.cast_date_to_compare(start_date),
            "end_date": self.connector.cast_date_to_compare(end_date),
        }

        logging.debug(f"Executing get_prices_data_for_product with params: {params}")
        logging.debug(f"Using view: {view_name}")
        logging.debug(f"Full query: {query}")

        results = self.connector.execute_query(query, params)

        logging.debug(f"Query returned {len(results)} results")

        return tuple(map(list, zip(*results)))
