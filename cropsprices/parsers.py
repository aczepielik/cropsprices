import logging
import warnings
from datetime import datetime
from typing import Any, List, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, field_validator

# Get a logger for this module
logger = logging.getLogger(__name__)


class ExcelHeader(BaseModel):
    df: pd.DataFrame

    @field_validator("df")
    @classmethod
    def validate_header(cls, v: pd.DataFrame) -> pd.DataFrame:
        if v.shape[0] != 3 or v.shape[1] < 4:
            raise ValueError("Header must have 3 rows and at least 4 columns")

        locations = v.iloc[0, 3:].dropna().tolist()
        dates = v.iloc[1, 3:].dropna().tolist()

        if not dates or not locations:
            raise ValueError("No dates or locations found in the header")

        # Check that locations fill half of the v.iloc[0,3:]
        if len(locations) * 2 != v.shape[1] - 3:
            raise ValueError("Each location should have exactly two columns.")

        for date in dates:
            if not isinstance(date, datetime):
                date_str = str(date)
                try:
                    datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    raise ValueError(
                        f"Invalid date format: {date_str}. Expected format: MM/DD/YYYY"
                    )

        return v

    class Config:
        arbitrary_types_allowed = True


class ExcelData(BaseModel):
    df: pd.DataFrame

    @field_validator("df")
    @classmethod
    def validate_data(cls, v: pd.DataFrame) -> pd.DataFrame:
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
            price_stats = row.iloc[3:]
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
        self, input_file: str, sheet_name: str, is_fruit: bool = False, **kwargs: Any
    ):
        self.input_file = input_file
        self.sheet_name = sheet_name
        self.is_fruit = is_fruit
        self.excel_read_kwargs = kwargs
        self.df = self._read_excel_file()

    def _read_excel_file(self) -> pd.DataFrame:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            df = pd.read_excel(
                self.input_file,
                sheet_name=self.sheet_name,
                header=None,
                **self.excel_read_kwargs,
            )

        ExcelHeader(df=df.iloc[:3]).df
        ExcelData(df=df.iloc[3:]).df

        return df

    def extract_dates_and_places(self) -> Tuple[List[str], List[str]]:
        dates = self.df.iloc[1, 3:].dropna().tolist()
        places = self.df.iloc[0, 3:].dropna().tolist()
        return dates, places

    def prepare_data_rows(self, places: List[str]) -> pd.DataFrame:
        data_rows = self.df.iloc[3:].reset_index(drop=True)
        if self.is_fruit:
            data_rows.columns = ["Product", "Variety", "Unit"] + [
                f"{place}_{stat}" for place in places for stat in ["Min", "Max"]
            ]
        else:
            data_rows.columns = ["Product", "", "Unit"] + [
                f"{place}_{stat}" for place in places for stat in ["Max", "Min"]
            ]

        # Check and swap Min and Max if necessary
        for place in places:
            min_col = f"{place}_Min"
            max_col = f"{place}_Max"
            if min_col in data_rows.columns and max_col in data_rows.columns:
                mask = data_rows[min_col] > data_rows[max_col]
                data_rows.loc[mask, [min_col, max_col]] = data_rows.loc[
                    mask, [max_col, min_col]
                ].values

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

        if self.is_fruit:
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

        # Remove unnamed columns
        data_rows = data_rows.loc[:, ~data_rows.columns.str.contains("^Unnamed")]

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
        melted_df: pd.DataFrame, places: List[str], dates: List[str]
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

    def convert_excel(self) -> List[dict]:
        try:
            dates, places = self.extract_dates_and_places()
            data_rows = self.prepare_data_rows(places)
            melted_df = self.melt_dataframe(data_rows)
            result_df = self.process_melted_df(melted_df, places, dates)
            result_df = self.clean_result_df(result_df)

            # Ensure proper types first
            for column in result_df.columns:
                if result_df[column].dtype == np.int64:
                    result_df[column] = result_df[column].astype(int)
                elif result_df[column].dtype == np.float64:
                    result_df[column] = result_df[column].astype(float)
                elif pd.api.types.is_datetime64_any_dtype(result_df[column]):
                    result_df[column] = result_df[column].dt.date.apply(
                        lambda x: x.isoformat() if pd.notnull(x) else None
                    )

            # Convert DataFrame to list of dictionaries
            result_list = result_df.dropna().to_dict("records")

            return result_list
        except ValueError as e:
            logger.error(f"Error occurred: {e}", exc_info=True)
            raise


def parse_excel(
    input_file: str,
    sheet_name: str,
    is_fruit: bool = False,
    **kwargs: Any,
) -> List[dict]:
    parser = ExcelParser(input_file, sheet_name, is_fruit, **kwargs)
    return parser.convert_excel()
