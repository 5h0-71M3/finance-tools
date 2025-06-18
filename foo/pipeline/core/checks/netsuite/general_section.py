from datetime import date

import pandas as pd
from dateutil.utils import today


def find_term_extension_transaction(
        transaction_date: pd.Series,
        expiration_date: pd.Series,
) -> pd.Series:
    """identifies transactions with term extension cancellation that is out in the future (by looking at the 2026 transaction date).
    """
    # Clean the data
    transaction_date = pd.to_datetime(transaction_date)
    expiration_date = pd.to_datetime(expiration_date)

    return pd.Series(transaction_date > "2026-01-01")
