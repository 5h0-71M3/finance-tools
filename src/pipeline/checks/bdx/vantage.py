import datetime

import pandas as pd


def vantage_commission_rate_matches_google_sheet(
    policy_effective_date: pd.Series,
    coalition_percent_commission: pd.Series,
) -> pd.Series:
    """the rate is based on the Google Sheet provided by Emily
    and the OTC team. Confirms whether the rate is correct
    and matches the file.

    https://docs.google.com/spreadsheets/d/1yHG90_XFwbneIrGhwgpDMNjelcn2BK90j36lu5BEijo/edit?gid=1587427731#gid=1587427731

    Carrier	Entity	Coalition Comm Rate	Effective
    Vantage	US	30.00%				Before and 12/31/24
    Vantage US	US	35.00%			    After 12/31/24

    :return: pass / fail
    """
    f = policy_effective_date.copy()
    policy_effective_date = pd.to_datetime(f)
    after_date = datetime.datetime(2025, 1, 1)

    results = []
    for effective_date, commission in zip(policy_effective_date, coalition_percent_commission):
        if effective_date >= after_date:
            if commission != .35:
                results.append(False)
                continue
            results.append(True)
        else:
            if commission != .30:
                results.append(False)
                continue
            results.append(True)
    return pd.Series(results)
