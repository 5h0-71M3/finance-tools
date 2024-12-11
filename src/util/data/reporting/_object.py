from abc import abstractmethod

from src.pipeline.checks.netsuite import carrier_details_section as _dq_cd

# BELOW ARE THE PROPS / FUNCTIONS FOR VALIDATING THE DATA
validate_net_premium = _dq_cd.validate_net_premium
validate_carrier_net_premium = _dq_cd.validate_carrier_net_premium
validate_carrier_bound_premium = _dq_cd.validate_carrier_bound_premium
validate_carrier_commission = _dq_cd.validate_carrier_commission_to_coalition


class Reporting:
    """class of functions for doing test_data validations or creating the deliverables

    """
    @abstractmethod
    def deliverable(self):
        ...

