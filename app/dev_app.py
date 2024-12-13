from typing import List, Literal

import duckdb
from nicegui import ui

TableType = Literal["fruits", "vegetables"]


class CropsPricesApp:
    def __init__(self):
        self.conn = duckdb.connect(".data/local.db", read_only=True)
        # setup colors
        ui.colors(
            primary="#606c38",
            secondary="#dda15e",
            accent="#bc6c25",
            positive="#4caf50",
            negative="#b71c1c",
            info="#29b6f6",
            warning="#f9a825",
            light="fffae0",
        )
        self.current_table = "vegetables"
        self.setup_layout()

    def setup_layout(self):
        # Header
        with ui.header().classes("bg-primary text-white"):
            ui.label("Ceny hurtowe owoców i warzyw").classes("text-h4 q-px-md q-py-sm")

        with ui.left_drawer(fixed=True).classes("w-96 p-4 bg-light shadow-xl"):

            def on_toggle_change(e):
                self.current_table = e.value

                # update products list
                products = self.get_products()
                self.product.options = products
                self.product.update()

                # update allowable dates
                self.date_filter = self.get_allowed_dates()
                self.date.props(f':options="{self.date_filter}"')
                self.date.update()

                # update prices table
                self.update_prices_table()

            # Fruits or vegetables toggle
            (
                ui.toggle(
                    {"vegetables": "Warzywa", "fruits": "Owoce"},
                    value="vegetables",
                    on_change=on_toggle_change,
                )
                .classes("text-h7 w-full")
                .props('toggle-color="secondary" spread no-caps')
            )

            # place select
            def on_place_change(e):
                # Update allowed dates when place changes
                self.date_filter = self.get_allowed_dates()
                self.date.props(f':options="{self.date_filter}"')
                self.date.update()

                self.update_prices_table()

            self.place = ui.select(
                options=self.get_markets(),
                label="Giełda",
                value="Bronisze",
                on_change=on_place_change,
            ).classes("w-full q-py-sm")

            self.date_filter = self.get_allowed_dates()

            def on_date_change(date_value):
                self.update_prices_table()

            self.date = (
                ui.date(value="2023-06-05")
                .classes("w-80")
                .props(
                    f'color="secondary" default-year-month=2023/06 :options="{self.date_filter}"'
                )
                .style("min-width: 240px !important")
                .on("update:model-value", on_date_change)
            )

        with ui.row().classes("flex-grow p-4 gap-10 w-full"):
            # Left column
            with ui.column().classes("flex-1"):
                ui.label("Ceny produktów").classes("text-h6")

                self.prices_table = ui.table(
                    columns=[
                        {"name": "product", "label": "Produkt", "field": "product"},
                        {
                            "name": "price_min",
                            "label": "Cena min",
                            "field": "price_min",
                        },
                        {
                            "name": "price_max",
                            "label": "Cena max",
                            "field": "price_max",
                        },
                        {
                            "name": "price_avg",
                            "label": "Cena średnia",
                            "field": "price_avg",
                        },
                    ],
                    rows=self.get_prices_data(),
                ).classes("w-full")

            # Right column
            with ui.column().classes("flex-1"):
                ui.label("Right Column Content").classes("text-h6")
                self.product = ui.select(
                    options=self.get_products(), label="Produkt"
                ).classes("w-full")

    def get_allowed_dates(self) -> List[str]:
        query = f"""
            SELECT DISTINCT strftime(Date, '%Y/%m/%d')
            FROM {self.current_table}
            WHERE Place = '{self.place.value}'
            ORDER BY DATE
        """
        return [row[0] for row in self.conn.execute(query).fetchall()]
        # return ["2023/01/10", "2023/01/12", "2023/01/15", "2023/01/18"]

    def get_products(self) -> List[str]:
        query = f"""
        SELECT DISTINCT Product || ' ' || Unit || ' (' || Origin || ')'
        FROM {self.current_table}
        ORDER BY Product
        """
        return [row[0] for row in self.conn.execute(query).fetchall()]

    def get_markets(self) -> List[str]:
        if self.current_table not in ["fruits", "vegetables"]:
            self.current_table = "vegetables"

        query = f"""
            SELECT Place
            FROM (
                SELECT Place, count(*) as freq
                FROM {self.current_table}
                WHERE Place IS NOT NULL
                GROUP BY Place
                ORDER BY freq DESC
            ) as sub
        """
        return [row[0] for row in self.conn.execute(query).fetchall()]

    def get_prices_data(self) -> List[dict]:
        date_str = self.date.value.replace(
            "/", "-"
        )  # Convert date format for SQL query
        query = f"""
            SELECT 
                Product || ' ' || Unit || ' (' || Origin || ')' as product,
                MIN(Price) as price_min,
                MAX(Price) as price_max,
                AVG(Price) as price_avg
            FROM {self.current_table}
            WHERE Place = '{self.place.value}'
            AND Date = '{date_str}'
            GROUP BY Product, Unit, Origin
            ORDER BY Product
        """
        results = self.conn.execute(query).fetchall()
        return [
            {
                "product": row[0],
                "price_min": f"{row[1]:.2f}",
                "price_max": f"{row[2]:.2f}",
                "price_avg": f"{row[3]:.2f}",
            }
            for row in results
        ]

    def update_prices_table(self):
        self.prices_table.rows = self.get_prices_data()
        self.prices_table.update()


def main():
    app = CropsPricesApp()  # noqa: F841
    ui.run(title="Ceny hurtowe owoców i warzyw", port=8080, language="pl")


if __name__ in {"__main__", "__mp_main__"}:
    main()
