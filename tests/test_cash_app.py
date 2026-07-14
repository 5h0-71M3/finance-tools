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
from finance_tools.cash_app.history import PayerLedger
from finance_tools.cash_app.keys import build_match_key, build_payment_id
from finance_tools.cash_app.payer import AGENCY, INSURED, build_index, resolve_entity
from finance_tools.cash_app.reference import (
    account_suffix,
    load_account_reference,
    normalize_currency,
)


def _candidates(*names):
    return pd.DataFrame({"Name": list(names), "Internal ID": range(len(names))})


def test_key_is_deterministic():
    assert build_match_key(1, "USD", 1195.95, "Varney") == build_match_key(1, "USD", 1195.95, "Varney")


def test_bank_and_ar_sides_agree():
    # Bank side carries an ISO code; AR side spells the currency out, and the
    # agency comes in with different casing/spacing. The key must come out
    # identical after normalization — that equality IS the join.
    bank = build_match_key(16, "GBP", 1547.76, "Acme Brokers")
    ar = build_match_key(16, normalize_currency("British pound"), 1547.76, "acme  brokers")
    assert bank == ar


def test_key_rounds_to_cents():
    assert build_match_key(1, "USD", 1195.950001, "A") == build_match_key(1, "USD", 1195.95, "A")


def test_different_inputs_diverge():
    base = build_match_key(1, "USD", 100.00, "Acme")
    assert build_match_key(2, "USD", 100.00, "Acme") != base  # subsidiary
    assert build_match_key(1, "CAD", 100.00, "Acme") != base  # currency
    assert build_match_key(1, "USD", 100.01, "Acme") != base  # amount
    assert build_match_key(1, "USD", 100.00, "Beta") != base  # agency


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


def _ar_frame(names=(), insureds=()):
    n = max(len(names), len(insureds))
    return pd.DataFrame(
        {
            "Name": list(names) + [None] * (n - len(names)),
            "Insured Name": list(insureds) + [None] * (n - len(insureds)),
        }
    )


def test_resolve_entity_finds_agency():
    idx = build_index(
        _ar_frame(names=[
            "Varney Agency Inc - AGENCIES-C-111",
            "Tabone Insurance - AGENCIES-C-222",
            "S&S Insurance Services Ltd. - AGENCIES-C-333",
        ]),
        AGENCY,
    )
    entity, score = resolve_entity("COMPANY NAME: Varney Agency SEC CODE: PPD", idx)
    assert entity is not None
    assert entity.value == "Varney Agency Inc"
    assert entity.dimension == "agency"
    assert score >= 0.6


def test_resolve_entity_resolves_insured_dimension():
    idx = build_index(
        _ar_frame(insureds=["Blue Ridge Bakery LLC", "Harbor Freight Tools"]),
        INSURED,
    )
    entity, _ = resolve_entity("COMPANY NAME: Blue Ridge Bakery SEC CODE: CCD", idx)
    assert entity is not None
    assert entity.value == "Blue Ridge Bakery LLC"
    assert entity.dimension == "insured"


def test_resolve_entity_declines_when_unknown():
    idx = build_index(_ar_frame(names=["Acme Insurance - AGENCIES-C-a", "Beta Insurance - AGENCIES-C-b"]), AGENCY)
    entity, _ = resolve_entity("UNRELATED WIRE TRANSFER 998877", idx)
    assert entity is None


def test_build_index_dedups_and_skips_empty():
    idx = build_index(
        _ar_frame(names=[
            "Varney Agency Inc - AGENCIES-C-111",
            "Varney Agency Inc - AGENCIES-C-999",  # same agency, different suffix
            "Insurance Group LLC - AGENCIES-C-222",  # all stopwords -> skipped
        ]),
        AGENCY,
    )
    assert [e.value for e in idx] == ["Varney Agency Inc"]


def test_agency_and_insured_keys_never_collide():
    # Same subsidiary/currency/amount and even the same name must yield distinct
    # keys across dimensions, so an agency-UUID can't match an insured field.
    a = build_match_key(1, "USD", 100.0, "Acme", dimension="agency")
    i = build_match_key(1, "USD", 100.0, "Acme", dimension="insured")
    assert a != i


def test_payer_ledger_observe_and_covers(tmp_path):
    ledger = PayerLedger(path=tmp_path / "payer_history.json")
    ledger.observe("Parent Brokers", "Child Agency")
    ledger.observe("Parent Brokers", "Child Agency")
    ledger.observe("Parent Brokers", "Other Agency")
    assert ledger.covers("Parent Brokers", "Child Agency")
    assert not ledger.covers("Parent Brokers", "Nobody")
    assert ledger.covered_customers("Parent Brokers") == {"Child Agency": 2, "Other Agency": 1}


def test_payer_ledger_roundtrips_to_disk(tmp_path):
    path = tmp_path / "payer_history.json"
    ledger = PayerLedger(path=path)
    ledger.observe("Parent Brokers", "Child Agency")
    ledger.save()
    assert PayerLedger.load(path).covers("Parent Brokers", "Child Agency")


def _candidate_invoices(*rows):
    # rows: (Name, Insured Name, Internal ID)
    return pd.DataFrame(
        [{"Name": n, "Insured Name": ins, "Internal ID": iid} for n, ins, iid in rows]
    )


def test_disambiguate_matches_insured_when_agency_absent():
    from finance_tools.cash_app.pipeline import _disambiguate

    cands = _candidate_invoices(
        ("Acme Agency - AGENCIES-C-a", "Blue Ridge Bakery LLC", 1),
        ("Beta Agency - AGENCIES-C-b", "Harbor Freight Tools", 2),
    )
    winner, dims = _disambiguate("COMPANY NAME: Blue Ridge Bakery SEC CODE: CCD", cands)
    assert winner is not None and winner["Internal ID"] == 1
    assert any(how == "insured" for how, _, _ in dims)


def test_disambiguate_declines_when_description_names_nobody():
    from finance_tools.cash_app.pipeline import _disambiguate

    cands = _candidate_invoices(
        ("Acme Agency - AGENCIES-C-a", "Blue Ridge Bakery LLC", 1),
        ("Beta Agency - AGENCIES-C-b", "Harbor Freight Tools", 2),
    )
    winner, dims = _disambiguate("WIRE REF 8837 UNRELATED TRANSFER", cands)
    assert winner is None and dims == []


def test_review_row_uses_ledger_for_likely_target(tmp_path):
    from finance_tools.cash_app.pipeline import _review_row

    indexes = {
        "agency": build_index(
            _ar_frame(names=["Parent Brokers - AGENCIES-C-p", "Beta Insurance - AGENCIES-C-b"]),
            AGENCY,
        ),
        "insured": build_index(_ar_frame(insureds=["Nobody Inc"]), INSURED),
    }
    ledger = PayerLedger(path=tmp_path / "l.json")
    ledger.observe("Parent Brokers", "Beta Insurance")  # learned from history
    rec = pd.Series({"description": "COMPANY NAME: Parent Brokers SEC CODE: PPD"})
    out = _review_row(
        rec, "amount matched multiple invoices", indexes, ledger,
        {"Beta Insurance", "Gamma Insurance"},
    )
    assert out["reason"] == "amount matched multiple invoices"
    assert out["agency_matched"] == "Parent Brokers"
    assert out["likely_target"] == "Beta Insurance"


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
