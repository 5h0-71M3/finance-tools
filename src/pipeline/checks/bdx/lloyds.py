"""For checks related to Lloyds"""

import pandas as pd


def lloyds_er_coverage_premium_matches_total(
        do_premium: pd.Series,
        epl_premium: pd.Series,
        fiduciary_premium: pd.Series,
        crime_premium: pd.Series,
        gwp_written_through_lloyds: pd.Series,
) -> pd.Series:
    """breakdown of DO, EPL, Fiduciary, Crime matches the total premium
    on the transaction

    :return: pass/fail
    """
    breakdown_total = sum(
        (
            do_premium,
            epl_premium,
            fiduciary_premium,
            crime_premium
        )
    )

    results = gwp_written_through_lloyds == breakdown_total
    return pd.Series(results)
