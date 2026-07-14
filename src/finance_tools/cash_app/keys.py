"""The deterministic match key tying a bank receipt to an open invoice.

The key is a UUID5 computed *independently* from each document out of the fields
the two genuinely share: the NetSuite subsidiary, the ISO currency, the money
amount, and the **agency**. Because UUID5 is deterministic, the bank side and
the AR side arrive at the *same* UUID whenever they describe the same payment —
so the match is a plain equality join.

The catch is the agency: the AR side has it verbatim (the invoice's ``Name``),
but the bank side only has the free-text ``Description``. So the agency is the
one field that is *fuzzy-resolved* first (see
:mod:`~finance_tools.cash_app.payer`) and then fed into the key as an exact
component. Everything downstream of that resolution is a deterministic equality
join; the fuzzy step's confidence rides alongside the match.

Folding the agency into the seed is what makes the key unique when several
invoices share an amount — it is the lever the earlier amount-only key lacked.
The trade-off is recall: a receipt whose agency cannot be resolved from its
description can no longer be keyed at all (it goes to review), even when its
amount happens to be unique.
"""
from __future__ import annotations

import uuid

#: Stable namespace for cash-application keys. Derived deterministically (no
#: randomness) so the same inputs always produce the same key across runs and
#: machines — which is what makes the key safe to reuse as an idempotent
#: External ID on the NetSuite upload.
CASH_APP_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "coalition.cash-application.v1")


def normalize_entity(entity: str) -> str:
    """Fold an agency/insured name to the canonical form used inside the key seed.

    Both sides must apply the *same* transform or their UUIDs will not line up,
    so this is deliberately simple: upper-case and collapse whitespace. Callers
    pass the already-cleaned name (the bank side's is the *resolved* AR entity),
    so the two sides feed identical text.
    """
    return " ".join(str(entity).split()).upper()


def build_match_key(
    subsidiary: int,
    currency: str,
    amount: float,
    entity: str,
    *,
    dimension: str = "agency",
) -> str:
    """Compute the UUID5 *match key* for one payment coordinate.

    The entity (an agency or an insured name) makes the key far more specific
    than the old amount-only key: two invoices of equal amount in one
    subsidiary/currency no longer collide unless they also share that entity.

    The ``dimension`` label is part of the seed so the agency key and the
    insured key live in *separate namespaces*: a bank receipt's agency-UUID can
    only ever match an invoice's agency-UUID, never its insured-UUID, even if an
    agency and an insured happen to share a name.

    :param subsidiary: NetSuite subsidiary internal id.
    :param currency: ISO currency code (see :mod:`~finance_tools.cash_app.reference`).
    :param amount: payment / open-balance amount; rounded to cents so float
        noise on either side cannot break the join.
    :param entity: the agency or insured name — verbatim on the AR side,
        fuzzy-resolved from the bank description on the bank side.
    :param dimension: which identifier ``entity`` is (``"agency"``, ``"insured"``,
        …); namespaces the key.
    """
    token = (
        f"{dimension.lower()}|{int(subsidiary)}|{currency.upper()}"
        f"|{round(float(amount), 2):.2f}|{normalize_entity(entity)}"
    )
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
