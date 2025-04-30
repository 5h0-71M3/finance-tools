# Imports for Netsuite Related Data Quality Checks
import pandas as pd

from src.pipeline.archives.reports.metadata import CheckSet
from src.pipeline.base.checks.netsuite import carrier_details_section as _dq_cd

# BELOW ARE THE PROPS / FUNCTIONS FOR VALIDATING THE DATA
validate_net_premium = _dq_cd.validate_net_premium
validate_carrier_net_premium = _dq_cd.validate_carrier_net_premium
validate_carrier_bound_premium = _dq_cd.validate_carrier_bound_premium
validate_carrier_commission = _dq_cd.validate_carrier_commission_to_coalition


class CarrierDetailsCheck(CheckSet):
    """Set of checks used to confirm premium amount

    Used in:
        *Carrier Details*: confirming that the carrier details sections match up

        *Carrier Reporting*: confirming that the premium amount ties out

    """
    def __init__(self, df: pd.DataFrame):
        self.df = self._verify_fields(df)

    def _verify_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def validate_net_premium(
            self,
            internal_id: pd.Series,
            *,
            tbp: pd.Series,
            commission_percent: pd.Series,
            net_premium: pd.Series,
            variance_cap: float = .02,
            test_name: str = "Net Premium Validation"
    ) -> dict:

        mapping = self.validation_mapping.copy()
        for iid, total, commission, net in zip(internal_id, tbp, commission_percent, net_premium):
            result = _dq_cd.validate_net_premium(total, commission, net, variance_cap)
            note = "Net Premium ties out"
            if result is False:
                note = f"Expected {result[1]} got {net}. 'Commission' or 'TBP' is off."

            # Adding the results of the testing
            mapping["id"].append(iid)
            mapping["result"].append(result[0])
            mapping["note"].append(note)
            mapping["test"].append(test_name)
        return mapping

    def validate_carrier_net_premium(
            self,
            internal_id: pd.Series,
            *,
            total_bound_premium: pd.Series,
            carrier_net_premium: pd.Series,
            carrier_commission_percent: pd.Series,
            quota_share: pd.Series,
            variance_cap: float = .02,
            test_name: str = "Net Premium Validation"
    ) -> dict:
        mapping = self.validation_mapping.copy()

        for iid, tb, net, com, qs in zip(
                internal_id,
                total_bound_premium,
                carrier_net_premium,
                carrier_commission_percent,
                quota_share
        ):
            result = _dq_cd.validate_carrier_net_premium(tb, net, com, qs, variance_cap)
            note = "Carrier Net Premium ties out"
            if result is False:
                note = f"Expected {result[1]} got {net}. 'Commission' or 'TBP' is off."

            # Adding the results of the testing
            mapping["id"].append(iid)
            mapping["result"].append(result[0])
            mapping["note"].append(note)
            mapping["test"].append(test_name)
        return mapping



    def validate_carrier_bound_premium(self) -> pd.DataFrame:
        ...

    def validate_carrier_commission_to_coalition(self) -> pd.DataFrame:
        ...
