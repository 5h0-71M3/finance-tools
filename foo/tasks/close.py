from abc import ABC, abstractmethod
from datetime import date
from typing import Callable

import pandas as pd
from dirlin import DirlinFormatter

from foo.io.directory_handler import FOLDERS
from foo.pipeline.core.reports.policy_list import carrier_info_tuples, Subsidiaries
from foo.pipeline.core.enums import stm_commission_percent_columns


def _close_transaction_report():
    ...


def _close_documents_report():
    ...


class Task(ABC):
    """used for individual close tasks, like Account Completeness or Duplicates.
    This object will then split it out by Subsidiary for the final deliverable.
    """
    def __init__(self):
        self.report: pd.DataFrame | None = None
        self.name: str = self._defined_name()
        self.subsidiaries = list(Subsidiaries.__dict__.values())
        self.save_folder_path = FOLDERS(initialize_posix_path=False).DOWNLOADS

    def complete(self, *args, **kwargs) -> None:
        # [1.1] Define the Dataframe we will be using
        df: pd.DataFrame = self.report.copy()

        # [1.2] Get the results of _run. Returns a Series
        results = self._run(df, *args, **kwargs)

        # [1.3] Set the name of the dataframe we are using with the result name
        df[self.name] = results

        # [1.4] Split the Dataframe by the Subsidiary for final deliverable
        unique_subs = df["Subsidiary [Agency Customer]"].unique().tolist()
        for sub in unique_subs:
            save_string = f"{self.name} - Close - {str(sub).split(':')[-1]} - {date.today()}.xlsx"
            df[df["Subsidiary [Agency Customer]"] == sub].to_excel(self.save_folder_path / save_string)

        # [1.5] Task Complete

    @abstractmethod
    def _run(self, df: pd.DataFrame, *args, **kwargs) -> pd.Series:
        """function for running the close tasks. Will be called in the public `complete` method.
        """
        ...

    @abstractmethod
    def _defined_name(self) -> str:
        ...


class Closer:
    def __init__(self):
        # [1.1] Base function and classes for init
        self.carrier_mapping = carrier_info_tuples()
        self.stm_commission_perc = stm_commission_percent_columns()
        self.subsidiaries = Subsidiaries

        # [1.2] Derived mapping and objects for init
        self.carrier_quota_share_columns = [f[0] for f in self.carrier_mapping.values()]
        """the Quota Share column for all existing carriers"""

        self.carrier_commission_perc_columns = list(set(f[6] for f in self.carrier_mapping.values()))
        """The % commission columns for all existing carriers"""

        # [2.1] init for subclasses used inside the class to close
        self.format = DirlinFormatter()

    @staticmethod
    def _get_unique_subsidiaries(policy_list: pd.DataFrame) -> list:
        """Gets the unique subsidiary values from a Policy List report"""
        return policy_list["Subsidiary [Agency Customer]"].unique().tolist()

    def close_month(
            self,
            policy_list: pd.DataFrame,
    ):

        subsidiaries = self._get_unique_subsidiaries(policy_list)

        reports = [
            ("Quota Check", self._close_carrier_quota_share_total),
            ("Commission Check", self._close_carrier_commission_percent),
            # ("Zero Dollar Check", self._close_zero_dollar_reinstatement),
        ]

        new_column_names = []
        for name, fn in reports:
            r = fn(policy_list)
            policy_list[name] = r
            new_column_names.append(name)
        return policy_list

    def _close_carrier_quota_share_total(self, policy_list: pd.DataFrame):
        """calculates that the total sum of the quota shares is 1
        """
        results = policy_list[self.carrier_quota_share_columns].sum(axis=1)
        deliverable = results.apply(lambda x: "Pass" if x == 1 else f"Fail: {x}")
        return deliverable

    def _close_carrier_commission_percent(self, policy_list: pd.DataFrame):
        """calculates that the total sum or `quota share` * `carrier commission` is equal
        to the `coalition commission`
        """
        # [1.1] Initializing the Reports
        temp_policy_list = policy_list.copy()
        quota_comm_per_pairs = [(pair[0], pair[6]) for pair in self.carrier_mapping.values()]

        # [1.2] formatting the percentage columns
        for q, c in quota_comm_per_pairs:
            temp_policy_list[c] = self.format.convert_percentage_to_float(temp_policy_list[c])

        # [1.3] formatting the Coalition Commission Column
        temp_policy_list["Coalition Commission %"] = self.format.convert_percentage_to_float(temp_policy_list["Coalition Commission %"])

        # [2.1] calculate the commission and quota breakdown sum with the values we have
        results = sum(temp_policy_list[quota] * temp_policy_list[comm] for quota, comm in quota_comm_per_pairs)

        # [2.2] compare against the Coalition Commission Rate we have
        margin = (temp_policy_list["Coalition Commission %"] - results).abs()

        # [2.3] write out the error messages depending on the margin
        deliverable = margin.apply(lambda x: "Pass" if x <= .005 else f"Fail: {x}")
        return deliverable

    @staticmethod
    def _close_zero_dollar_reinstatement(policy_list: pd.DataFrame) -> pd.Series:
        # [1.1] initializing and setting up the masks
        error_description = ["Reinstatement", "Cancellation - Flat", "Cancellation - Pro-Rated"]
        mask_zero_dollar_policy = policy_list["Total Bound Premium"] == 0
        mask_description_in_error = policy_list["Transaction Description"].isin(error_description)

        # [1.2] going to try and use loc and masks to get this down correctly
        mask_incorrect = mask_description_in_error & mask_zero_dollar_policy

        # [1.3] applying the masks and getting the results
        # results = np.where(mask_zero_dollar_policy and mask_description_in_error, "Pass", "Invalid $0 Transaction")
        results = policy_list.loc[mask_incorrect]

        # [1.4] convert to pd.Series
        deliverable = pd.Series(results)
        return deliverable
