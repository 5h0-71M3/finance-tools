"""Unit tests for the cash-application match key and reference normalization.

These are deliberately self-contained (no FOLDERS / filesystem) so they run
anywhere. The integration against the example workbooks is exercised manually
via `finance-tools apply-cash`.
"""
import pandas as pd

from finance_tools.cash_app.disambiguate import (
    agency_name,
    disambiguate,
    extract_payer,
    normalize_tokens,
)
from finance_tools.cash_app.keys import build_match_key, build_payment_id
from finance_tools.cash_app.reference import (
    account_suffix,
    load_account_reference,
    normalize_currency,
)


def _candidates(*names):
    return pd.DataFrame({"Name": list(names), "Internal ID": range(len(names))})


def test_key_is_deterministic():
    assert build_match_key(1, "USD", 1195.95) == build_match_key(1, "USD", 1195.95)


def test_bank_and_ar_sides_agree():
    # Bank side carries an ISO code; AR side spells the currency out. The key
    # must come out identical after normalization — that equality IS the join.
    bank = build_match_key(16, "GBP", 1547.76)
    ar = build_match_key(16, normalize_currency("British pound"), 1547.76)
    assert bank == ar


def test_key_rounds_to_cents():
    assert build_match_key(1, "USD", 1195.950001) == build_match_key(1, "USD", 1195.95)


def test_different_inputs_diverge():
    base = build_match_key(1, "USD", 100.00)
    assert build_match_key(2, "USD", 100.00) != base  # subsidiary
    assert build_match_key(1, "CAD", 100.00) != base  # currency
    assert build_match_key(1, "USD", 100.01) != base  # amount


def test_currency_normalization():
    assert normalize_currency("US Dollar") == "USD"
    assert normalize_currency("Danish Krone DKK") == "DKK"  # known AR inconsistency
    assert normalize_currency("EUR") == "EUR"
    assert normalize_currency("") is None
    assert normalize_currency(None) is None


def test_account_suffix_extraction():
    assert account_suffix("USB x2639") == "x2639"
    assert account_suffix("970 Carrier Restricted Cash : INC USB Receivables x2639") == "x2639"
    assert account_suffix("no suffix here") is None


def test_payment_id_is_invoice_specific():
    # Two receipts sharing a match key but applying to different invoices must
    # get distinct External IDs.
    a = build_payment_id(111, 100.00, "x2639", "6/5/26")
    b = build_payment_id(222, 100.00, "x2639", "6/5/26")
    assert a != b
    assert a == build_payment_id(111, 100.00, "x2639", "6/5/26")  # deterministic


def test_extract_payer_handles_ach_format():
    assert extract_payer("COMPANY NAME: Varney Agency SEC CODE: PPD") == "Varney Agency"
    assert extract_payer("S&AMP;S VANCOUV") == "S&S VANCOUV"  # html-unescaped


def test_normalize_tokens_drops_stopwords():
    assert normalize_tokens("Varney Agency Inc") == ["VARNEY"]


def test_agency_name_strips_system_suffix():
    assert agency_name("Varney Agency Inc - AGENCIES-C-532b1323") == "Varney Agency Inc"


def test_disambiguate_picks_clear_winner():
    cands = _candidates(
        "Tabone Insurance - AGENCIES-C-aaa",
        "S&S Insurance Services Ltd. - AGENCIES-C-bbb",
    )
    winner, score = disambiguate("S&AMP;S VANCOUV", cands)
    assert winner is not None
    assert winner["Internal ID"] == 1  # the S&S row


def test_disambiguate_declines_when_unclear():
    cands = _candidates(
        "Acme Insurance - AGENCIES-C-aaa",
        "Beta Insurance - AGENCIES-C-bbb",
    )
    winner, _ = disambiguate("UNRELATED WIRE TRANSFER 998877", cands)
    assert winner is None


def test_account_reference_skips_non_account_rows():
    # Mirrors the Subsidiary Details shape: banner row + an account row.
    subs = pd.DataFrame(
        [
            [None, "Bank Accounts", None, None, None, None, "Country", "Subsidiary", "Currency"],
            [None, "970 Carrier Restricted Cash : INC USB Receivables x2639", None, None, None, None, "US", 1, "USD"],
            [None, "Subsidiaries", None, None, None, None, None, None, None],
        ]
    )
    accounts = load_account_reference(subs)
    assert set(accounts) == {"x2639"}
    acct = accounts["x2639"]
    assert acct.subsidiary == 1 and acct.currency == "USD"
    assert acct.full_name.endswith("x2639")
