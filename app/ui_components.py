from typing import Callable, Dict, List

from nicegui import ui


class UIComponents:
    """Handles creation and setup of UI components"""

    @staticmethod
    def create_table_toggle(
        on_change: Callable, initial_value: str = "vegetables"
    ) -> ui.toggle:
        """Create toggle switch for table selection (vegetables/fruits)"""
        return (
            ui.toggle(
                {"vegetables": "Warzywa", "fruits": "Owoce"},
                value=initial_value,
                on_change=on_change,
            )
            .classes("text-h7 w-full")
            .props('toggle-color="secondary" spread no-caps')
        )

    @staticmethod
    def create_origin_toggle(
        on_change: Callable, initial_value: str = "KRAJOWE"
    ) -> ui.toggle:
        """Create toggle switch for origin selection (domestic/imported)"""
        return (
            ui.toggle(
                {
                    "KRAJOWE": "Krajowe",
                    "IMPORTOWANE": "Importowane",
                },
                value=initial_value,
                on_change=on_change,
            )
            .classes("text-h7 w-full q-mt-sm")
            .props('toggle-color="secondary" spread no-caps')
        )

    @staticmethod
    def create_place_select(
        options: List[str], on_change: Callable, initial_value: str = "Bronisze"
    ) -> ui.select:
        """Create market place selection dropdown"""
        return ui.select(
            options=options,
            label="Giełda",
            value=initial_value,
            on_change=on_change,
        ).classes("w-full q-py-sm")

    @staticmethod
    def create_date_picker(
        on_change: Callable, date_filter: List[str], initial_value: str = "2023-06-05"
    ) -> ui.date:
        """Create date picker with filtered dates"""
        return (
            ui.date(value=initial_value)
            .classes("w-80")
            .props(
                f'color="secondary" default-year-month=2023/06 :options="{date_filter}"'
            )
            .style("min-width: 240px !important")
            .on("update:model-value", on_change)
        )

    @staticmethod
    def create_prices_table(
        columns: List[Dict], rows: List[Dict], on_select: Callable
    ) -> ui.table:
        """Create prices table with comparison indicators"""
        table = (
            ui.table(
                columns=columns,
                rows=rows,
                pagination=10,
                selection="single",
                row_key="product",
                on_select=on_select,
            )
            .props("virtual-scroll")
            .classes("w-full")
        )

        UIComponents._add_price_comparison_slots(table)
        return table

    @staticmethod
    def _add_price_comparison_slots(table: ui.table) -> None:
        """Add custom slots for price comparison indicators"""
        table.add_slot(
            "body-cell-price_min",
            """
            <q-td key="price_min" :props="props">
                {{ props.value }}
                <q-icon v-if="props.row.price_min !== 'N/A' && props.row.year_ago_min !== 'N/A'"
                    :name="parseFloat(props.row.price_min) < parseFloat(props.row.year_ago_min) ? 'arrow_downward' : 
                           parseFloat(props.row.price_min) > parseFloat(props.row.year_ago_min) ? 'arrow_upward' : ''"
                    :color="parseFloat(props.row.price_min) < parseFloat(props.row.year_ago_min) ? 'positive' :
                            parseFloat(props.row.price_min) > parseFloat(props.row.year_ago_min) ? 'negative' : ''"
                    size="xs"
                />
            </q-td>
            """,
        )

        table.add_slot(
            "body-cell-price_max",
            """
            <q-td key="price_max" :props="props">
                {{ props.value }}
                <q-icon v-if="props.row.price_max !== 'N/A' && props.row.year_ago_max !== 'N/A'"
                    :name="parseFloat(props.row.price_max) < parseFloat(props.row.year_ago_max) ? 'arrow_downward' : 
                           parseFloat(props.row.price_max) > parseFloat(props.row.year_ago_max) ? 'arrow_upward' : ''"
                    :color="parseFloat(props.row.price_max) < parseFloat(props.row.year_ago_max) ? 'positive' :
                            parseFloat(props.row.price_max) > parseFloat(props.row.year_ago_max) ? 'negative' : ''"
                    size="xs"
                />
            </q-td>
            """,
        )

    @staticmethod
    def create_product_select(options: List[str], on_change: Callable) -> ui.select:
        """Create product selection dropdown"""
        return ui.select(
            options=options,
            label="Produkt",
            on_change=on_change,
        ).classes("w-full")

    @staticmethod
    def create_product_label() -> ui.label:
        """Create label for selected product display"""
        return ui.label("").classes("text-h6 q-mt-md")

    @staticmethod
    def create_header() -> None:
        """Create application header"""
        with ui.header().classes("bg-primary text-white"):
            ui.label("Ceny hurtowe owoców i warzyw").classes("text-h4 q-px-md q-py-sm")

    @staticmethod
    def create_left_drawer() -> ui.left_drawer:
        """Create left drawer container"""
        return ui.left_drawer(fixed=True).classes("w-96 p-4 bg-light shadow-xl")

    @staticmethod
    def create_main_content_layout() -> ui.row:
        """Create main content row layout"""
        return ui.row().classes("flex-grow p-4 gap-10 w-full")

    @staticmethod
    def create_column_layout() -> ui.column:
        """Create column layout for content sections"""
        return ui.column().classes("flex-1 w-1/2 pr-2")
