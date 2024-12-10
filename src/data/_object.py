from abc import abstractmethod, ABC
from collections.abc import Callable

from typing import Optional, TypeVar

import pandas as pd


class Metadata:

    @classmethod
    def _check_functions(cls) -> dict[str, Callable[..., bool]]:
        """creates a list of data check functions associated with the metadata

        :return: a list of all the checks you want to / can run
        """
        ...


T = TypeVar("T", bound=Metadata)
"""Adding type T to allow for Metadata typing without errors in IDE. Denotes any Metadata"""


class Report(ABC):
    df: pd.DataFrame
    _metadata: T

    @abstractmethod
    def _format(self, *args, **kwargs) -> pd.DataFrame:
        """
        Implement this with the self.df in order to properly format your report

        Formatting a report is a two-step process:
            (1) The object inheriting this abstract class needs to call this _format() method in the init.
                The convention is to set it to self.df

            (2) These classes will just pull the report from the directory. We can decouple in the future
                but for now, inside the _format function, (a) use the Directory class to pull the report
                from the directory and (b) use the metadata to rename the columns in the report to
                normalize it


        :param args: any argument you may need to format the report
        :param kwargs: any keyword argument you may need to format the report
        :return: a formatted based reported as a DataFrame
        """
        ...

    def _run_checks(self, *args, **kwargs) -> pd.DataFrame:
        """function for running and validating the data checks on the report

        call on the self._metadata to call the function (denoted with validate* in the keyword).
        Not sure on what errors should create, but might need to be some type of report or
        based on an argument.

        Can add the checks to columns, create a validation report, or create and upload file
        to fix.

        """
        ...

    @classmethod
    def _format_percentage_column(cls, column: pd.Series) -> pd.Series:
        """
        Takes an unformatted percentage column and returns a formatted percentage column

        :param column: percentage type column
        :return: formatted percentage column
        """
        if not isinstance(column, pd.Series):
            raise TypeError(f"{column} is not a pandas Series, got {type(column)}")

        column = column.fillna("0").str.replace("%", "").astype(float) / 100
        return column

    @classmethod
    def _format_limit_column(cls, column: pd.Series, add_aggregate: Optional[pd.Series] = None) -> pd.Series:
        """
        Takes an unformatted limit column, and returns a formatted limit column

        :param column: the sublimit or limit to format and process
        :param add_aggregate: (optional) when used, will use the argument to fill in missing sublimit columns with the aggregate limit amount.
        :return:
        """
        if not isinstance(column, pd.Series):
            raise TypeError(f"{column} is not a valid pandas Series, got {type(column)}")
        try:
            column = column.astype(str).str.replace("$", "").str.strip().str.replace(",", "")
            if add_aggregate is None:
                column = pd.to_numeric(column, errors="coerce").fillna(0).astype(int)
            else:
                column = pd.to_numeric(column, errors="coerce").fillna(add_aggregate).astype(int)
            column = column.astype(int)
        except ValueError as e:
            raise e
        return column
