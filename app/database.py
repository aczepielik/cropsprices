from datetime import datetime
from typing import Any, Dict, List, Tuple

import duckdb


class DatabaseManager:
    """Handles all database operations"""

    def __init__(self, db_path: str):
        self.conn = duckdb.connect(db_path, read_only=True)

    def get_allowed_dates(self, table: str, place: str, origin_type: str) -> List[str]:
        query = f"""
            SELECT DISTINCT strftime(Date, '%Y/%m/%d')
            FROM {table}
            WHERE Place = ?
            AND Origin = ?
            ORDER BY DATE
        """
        return [
            row[0] for row in self.conn.execute(query, [place, origin_type]).fetchall()
        ]

    def get_products(self, table: str, origin_type: str) -> List[str]:
        query = f"""
        SELECT DISTINCT Product || ' ' || Unit
        FROM {table}
        WHERE Origin = ?
        ORDER BY Product
        """
        return [row[0] for row in self.conn.execute(query, [origin_type]).fetchall()]

    def get_markets(self, table: str) -> List[str]:
        query = f"""
            SELECT Place
            FROM (
                SELECT Place, count(*) as freq
                FROM {table}
                WHERE Place IS NOT NULL
                GROUP BY Place
                ORDER BY freq DESC
            ) as sub
        """
        return [row[0] for row in self.conn.execute(query).fetchall()]

    def get_prices_data(
        self, table: str, place: str, date: str, origin_type: str
    ) -> List[Dict[str, Any]]:
        view_name = f"{table}_year_over_year"
        query = f"""
            SELECT 
                Product || ', ' || Unit as product,
                MIN(CASE WHEN Statistic = 'Min' THEN current_price END) as price_min,
                MAX(CASE WHEN Statistic = 'Max' THEN current_price END) as price_max,
                MIN(CASE WHEN Statistic = 'Min' THEN year_ago_price END) as year_ago_min,
                MAX(CASE WHEN Statistic = 'Max' THEN year_ago_price END) as year_ago_max
            FROM {view_name}
            WHERE Place = ?
            AND current_date = ?
            AND Origin = ?
            GROUP BY Product, Unit
            ORDER BY Product
        """
        results = self.conn.execute(query, [place, date, origin_type]).fetchall()
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
        query = f"""
            SELECT 
                current_date as Date,
                MIN(CASE WHEN Statistic = 'Min' THEN current_price END) as price_min,
                MAX(CASE WHEN Statistic = 'Max' THEN current_price END) as price_max,
                MIN(CASE WHEN Statistic = 'Min' THEN year_ago_price END) as year_ago_min,
                MAX(CASE WHEN Statistic = 'Max' THEN year_ago_price END) as year_ago_max
            FROM {view_name}
            WHERE Place = ?
            AND Product || ', ' || Unit = ?
            AND Origin = ?
            AND current_date BETWEEN ? AND ?
            GROUP BY Date
            ORDER BY Date
        """
        results = self.conn.execute(
            query, [place, product_unit, origin_type, start_date, end_date]
        ).fetchall()
        return tuple(map(list, zip(*results)))
