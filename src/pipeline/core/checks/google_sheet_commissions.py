import datetime
from typing import Literal

import numpy as np
import pandas as pd


##################################
# GOOGLE SHEET COMMISSION SECTION
##################################
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


def aspen_commission_rate_matches_google_sheet(
    policy_effective_date: pd.Series,
    coalition_percent_commission: pd.Series,
    insurance_program: pd.Series
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    Since Aspen is Program dependent (Small, Middle, Large) we need an extra insurance_program parameter
    to determine if the commission is correct.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

        Entity	Coalition Comm Rate	Brokerage Fee 	Status	Effective Date	Expiration Date
        Aspen SMB	US	38.00%	1.50%	New	7/1/24
        Aspen MM	US	36.50%	1.50%	New	4/1/24
        Aspen LM	US	36.50%	1.50%	Expired	4/1/24	6/27/24
        Aspen LM	US	36.00%	1.50%	New	6/28/24

    :return: pass / fail
    """
    policy_effective_date = pd.to_datetime(policy_effective_date)
    after_date = datetime.datetime(2024, 6, 28)

    results = []
    for d, commission, program in zip(policy_effective_date, coalition_percent_commission, insurance_program):
        if d >= after_date and program == "Large Market":
            if commission != .36:
                results.append(False)
                continue
            results.append(True)
        else:
            if program in ("SMB Program", "US Cyber MPL SME"):
                if commission != .38:
                    results.append(False)
                    continue
            else:
                if commission != .365:
                    results.append(False)
                    continue
                results.append(True)
    return pd.Series(results)


def chaucer_commission_rate_matches_google_sheet(
        policy_effective_date: pd.Series,
        coalition_percent_commission: pd.Series,
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

        Entity	Coalition Comm Rate	Brokerage Fee 	Status	Effective Date
        Chaucer	US	33.50%	1.00%	Expired	PY
        Chaucer	US	34.50%	1.00%	New	7/1/24

    :return: pass / fail
    """
    policy_effective_date = pd.to_datetime(policy_effective_date)
    after_date = datetime.datetime(2024, 7, 1)

    results = []
    for effective_day, commission in zip(policy_effective_date, coalition_percent_commission):
        if effective_day >= after_date:
            if commission != .345:
                results.append(False)
                continue
            results.append(True)
        else:
            if commission != .335:
                results.append(False)
                continue
            results.append(True)
    return pd.Series(results)


def fortegra_commission_rate_matches_google_sheet(
        policy_effective_date: pd.Series,
        coalition_percent_commission: pd.Series,
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

        Entity	Coalition Comm Rate	Brokerage Fee 	Status	Effective Date	Expiration Date
        Fortegra	US	30.00%				12/31/24
        Fortegra	US	32.00%	1.25%		1/1/25

    :return: pass / fail
    """
    policy_effective_date = pd.to_datetime(policy_effective_date)
    after_date = datetime.datetime(2025, 1, 1)

    results = []
    for effective_day, commission in zip(policy_effective_date, coalition_percent_commission):
        if effective_day >= after_date:
            if commission != .32:
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
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

        Entity	Coalition Comm Rate	Brokerage Fee 	Status	Effective Date	Expiration Date
        Lloyd's CAN	CAN	32.00%	1.00%
        Lloyd's CAN	CAN	36.50%	1.00%		4/1/25		No profit sharing for 2025 UMR.
        Lloyd's UK	UK	32.00%	1.00%
        Lloyd's UK	UK	36.50%	1.00%		4/1/25		No profit sharing for 2025 UMR.

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


def lloyds_er_commission_rate_matches_google_sheet(
        policy_effective_date: pd.Series,
        coalition_percent_commission: pd.Series,
        broker_commission: pd.Series,
        carrier_quota_share: pd.Series
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

        Entity	Coalition Comm Rate	Brokerage Fee 	Status	Effective Date	Expiration Date
        Lloyd's ER (non-RNR)	US	31.00%	1.75%
        Lloyd's ER (RenRe)	US	32.00%				10/10/24
        Lloyd's ER (RenRe)	US	31.00%	1.00%		10/11/24

    :return: pass / fail
    """
    # Step 1: Create the masks and mapping for function
    # (1.1) masks for report ID
    mask_is_syndicate = carrier_quota_share.iloc[0] == .75  # first record has 75% lloyds quota share
    mask_is_renre = carrier_quota_share.iloc[0] == .25  # first record has 25% lloyds quota share, which indicates RenRe report

    # (1.2) Create the UMR mapping to help identify the correct Coalition Commission
    umr_mapping = {
        "B174010162SS23": ("renre", 2023),
        "B174010162SS24": ("renre", 2024),
        "B174010140SS23": ("syndicate", 2023),
        "B174010140SS24": ("syndicate", 2024),
    }

    # (1.3) Formatting the policy dates on a record level
    policy_effective_date = pd.to_datetime(policy_effective_date)
    after_date = datetime.datetime(2024, 10, 11)

    # Step 2: confirm correct percentages were used
    results = []
    for effective_day, commission, broker in zip(policy_effective_date, coalition_percent_commission, broker_commission):
        if mask_is_syndicate:
            if commission == .31 and broker == .0175:  # correct breakdown for syndicates
                results.append(True)
            else:
                results.append(False)
            continue
        elif mask_is_renre:
            if effective_day >= after_date:
                if commission == .31 and broker == .01:  # correct breakdown for post 10.11.2025 Lloyds ER
                    results.append(True)
                else:
                    results.append(False)
                continue
            else:  # assuming that effective date is pre-2025.10.10
                if commission == .32 and broker == 0:
                    results.append(True)
                else:
                    results.append(False)
                continue
        else:
            raise TypeError(f"Unexpected breakdown with Lloyds Quota Share. Checks for 75% or 25%. Got {carrier_quota_share.iloc[0]}, {carrier_quota_share.iloc[0]}")
    return pd.Series(results)







