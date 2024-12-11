"""The REPORT API for Policy Pages

Each one of these reports is a Netsuite report that reflects a Policy Page on Netsuite
"""

from typing import Optional

import pandas as pd

from src.data.metadata._object import Report
from src.data.insured_page import TransactionStack, CoverageDetailTransactionLine
from src.file_handling.directory_handler import Directory

from src.data.metadata import (
    NetsuiteCarrierV1Metadata,
    NetsuiteLimitMetadata,
    LookerLimitMetadata,
    NetsuiteSurchargeMetadata
)


# =========================================
# NETSUITE REPORTS TIED TO A TAB OR SECTION
# =========================================
class CarrierDetails(Report):
    def __init__(self):
        self.df = self._format()
        self._metadata = NetsuiteCarrierV1Metadata()

    def _format(self) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualityCarrierV1CheckSTMResults")
        df = df.rename(columns=self._metadata.field_mapping)

        # Combining the quota share column with the Commission Percentage Columns
        _percentage_columns = self._metadata.percentage_agg_columns
        for column in _percentage_columns:
            df[column] = self._format_percentage_column(df[column])

        # Formatting the Premium Columns adding commission, net premium, and bound premium
        _premium_columns = self._metadata.premium_agg_columns
        for column in _premium_columns:
            df[column] = df[column].fillna(0)
        print(f"Running Carrier Details formatting...")
        return df

    def _run_checks(self, *args, **kwargs) -> pd.DataFrame:
        ...


class CoverageDetails(Report):
    """
    I'm going to include Aggregate Limit and SIR with this report since they are all related, even though they
    are under different sections in Netsuite

    This is the Data Quality - Limits - STM Report
    """
    def __init__(self, filename: Optional[str] = None):
        self.df = self._format()
        self._metadata = NetsuiteLimitMetadata()
        self._looker_metadata = LookerLimitMetadata()
        self.coverage_table = self._generate_platform_coverage_table()

    def _format(self, filename: Optional[str] = None) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualityLimitsSTMResults") if filename is None else Directory.DOWNLOADS.open(filename)
        df = df.rename(columns=self._metadata.field_mapping)

        # formatting as a Limit field
        for coverage in self._metadata.limit_columns:
            df[coverage] = self._format_limit_column(df[coverage])
        return df

    def _generate_platform_coverage_table(self) -> dict:
        """
        This comes from a Looker report and has the Coverage amounts by policy.
        The coverage table can be used when trying to see if the limits line up with what is expected on the policy.

        :return:
        """
        looker_df = Directory.DOWNLOADS.open_recent(filename_pattern="policy limits v1")
        looker_df = looker_df.rename(columns=self._looker_metadata.field_mapping)

        for limit in self._looker_metadata.limit_columns:
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
        Generates a TransactionStack mapping based on Policy# so that the policy can be checked over its insured_page

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
        self._metadata = NetsuiteSurchargeMetadata()

    def _format(self) -> pd.DataFrame:
        df = Directory.DOWNLOADS.open_recent(filename_pattern="DataQualitySurchargeSTMResults")
        df = df.rename(columns=self._metadata.field_mapping)
        return df
