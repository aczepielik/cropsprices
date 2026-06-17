import io
import logging
import warnings
from datetime import datetime
from typing import Any, List, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, ValidationInfo, field_validator

# Get a logger for this module
logger = logging.getLogger(__name__)


class ExcelHeader(BaseModel):
    df: pd.DataFrame

    @field_validator("df")
    @classmethod
    def validate_header(cls, v: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        if v.shape[0] != 3 or v.shape[1] < 3:
            raise ValueError("Header must have 3 rows and at least 3 columns")

        # Find the first occurrence of a date in row 1 (index 1)
        start_col = None
        for col in range(v.shape[1]):
            cell_value = v.iloc[1, col]
            if pd.notna(cell_value):
                try:
                    if isinstance(cell_value, datetime):
                        start_col = col
                        break
                    date_str = str(cell_value)
                    datetime.strptime(date_str, "%m/%d/%Y")
                    start_col = col
                    break
                except ValueError:
                    continue

        if start_col is None:
            raise ValueError("No valid date found in row 1")
        locations = v.iloc[0, start_col:].dropna().tolist()
        dates = v.iloc[1, start_col:].dropna().tolist()

        if not dates or not locations:
            raise ValueError("No dates or locations found in the header")

        for date in dates:
            if not isinstance(date, datetime):
                date_str = str(date)
                try:
                    datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    raise ValueError(
                        f"Invalid date format: {date_str}. Expected format: MM/DD/YYYY"
                    )

        return v, start_col

    class Config:
        arbitrary_types_allowed = True


class ExcelData(BaseModel):
    start_col: int = 3
    df: pd.DataFrame

    @field_validator("df")
    @classmethod
    def validate_data(cls, v: pd.DataFrame, info: ValidationInfo) -> pd.DataFrame:
        v = v.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))
        v = v.replace("", np.nan)
        start_col = info.data.get("start_col", 3)
        if v.shape[0] < 1 or v.shape[1] < 4:
            raise ValueError("Data must have at least 1 row and 4 columns")
        if (
            "KRAJOWE" not in v.iloc[:, 0].values
            and "IMPORTOWANE" not in v.iloc[:, 0].values
        ):
            raise ValueError(
                "Data must contain 'KRAJOWE' or 'IMPORTOWANE' in the first column"
            )
        for index, row in v.iterrows():
            product_name = row.iloc[0]
            if not isinstance(product_name, str) and pd.notna(product_name):
                raise ValueError(
                    f"Product name at row {index} is not a string: {product_name}"
                )
            price_stats = row.iloc[start_col:]
            for col, value in price_stats.items():
                if pd.notna(value):
                    try:
                        float(value)
                    except ValueError:
                        raise ValueError(
                            f"Price-statistic at row {index}, column {col} is not a valid float: {value}"
                        )
        return v

    class Config:
        arbitrary_types_allowed = True


class ExcelParser:
    def __init__(
        self,
        input_file: io.BytesIO | str,
        sheet_name: str,
        is_fruit: bool = False,
        **kwargs: Any,
    ):
        self.input_file = input_file
        self.sheet_name = sheet_name
        self.is_fruit = is_fruit
        self.excel_read_kwargs = kwargs
        self.df, self.start_col = self._read_excel_file()

    def _read_excel_file(self) -> Tuple[pd.DataFrame, int]:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            df = pd.read_excel(
                self.input_file,
                sheet_name=self.sheet_name,
                header=None,
                **self.excel_read_kwargs,
            )

        _, start_col = ExcelHeader(df=df.iloc[:3]).df
        ExcelData(df=df.iloc[3:], start_col=start_col).df  # type: ignore

        return df, start_col  # type: ignore

    def parse_price_changes(self, sheet_name) -> List[dict]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                df = pd.read_excel(
                    self.input_file,
                    sheet_name=sheet_name,
                    header=None,
                )

            # Find the row with column headers by checking all columns
            header_row = None
            for col in df.columns:
                header_indices = df[df.iloc[:, col] == "Produkt"].index
                if len(header_indices) > 0:
                    header_row = header_indices[0]
                    break

            if header_row is None:
                raise ValueError("Could not find header row with 'Produkt' column")

            # Set the header and reset index
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1 :].reset_index(drop=True)

            # Extract only the 'Produkt' and 'Jedn.' columns
            result_df = df[["Produkt", "Jedn."]].copy()

            # Remove rows where 'Produkt' is NaN or empty
            result_df = result_df[
                result_df["Produkt"].notna() & (result_df["Produkt"] != "")
            ]

            # Remove rows with headers like "Warzywa krajowe", "Owoce krajowe", etc.
            result_df = result_df[
                ~result_df["Produkt"].str.contains(
                    "krajowe|importowane", case=False, na=False
                )
            ]

            # Rename columns
            result_df = result_df.rename(
                columns={"Produkt": "Product", "Jedn.": "Unit"}
            )

            # Ensure product is unique by keeping the first occurrence
            result_df = result_df.drop_duplicates(subset=["Product"], keep="first")

            # Convert DataFrame to list of dictionaries
            result_list = result_df.to_dict("records")

            return result_list

        except Exception as e:
            logger.error(
                f"Error occurred while parsing price changes: {e}", exc_info=True
            )
            raise

    def extract_dates_and_places(self) -> Tuple[List[str], List[str]]:
        header_row = self.df.iloc[2, self.start_col :]
        num_pairs = sum(1 for v in header_row if v in ["Max", "Min"]) // 2

        raw_places = self.df.iloc[0, self.start_col :].tolist()
        places = []
        for i in range(num_pairs):
            col_idx = i * 2
            if col_idx < len(raw_places):
                val = raw_places[col_idx]
                if pd.notna(val) and val not in ["Max", "Min", "Jedn.", "Miejscowość"]:
                    places.append(str(val))
                else:
                    places.append(f"Rynek{i + 1}")
            else:
                places.append(f"Rynek{i + 1}")

        raw_dates = self.df.iloc[1, self.start_col :].tolist()
        dates = []
        for i in range(num_pairs):
            col_idx = i * 2
            if col_idx < len(raw_dates):
                dates.append(raw_dates[col_idx])
            else:
                dates.append(None)

        return dates, places

    def prepare_data_rows(self, places: List[str]) -> pd.DataFrame:
        data_rows = self.df.iloc[3:].reset_index(drop=True)
        data_rows = self._set_data_rows_columns(data_rows, places)
        data_rows = self._fill_product_names(data_rows)
        data_rows = self._fill_empty_units(data_rows)
        data_rows = self._swap_min_max_if_necessary(data_rows, places)
        data_rows = self._set_origin(data_rows)

        if self.is_fruit:
            data_rows = self._process_fruit_data(data_rows)

        return data_rows.loc[:, ~data_rows.columns.str.contains("^Unnamed")]

    def _set_data_rows_columns(
        self, data_rows: pd.DataFrame, places: List[str]
    ) -> pd.DataFrame:
        if self.is_fruit:
            id_cols = ["Product", "Variety", "Unit"]
        else:
            empty_cols = [""] * (self.start_col - 2) if self.start_col > 2 else []
            id_cols = ["Product"] + empty_cols + ["Unit"]

        expected_cols = len(id_cols) + len(places) * 2

        if data_rows.shape[1] > expected_cols:
            data_rows = data_rows.iloc[:, :expected_cols]

        data_rows.columns = pd.Index(
            id_cols + [f"{place}_{stat}" for place in places for stat in ["Max", "Min"]]
        )
        return data_rows

    def _fill_product_names(self, data_rows: pd.DataFrame) -> pd.DataFrame:
        data_rows.loc[:, "Product"] = data_rows.loc[:, "Product"].ffill()
        return data_rows

    def _fill_empty_units(self, data_rows: pd.DataFrame) -> pd.DataFrame:
        if data_rows["Unit"].isna().all():
            price_changes_data = self.parse_price_changes("zmiany cen hurt")
            product_unit_map = {
                item["Product"]: item["Unit"] for item in price_changes_data
            }
            data_rows["Unit"] = data_rows["Product"].map(product_unit_map)
        return data_rows

    def _swap_min_max_if_necessary(
        self, data_rows: pd.DataFrame, places: List[str]
    ) -> pd.DataFrame:
        for place in places:
            min_col, max_col = f"{place}_Min", f"{place}_Max"
            if min_col in data_rows.columns and max_col in data_rows.columns:
                mask = data_rows[min_col].gt(data_rows[max_col], fill_value=False)
                data_rows.loc[mask, [min_col, max_col]] = data_rows.loc[
                    mask, [max_col, min_col]
                ].values
        return data_rows

    def _set_origin(self, data_rows: pd.DataFrame) -> pd.DataFrame:
        data_rows["Origin"] = ""
        domestic_indices = data_rows[data_rows["Product"] == "KRAJOWE"].index
        imported_indices = data_rows[data_rows["Product"] == "IMPORTOWANE"].index

        if len(domestic_indices) > 0 and len(imported_indices) > 0:
            domestic_start = domestic_indices[0]
            imported_start = imported_indices[0]
            data_rows.loc[domestic_start + 1 : imported_start - 1, "Origin"] = "KRAJOWE"
            data_rows.loc[imported_start + 1 :, "Origin"] = "IMPORTOWANE"
        elif len(domestic_indices) > 0:
            data_rows.loc[:, "Origin"] = "KRAJOWE"
        elif len(imported_indices) > 0:
            data_rows.loc[:, "Origin"] = "IMPORTOWANE"

        return data_rows

    def _process_fruit_data(self, data_rows: pd.DataFrame) -> pd.DataFrame:
        notna_or_empty = lambda x: x if pd.notna(x) else ""  # noqa: E731
        last_product = ""
        for i, row in data_rows.iterrows():
            if pd.isna(row["Product"]) and pd.notna(row["Variety"]):
                data_rows.at[i, "Product"] = last_product
            else:
                last_product = row["Product"]

        data_rows["Product"] = data_rows.apply(
            lambda row: f"{notna_or_empty(row['Product'])} {notna_or_empty(row['Variety'])}".strip(),
            axis=1,
        )
        data_rows = data_rows.drop("Variety", axis=1)

        return data_rows

    @staticmethod
    def melt_dataframe(data_rows: pd.DataFrame) -> pd.DataFrame:
        id_vars = ["Product", "Unit", "Origin"]
        value_vars = [col for col in data_rows.columns if col not in id_vars]
        return pd.melt(
            data_rows,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="Place_Stat",
            value_name="Price",
        )

    @staticmethod
    def process_melted_df(
        melted_df: pd.DataFrame, places: List[str], dates: List[str] | List[datetime]
    ) -> pd.DataFrame:
        melted_df[["Place", "Statistic"]] = melted_df["Place_Stat"].str.split(
            "_", expand=True
        )
        melted_df = melted_df.drop("Place_Stat", axis=1)

        # Convert dates to datetime objects if they're not already
        dates = [
            date
            if isinstance(date, datetime)
            else datetime.strptime(str(date), "%m/%d/%Y")
            for date in dates
        ]

        # Create a dictionary mapping places to datetime objects
        date_dict = dict(zip(places, dates))

        # Map the dates and convert to datetime
        melted_df["Date"] = melted_df["Place"].map(date_dict)

        # Ensure Date is in datetime format
        melted_df["Date"] = pd.to_datetime(melted_df["Date"])
        melted_df["Date"] = melted_df["Date"].dt.date.apply(
            lambda x: x.isoformat() if pd.notnull(x) else None
        )

        return melted_df[
            ["Product", "Unit", "Place", "Date", "Statistic", "Price", "Origin"]
        ]

    @staticmethod
    def clean_result_df(result_df: pd.DataFrame) -> pd.DataFrame:
        result_df = result_df[
            result_df["Product"].notna()
            & (result_df["Product"] != "")
            & (result_df["Product"] != "KRAJOWE")
            & (result_df["Product"] != "IMPORTOWANE")
        ]
        return result_df.replace("", np.nan)

    @staticmethod
    def _ensure_proper_types(df: pd.DataFrame) -> pd.DataFrame:
        for column in df.columns:
            if df[column].dtype == np.int64:
                df[column] = df[column].astype(int)
            elif df[column].dtype == np.float64:
                df[column] = df[column].astype(float)
            elif pd.api.types.is_datetime64_any_dtype(df[column]):
                df[column] = df[column].dt.date.apply(
                    lambda x: x.isoformat() if pd.notnull(x) else None
                )
        return df

    def convert_excel(self) -> List[dict]:
        try:
            dates, places = self.extract_dates_and_places()
            data_rows = self.prepare_data_rows(places)
            melted_df = self.melt_dataframe(data_rows)
            result_df = self.process_melted_df(melted_df, places, dates)
            result_df = self.clean_result_df(result_df)
            result_df = self._ensure_proper_types(result_df)

            # Convert DataFrame to list of dictionaries
            result_list = result_df.dropna().to_dict("records")

            return result_list
        except ValueError as e:
            logger.error(f"Error occurred: {e}", exc_info=True)
            raise


def parse_excel(
    input_file: io.BytesIO | str,
    sheet_name: str,
    is_fruit: bool = False,
    **kwargs: Any,
) -> List[dict]:
    parser = ExcelParser(input_file, sheet_name, is_fruit, **kwargs)
    return parser.convert_excel()
