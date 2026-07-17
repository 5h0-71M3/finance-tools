import datetime

import pandas as pd

# Validation functions for the Vantage pipeline, ported for pipeui discovery.
#
# pipeui scans this file in isolation and registers only functions defined here
# (imports are filtered out), classifying each by its return annotation:
#   - `-> pd.Series[bool]`  → column-shaped validation (one result per row)
#   - `-> bool`             → row-by-row validation (scalar params, run per row)
# A bare `-> pd.Series` would misclassify as a transform, so boolean column
# returns are annotated `pd.Series[bool]` explicitly.
#
# The set below mirrors the legacy `VantageValidation` MRO in
# `finance_tools.pipeline_v2.validations.carriers`:
#   VantageValidation -> BasicValidationUS -> BasicValidation
# Parameter names are the canonical alias keys those classes bind columns to.


# ----------------------------------------------------------------------------
# BasicValidation — record-level checks run on every carrier
# ----------------------------------------------------------------------------
def transaction_id_is_nan(external_id: pd.Series) -> pd.Series[bool]:
    """Transaction ID is not blank.

    :return: pass / fail
    """
    results = []
    for transaction in external_id:
        if pd.isnull(transaction) or str(transaction) == "nan":
            results.append(False)
        else:
            results.append(True)
    return pd.Series(results)


def validate_carrier_bound_premium(df: pd.DataFrame) -> pd.Series[bool]:
    """Expected formula for Carrier Bound Premium => TBP x Quota Share.

    Multi-column check: pipeui binds only one column per validation, so a row-wise
    check across several columns takes the whole table and reads the columns by name
    (the legacy VantageValidation alias mapping). Column names:
      - tbp                    -> "Total Bound Premium"   (BasicValidation alias)
      - carrier_bound_premium  -> "Vantage Bound Premium"  (VantageValidation alias)
      - carrier_quota_share    -> "Vantage Quota Share"    (source column; the legacy
                                   alias was "Vantage Quota Share %", absent here)

    :return: pass / fail per row
    """
    option_variance_cap: float = .02
    expected_carrier_bound_premium = (
        df["Total Bound Premium"] * df["Vantage Quota Share"]
    ).round(2)
    variance = (expected_carrier_bound_premium - df["Vantage Bound Premium"]).abs()
    return variance <= option_variance_cap


def validate_carrier_net_premium(
    tbp: float,
    carrier_net_premium: float,
    carrier_percent_commission: float,
    carrier_quota_share: float,
) -> bool:
    """Expected Formula for Carrier Net Premium =>
    (TBP * Quota Share) - ((TBP * Quota Share) * Carrier Commission Percent).

    :param tbp: the total premium of the policy
    :param carrier_net_premium: TBP x Quota Share of the policy less Coalition Commission
    :param carrier_percent_commission: the Coalition Commission percent of the policy
    :param carrier_quota_share: the quota split of the carrier

    :return: pass / fail
    """
    option_variance_cap: float = .02
    expected_carrier_net_premium = round(tbp * ((1 - carrier_percent_commission) * carrier_quota_share), 2)
    if abs(expected_carrier_net_premium - carrier_net_premium) > option_variance_cap:
        return False
    return True


def validate_carrier_commission_to_coalition(
    carrier_bound_premium: float,
    carrier_percent_commission: float,
    carrier_commission_to_coalition: float,
) -> bool:
    """Validates the carrier commission amount.

    :param carrier_bound_premium: the carrier premium amount
    :param carrier_percent_commission: the Coalition Commission percent of the policy
    :param carrier_commission_to_coalition: Carrier Bound Premium x Carrier Commission Percent

    :return: pass / fail
    """
    option_variance_cap: float = .02
    expected_carrier_commission = round(carrier_bound_premium * carrier_percent_commission, 2)
    if abs(expected_carrier_commission - carrier_commission_to_coalition) > option_variance_cap:
        return False
    return True


def validate_limit_signature_matches_tbp(tbp: float, base_limit: int) -> bool:
    """The signature of the limit columns matches the tbp signature (+ vs -).

    :return: pass / fail
    """
    if base_limit < 0:
        if tbp <= 0:
            return True
    elif base_limit > 0:
        if tbp >= 0:
            return True
    elif base_limit == 0:
        return True
    return False


# ----------------------------------------------------------------------------
# BasicValidationUS — additional checks for US entities
# ----------------------------------------------------------------------------
def carrier_tria_zero_if_total_is_zero(
    total_tria: pd.Series,
    carrier_tria: pd.Series,
) -> pd.Series[bool]:
    """If carrier tria is filled but the total tria is 0, then the carrier tria
    should match the total tria as 0.

    :return: pass / fail
    """
    results = []
    for total, carrier in zip(total_tria, carrier_tria):
        if total == 0 and carrier != 0 or total != 0 and carrier == 0:
            results.append(False)
            continue
        results.append(True)
    return pd.Series(results)


def earned_unearned_field_is_zero(
    total_earned_premium: pd.Series,
    total_unearned_premium: pd.Series,
) -> pd.Series[bool]:
    """Total earned and unearned premium fields are blank.

    :return: pass / fail
    """
    total_earned_premium = total_earned_premium.fillna(0)
    total_unearned_premium = total_unearned_premium.fillna(0)

    result = [
        True if earned == 0 and unearned == 0 else
        False for earned, unearned in
        zip(total_earned_premium, total_unearned_premium)
    ]
    return pd.Series(result)


# ----------------------------------------------------------------------------
# VantageValidation — carrier-specific checks
# ----------------------------------------------------------------------------
def vantage_commission_rate_matches_google_sheet(
    policy_effective_date: pd.Series,
    coalition_percent_commission: pd.Series,
) -> pd.Series[bool]:
    """The rate is based on the Google Sheet provided by Emily and the OTC team.
    Confirms whether the rate is correct and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

    Carrier      Entity   Coalition Comm Rate   Effective
    Vantage      US       30.00%                Before and 12/31/24
    Vantage US   US       35.00%                After 12/31/24

    :return: pass / fail
    """
    f = policy_effective_date.copy()
    policy_effective_date = pd.to_datetime(f)
    after_date = datetime.datetime(2025, 1, 1)

    results = []
    for effective_date, commission in zip(policy_effective_date, coalition_percent_commission):
        if effective_date >= after_date:
            if commission - .35 > .01:
                results.append(False)
                continue
            results.append(True)
        else:
            if commission - .30 > .01:
                results.append(False)
                continue
            results.append(True)
    return pd.Series(results)


def surplus_3_0_filled(surplus_3_0: pd.Series) -> pd.Series[bool]:
    """Confirms that the Surplus 3.0 section has been filled with "No" or "Yes"
    values and not left blank.

    :return: pass / fail
    """
    return pd.Series(~pd.isnull(surplus_3_0))
