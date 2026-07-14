"""Reference data shared by both sides of the match.

Bank receipts and the open-AR report describe the same money in different
vocabularies, so before anything can be tied together we have to normalize:

* The bank file labels accounts with a short tag like ``"USB x2639"``; the
  *Subsidiary Details* tab maps that account to a NetSuite subsidiary, an ISO
  currency, and the full account name NetSuite expects on the upload.
* The open-AR report spells currencies out (``"US Dollar"``) and is sometimes
  inconsistent (``"Danish Krone DKK"``), so we fold everything down to an ISO
  code before it ever reaches a match key.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

#: Regex pulling the account suffix (``x2639``) out of either the short bank
#: tag or the full Subsidiary Details account name. The suffix is the only
#: token the two share, so it is what we join on.
ACCOUNT_SUFFIX = re.compile(r"(x\d+)", re.IGNORECASE)

#: Open-AR currency labels folded down to ISO codes. The bank side already
#: uses ISO codes, so this only needs to cover the long-form AR spellings
#: (including the ``"Danish Krone DKK"`` inconsistency seen in the report).
AR_CURRENCY_TO_ISO = {
    "US Dollar": "USD",
    "Canadian Dollar": "CAD",
    "British pound": "GBP",
    "British Pound": "GBP",
    "Australian Dollar": "AUD",
    "Euro": "EUR",
    "Danish Krone": "DKK",
    "Danish Krone DKK": "DKK",
    "Swedish Krona": "SEK",
}


def normalize_currency(value: str) -> str | None:
    """Fold a currency label to its ISO code.

    Accepts ISO codes (returned untouched, upper-cased) and the long-form
    spellings used in the open-AR report. Returns ``None`` when the label is
    blank or unrecognized so callers can route the row to manual review.
    """
    if not isinstance(value, str):
        return None
    label = value.strip()
    if not label:
        return None
    if label in AR_CURRENCY_TO_ISO:
        return AR_CURRENCY_TO_ISO[label]
    # Bank side is already ISO; accept any bare 3-letter code.
    if len(label) == 3 and label.isalpha():
        return label.upper()
    # Last resort: a trailing ISO token, e.g. "Danish Krone DKK".
    tail = label.split()[-1]
    if len(tail) == 3 and tail.isalpha():
        return tail.upper()
    return None


@dataclass(frozen=True)
class BankAccount:
    """A bank account resolved from the *Subsidiary Details* tab."""

    suffix: str
    full_name: str
    subsidiary: int
    currency: str  # ISO code


def load_account_reference(subsidiary_details: pd.DataFrame) -> dict[str, BankAccount]:
    """Build a ``{suffix -> BankAccount}`` lookup from the Subsidiary Details tab.

    The tab is read with no header (it has a banner row and a second
    *Subsidiaries* block lower down), so we scan for the account rows by their
    shape: an account name starting with a digit in column index 1, with
    country/subsidiary/currency in columns 6/7/8.
    """
    accounts: dict[str, BankAccount] = {}
    for _, row in subsidiary_details.iterrows():
        name = row.iloc[1] if len(row) > 1 else None
        if not isinstance(name, str) or not re.match(r"^\d", name.strip()):
            continue
        match = ACCOUNT_SUFFIX.search(name)
        currency = normalize_currency(row.iloc[8]) if len(row) > 8 else None
        subsidiary = row.iloc[7] if len(row) > 7 else None
        if match is None or currency is None or pd.isna(subsidiary):
            continue
        suffix = match.group(1).lower()
        accounts[suffix] = BankAccount(
            suffix=suffix,
            full_name=name.strip(),
            subsidiary=int(subsidiary),
            currency=currency,
        )
    return accounts


def account_suffix(account: str) -> str | None:
    """Pull the ``x####`` suffix out of a bank account tag (or full name)."""
    if not isinstance(account, str):
        return None
    match = ACCOUNT_SUFFIX.search(account)
    return match.group(1).lower() if match else None
