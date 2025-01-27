import datetime

import pandas as pd


def carrier_tria_zero_if_total_is_zero(
    total_tria: pd.Series,
    carrier_tria: pd.Series,
) -> pd.Series:
    """if carrier tria is filled, but the total tria is 0,
    then the carrier tria should match the total tria as 0.

    :return: pass/fail
    """
    results = []
    for total, carrier in zip(total_tria, carrier_tria):
        if total == 0 and carrier != 0 or total != 0 and carrier == 0:
            results.append(False)
            continue
        results.append(True)
    return pd.Series(results)
