###########################################
# CHECKS FOR ALLIANZ US
###########################################
# SHOULD BE PROCESSED IN ALL ALLIANZ CARRIER REPORTS (GERMANY, AUS, US)
import datetime

import pandas as pd


def package_key_missing_on_expected_transactions(
    transaction_description: pd.Series,
    soft_delete: pd.Series,
    external_id: pd.Series,
    package_key: pd.Series,
):
    """this check aims to check if there are package keys missing,
    usually due to custom endorsements, where the endorsement
    UUID is missing.

    :return:
    """
    results = []
    for desc, sd, eid, pk in zip(
            transaction_description,
            soft_delete,
            external_id,
            package_key
    ):
        if not str(pk).isalpha() or str(pk) == "":
            # not expected transactions
            if desc not in ("Cancellation - Flat", "Cancellation - Pro-Rated", "Endorsement"):
                results.append(True)
                continue
            # is a soft delete
            if str(sd) == "Yes":
                results.append(True)
                continue
            # checking if BE series
            last_three_char = str(eid)[-3]
            first_two_of_last_three_char = last_three_char[:2].lower()
            if first_two_of_last_three_char == "be":
                results.append(True)
                continue
            # otherwise, it should have a Package Key
            results.append(False)
    return pd.Series(results)


###########################################
# CHECKS FOR ALLIANZ AUSTRALIA
###########################################
def stamp_duty_breakdown_matches_sd_total(
    australia_nsw_sd: pd.Series,
    australia_qld_sd: pd.Series,
    australia_act_sd: pd.Series,
    australia_vic_sd: pd.Series,
    australia_nt_sd: pd.Series,
    australia_sa_sd: pd.Series,
    australia_wa_sd: pd.Series,
    australia_tas_sd: pd.Series,
    australia_overseas_sd: pd.Series,
    stamp_duty_total: pd.Series,
) -> pd.Series:
    """confirms that the breakdown total for Stamp Duty matches the Total

    :return:
    """
    breakdown_total = sum(
        (
            australia_nsw_sd,
            australia_qld_sd,australia_act_sd,
            australia_vic_sd,
            australia_nt_sd,
            australia_sa_sd,
            australia_wa_sd,
            australia_tas_sd,
            australia_overseas_sd
        )
    )
    results = breakdown_total == stamp_duty_total
    return pd.Series(results)


def gwp_breakdown_matches_sd_total(
    gwp_nsw_premium: pd.Series,
    gwp_qld_premium: pd.Series,
    gwp_act_premium: pd.Series,
    gwp_vic_premium: pd.Series,
    gwp_nt_premium: pd.Series,
    gwp_sa_premium: pd.Series,
    gwp_wa_premium: pd.Series,
    gwp_tas_premium: pd.Series,
    gwp_overseas_premium: pd.Series,
    stamp_duty_total: pd.Series,
) -> pd.Series:
    """confirms that the breakdown total for GWP matches the Total

    :return:
    """
    breakdown_total = sum(
        (
            gwp_nsw_premium,
            gwp_qld_premium,
            gwp_act_premium,
            gwp_vic_premium,
            gwp_nt_premium,
            gwp_sa_premium,
            gwp_wa_premium,
            gwp_tas_premium,
            gwp_overseas_premium
        )
    )
    results = breakdown_total == stamp_duty_total
    return pd.Series(results)


def gross_premium_amount_equals_base_gst_stamp_duty(
        gross_premium_amount: pd.Series,
        base_premium_amount: pd.Series,
        premium_gst: pd.Series,
        stamp_duty_total: pd.Series,
) -> pd.Series:
    sub_total = sum((base_premium_amount, premium_gst, stamp_duty_total))
    results = gross_premium_amount == sub_total
    return pd.Series(results)


def allianz_commission_rate_matches_google_sheet(
    policy_effective_date: pd.Series,
    coalition_percent_commission: pd.Series,
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

    Carrier	Entity	Coalition Comm Rate	Effective
    Allianz US	US	30.00%				Before 10/31/24
    Allianz US	US	31.00%			    After 11/1/24

    :return: pass / fail
    """
    f = policy_effective_date.copy()
    policy_effective_date = pd.to_datetime(policy_effective_date)
    # before_date = datetime.datetime(2024, 10, 31)
    after_date = datetime.datetime(2024, 11, 1)

    results = []
    for d, commission in zip(policy_effective_date, coalition_percent_commission):
        if d >= after_date:
            if commission != .31:
                results.append(False)
                continue
            results.append(True)
        else:
            if commission != .30:
                results.append(False)
                continue
            results.append(True)
    return pd.Series(results)
