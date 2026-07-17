"""Reusable, cross-carrier validation functions ported for pipeui.

Defined ONCE here and reused across carriers (pipeui collapses identical functions
by content hash anyway; bind each source's columns at attach time via the alias map).

Contains only checks NOT already provided by ``vantage/validations.py``:
  - ``validate_carrier_bound_premium`` — the generic SCALAR form (Vantage's copy is a
    DataFrame-shaped variant hardcoded to Vantage columns; this one binds columns via
    the alias map, so every carrier can reuse it).
  - ``allianz_commission_rate_matches_google_sheet`` — Allianz US/UK/Germany/Denmark.
  - ``lloyds_uk_canada_commission_rate_matches_google_sheet`` — Lloyds Canada/UK.

The base checks (``validate_carrier_net_premium``, ``validate_carrier_commission_to_coalition``,
``validate_limit_signature_matches_tbp``, ``transaction_id_is_nan``,
``carrier_tria_zero_if_total_is_zero``, ``earned_unearned_field_is_zero``,
``surplus_3_0_filled``) are reused from ``vantage/validations.py`` — not redefined here.

Return annotations drive pipeui classification: ``-> bool`` = row-by-row (scalar);
``-> pd.Series[bool]`` = column-shaped.
"""
import datetime

import numpy as np
import pandas as pd


def validate_carrier_bound_premium(
        tbp: float,
        carrier_bound_premium: float,
        carrier_quota_share: float,
) -> bool:
    """Expected formula for Carrier Bound Premium => TBP x Quota Share.

    :return: pass / fail
    """
    option_variance_cap: float = .02
    try:
        expected_carrier_bound_premium = round(tbp * carrier_quota_share, 2)
    except TypeError as te:
        raise TypeError(f"{tbp}, {carrier_quota_share}: {te}")
    if abs(expected_carrier_bound_premium - carrier_bound_premium) > option_variance_cap:
        return False
    return True


def allianz_commission_rate_matches_google_sheet(
    policy_effective_date: pd.Series,
    coalition_percent_commission: pd.Series,
) -> pd.Series[bool]:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    Allianz US US 30.00% Before 10/31/24
    Allianz US US 31.00% After 11/1/24

    :return: pass / fail
    """
    policy_effective_date = pd.to_datetime(policy_effective_date)
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


def lloyds_uk_canada_commission_rate_matches_google_sheet(
        policy_effective_date: pd.Series,
        coalition_percent_commission: pd.Series,
) -> pd.Series[bool]:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    Lloyd's CAN/UK 32.00% before 4/1/25; 36.50% on/after 4/1/25.

    :return: pass / fail
    """
    # format the dates
    policy_effective_date = pd.to_datetime(policy_effective_date)
    after_date = datetime.datetime(2025, 4, 1)

    # create the filters
    # [2.1] for the new rate
    mask_new_rate_applies = policy_effective_date >= after_date  # boolean pd.Series
    mask_new_commission_rate = coalition_percent_commission == .365
    bool_new_rate = mask_new_rate_applies & mask_new_commission_rate

    # [2.2] for the old rate
    mask_old_rate_applies = policy_effective_date < after_date
    mask_old_commission_rate = coalition_percent_commission == .32
    bool_old_rate = mask_old_rate_applies & mask_old_commission_rate

    results = np.where(bool_new_rate | bool_old_rate, True, False)
    return pd.Series(results)
