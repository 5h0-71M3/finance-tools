"""This section represents Netsuite reports not tied to a specific section on the Policy Page"""
import pandas as pd

from src.data.metadata.netsuite.ns_reports import FieldNamingConventions
from src.data._object import Report
from src.file_handling.directory_handler import Directory


# ==============================================================
# BASE NETSUITE REPORTS NOT TIED TO A POLICY PAGE SECTION / TAB
# ==============================================================
class DataQualityDailyTransaction(Report):
    def __init__(self, remove_financial_transactions: bool = False):
        """Represents the Data Quality Transaction Report

        :param remove_financial_transactions: will remove financial based transactions like a Soft Delete or Binder Edits
        """
        self.df = self._format(remove_financial_transactions)
        self._metadata = FieldNamingConventions()

    def _format(self, remove_financial_transactions: bool = False) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualityDailyTransaction")
        df = df.rename(columns=self._metadata.data_quality_transaction)

        if remove_financial_transactions:
            filter_be_sd_complete = df["be_sd_complete"] == "Yes"
            filter_sd = df["soft_delete"] == "Yes"
            filter_be = df["be_sd_complete"] == "Yes"
            filter_applied = filter_be_sd_complete & (filter_sd | filter_be)
            df = df[~filter_applied]

        df["nj_sla"] = df["nj_sla"].fillna("")
        df = df.sort_values(by=["date_created", "internal_id"])

        return df


class NewJerseySLAQuery(Report):
    def __init__(self):
        df = Directory.DOWNLOADS.open_recent(filename_pattern="NJ SLA Query")
        self.df = df
        self._metadata = FieldNamingConventions()

    def _format(self) -> pd.DataFrame:
        df = self.df.rename(columns=self._metadata.nj_sla_query)
        return df
