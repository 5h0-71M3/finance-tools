from dirlin.pipeline import Check, Validation

from src.pipeline.checks.bdx import (
    allianz_commission_rate_matches_google_sheet,
    carrier_tria_zero_if_total_is_zero,
    package_key_missing_on_expected_transactions
)
from src.pipeline.checks.netsuite.carrier_details_section import (
    validate_carrier_bound_premium,
    validate_carrier_net_premium,
    validate_carrier_commission_to_coalition
)
from src.pipeline.checks.netsuite.coverage_details_section import validate_limit_signature_matches_tbp

# Initializing all checks

###################
# BASIC CHECKS
###################
_validate_carrier_bound_premium = Check(validate_carrier_bound_premium)
"""(Basic) Carrier Bound Premium matches the expected Net Premium amount
"""

_validate_carrier_net_premium = Check(validate_carrier_net_premium)
"""(Basic) Carrier Net Premium matches expected Carrier  Net Premium amount
"""

_validate_carrier_commission_to_coalition = Check(validate_carrier_commission_to_coalition)
"""(Basic) Carrier Commission to Coalition matches expected amount
"""

_validate_limit_signatures = Check(validate_limit_signature_matches_tbp)
"""(Basic) limits match the signature of tbp
"""

_carrier_tria_zero_if_total_is_zero = Check(carrier_tria_zero_if_total_is_zero)
"""(Basic) total tria and carrier tria matches
"""

######################
# CARRIER SPECIFIC
######################

_allianz_commission_rate_matches_google_sheet = Check(allianz_commission_rate_matches_google_sheet)
"""(Allianz US) check doc under allianz_commission_rate_matches_google_sheet. Confirms commission rates
"""

_package_key_missing_on_expected_transactions = Check(package_key_missing_on_expected_transactions)
"""(Allianz US) checks for missing package keys on Allianz US reports
"""


# ==== making collections ====

#######################
# BASIC CHECKS
#######################
_basic_checks = [
    _validate_carrier_bound_premium,
    _validate_carrier_net_premium,
    _validate_carrier_commission_to_coalition,
    _carrier_tria_zero_if_total_is_zero,
    _validate_limit_signatures
    ]

#########################
# ALLIANZ SPECIFIC
#########################
_allianz_checks = [
    _allianz_commission_rate_matches_google_sheet,
    _package_key_missing_on_expected_transactions
]
_allianz_checks.extend(_basic_checks)

# ===== Validation API ====

# This can be made into a class for example
BasicBDXValidation = Validation(check=_basic_checks)
LimitValidation = Validation(check=[_validate_limit_signatures])
AllianzUsBDXValidation = Validation(
    check=_allianz_checks,
)
