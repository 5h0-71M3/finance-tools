from src.pipeline.core.checks.bdx import (
    gross_premium_amount_equals_base_gst_stamp_duty,
    stamp_duty_breakdown_matches_sd_total,
    carrier_tria_zero_if_total_is_zero,
    package_key_missing_on_expected_transactions,
    earned_unearned_field_is_zero,
    transaction_id_is_nan, gwp_breakdown_matches_premium_total
)
from src.pipeline.core.checks import allianz_commission_rate_matches_google_sheet
from src.pipeline.core.checks.bdx.vantage import vantage_commission_rate_matches_google_sheet
from src.pipeline.core.checks.netsuite.carrier_details_section import (
    validate_carrier_bound_premium,
    validate_carrier_net_premium,
    validate_carrier_commission_to_coalition
)
from src.pipeline.core.checks.netsuite.coverage_details_section import validate_limit_signature_matches_tbp

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

_transaction_id_is_nan = Check(transaction_id_is_nan)
"""(Basic) Transaction ID is not a NAN value
"""

######################
# CARRIER SPECIFIC
######################

# ==== Commission Rate Checks ====
_allianz_commission_rate_matches_google_sheet = Check(allianz_commission_rate_matches_google_sheet)
"""(Allianz US) check doc under allianz_commission_rate_matches_google_sheet. Confirms commission rates
"""

_vantage_commission_rate_matches_google_sheet = Check(vantage_commission_rate_matches_google_sheet)
"""(Vantage) check doc under vantage_commission_rate_matches_google_sheet. Confirms commission rates
"""

# ==== MISC ====

_package_key_missing_on_expected_transactions = Check(package_key_missing_on_expected_transactions)
"""(Allianz US) checks for missing package keys on Allianz US reports
"""

_earned_unearned_field_is_zero = Check(earned_unearned_field_is_zero)
"""checks to make sure that these two columns are blank and empty
"""

# ==== Allianz Australia Checks ====
_gwp_breakdown_matches_premium_total = Check(gwp_breakdown_matches_premium_total)
"""confirms that the breakdown total for GWP matches the Annual Gross Written Premium
"""

_gross_premium_amount_equals_base_gst_stamp_duty = Check(gross_premium_amount_equals_base_gst_stamp_duty)
"""
"""

_stamp_duty_breakdown_matches_sd_total = Check(stamp_duty_breakdown_matches_sd_total)
"""confirms that the breakdown total for Stamp Duty matches the Total
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
    _validate_limit_signatures,
    _transaction_id_is_nan
    ]

_non_us_basic_checks = [
    _validate_carrier_bound_premium,
    _validate_carrier_net_premium,
    _validate_carrier_commission_to_coalition,
    _validate_limit_signatures,
    _transaction_id_is_nan
]

#########################
# ALLIANZ US SPECIFIC
#########################
_allianz_checks = [
    _allianz_commission_rate_matches_google_sheet,
    _package_key_missing_on_expected_transactions
]
_allianz_checks.extend(_basic_checks)

#########################
# ALLIANZ AUS SPECIFIC
#########################
_allianz_aus_checks = [
    _validate_limit_signatures,
    _gwp_breakdown_matches_premium_total,
    _gross_premium_amount_equals_base_gst_stamp_duty,
    _stamp_duty_breakdown_matches_sd_total
]

#########################
# ALLIANZ Germany SPECIFIC
#########################
_allianz_de_checks = [
    _allianz_commission_rate_matches_google_sheet,
]
_allianz_de_checks.extend(_non_us_basic_checks)

#########################
# ALLIANZ UK SPECIFIC
#########################
_allianz_uk_checks = [
    _allianz_commission_rate_matches_google_sheet,
    _earned_unearned_field_is_zero
]
_allianz_uk_checks.extend(_non_us_basic_checks)

###########################
# ASCOT SPECIFIC
###########################
_ascot_checks = [
    _earned_unearned_field_is_zero
]
_ascot_checks.extend(_basic_checks)

##################################
# LLOYDS NON US SPECIFIC
##################################
_lloyds_non_us_checks = [
    _earned_unearned_field_is_zero
]
_lloyds_non_us_checks.extend(_non_us_basic_checks)


###################################
# VANTAGE SPECIFIC
###################################
_vantage_checks = [
    _earned_unearned_field_is_zero,
    _vantage_commission_rate_matches_google_sheet,
]
_vantage_checks.extend(_basic_checks)


#####################################
# ***********************************
# PUBLIC API BELOW
# ***********************************
#####################################


######################################
# VALIDATION API
######################################
# ===== Validation API ====

# This can be made into a class for example
BasicBDXValidation = Validation(check=_basic_checks)
LimitValidation = Validation(check=[_validate_limit_signatures])

# ==== Carriers ====
AllianzAusValidation = Validation(check=_allianz_aus_checks)

AllianzDEValidation = Validation(check=_allianz_de_checks)

AllianzUKValidation = Validation(check=_allianz_uk_checks)

AllianzUsBDXValidation = Validation(
    check=_allianz_checks,
)

AscotBDXValidation = Validation(
    check=_ascot_checks
)

LloydsCanada2023BDXValidation = Validation(
    check=_lloyds_non_us_checks,
)

LloydsCanada2024BDXValidation = Validation(
    check=_lloyds_non_us_checks,
)

LloydsUK2023BDXValidation = Validation(
    check=_lloyds_non_us_checks,
)

LloydsUK2024BDXValidation = Validation(
    check=_lloyds_non_us_checks,
)

VantageBDXValidation = Validation(
    check=_vantage_checks,
)
