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
        {"name": "year_ago_min", "label": "Rok temu min", "field": "year_ago_min"},
        {"name": "year_ago_max", "label": "Rok temu max", "field": "year_ago_max"},
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
            with ui.column().classes("flex-1 w-1/2 pr-2"):
                self._setup_prices_table()
            with ui.column().classes("flex-1 w-1/2 pr-2"):
                self._setup_product_selection()

    def _setup_prices_table(self):
        self.prices_table = (
            ui.table(
                columns=self.config.TABLE_COLUMNS,
                rows=self.get_prices_data(),
                pagination=10,
                selection="single",  # Enable single row selection
                row_key="product",  # Specify which field to use as the unique identifier
                on_select=self.handle_row_selection,
            )
            .props("virtual-scroll")
            .classes("w-full")
        )

        # Add slots for year-ago price columns with conditional formatting
        self.prices_table.add_slot(
            "body-cell-year_ago_min",
            """
            <q-td key="year_ago_min" :props="props">
                <span :style="{
                    color: props.row.price_min !== 'N/A' && props.value !== 'N/A' ? 
                        (parseFloat(props.row.price_min) < parseFloat(props.value) * 0.95 ? '#4caf50' :
                         parseFloat(props.row.price_min) > parseFloat(props.value) * 1.05 ? '#b71c1c' : 'black')
                        : 'black'
                }">
                    {{ props.value }}
                </span>
            </q-td>
        """,
        )

        self.prices_table.add_slot(
            "body-cell-year_ago_max",
            """
            <q-td key="year_ago_max" :props="props">
                <span :style="{
                    color: props.row.price_max !== 'N/A' && props.value !== 'N/A' ? 
                        (parseFloat(props.row.price_max) < parseFloat(props.value) * 0.95 ? '#4caf50' :
                         parseFloat(props.row.price_max) > parseFloat(props.value) * 1.05 ? '#b71c1c' : 'black')
                        : 'black'
                }">
                    {{ props.value }}
                </span>
            </q-td>
        """,
        )

    def _setup_product_selection(self):
        self.product = ui.select(
            options=self.db.get_products(self.current_table, self.current_origin),
            label="Produkt",
            on_change=self.handle_product_selection,  # Add on_change handler
        ).classes("w-full")

        # Add label to show selected product
        self.selected_product_label = ui.label("").classes("text-h6 q-mt-md")

    def handle_product_selection(self, event):
        """Handle product selection from dropdown"""
        if event.value:
            self.selected_product_label.text = f"Wybrany produkt: {event.value}"
            # Clear table selection
            self.prices_table.selected = []
            self.prices_table.update()
        else:
            self.selected_product_label.text = ""
        self.selected_product_label.update()

    def handle_row_selection(self, event):
        """Handle row selection in prices table"""
        if event.selection:
            selected_row = event.selection[0]  # Get first (and only) selected row
            self.selected_product_label.text = (
                f'Wybrany produkt: {selected_row["product"]}'
            )
        else:
            self.selected_product_label.text = ""
        self.selected_product_label.update()

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
        results = self.db.get_prices_data(
            self.current_table, self.place.value, date_str, self.current_origin
        )
        return results

    def update_prices_table(self):
        self.prices_table.rows = self.get_prices_data()
        self.prices_table.update()


def main():
    app = CropsPricesApp()  # noqa: F841
    ui.run(title="Ceny hurtowe owoców i warzyw", port=8080, language="pl")


if __name__ in {"__main__", "__mp_main__"}:
    main()
