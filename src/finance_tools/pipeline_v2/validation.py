from dirlin.dq.pipelines import Pipeline

from finance_tools.io.directory_handler import FOLDERS
from finance_tools.bar import (
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
    allianz_commission_rate_matches_google_sheet,
    fortegra_commission_rate_matches_google_sheet,
    fortegra_v2_columns_are_blank,
    surplus_3_0_filled,
    lloyds_uk_canada_commission_rate_matches_google_sheet,
    lloyds_er_coverage_premium_matches_total,
    lloyds_er_commission_rate_matches_google_sheet, chaucer_commission_rate_matches_google_sheet
)


# GLOBAL
f = FOLDERS()


# class DailyValidation(Pipeline):
#     """Validations to be run on Netsuite data to ensure data quality."""
#
#     # The checks we want to run
#     _find_term_extension_transaction = find_term_extension_transaction
#
#     alias_mapping = {
#         "transaction_date": "Transaction Effective Date",
#         "expiration_date": "Policy Expiration Date"
#     }


##############################
# BDX LEVEL VALIDATION
##############################
class SmallCarrierPipeline(Pipeline):
    """Validations for Ascot, Chaucer, Hartford, HDI"""
    # Checks
    _validate_carrier_bound_premium = validate_carrier_bound_premium
    _validate_carrier_net_premium = validate_carrier_net_premium
    _validate_carrier_commission_to_coalition = validate_carrier_commission_to_coalition
    _validate_limit_signature_matches_tbp = validate_limit_signature_matches_tbp
    _transaction_id_is_nan = transaction_id_is_nan
    _carrier_tria_zero_if_total_zero = carrier_tria_zero_if_total_is_zero
    _earned_unearned_field_is_zero = earned_unearned_field_is_zero
    _surplus_3_0_filled = surplus_3_0_filled
    _chaucer_commission_rate_matches_google_sheet = chaucer_commission_rate_matches_google_sheet

    # Aliases
    alias_mapping = {
        "policy_effective_date": "Policy Effective Date",
        "coalition_percent_commission": "Coalition Commission %",
        "soft_delete": "Soft Delete",
        "total_tria": "Total TRIA",
        "total_earned_premium": "Total Earned Premium",
        "total_unearned_premium": "Total Unearned Premium",
        "tbp": [
            "Total Bound Premium",
            "Total Gross Written Premium (GWP)"
        ],
        "carrier_percent_commission": "Coalition Commission %",
        "base_limit": "Aggregate Total Limit",
        'external_id': [
            'External ID',
            "Transaction ID",
        ],
        "surplus_3_0": "Surplus 3.0",
        "carrier_bound_premium": [
            "Gross Premium - Ascot",
            "HDI Bound Premium",
            "Hartford Bound Premium",
            "Chaucer Bound Premium"
        ],
        "carrier_net_premium": [
            "Ascot Net Premium",
            "HDI Net Premium",
            "Hartford Net Premium",
            "Chaucer Net Premium"
        ],
        "carrier_quota_share": [
            "Ascot Quota Share %",
            "HDI Quota Share %",
            "Hartford Quota Share %",
            "Chaucer %"
        ],
        "carrier_commission_to_coalition": [
            "Ascot $ Commission To Coalition",
            "HDI $ Commission to Coalition",
            "Hartford Commission to Coalition"
        ],
    }

    # Reports
    ascot = f.get_ascot()
    hartford_df = f.get_hartford_bdx()
    hdi_df = f.get_hdi_bdx()


class FortegraPipeline(Pipeline):
    """Validations for the Fortegra BDX Report"""
    # The checks we want to run
    _validate_carrier_bound_premium = validate_carrier_bound_premium
    _validate_carrier_net_premium = validate_carrier_net_premium
    _validate_carrier_commission_to_coalition = validate_carrier_commission_to_coalition
    _validate_limit_signature_matches_tbp = validate_limit_signature_matches_tbp
    _transaction_id_is_nan = transaction_id_is_nan
    _carrier_tria_zero_if_total_zero = carrier_tria_zero_if_total_is_zero
    _earned_unearned_field_is_zero = earned_unearned_field_is_zero

    # Fortegra Specific
    _fortegra_commission_rate_matches_google_sheet = fortegra_commission_rate_matches_google_sheet
    _fortegra_v2_columns_are_blank = fortegra_v2_columns_are_blank

    # Report
    fortegra_df = f.get_fortegra_bdx()

    # Aliases
    alias_mapping = {
        "carrier_bound_premium": "Fortegra Bound Premium",
        "carrier_net_premium": "Fortegra Net Premium",
        "carrier_quota_share": "Fortegra %",
        "carrier_commission_to_coalition": "Coalition Commission $",
        'carrier_bound_less_tria': "Fortegra Bound Premium Less TRIA",
        'carrier_bound_cyber_less_tria': 'Fortegra Bound Cyber Premium Less TRIA',
        'carrier_net_cyber': 'Fortegra Net Cyber Premium',
        "surplus_3_0": "Surplus 3.0",
        'coalition_percent_commission': 'Coalition Commission%',
        'carrier_percent_commission': 'Coalition Commission%',
        'base_limit': 'Total Limit',
        "external_id": "Transaction ID",
    }


class BasicValidation(Pipeline):
    """Validations that apply to all BDX files at some level or form. Is not specific
    to a carrier.

    Checks:
        - validate_carrier_bound_premium
        - validate_carrier_net_premium
        - validate_carrier_commission_to_coalition
        - validate_limit_signature_matches_tbp
        - transaction_id_is_nan
        - carrier_tria_zero_if_total_is_zero
        - earned_unearned_field_is_zero
        - allianz_commission_rate_matches_google_sheet
        - fortegra_commission_rate_matches_google_sheet
        - fortegra_v2_columns_are_blank
        - lloyds_uk_canada_commission_rate_matches_google_sheet
        - lloyds_er_coverage_premium_matches_total
        - lloyds_er_commission_rate_matches_google_sheet
        - surplus_3_0_filled

    BDXs:
        - allianz_us
        - allianz_uk_primary
        - allianz_uk_excess
        - allianz_aus
        - allianz_aus_as_uk
        - allianz_germany
        - allianz_denmark
        - ascot
        - chaucer_df
        - fortegra_df
        - hartford_df
        - hdi_df
        - lloyds_can_2023
        - lloyds_can_2024
        - lloyds_can_2025
        - lloyds_uk_2023
        - lloyds_uk_2024
        - lloyds_uk_2025
        - lloyds_er_renre
        - lloyds_er_syndicates
        - lloyds_us
        - msig_df
        - sre_surplus
        - sre_admitted
        - sre_cad
        - sre_usd
        - vantage_df
    """

    # The checks we want to run
    _validate_carrier_bound_premium = validate_carrier_bound_premium
    _validate_carrier_net_premium = validate_carrier_net_premium
    _validate_carrier_commission_to_coalition = validate_carrier_commission_to_coalition
    _validate_limit_signature_matches_tbp = validate_limit_signature_matches_tbp
    _transaction_id_is_nan = transaction_id_is_nan
    _carrier_tria_zero_if_total_zero = carrier_tria_zero_if_total_is_zero
    _earned_unearned_field_is_zero = earned_unearned_field_is_zero

    # carrier specific checks
    _allianz_commission_rate_matches_google_sheet = allianz_commission_rate_matches_google_sheet
    _fortegra_commission_rate_matches_google_sheet = fortegra_commission_rate_matches_google_sheet
    _fortegra_v2_columns_are_blank = fortegra_v2_columns_are_blank
    _lloyds_uk_canada_commission_rate_matches_google_sheet = lloyds_uk_canada_commission_rate_matches_google_sheet
    _lloyds_er_coverage_premium_matches_total = lloyds_er_coverage_premium_matches_total
    _lloyds_er_commission_rate_matches_google_sheet = lloyds_er_commission_rate_matches_google_sheet
    _surplus_3_0_filled = surplus_3_0_filled

    # BDXs we want to run
    vantage_df = f.get_vantage_bdx()

    # Day 5
    allianz_us = f.get_allianz_us()
    allianz_uk_primary = f.get_allianz_uk(version="primary")
    allianz_uk_excess = f.get_allianz_uk(version="excess")
    allianz_aus = f.get_allianz_aus(version="aus")
    allianz_aus_as_uk = f.get_allianz_aus(version="uk")
    allianz_germany = f.get_allianz_germany()
    allianz_denmark = f.get_allianz_denmark()
    ascot = f.get_ascot()
    lloyds_can_2024 = f.get_lloyds_canada(version="2024")
    lloyds_can_2025 = f.get_lloyds_canada(version="2025")
    lloyds_uk_2024 = f.get_lloyds_uk(version="2024")
    lloyds_uk_2025 = f.get_lloyds_uk(version="2025")
    try:
        lloyds_can_2023 = f.get_lloyds_canada(version="2023")
    except FileNotFoundError as FNF:
        print(f"Lloyds Canada 2023: {FNF}")

    try:
        lloyds_uk_2023 = f.get_lloyds_uk(version="2023")
    except FileNotFoundError as FNF:
        print(f"Lloyds UK 2023: {FNF}")

    # Day 10
    msig_df = f.get_msig_bdx()
    chaucer_df = f.get_chaucer_bdx()
    fortegra_df = f.get_fortegra_bdx()
    hartford_df = f.get_hartford_bdx()
    hdi_df = f.get_hdi_bdx()
    # Aspen, Zurich,

    # Day 15
    try:
        lloyds_er_renre = f.get_lloyds_er(version="renre")
        lloyds_er_syndicates = f.get_lloyds_er(version="syndicates")
    except FileNotFoundError as FNF:
        print(f"Lloyds ER: {FNF}")
    except ValueError as VE:
        print(f"Lloyds ER: {VE}")

    try:
        lloyds_us = f.get_lloyds_us_bdx()
    except FileNotFoundError as FNF:
        print(f"Lloyds US: {FNF}")
    except ValueError as VE:
        print(f"Lloyds US: {VE}")

    try:
        sre_surplus = f.get_sre_bdx("surplus")
    except FileNotFoundError as FNF:
        print(f"SRE Surplus: {FNF}")
    except ValueError as VE:
        print(f"SRE Surplus: {VE}")

    try:
        sre_admitted = f.get_sre_bdx("admitted")
    except FileNotFoundError as FNF:
        print(f"SRE Admitted: {FNF}")
    except ValueError as VE:
        print(f"SRE Admitted: {VE}")

    try:
        sre_cad = f.get_sre_bdx("cad")
    except FileNotFoundError as FNF:
        print(f"SRE CAD: {FNF}")
    except ValueError as VE:
        print(f"SRE CAD: {VE}")

    try:
        sre_usd = f.get_sre_bdx("usd")
    except FileNotFoundError as FNF:
        print(f"SRE USD: {FNF}")
    except ValueError as VE:
        print(f"SRE USD: {VE}")

    # the alias mapping, tying param to columns
    alias_mapping = {
        "tbp": [
            "Total Bound Premium",
            "Annual Gross Written Premium",
            "Total Gross Written Premium (GWP)"
        ],
        "carrier_percent_commission": "Coalition Commission %",
        "coalition_percent_commission": [
            "Coalition Commission %",
            "Coalition Commission%"
        ],
        "policy_effective_date": [
            "Policy Effective Date",
            "Risk Inception Date"
        ],
        "soft_delete": "Soft Delete",
        "total_tria": "Total Tria",
        "total_earned_premium": "Total Earned Premium",
        "total_unearned_premium": "Total Unearned Premium",
        "base_limit": [
            "Aggregate Total Limit",
            'Total Limit'
        ],
        'external_id': [
            'External ID',
            "Transaction ID",
        ],
        'transaction_description': 'Transaction Description',
        'package_key': 'Package Keys',
        "surplus_3_0": "Surplus 3.0",
        # carrier specific section
        "carrier_tria": [
            "Allianz TRIA",
            "SwissRe TRIA Premium",
            "Vantage TRIA"
        ],
        "carrier_bound_premium": [
            "Allianz Bound Premium",
            "Chaucer Bound Premium",
            "Fortegra Bound Premium",
            "Bound Premium",
            "Swiss Re Bound Premium",
            "Vantage Bound Premium"
        ],
        "carrier_net_premium": [
            "Allianz Net Premium",
            "Chaucer Net Premium",
            "Fortegra Net Premium",
            "Net Premium to London in USD (GWP",
            "Swiss Re Net Premium",
            "Vantage Net Premium"
        ],
        "carrier_quota_share": [
            "Allianz Quota Share %",
            "Chaucer %",
            "Fortegra %",
            "Lloyds Quota Share %",
            "Swiss Re %",
            "Vantage Quota Share %"
        ],
        "carrier_commission_to_coalition": [
            "Allianz $ Commission To Coalition",
            "Allianz Commission to Coalition",
            "Coalition Commission $",
            "Lloyds Commission to Coalition",
            "Swiss Re Commission Paid",
            "Vantage $ Commission To Coalition"
        ],
        'carrier_bound_less_tria': "Fortegra Bound Premium Less TRIA",
        'carrier_bound_cyber_less_tria': 'Fortegra Bound Cyber Premium Less TRIA',
        'carrier_net_cyber': 'Fortegra Net Cyber Premium',
        "broker_commission": "Brokerage % of Gross Premium",
        'do_premium': "D and O Premium",
        'epl_premium': "Epl Premium",
        'fiduciary_premium': "Fiduciary Premium",
        'crime_premium': "Crime Premium",
        'gwp_written_through_lloyds': "$ GWP written through Lloyd's quota share"
    }


##############################
# Australia BDX
##############################
class AustraliaPipeline(BasicValidation):
    """Validation for Allianz AUS and MSIG Australian BDX reports"""

    # Australia specific checks
    _gwp_breakdown_matches_premium_total = gwp_breakdown_matches_premium_total
    _gross_premium_amount_equals_base_gst_stamp_duty = gross_premium_amount_equals_base_gst_stamp_duty
    _stamp_duty_breakdown_matches_sd_total = stamp_duty_breakdown_matches_sd_total

    # alias_mapping
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

    # Reports we want to use
    msig_df = f.get_msig_bdx()
    allianz_aus = f.get_allianz_aus(version="aus")
