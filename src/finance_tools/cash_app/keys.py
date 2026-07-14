"""The deterministic match key tying a bank receipt to an open invoice.

The key is a UUID5 computed *independently* from each document out of the few
fields the two genuinely share: the NetSuite subsidiary, the ISO currency, and
the money amount. Because UUID5 is deterministic, the bank side and the AR side
arrive at the *same* UUID whenever they describe the same payment — so the
match is a plain equality join, with no fuzzy logic or free-text parsing.

Which fields seed the key is the lever for how aggressive the automation is.
The current seed (subsidiary + currency + amount) is deliberately
conservative: it only auto-applies when the amount is unique within a
subsidiary's currency. Adding fields (e.g. a parsed agency) would resolve more
of today's ambiguous receipts in a future pass.
"""
from __future__ import annotations

import uuid

#: Stable namespace for cash-application keys. Derived deterministically (no
#: randomness) so the same inputs always produce the same key across runs and
#: machines — which is what makes the key safe to reuse as an idempotent
#: External ID on the NetSuite upload.
CASH_APP_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "coalition.cash-application.v1")


def build_match_key(subsidiary: int, currency: str, amount: float) -> str:
    """Compute the UUID5 *match key* for one (subsidiary, currency, amount) tuple.

    This is the join key tying a bank receipt to open invoices; it is amount-
    level, so several invoices can share it (those are the ambiguous cases).

    :param subsidiary: NetSuite subsidiary internal id.
    :param currency: ISO currency code (see :mod:`~finance_tools.cash_app.reference`).
    :param amount: payment / open-balance amount; rounded to cents so float
        noise on either side cannot break the join.
    """
    token = f"{int(subsidiary)}|{currency.upper()}|{round(float(amount), 2):.2f}"
    return str(uuid.uuid5(CASH_APP_NAMESPACE, token))


def build_payment_id(
    invoice_internal_id: object, amount: float, account_suffix: str, payment_date: str
) -> str:
    """Compute the upload's External ID / Payment # for one applied receipt.

    Unlike the match key, this is *payment-level*: it includes the specific
    invoice being paid, so two receipts that share a match key but apply to
    different invoices still get distinct, non-colliding External IDs. It stays
    deterministic (same receipt -> same id) so re-running never double-creates.
    """
    token = (
        f"{invoice_internal_id}|{round(float(amount), 2):.2f}"
        f"|{account_suffix}|{payment_date}"
    )
    return str(uuid.uuid5(CASH_APP_NAMESPACE, token))
