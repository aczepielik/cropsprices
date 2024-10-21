from datetime import datetime
from typing import Any, List, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, field_validator


class ExcelHeader(BaseModel):
    df: pd.DataFrame

    @field_validator("df")
    @classmethod
    def validate_header(cls, v: pd.DataFrame) -> pd.DataFrame:
        if v.shape[0] != 2 or v.shape[1] < 4:
            raise ValueError("Header must have 2 rows and at least 4 columns")

        locations = v.iloc[0, 3:].dropna().tolist()
        dates = v.iloc[1, 3:].dropna().tolist()

        if not dates or not locations:
            raise ValueError("No dates or locations found in the header")

        for date in dates:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    f"Invalid date format: {date}. Expected format: YYYY-MM-DD"
                )

        if len(dates) != len(locations) * 2:
            raise ValueError(
                "Each location should have exactly two price-statistic columns"
            )

        return v


class ExcelData(BaseModel):
    df: pd.DataFrame

    @field_validator("df")
    @classmethod
    def validate_data(cls, v: pd.DataFrame) -> pd.DataFrame:
        if v.shape[0] < 1 or v.shape[1] < 4:
            raise ValueError("Data must have at least 1 row and 4 columns")
        if (
            "KRAJOWE" not in v.iloc[:, 0].values
            or "IMPORTOWANE" not in v.iloc[:, 0].values
        ):
            raise ValueError(
                "Data must contain 'KRAJOWE' and 'IMPORTOWANE' in the first column"
            )

        for index, row in v.iterrows():
            product_name = row.iloc[0]
            if not isinstance(product_name, str):
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
        df = pd.read_excel(
            self.input_file,
            sheet_name=self.sheet_name,
            header=None,
            **self.excel_read_kwargs,
        )
        ExcelHeader(df=df.iloc[:2])
        ExcelData(df=df.iloc[2:])
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

        data_rows["Origin"] = ""
        domestic_start = data_rows[data_rows["Product"] == "KRAJOWE"].index[0]
        imported_start = data_rows[data_rows["Product"] == "IMPORTOWANE"].index[0]

        data_rows.loc[domestic_start + 1 : imported_start - 1, "Origin"] = "KRAJOWE"
        data_rows.loc[imported_start + 1 :, "Origin"] = "IMPORTOWANE"

        if self.is_fruit:
            data_rows["Product"] = data_rows.apply(
                lambda row: f"{row['Product']} {row['Variety']}".strip(), axis=1
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
        melted_df: pd.DataFrame, places: List[str], dates: List[str]
    ) -> pd.DataFrame:
        melted_df[["Place", "Statistic"]] = melted_df["Place_Stat"].str.split(
            "_", expand=True
        )
        melted_df = melted_df.drop("Place_Stat", axis=1)
        melted_df["Date"] = melted_df["Place"].map(dict(zip(places, dates)))
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

    def convert_excel(self, output_file: str) -> None:
        try:
            dates, places = self.extract_dates_and_places()
            data_rows = self.prepare_data_rows(places)
            melted_df = self.melt_dataframe(data_rows)
            result_df = self.process_melted_df(melted_df, places, dates)
            result_df = self.clean_result_df(result_df)
            result_df.to_excel(output_file, index=False, engine="openpyxl")
        except ValueError as e:
            print(f"Error: {e}")
            raise


def convert_excel_pandas(
    input_file: str,
    sheet_name: str,
    output_file: str,
    is_fruit: bool = False,
    **kwargs: Any,
) -> None:
    parser = ExcelParser(input_file, sheet_name, is_fruit, **kwargs)
    parser.convert_excel(output_file)


# Usage example (can be commented out or removed if not needed)
# try:
#     input_file = '/home/adam/Lab/cropsprices/.notes/input.xlsx'
#     output_file = '/home/adam/Lab/cropsprices/.notes/converted_output.xlsx'
#
#     # For vegetables, with additional arguments for pd.read_excel
#     convert_excel_pandas(input_file, 'Sheet1', output_file, is_fruit=False,
#                          skiprows=1, usecols="A:K")
#
#     # For fruits, with different additional arguments
#     convert_excel_pandas(input_file, 'Sheet2', output_file, is_fruit=True,
#                          engine='openpyxl', na_values=['N/A', 'NA'])
# except Exception as e:
#     print(f"An error occurred: {e}")
