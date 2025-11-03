import pandas as pd


def current_reported(pl: pd.DataFrame) -> pd.DataFrame:
    # [1] Policies with SwissRe Quota Share
    pl["Swiss Re %"] = pl["Swiss Re %"].fillna(0)
    mask_has_sre_quota_share = pl["Swiss Re %"] > 0

    # [2] That has not been reported
    mask_non_reported_us = pl["Reported - Swiss Re USA"] != "Yes"
    mask_non_reported_can = pl["Reported - Swiss Re CAN"] != "Yes"

    # [3] Apply the two masks
    mask_swiss_re_non_reported = (mask_non_reported_us | mask_non_reported_can) & mask_has_sre_quota_share
    pl = pl[mask_swiss_re_non_reported].copy()
    return pl


def compare_to_itd(pl: pd.DataFrame, itd: pd.DataFrame) -> pd.DataFrame:
    """use this function in conjunction with the previous function. This grabs the population
    then compares it against what is in the ITD. If the population is there, then we check it off on the
    reported section.
    """
    # Subsidiary Setup
    us_subsidiary = "ProForma : GAAP : MGA Consolidation : Coalition, Inc"
    can_subsidiary = "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Coalition Insurance Solutions Canada Inc."

    # [1] Create the masks
    mask_pl_is_us = pl["Subsidiary [Agency Customer]"] == us_subsidiary
    mask_pl_is_can = pl["Subsidiary [Agency Customer]"] == can_subsidiary
    mask = pl["Internal ID"].isin(itd["Internal ID"])

    # [2] Get the indexes together
    # itd = itd.set_index(["Internal ID"], drop=False)
    # itd["Reported"] = "Yes"

    # pl = pl.set_index(["Internal ID"], drop=False)

    # [3]
    pl.loc[mask_pl_is_us & mask, "Reported - Swiss Re USA"] = itd["From"]
    pl.loc[mask_pl_is_can & mask, "Reported - Swiss Re CAN"] = itd["From"]

    return pl
