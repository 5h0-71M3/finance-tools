from dirlin.validation import BaseValidation

from finance_tools.bar.core.checks import (
    validate_carrier_bound_premium,
    validate_carrier_net_premium,
    validate_carrier_commission_to_coalition,
    validate_limit_signature_matches_tbp,
    transaction_id_is_nan,
    carrier_tria_zero_if_total_is_zero,
    earned_unearned_field_is_zero,
    gwp_breakdown_matches_premium_total,
    gross_premium_amount_equals_base_gst_stamp_duty,
    stamp_duty_breakdown_matches_sd_total,
    package_key_missing_on_expected_transactions,
    vantage_commission_rate_matches_google_sheet,
    allianz_commission_rate_matches_google_sheet,
    fortegra_commission_rate_matches_google_sheet,
    surplus_3_0_filled,
    fortegra_v2_columns_are_blank,
    lloyds_er_coverage_premium_matches_total,
    lloyds_er_commission_rate_matches_google_sheet,
    lloyds_uk_canada_commission_rate_matches_google_sheet
)

##############################
# HIGH LEVEL BASE VALIDATION
##############################
class BasicValidation(BaseValidation):
    """Basic Validation to be run on non-US entities

    This is mostly on a record level, and does not complete validations with
    Policy Stacks
    """
    _validate_carrier_bound_premium = validate_carrier_bound_premium
    _validate_carrier_net_premium = validate_carrier_net_premium
    _validate_carrier_commission_to_coalition = validate_carrier_commission_to_coalition
    _validate_limit_signature_matches_tbp = validate_limit_signature_matches_tbp
    _transaction_id_is_nan = transaction_id_is_nan

    alias_mapping = {
        "policy_effective_date": ["Policy Effective Date",],
        "coalition_percent_commission": ["Coalition Commission %",],
        "soft_delete": ["Soft Delete"],
        "total_tria": ["Total TRIA",],
        "total_earned_premium": ["Total Earned Premium",],
        "total_unearned_premium": ["Total Unearned Premium",],
        "tbp": ["Total Bound Premium",],
        "carrier_percent_commission": ["Coalition Commission %",],
        "base_limit": "Aggregate Total Limit",
        'external_id': 'External ID',
        "carrier_bound_premium": [
            "Gross Premium - Ascot",
            "HDI Bound Premium",
            "Hartford Bound Premium"
        ],
        "carrier_net_premium": [
            "Ascot Net Premium",
            "HDI Net Premium",
            "Hartford Net Premium"
        ],
        "carrier_quota_share": [
            "Ascot Quota Share %",
            "HDI Quota Share %",
            "Hartford Quota Share %"
        ],
        "carrier_commission_to_coalition": [
            "Ascot $ Commission To Coalition",
            "HDI $ Commission to Coalition",
            "Hartford Commission to Coalition"
        ],
    }


class AustraliaValidation(BaseValidation):
    """Validation for Allianz AUS and MSIG Australian BDX reports"""
    _gwp_breakdown_matches_premium_total = gwp_breakdown_matches_premium_total
    _gross_premium_amount_equals_base_gst_stamp_duty = gross_premium_amount_equals_base_gst_stamp_duty
    _stamp_duty_breakdown_matches_sd_total = stamp_duty_breakdown_matches_sd_total

    alias_mapping = {
        'gwp_act_premium': "GWP ACT Premium",
        'gwp_nsw_premium': "GWP NSW Premium",
        'gwp_nt_premium': "GWP NT Premium",
        'gwp_overseas_premium': "GWP Overseas Premium",
        'gwp_qld_premium': "GWP QLD Premium",
        'gwp_sa_premium': "GWP SA Premium",
        'gwp_tas_premium': "GWP TAS Premium",
        'gwp_vic_premium': "GWP VIC Premium",
        'gwp_wa_premium': "GWP WA Premium",
        'gross_premium_amount': "Gross Premium Amount",
        'base_premium_amount': "Base Premium Amount",
        'premium_gst': "Premium GST",
        'stamp_duty_total': "Stamp Duty Total",
        'australia_nsw_sd': "Australia NSW SD",
        'australia_qld_sd': "Australia QLD SD",
        'australia_act_sd': "Australia ACT SD",
        'australia_vic_sd': "Australia VIC SD",
        'australia_nt_sd': "Australia NT SD",
        'australia_sa_sd': "Australia SA SD",
        'australia_wa_sd': "Australia WA SD",
        'australia_tas_sd': "Australia TAS SD",
        'australia_overseas_sd': "Australia Overseas SD",
        'tbp': "Annual Gross Written Premium",
    }


# ==== Ascot, Chaucer ====
class BasicValidationUS(BasicValidation):
    """Basic Validation to be run on US entities

    Should work for:
        - Ascot US
    """
    _carrier_tria_zero_if_total_zero = carrier_tria_zero_if_total_is_zero
    _earned_unearned_field_is_zero = earned_unearned_field_is_zero
    alias_mapping = {
        "carrier_tria": ["Gross TRIA - Ascot", "Chaucer TRIA"],
    }


##############################
# CARRIER SPECIFIC VALIDATIONS
##############################

##############################
# ASPEN VALIDATIONS
##############################
# final_dataset["Aggregate Total Limit Balance"] = final_dataset["Aggregate Total Limit Balance"] * final_dataset["Aspen Quota Share"]
# final_dataset["Limit Variance"] = final_dataset["Aggregate Total Limit Balance"] - final_dataset[self.limits_without_sir].max(axis=1)  # Emily Check (max coverage - agg balance)
# final_dataset["Check - Balance to Calculated Agg Diff"] = final_dataset["Aggregate Total Limit"] - final_dataset["Aggregate Total Limit Balance"]  # calculated agg - NS agg
# final_dataset["Check - Negative Limits"] = final_dataset[self.limits_only_columns].min(axis=1)
# bdx["Limit Variance"] = [sir_backup[iid]["Limit Variance"] for iid in bdx["Internal ID"]]
# bdx["Check - Balance to Calculated Agg Diff"] = [sir_backup[iid]["Check - Balance to Calculated Agg Diff"] for iid in bdx["Internal ID"]]
# bdx["Check - Negative Limits"] = [sir_backup[iid]["Check - Negative Limits"] for iid in bdx["Internal ID"]]
# # todo now at this point we just need to be able to apply this new mapping to the existing BDX
# # bdx.to_csv(f"/Users/shomendoza/Downloads/Aspen - Sample - {date.today()} - v5 .csv")
# bdx.insert(0, "Check - Negative Limits", bdx.pop("Check - Negative Limits"))
# bdx.insert(0, "Check - Balance to Calculated Agg Diff", bdx.pop("Check - Balance to Calculated Agg Diff"))
# bdx.insert(0, "Limit Variance", bdx.pop("Limit Variance"))


#############################
# ALLIANZ VALIDATIONS
#############################
# Used for carriers with specific checks not applied anywhere else
class AllianzBasicValidation(BasicValidation):
    """Should work for all International Allianz entities except for Australia, which has their
    own set of core validations. Allianz US has its own class, but should work for
    Germany, UK, Nordics

    """
    _allianz_commission_rate_matches_google_sheet = allianz_commission_rate_matches_google_sheet
    alias_mapping = {
        "carrier_tria": "Allianz TRIA",
        "carrier_bound_premium": "Allianz Bound Premium",
        "carrier_net_premium": "Allianz Net Premium",
        "carrier_quota_share": "Allianz Quota Share %",
    }


class AllianzUSValidation(AllianzBasicValidation):
    """Validation for Allianz US reports"""
    _package_key_missing_on_expected_transactions = package_key_missing_on_expected_transactions
    _surplus_3_0_filled = surplus_3_0_filled

    alias_mapping = {
        'transaction_description': 'Transaction Description',
        'package_key': 'Package Keys',
        "carrier_commission_to_coalition": "Allianz $ Commission To Coalition",
        "surplus_3_0": "Surplus 3.0"
    }


class AllianzUKValidation(BasicValidation):
    """Validation for Allianz UK reports"""
    _allianz_commission_rate_matches_google_sheet = allianz_commission_rate_matches_google_sheet

    alias_mapping = {
        "carrier_bound_premium": "Allianz Bound Premium",
        "carrier_net_premium": "Allianz Net Premium",
        "carrier_quota_share": "Allianz Quota Share %",
        "carrier_commission_to_coalition": "Allianz Commission to Coalition"
    }


##########################
# CHAUCER US Validations
##########################
class ChaucerValidation(BaseValidation):
    """Validation for Chaucer reports"""
    _surplus_3_0_filled = surplus_3_0_filled
    # Chaucer is missing a column we need for this Google Sheet calculation
    # _chaucer_commission_rate_matches_google_sheet = chaucer_commission_rate_matches_google_sheet
    _validate_carrier_bound_premium = validate_carrier_bound_premium
    _validate_limit_signature_matches_tbp = validate_limit_signature_matches_tbp
    _transaction_id_is_nan = transaction_id_is_nan

    alias_mapping = {
        "carrier_bound_premium": "Chaucer Bound Premium",
        "carrier_net_premium": "Chaucer Net Premium",
        "carrier_quota_share": "Chaucer %",
        "surplus_3_0": "Surplus 3.0",
        "coalition_percent_commission": ["Coalition Commission %", ],
        "tbp": ["Total Gross Written Premium (GWP)", ],
        "base_limit": "Aggregate Total Limit",
        'external_id': 'Transaction ID',
        'policy_effective_date': 'Policy Effective Date',
    }


#############################
# Fortegra VALIDATIONS
#############################
class FortegraValidation(BasicValidation):
    """Validation for Fortegra reports"""
    _fortegra_commission_rate_matches_google_sheet = fortegra_commission_rate_matches_google_sheet
    _fortegra_v2_columns_are_blank = fortegra_v2_columns_are_blank
    _surplus_3_0_filled = surplus_3_0_filled

    alias_mapping = {
        "carrier_bound_premium": "Fortegra Bound Premium",
        "carrier_net_premium": "Fortegra Net Premium",
        "carrier_quota_share": "Fortegra %",
        "carrier_commission_to_coalition": "Coalition Commission $",
        "surplus_3_0": "Surplus 3.0",
        'carrier_bound_less_tria': "Fortegra Bound Premium Less TRIA",
        'carrier_bound_cyber_less_tria': 'Fortegra Bound Cyber Premium Less TRIA',
        'carrier_net_cyber': 'Fortegra Net Cyber Premium',
        'coalition_percent_commission': 'Coalition Commission%',
        'carrier_percent_commission': 'Coalition Commission%',
        'base_limit': 'Total Limit',
        "external_id": "Transaction ID",
    }


#############################
# Lloyds VALIDATIONS
#############################
class LloydsValidation(BasicValidation):
    _lloyds_uk_canada_commission_rate_matches_google_sheet = lloyds_uk_canada_commission_rate_matches_google_sheet
    _earned_unearned_field_is_zero = earned_unearned_field_is_zero

    """Validation for Lloyds reports"""
    alias_mapping = {
        "carrier_bound_premium": "Bound Premium",
        "carrier_net_premium": "Net Premium to London in USD (GWP",
        "carrier_quota_share": "Lloyds Quota Share %",
        "carrier_commission_to_coalition": "Lloyds Commission to Coalition",
    }


class LloydsUnitedStatesValidation(BasicValidation):
    """Validation for Lloyds US reports"""
    alias_mapping = {
        "carrier_bound_premium": "$ GWP written through Lloyd's quota share",
        "carrier_quota_share": "% GWP written through Lloyd's quota share",
        "carrier_commission_to_coalition": "Coverholder Commission Amount",
        "carrier_net_premium": "Net Premium to London in USD (GWP less Coverholder Commission)",
        "carrier_percent_commission": "Coverholder Commission %",
        "coalition_percent_commission": "Coverholder Commission %",
        "tbp": "Total Gross Written Premium (GWP)",
        "base_limit": "Sum Insured Amount (Aggregate Total Limit)",
        "external_id": "Coalition Transaction ID"
    }


class LloydsExecutiveRiskValidation(LloydsUnitedStatesValidation):
    _lloyds_er_coverage_premium_matches_total = lloyds_er_coverage_premium_matches_total
    _lloyds_er_commission_rate_matches_google_sheet = lloyds_er_commission_rate_matches_google_sheet
    alias_mapping = {
        "broker_commission": "Brokerage % of Gross Premium",
        'do_premium': "D and O Premium",
        'epl_premium': "Epl Premium",
        'fiduciary_premium': "Fiduciary Premium",
        'crime_premium': "Crime Premium",
        'gwp_written_through_lloyds': "$ GWP written through Lloyd's quota share",
        "policy_effective_date": "Risk Inception Date",
    }


#############################
# SwissRe VALIDATIONS
#############################
class SwissReValidation(BasicValidationUS):
    """Validation for SwissRe reports"""

    alias_mapping = {
        "carrier_bound_premium": "Swiss Re Bound Premium",
        "carrier_net_premium": "Swiss Re Net Premium",
        "carrier_quota_share": "Swiss Re %",
        "carrier_commission_to_coalition": "Swiss Re Commission Paid",
        "external_id": "Transaction ID",
        "carrier_tria": "SwissRe TRIA Premium"
    }


#############################
# VANTAGE VALIDATIONS
#############################
class VantageValidation(BasicValidationUS):
    """Validation for Vantage reports"""
    _vantage_commission_rate_matches_google_sheet = vantage_commission_rate_matches_google_sheet
    _surplus_3_0_filled = surplus_3_0_filled
    alias_mapping = {
        "carrier_tria": "Vantage TRIA",
        "surplus_3_0": "Surplus 3.0",
        "carrier_bound_premium": "Vantage Bound Premium",
        "carrier_net_premium": "Vantage Net Premium",
        "carrier_quota_share": "Vantage Quota Share %",
        "carrier_commission_to_coalition": "Vantage $ Commission To Coalition"
    }
