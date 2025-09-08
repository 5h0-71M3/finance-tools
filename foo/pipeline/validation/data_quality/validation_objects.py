from dirlin import BaseValidation

from foo.pipeline.core.api import find_term_extension_transaction


class DailyValidation(BaseValidation):
    """Validation to be run on Netsuite data to ensure data quality."""

    # The checks we want to run
    _find_term_extension_transaction = find_term_extension_transaction

    # Tying the column name to check params
    alias_mapping = {
        "transaction_date": "Transaction Effective Date",
        "expiration_date": "Policy Expiration Date"
    }
