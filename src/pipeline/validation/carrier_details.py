from dirlin.pipeline import Validation, Check

from src.pipeline.checks.netsuite.carrier_details_section import (
    validate_carrier_bound_premium,
    validate_carrier_net_premium,
    validate_net_premium,
    validate_carrier_commission_to_coalition,
)

##################################
# Instantiated Check Objects
##################################
_shared_carrier_exclusion = [
    "palekana",
    "total",
    "cic",
    "argo"
]

# From Carrier Details Module
_validate_net_premium = Check(validate_net_premium)
"""Net Premium matches the expected Net Premium amount"""

_validate_carrier_bound_premium = Check(validate_carrier_bound_premium)
"""Carrier Bound Premium matches the expected Net Premium amount"""

_validate_carrier_net_premium = Check(validate_carrier_net_premium)
"""Carrier Net Premium matches expected Carrier  Net Premium amount"""

_validate_carrier_commission_to_coalition = Check(validate_carrier_commission_to_coalition)
"""Carrier Commission to Coalition matches expected amount"""


##################################
# Instantiated Validation Objects
##################################
_carrier_details_validation_selection = [
    _validate_net_premium,
    _validate_carrier_bound_premium,
    _validate_carrier_net_premium,
    _validate_carrier_commission_to_coalition
]

CarrierDetailsValidation = Validation(
    check=_carrier_details_validation_selection
)
