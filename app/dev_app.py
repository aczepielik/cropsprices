from dataclasses import dataclass
from typing import Any, Dict, List, Literal

import duckdb
from nicegui import ui

TableType = Literal["fruits", "vegetables"]


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
    ]


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
        query = f"""
            SELECT 
                Product || ', ' || Unit as product,
                MIN(Price) as price_min,
                MAX(Price) as price_max,
            FROM {table}
            WHERE Place = ?
            AND Date = ?
            AND Origin = ?
            GROUP BY Product, Unit, Origin
            ORDER BY Product
        """
        results = self.conn.execute(query, [place, date, origin_type]).fetchall()
        return [
            {
                "product": row[0],
                "price_min": f"{row[1]:.2f}",
                "price_max": f"{row[2]:.2f}",
            }
            for row in results
        ]


class CropsPricesApp:
    def __init__(self):
        self.db = DatabaseManager(".data/local.db")
        self.config = AppConfig()
        self.current_table = "vegetables"
        self.current_origin = "KRAJOWE"

        # Initialize UI colors
        ui.colors(**self.config.COLORS)

        # Setup main layout
        self.setup_layout()

    def setup_header(self):
        with ui.header().classes("bg-primary text-white"):
            ui.label("Ceny hurtowe owoców i warzyw").classes("text-h4 q-px-md q-py-sm")

    def setup_left_drawer(self):
        with ui.left_drawer(fixed=True).classes("w-96 p-4 bg-light shadow-xl"):
            self._setup_table_toggle()
            self._setup_origin_toggle()
            self._setup_place_select()
            self._setup_date_picker()

    def _setup_table_toggle(self):
        def on_toggle_change(e):
            self.current_table = e.value
            self._refresh_ui_components()

        ui.toggle(
            {"vegetables": "Warzywa", "fruits": "Owoce"},
            value="vegetables",
            on_change=on_toggle_change,
        ).classes("text-h7 w-full").props('toggle-color="secondary" spread no-caps')

    def _setup_origin_toggle(self):
        def on_origin_toggle_change(e):
            self.current_origin = e.value
            self._refresh_ui_components()

        ui.toggle(
            {
                "KRAJOWE": "Krajowe",
                "IMPORTOWANE": "Importowane",
            },  # Changed to match database values
            value="KRAJOWE",
            on_change=on_origin_toggle_change,
        ).classes("text-h7 w-full q-mt-sm").props(
            'toggle-color="secondary" spread no-caps'
        )

    def _setup_place_select(self):
        def on_place_change(e):
            self._refresh_ui_components()

        self.place = ui.select(
            options=self.db.get_markets(self.current_table),
            label="Giełda",
            value="Bronisze",
            on_change=on_place_change,
        ).classes("w-full q-py-sm")

    def _setup_date_picker(self):
        def on_date_change(date_value):
            self.update_prices_table()

        self.date_filter = self.db.get_allowed_dates(
            self.current_table, self.place.value, self.current_origin
        )
        self.date = (
            ui.date(value="2023-06-05")
            .classes("w-80")
            .props(
                f'color="secondary" default-year-month=2023/06 :options="{self.date_filter}"'
            )
            .style("min-width: 240px !important")
            .on("update:model-value", on_date_change)
        )

    def setup_main_content(self):
        with ui.row().classes("flex-grow p-4 gap-10 w-full"):
            self._setup_prices_table()
            self._setup_product_selection()

    def _setup_prices_table(self):
        with ui.column().classes("flex-1"):
            self.prices_table = ui.table(
                columns=self.config.TABLE_COLUMNS,
                rows=self.get_prices_data(),
            ).classes("w-full")

    def _setup_product_selection(self):
        with ui.column().classes("flex-1"):
            self.product = ui.select(
                options=self.db.get_products(self.current_table, self.current_origin),
                label="Produkt",
            ).classes("w-full")

    def setup_layout(self):
        self.setup_header()
        self.setup_left_drawer()
        self.setup_main_content()

    def _refresh_ui_components(self):
        """Update all UI components that depend on current selection"""
        self.product.options = self.db.get_products(
            self.current_table, self.current_origin
        )
        self.product.update()

        self.date_filter = self.db.get_allowed_dates(
            self.current_table, self.place.value, self.current_origin
        )
        self.date.props(f':options="{self.date_filter}"')
        self.date.update()

        self.update_prices_table()

    def get_prices_data(self) -> List[Dict[str, Any]]:
        date_str = self.date.value.replace("/", "-")
        return self.db.get_prices_data(
            self.current_table, self.place.value, date_str, self.current_origin
        )

    def update_prices_table(self):
        self.prices_table.rows = self.get_prices_data()
        self.prices_table.update()


def main():
    app = CropsPricesApp()  # noqa: F841
    ui.run(title="Ceny hurtowe owoców i warzyw", port=8080, language="pl")


if __name__ in {"__main__", "__mp_main__"}:
    main()
