from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from nicegui import ui

from app.config import AppConfig
from app.database import DatabaseManager
from app.ui_components import UIComponents


class CropsPricesApp:
    """Main application class handling the wholesale prices dashboard"""

    def __init__(self):
        """Initialize the application with database, config, and UI components"""
        self.db = DatabaseManager(".data/local.db")
        self.config = AppConfig()
        self.state = {
            "current_table": "vegetables",
            "current_origin": "KRAJOWE",
            "selected_product": None,
        }
        self.ui = UIComponents()

        # Initialize UI components references
        self.drawer = None
        self.table_toggle = None
        self.origin_toggle = None
        self.place = None
        self.date = None
        self.prices_table = None
        self.product = None
        self.chart_container = None
        self.date_filter = None

        # Initialize UI
        ui.colors(**self.config.COLORS)
        self._init_ui()
        plt.style.use(["app/material_design2.mplstyle", "fast"])

    def _init_ui(self) -> None:
        """Initialize all UI components"""
        self._setup_layout()

    def _setup_layout(self) -> None:
        """Setup main application layout"""
        self._setup_header()
        self._setup_left_drawer()
        self._setup_main_content()

    def _setup_header(self) -> None:
        """Setup application header"""
        with ui.header().classes("bg-primary text-white flex flex-row items-center"):
            with ui.row().classes("w-full items-center justify-start q-px-sm no-wrap"):
                ui.button(icon="menu", on_click=self._toggle_drawer).classes(
                    "sm:block lg:hidden text-h6 w-16 h-16 flex items-center justify-center"
                )
                ui.label("Ceny hurtowe owoców i warzyw").classes(
                    "text-h4 q-px-md q-py-sm"
                )

    def _setup_left_drawer(self) -> None:
        """Setup left drawer with filters and controls"""
        # Store the drawer reference
        self.drawer = self.ui.create_left_drawer()

        with self.drawer:
            # Add responsive classes
            ui.query(".left-drawer").classes(
                replace="w-96 p-4 bg-light shadow-xl "
                + "md:w-96 sm:w-full xs:w-full "  # Responsive widths
                + "md:static sm:fixed xs:fixed "  # Position handling
                + "md:transform-none "  # Prevent transform on medium screens
                + "sm:translate-x-0 xs:translate-x-[-100%]"  # Slide handling for mobile
            )

            self._setup_table_toggle()
            self._setup_origin_toggle()
            self._setup_place_select()
            self._setup_date_picker()

    def _toggle_drawer(self) -> None:
        """Toggle the drawer open/closed state"""
        self.drawer.toggle()

    def _setup_table_toggle(self) -> None:
        """Setup toggle for switching between vegetables and fruits"""
        self.table_toggle = self.ui.create_table_toggle(
            on_change=self._on_table_toggle, initial_value=self.state["current_table"]
        )

    def _setup_origin_toggle(self) -> None:
        """Setup toggle for switching between domestic and imported products"""
        self.origin_toggle = self.ui.create_origin_toggle(
            on_change=self._on_origin_toggle, initial_value=self.state["current_origin"]
        )

    def _setup_place_select(self) -> None:
        """Setup market place selection dropdown"""
        self.place = self.ui.create_place_select(
            options=self.db.get_markets(self.state["current_table"]),
            on_change=self._on_place_change,
        )

    def _setup_date_picker(self) -> None:
        """Setup date picker with available dates"""
        self.date_filter = self.db.get_allowed_dates(
            self.state["current_table"], self.place.value, self.state["current_origin"]
        )
        self.date = self.ui.create_date_picker(
            on_change=self._on_date_change, date_filter=self.date_filter
        )

    def _setup_main_content(self) -> None:
        """Setup main content area with prices table and product selection"""
        with ui.grid().classes(
            """
            w-full gap-4 pl-0 pr-4 pt-4 pb-4
            xl:grid-cols-2 grid-cols-1
            xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]
            """
        ):
            # Left column - prices table
            with ui.column().classes("w-full min-w-0"):
                self._setup_prices_table()

            # Right column - product selection and chart
            chart_column = ui.column().classes("w-full min-w-0 overflow-hidden")
            with chart_column:
                self._setup_product_selection()
                self.chart_container = ui.matplotlib(figsize=(6, 5)).classes(
                    "w-full mt-4 nicegui-pyplot"
                )

    def _setup_prices_table(self) -> None:
        """Setup prices comparison table"""
        self.prices_table = self.ui.create_prices_table(
            columns=self.config.TABLE_COLUMNS,
            rows=self.get_prices_data(),
            on_select=self._handle_row_selection,
        )

    def _setup_product_selection(self) -> None:
        """Setup product selection dropdown and label"""
        self.product = self.ui.create_product_select(
            options=self.db.get_products(
                self.state["current_table"], self.state["current_origin"]
            ),
            on_change=self._handle_product_selection,
        )

    def _handle_product_selection(self, event: Any) -> None:
        """Handle product selection from dropdown"""
        if event.value:
            self.state["selected_product"] = event.value
            # Clear table selection
            self.prices_table.selected = []
            self.prices_table.update()
            self.update_chart()

    def _handle_row_selection(self, event: Any) -> None:
        """Handle row selection in prices table"""
        if event.selection:
            selected_row = event.selection[0]
            self.state["selected_product"] = selected_row["product"]
            self.update_chart()

    def _on_table_toggle(self, event: Any) -> None:
        """Handle table type toggle change"""
        self.state["current_table"] = event.value
        self._refresh_ui_components()

    def _on_origin_toggle(self, event: Any) -> None:
        """Handle origin toggle change"""
        self.state["current_origin"] = event.value
        self._refresh_ui_components()

    def _on_place_change(self, event: Any) -> None:
        """Handle market place selection change"""
        self._refresh_ui_components()

    def _on_date_change(self, date_value: str) -> None:
        """Handle date selection change"""
        self.update_prices_table()

    def _refresh_ui_components(self) -> None:
        """Update all UI components that depend on current selection"""
        self.product.options = self.db.get_products(
            self.state["current_table"], self.state["current_origin"]
        )
        self.product.update()

        self.date_filter = self.db.get_allowed_dates(
            self.state["current_table"], self.place.value, self.state["current_origin"]
        )
        self.date.props(f':options="{self.date_filter}"')
        self.date.update()

        self.update_prices_table()

    def get_prices_data(self) -> List[Dict[str, Any]]:
        """Get prices data from database"""
        date_str = self.date.value.replace("/", "-")
        return self.db.get_prices_data(
            self.state["current_table"],
            self.place.value,
            date_str,
            self.state["current_origin"],
        )

    def get_chart_data(self) -> Tuple[List[Any], ...]:
        date_str = self.date.value.replace("/", "-")
        start_date = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(weeks=50)
        end_date = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(weeks=2)
        data = self.db.get_prices_data_for_product(
            table=self.state["current_table"],
            product_unit=self.state["selected_product"],
            place=self.place.value,
            origin_type=self.state["current_origin"],
            start_date=start_date,
            end_date=end_date,
        )

        return data if data else tuple([] for _ in range(5))

    def update_prices_table(self) -> None:
        """Update prices table with new data"""
        self.prices_table.rows = self.get_prices_data()
        self.prices_table.update()

    def update_chart(self) -> None:
        with self.chart_container.figure as fig:
            fig.clear()
            self.ui.create_prices_chart(
                fig=fig,
                data=self.get_chart_data(),
                title=" | ".join((self.state["selected_product"], self.place.value)),
            )


def main() -> None:
    """Application entry point"""
    app = CropsPricesApp()  # noqa: F841
    ui.run(
        title="Ceny hurtowe owoców i warzyw",
        port=8080,
        language="pl",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
