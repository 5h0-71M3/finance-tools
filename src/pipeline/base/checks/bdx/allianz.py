"""For checks related specifically to Allianz"""

###########################################
# CHECKS FOR ALLIANZ US
###########################################
# SHOULD BE PROCESSED IN ALL ALLIANZ CARRIER REPORTS (GERMANY, AUS, US)

import pandas as pd


def package_key_missing_on_expected_transactions(
    transaction_description: pd.Series,
    soft_delete: pd.Series,
    external_id: pd.Series,
    package_key: pd.Series,
) -> pd.Series:
    """this check aims to check if there are package keys missing,
    usually due to custom endorsements, where the endorsement
    UUID is missing.

    :return:
    """
    package_key = package_key.fillna("missing")

    results = []
    for desc, sd, eid, pk in zip(
            transaction_description,
            soft_delete,
            external_id,
            package_key
    ):
        if pk == "missing":
            # not expected transactions
            if desc not in ("Cancellation - Flat", "Cancellation - Pro-Rated", "Endorsement"):
                results.append(True)
                continue
            # is a soft delete
            if str(sd) == "Yes":
                results.append(True)
                continue
            # checking if BE series
            last_three_char = str(eid)[-3:]
            first_two_of_last_three_char = last_three_char[:2].lower()
            if first_two_of_last_three_char == "be":
                results.append(True)
                continue
            # otherwise, it should have a Package Key
            results.append(False)
        else:
            # package key is not missing
            results.append(True)
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
    results = []
    for nsw, qld, act,  vic,  nt, sa, wa, tas, overseas, total in zip(
            australia_nsw_sd,
            australia_qld_sd,
            australia_act_sd,
            australia_vic_sd,
            australia_nt_sd,
            australia_sa_sd,
            australia_wa_sd,
            australia_tas_sd,
            australia_overseas_sd,
            stamp_duty_total,
    ):
        subtotal = sum([nsw, act, vic, nt, sa, wa, tas, overseas])

        if abs(subtotal - total) <= .02:
            results.append(True)
            continue
        results.append(False)
    return pd.Series(results)


def gwp_breakdown_matches_premium_total(
    gwp_act_premium: pd.Series,
    gwp_nsw_premium: pd.Series,
    gwp_nt_premium: pd.Series,
    gwp_overseas_premium: pd.Series,
    gwp_qld_premium: pd.Series,
    gwp_sa_premium: pd.Series,
    gwp_tas_premium: pd.Series,
    gwp_vic_premium: pd.Series,
    gwp_wa_premium: pd.Series,
    tbp: pd.Series,
) -> pd.Series:
    """confirms that the breakdown total for GWP matches the Annual Gross Written Premium

    :return:
    """
    results = []
    for nsw, qld, act, vic, nt, sa, wa, tas, overseas, premium in zip(
        gwp_nsw_premium,
        gwp_qld_premium,
        gwp_act_premium,
        gwp_vic_premium,
        gwp_nt_premium,
        gwp_sa_premium,
        gwp_wa_premium,
        gwp_tas_premium,
        gwp_overseas_premium,
        tbp
    ):
        subtotal = sum([nsw, qld, act, vic, nt, sa, wa, tas, overseas])

        if abs(subtotal - premium) <= .02:
            results.append(True)
            continue
        results.append(False)
    return pd.Series(results)


def gross_premium_amount_equals_base_gst_stamp_duty(
        gross_premium_amount: pd.Series,
        base_premium_amount: pd.Series,
        premium_gst: pd.Series,
        stamp_duty_total: pd.Series,
) -> pd.Series:
    results = []
    for base_premium, gst, stamp_duty, gross_premium in zip(
        base_premium_amount,
        premium_gst,
        stamp_duty_total,
        gross_premium_amount
    ):
        sub_total = sum((base_premium, gst, stamp_duty))
        if abs(gross_premium - sub_total) <= .02:
            results.append(True)
            continue
        results.append(False)
    return pd.Series(results)
