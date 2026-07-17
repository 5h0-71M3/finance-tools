"""Validation functions for the Allianz AUS report (Day 5 BDX), ported for pipeui.

Mirrors the legacy ``AustraliaValidation`` in
``finance_tools.pipeline_v2.validations.carriers``. AustraliaValidation inherits
directly from BaseValidation, so it runs ONLY these three breakdown checks (it does
NOT inherit the BasicValidation carrier-premium checks).

All three are column-shaped validations (``-> pd.Series[bool]``).

Column bindings (function param -> report column), from the legacy alias map:
  gwp_act_premium       -> "GWP ACT Premium"
  gwp_nsw_premium       -> "GWP NSW Premium"
  gwp_nt_premium        -> "GWP NT Premium"
  gwp_overseas_premium  -> "GWP Overseas Premium"
  gwp_qld_premium       -> "GWP QLD Premium"
  gwp_sa_premium        -> "GWP SA Premium"
  gwp_tas_premium       -> "GWP TAS Premium"
  gwp_vic_premium       -> "GWP VIC Premium"
  gwp_wa_premium        -> "GWP WA Premium"
  gross_premium_amount  -> "Gross Premium Amount"
  base_premium_amount   -> "Base Premium Amount"
  premium_gst           -> "Premium GST"
  stamp_duty_total      -> "Stamp Duty Total"
  australia_nsw_sd      -> "Australia NSW SD"
  australia_qld_sd      -> "Australia QLD SD"
  australia_act_sd      -> "Australia ACT SD"
  australia_vic_sd      -> "Australia VIC SD"
  australia_nt_sd       -> "Australia NT SD"
  australia_sa_sd       -> "Australia SA SD"
  australia_wa_sd       -> "Australia WA SD"
  australia_tas_sd      -> "Australia TAS SD"
  australia_overseas_sd -> "Australia Overseas SD"
  tbp                   -> "Annual Gross Written Premium"
"""
import pandas as pd


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
) -> pd.Series[bool]:
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

        if abs(subtotal - premium) <= .03:
            results.append(True)
            continue
        results.append(False)
    return pd.Series(results)


def gross_premium_amount_equals_base_gst_stamp_duty(
        gross_premium_amount: pd.Series,
        base_premium_amount: pd.Series,
        premium_gst: pd.Series,
        stamp_duty_total: pd.Series,
) -> pd.Series[bool]:
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
) -> pd.Series[bool]:
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

        if abs(subtotal - total) <= .03:
            results.append(True)
            continue
        results.append(False)
    return pd.Series(results)
