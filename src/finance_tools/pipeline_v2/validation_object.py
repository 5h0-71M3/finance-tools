from dirlin.validation import BaseValidation

from finance_tools.core.checks import check_zip_code_matches, find_term_extension_transaction


class DailyValidation(BaseValidation):
    """Validation to be run on Netsuite data to ensure data quality."""

    # The checks we want to run
    _find_term_extension_transaction = find_term_extension_transaction
    _check_zip_code_matches = check_zip_code_matches

    # Tying the column name to check params
    alias_mapping = {
        "transaction_date": "Transaction Effective Date",
        "expiration_date": "Policy Expirtation Date"
    }
