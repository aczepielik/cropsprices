from datetime import datetime
from typing import List, Literal

import duckdb
import plotly.express as px  # type: ignore
import plotly.graph_objects as go  # type: ignore
from nicegui import ui

TableType = Literal["fruits", "vegetables"]


class CropsPricesApp:
    def __init__(self):
        self.conn = duckdb.connect(".data/local.db", read_only=True)
        self.current_table: TableType = "vegetables"
        self.setup_layout()

    def setup_layout(self):
        # Header
        with ui.header().classes("bg-primary text-white"):
            ui.label("Crops Prices Dashboard").classes("text-h4 q-px-md q-py-sm")

        # Main content
        with ui.row():
            # Filters sidebar
            with ui.column().classes("w-64 p-4 bg-gray-100"):
                ui.label("Filters").classes("text-h6")

                # Table type selector
                self.table_type = ui.select(
                    options=["vegetables", "fruits"],
                    value="vegetables",
                    label="Product Category",
                ).on("change", self.update_table_type)

                # Date pickers
                self.start_date = ui.date(value=datetime.now().date())
                self.end_date = ui.date(value=datetime.now().date())

                # Product dropdown
                self.product = ui.select(options=self.get_products(), label="Product")

                # Place dropdown
                self.place = ui.select(options=self.get_places(), label="Place")

                # Origin dropdown
                self.origin = ui.select(options=self.get_origins(), label="Origin")

                ui.button("Update Chart", on_click=self.update_chart).classes("mt-4")

            # Main chart area
            with ui.column().classes("flex-grow p-4"):
                # Create empty figure
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    title="Select filters and click 'Update Chart' to view data",
                    xaxis_title="Date",
                    yaxis_title="Price (PLN)",
                )
                self.chart_container = ui.plotly(empty_fig).classes("w-full h-full")

    def update_table_type(self):
        self.current_table = self.table_type.value
        # Update all dropdowns when table type changes
        self.product.options = self.get_products()
        self.place.options = self.get_places()
        self.origin.options = self.get_origins()

    def get_products(self) -> List[str]:
        query = f"SELECT DISTINCT Product FROM {self.current_table} ORDER BY Product"
        return [row[0] for row in self.conn.execute(query).fetchall()]

    def get_places(self) -> List[str]:
        query = f"SELECT DISTINCT Place FROM {self.current_table} ORDER BY Place"
        return [row[0] for row in self.conn.execute(query).fetchall()]

    def get_origins(self) -> List[str]:
        query = f"SELECT DISTINCT Origin FROM {self.current_table} WHERE Origin IS NOT NULL ORDER BY Origin"
        return [row[0] for row in self.conn.execute(query).fetchall()]

    def update_chart(self):
        query = f"""
        SELECT 
            Date,
            Statistic,
            Price
        FROM {self.current_table}
        WHERE 
            Date BETWEEN ? AND ?
            AND Product = ?
            AND Place = ?
            AND Origin = ?
        ORDER BY Date
        """

        df = self.conn.execute(
            query,
            [
                self.start_date.value,
                self.end_date.value,
                self.product.value,
                self.place.value,
                self.origin.value,
            ],
        ).df()

        # Pivot the data to get Min/Max/Avg prices
        df_pivot = df.pivot(index="Date", columns="Statistic", values="Price")

        fig = px.line(
            df_pivot,
            title=f"Price Trends: {self.product.value} in {self.place.value} ({self.origin.value})",
            labels={"Date": "Date", "value": "Price (PLN)", "variable": "Statistic"},
        )

        # Add unit information to the title
        unit_query = f"""
        SELECT DISTINCT Unit 
        FROM {self.current_table} 
        WHERE Product = ?
        LIMIT 1
        """
        unit = self.conn.execute(unit_query, [self.product.value]).fetchone()[0]
        fig.update_layout(
            title=f"Price Trends: {self.product.value} ({unit}) in {self.place.value} ({self.origin.value})"
        )

        # Update the existing chart
        self.chart_container.update_figure(fig)


def main():
    app = CropsPricesApp()  # noqa: F841
    ui.run(title="Crops Prices Dashboard", port=8080)


if __name__ in {"__main__", "__mp_main__"}:
    main()
