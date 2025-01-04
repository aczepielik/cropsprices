import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from nicegui import app as ngapp
from nicegui import ui

from app.config import AppConfig, EnvironmentType
from app.database import DatabaseManager
from app.logs import log_ui_interaction, setup_logger
from app.ui_components import UIComponents


class ClientState:
    """Class to hold client-specific state"""

    def __init__(self):
        # UI Components
        self.drawer: ui.drawer
        self.table_toggle: ui.toggle
        self.origin_toggle: ui.toggle
        self.place: ui.select
        self.date: ui.date
        self.prices_table: ui.table
        self.product: ui.select
        self.chart_container: ui.matplotlib
        self.date_filter: List[str]

        # App State
        self.current_table: str = "vegetables"
        self.current_origin: str = "KRAJOWE"
        self.selected_product: str = ""


class CropsPricesApp:
    """Main application class handling the wholesale prices dashboard"""

    def __init__(self, env: EnvironmentType = "dev"):
        """Initialize the application with database, config, and UI components"""
        self.env = env
        self.config = AppConfig()
        db_config = self.config.get_db_config(env)
        self.db = DatabaseManager(env=env, db_config=db_config)

        self.ui = UIComponents()

        @ui.page("/")
        def landing_page():
            # Initialize client state if needed
            if "state" not in ngapp.storage.client:
                ngapp.storage.client["state"] = ClientState()

            ui.colors(**self.config.COLORS)
            plt.style.use(["app/material_design2.mplstyle", "fast"])

            ngapp.storage.client["app_state"] = {
                "current_table": "vegetables",
                "current_origin": "KRAJOWE",
                "selected_product": "",
            }

            self._init_ui()

    def _get_state(self) -> ClientState:
        """Get the current client's state"""
        return ngapp.storage.client["state"]

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
        state = self._get_state()
        # Store the drawer reference
        state.drawer = self.ui.create_left_drawer()

        with state.drawer:
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
        state = self._get_state()
        if state.drawer:
            state.drawer.toggle()

    def _setup_table_toggle(self) -> None:
        """Setup toggle for switching between vegetables and fruits"""
        state = self._get_state()
        state.table_toggle = self.ui.create_table_toggle(
            on_change=self._on_table_toggle,
            initial_value=state.current_table,
        )

    def _setup_origin_toggle(self) -> None:
        """Setup toggle for switching between domestic and imported products"""
        state = self._get_state()
        state.origin_toggle = self.ui.create_origin_toggle(
            on_change=self._on_origin_toggle,
            initial_value=state.current_origin,
        )

    def _setup_place_select(self) -> None:
        """Setup market place selection dropdown"""
        state = self._get_state()
        state.place = self.ui.create_place_select(
            options=self.db.get_markets(state.current_table),
            on_change=self._on_place_change,
        )

    def _setup_date_picker(self) -> None:
        """Setup date picker with available dates"""
        state = self._get_state()
        if state.place:
            state.date_filter = self.db.get_allowed_dates(
                state.current_table,
                state.place.value,
                state.current_origin,
            )
            state.date = self.ui.create_date_picker(
                on_change=self._on_date_change, date_filter=state.date_filter
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
                state = self._get_state()
                state.chart_container = ui.matplotlib(figsize=(6, 5)).classes(
                    "w-full mt-4 nicegui-pyplot"
                )

    def _setup_prices_table(self) -> None:
        """Setup prices comparison table"""
        state = self._get_state()
        state.prices_table = self.ui.create_prices_table(
            columns=self.config.TABLE_COLUMNS,
            rows=self.get_prices_data(),
            on_select=self._handle_row_selection,
        )

    def _setup_product_selection(self) -> None:
        """Setup product selection dropdown and label"""
        state = self._get_state()
        if state.place:
            state.product = self.ui.create_product_select(
                options=self.db.get_products(
                    state.current_table,
                    state.current_origin,
                    state.place.value,
                ),
                on_change=self._handle_product_selection,
            )

    @log_ui_interaction
    def _handle_product_selection(self, event: Any) -> None:
        """Handle product selection from dropdown"""
        state = self._get_state()
        if event.value:
            state.selected_product = event.value
            # Clear table selection
            if state.prices_table:
                state.prices_table.selected = []
                state.prices_table.update()
            self.update_chart()

    @log_ui_interaction
    def _handle_row_selection(self, event: Any) -> None:
        """Handle row selection in prices table"""
        state = self._get_state()
        if event.selection:
            selected_row = event.selection[0]
            state.selected_product = selected_row["product"]
            self.update_chart()

    @log_ui_interaction
    def _on_table_toggle(self, event: Any) -> None:
        """Handle table type toggle change"""
        state = self._get_state()
        state.current_table = event.value
        self._refresh_ui_components()

    @log_ui_interaction
    def _on_origin_toggle(self, event: Any) -> None:
        """Handle origin toggle change"""
        state = self._get_state()
        state.current_origin = event.value
        self._refresh_ui_components()

    @log_ui_interaction
    def _on_place_change(self, event: Any) -> None:
        """Handle market place selection change"""
        self._refresh_ui_components()

    @log_ui_interaction
    def _on_date_change(self, date_value: str) -> None:
        """Handle date selection change"""
        self.update_prices_table()

    @log_ui_interaction
    def _refresh_ui_components(self) -> None:
        """Update all UI components that depend on current selection"""
        state = self._get_state()

        if state.product and state.place:
            state.product.options = self.db.get_products(
                state.current_table,
                state.current_origin,
                state.place.value,
            )
            state.product.update()

        if state.place:
            state.date_filter = self.db.get_allowed_dates(
                state.current_table,
                state.place.value,
                state.current_origin,
            )
            if state.date:
                state.date.props(f':options="{state.date_filter}"')
                state.date.update()

        self.update_prices_table()

    def get_prices_data(self) -> List[Dict[str, Any]]:
        """Get prices data from database"""
        state = self._get_state()
        if state.date and state.place:
            date_str = state.date.value.replace("/", "-")
            return self.db.get_prices_data(
                state.current_table,
                state.place.value,
                date_str,
                state.current_origin,
            )
        return []

    def get_chart_data(self) -> Tuple[List[Any], ...]:
        state = self._get_state()
        if state.date and state.place:
            date_str = state.date.value.replace("/", "-")
            start_date = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(weeks=50)
            end_date = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(weeks=2)
            data = self.db.get_prices_data_for_product(
                table=state.current_table,
                product_unit=state.selected_product,
                place=state.place.value,
                origin_type=state.current_origin,
                start_date=start_date,
                end_date=end_date,
            )
            return data if data else tuple([] for _ in range(5))
        return tuple([] for _ in range(5))

    @log_ui_interaction
    def update_prices_table(self) -> None:
        """Update prices table with new data"""
        state = self._get_state()
        if state.prices_table:
            state.prices_table.rows = self.get_prices_data()
            state.prices_table.update()

    @log_ui_interaction
    def update_chart(self) -> None:
        state = self._get_state()
        if state.chart_container and state.place:
            with state.chart_container.figure as fig:
                fig.clear()
                self.ui.create_prices_chart(
                    fig=fig,
                    data=self.get_chart_data(),
                    title=" | ".join(
                        (
                            state.selected_product,
                            state.current_origin.title(),
                            state.place.value,
                        )
                    ),
                )


def main() -> None:
    """Application entry point"""
    # Get environment from ENV variable, default to 'dev'
    env = os.getenv("APP_ENV", "dev")
    if env not in ("dev", "staging", "prod"):
        raise ValueError(f"Invalid environment: {env}")

    # Setup logging before initializing the app
    setup_logger(env)

    try:
        app = CropsPricesApp(env=env)  # type: ignore # noqa: F841
        port = int(os.getenv("PORT", "8080"))

        ui.run(
            title="Ceny hurtowe owoców i warzyw",
            port=port,
            host="0.0.0.0",  # Required for Cloud Run
            language="pl",
            reload=bool(os.getenv("RELOAD", "")),
        )
    except Exception as e:
        logging.error(f"Application failed to start: {str(e)}", exc_info=True)
        raise


if __name__ in {"__main__", "__mp_main__"}:
    main()
