"""Cash Application: match incoming bank receipts to open AR invoices.

The first version handles the *easiest* applications only: a bank receipt is
applied automatically when exactly one open invoice ties to it via a
deterministic match key (a UUID5 computed independently from each document).
Ambiguous (many candidate invoices) and unmatched receipts are set aside for
later, more complex passes.

Entry point: :func:`finance_tools.cash_app.pipeline.run_cash_application`.
"""
from finance_tools.cash_app.pipeline import (
    CashApplicationResult,
    run_cash_application,
)

__all__ = ["CashApplicationResult", "run_cash_application"]
