from abc import abstractmethod, ABC
from typing import Optional

import pandas as pd

from src.file_handling.directory_handler import Directory
from src.reporting.metadata.looker.looker_limit import looker_limit_field_mapping, looker_limit_columns
from src.reporting.metadata.netsuite.carrier_v1 import (
    netsuite_carrierv1_field_mapping,
    netsuite_carrierv1_commission_percentage,
    netsuite_carrierv1_quota_share,
    netsuite_carrierv1_commission_amount,
    netsuite_carrierv1_net_premium,
    netsuite_carrierv1_bound_premium
)
from src.reporting.metadata.netsuite.netsuite_limit import netsuite_limit_field_mapping, netsuite_limit_columns
from src.reporting.metadata.netsuite.netsuite_surcharge import netsuite_surcharge_field_mapping
from src.reporting.metadata.netsuite.ns_reports import FieldNamingConventions
from src.structs.policy_container import TransactionStack, CoverageDetailTransactionLine


class Report(ABC):
    df: pd.DataFrame

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


# ==============================================================
# BASE NETSUITE REPORTS NOT TIED TO A POLICY PAGE SECTION / TAB
# ==============================================================
"""This section represents Netsuite reports not tied to a specific section on the Policy Page"""


class DataQualityDailyTransaction(Report):
    def __init__(self, remove_financial_transactions: bool = False):
        """Represents the Data Quality Transaction Report

        :param remove_financial_transactions: will remove financial based transactions like a Soft Delete or Binder Edits
        """
        self.df = self._format(remove_financial_transactions)

    def _format(self, remove_financial_transactions: bool = False) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualityDailyTransaction")
        df = df.rename(columns=FieldNamingConventions.data_quality_transaction)

        if remove_financial_transactions:
            filter_be_sd_complete = df["be_sd_complete"] == "Yes"
            filter_sd = df["soft_delete"] == "Yes"
            filter_be = df["be_sd_complete"] == "Yes"
            filter_applied = filter_be_sd_complete & (filter_sd | filter_be)
            df = df[~filter_applied]

        df["nj_sla"] = df["nj_sla"].fillna("")
        df = df.sort_values(by=["date_created", "internal_id"])

        return df


class NewJerseySLAQuery:
    def __init__(self):
        df = Directory.DOWNLOADS.open_recent(filename_pattern="NJ SLA Query")
        df = df.rename(columns=FieldNamingConventions.nj_sla_query)
        self.df = df


# =========================================
# NETSUITE REPORTS TIED TO A TAB OR SECTION
# =========================================
"""
Each one of these report is a Netsuite report that reflects a Policy Page on Netsuite
"""


class CarrierDetails(Report):
    def __init__(self):
        self.df = self._format()

    def _format(self) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualityCarrierV1CheckSTMResults")
        df = df.rename(columns=netsuite_carrierv1_field_mapping)

        # Combining the quota share column with the Commission Percentage Columns
        _percentage_columns = netsuite_carrierv1_commission_percentage + netsuite_carrierv1_quota_share
        _percentage_columns.append('coalition_commission_percent')
        for column in _percentage_columns:
            df[column] = self._format_percentage_column(df[column])

        # Formatting the Premium Columns adding commission, net premium, and bound premium
        _premium_columns = netsuite_carrierv1_commission_amount + netsuite_carrierv1_net_premium + netsuite_carrierv1_bound_premium
        for column in _premium_columns:
            df[column] = df[column].fillna(0)
        return df


class CoverageDetails(Report):
    """
    I'm going to include Aggregate Limit and SIR with this report since they are all related, even though they
    are under different sections in Netsuite

    This is the Data Quality - Limits - STM Report
    """
    def __init__(self, filename: Optional[str] = None):
        self.df = self._format()
        self.coverage_table = self._generate_platform_coverage_table()

    def _format(self, filename: Optional[str] = None) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualityLimitsSTMResults") if filename is None else Directory.DOWNLOADS.open(filename)
        df = df.rename(columns=netsuite_limit_field_mapping)

        # formatting as a Limit field
        for coverage in netsuite_limit_columns:
            df[coverage] = self._format_limit_column(df[coverage])
        return df

    def _generate_platform_coverage_table(self) -> dict:
        """
        This comes from a Looker report and has the Coverage amounts by policy.
        The coverage table can be used when trying to see if the limits line up with what is expected on the policy.

        :return:
        """
        looker_df = Directory.DOWNLOADS.open_recent(filename_pattern="policy limits v1")
        looker_df = looker_df.rename(columns=looker_limit_field_mapping)

        for limit in looker_limit_columns:
            looker_df[limit] = self._format_limit_column(looker_df[limit])

        coverage_table = {}  # policy#: {coverages}
        for row in looker_df.itertuples():
            coverages = dict()
            coverages["digital_asset_restoration"] = int(row.asset_restoration_sublimit)
            coverages["bi_pd_first_party"] = int(row.bipd_first_party_sublimit)
            coverages["bi_pd_third_party"] = int(row.bipd_third_party_sublimit)
            coverages["breach_response_costs_sublimit"] = int(row.breach_response_costs_sublimit)
            coverages["breach_response"] = int(row.breach_response_sublimit)
            coverages["network_and_information_security"] = int(row.network_sublimit)
            coverages["regulatory_fines_and_penalties"] = int(row.regulatory_defense_sublimit)
            coverages["multimedia_content"] = int(row.media_liability_sublimit)
            coverages["pci_fines_and_assessments"] = int(row.pci_sublimit)
            coverages["crisis_management_and_public"] = int(row.crisis_management_sublimit)
            coverages["cyber_extortion"] = int(row.extortion_sublimit)
            coverages["business_interruption_and_extra"] = int(row.business_interruption_sublimit)
            coverages["funds_transfer_fraud"] = int(row.funds_transfer_sublimit)
            coverages["reputation_repair"] = int(row.reputation_sublimit)
            coverages["pollution"] = int(row.pollution_sublimit)
            coverages["systems_integrity_restoration"] = int(row.systems_integrity_sublimit)
            coverages["computer_replacement"] = int(row.computer_replacement_sublimit)
            coverages["technology_eo"] = int(row.tech_eo_sublimit)
            coverages["service_fraud"] = int(row.service_fraud_sublimit)
            coverages["reputational_harm_loss"] = int(row.reputational_harm_sublimit)
            coverages["mpl_sublimit"] = int(row.mpl_sublimit)
            coverages["invoice_manipulation_sublimit"] = int(row.invoice_manipulation_sublimit)
            coverages["phising_sublimit"] = int(row.phishing_sublimit)
            coverages["funds_transfer_liability_sublimit"] = int(row.funds_transfer_sublimit)
            coverages["criminal_reward_sublimit"] = int(row.criminal_reward_sublimit)
            coverages["court_attendance_sublimit"] = int(row.court_attendance_sublimit)
            coverages["bound_agg_limit_sublimit"] = int(row.bound_agg_limit_sublimit)
            coverages["policy_agg_limit_sublimit"] = int(row.policy_agg_limit_sublimit)
            coverages["quote_agg_limit_sublimit"] = int(row.quote_agg_limit_sublimit)
            coverage_table[row.quote_coalition_policy_number] = coverages
        return coverage_table

    def create_stack_mapping(self) -> dict[str, TransactionStack]:
        """
        Generates a TransactionStack mapping based on Policy# so that the policy can be checked over its lifetime

        :return: uses the tools from the lib.structs library to perform sorting and data parsing
        """
        # 2024/09/11 the initial idea is to remove binder edits to avoid any confusion
        initial_df = self.df[self.df["binder_edit"].str.lower() != "yes"].copy()
        initial_df = initial_df.sort_values(by="transaction_id")

        data = dict()

        for record in initial_df.itertuples():
            if record.coalition_policy_number not in data:
                data[record.coalition_policy_number] = TransactionStack()

            line = CoverageDetailTransactionLine(
                internal_id=record.internal_id,
                description=record.transaction_description,
                aggregate_limit=record.aggregate_total_limit,
                aggregate_limit_balance=record.aggregate_total_limit_balance,
                sir=record.sir,
            )
            data[record.coalition_policy_number].t_push(line)
        return data


class SurchargeSection(Report):
    def __init__(self):
        self.df = self._format()

    def _format(self) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualitySurchargeSTMResults")
        df = df.rename(columns=netsuite_surcharge_field_mapping)
        return df
