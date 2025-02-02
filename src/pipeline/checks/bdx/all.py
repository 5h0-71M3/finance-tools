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


def earned_unearned_field_is_zero(
        total_earned_premium: pd.Series,
        total_unearned_premium: pd.Series,
) -> pd.Series:
    """total earned and unearned premium fields are blank

    :return: pass/fail
    """
    total_earned_premium = total_earned_premium.fillna(0)
    total_unearned_premium = total_unearned_premium.fillna(0)

    result = [
        True if earned == 0 and unearned == 0 else
        False for earned, unearned in
        zip(total_earned_premium, total_unearned_premium)
    ]
    return pd.Series(result)


def transaction_id_is_nan(external_id: pd.Series) -> pd.Series:
    results = []
    for transaction in external_id:
        if pd.isnull(transaction) or str(transaction) == "nan":
            results.append(False)
        else:
            results.append(True)
    return pd.Series(results)
