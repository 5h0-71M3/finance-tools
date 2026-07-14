"""Match bank receipts to open AR invoices and build the NetSuite upload.

Flow:

1. Read the bank receipts and the *Subsidiary Details* tab from the bank file,
   and the open-AR report.
2. Resolve each receipt's account to a subsidiary + ISO currency + full account
   name, and compute its match key.
3. Compute the same match key for every open invoice.
4. A receipt is *easy* when exactly one open invoice shares its key — apply it.
   Receipts with zero or many candidates are set aside for review.
5. Emit the easy applications in the NetSuite CSV-upload schema.

The bank file's *Uploaded Remittance Advice* column is the human answer key and
is intentionally dropped on read so the automation never sees it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from finance_tools.cash_app.disambiguate import disambiguate
from finance_tools.cash_app.keys import build_match_key, build_payment_id
from finance_tools.cash_app.reference import (
    account_suffix,
    load_account_reference,
    normalize_currency,
)

# --- Source schema -------------------------------------------------------

#: Bank Data tab, by position. The 6th column (Uploaded Remittance Advice) is
#: the answer key and is dropped — the automation must derive the match itself.
BANK_COLUMNS = ["data_date", "payment_date", "account", "description", "amount"]

BANK_SHEET = "Bank Data"
SUBSIDIARY_SHEET = "Subsidiary Details"

# --- NetSuite upload schema ---------------------------------------------

#: Column order of the NetSuite payment upload, matching the example file.
#: "Do Not Map" columns are for human legibility and are ignored on upload.
UPLOAD_COLUMNS = [
    "Policy #: Do Not Map",
    "Insured Name: Do Not Map",
    "Invoice #: Do Not Map",
    "Invoice Internal ID",
    "A/R Account Internal ID",
    "Customer ID",
    "Payment: Payment Amount",
    "Invoices: Payment",
    "Payment Verification: Do Not Map",
    "Payment Difference: Do Not Map",
    "Total Unapplied Payment: Do Not Map",
    "Date",
    "Memo",
    "Pmt Incr: Do Not Map",
    "Pmt Numerator: Do Not Map",
    "Pmt Denominator: Do Not Map",
    "Payment #",
    "External ID",
    "Account",
    "Currency",
    "Subsidiary",
]


@dataclass
class CashApplicationResult:
    """Outcome of one cash-application run.

    :param upload: easy applications in the NetSuite upload schema.
    :param ambiguous: receipts that matched more than one open invoice.
    :param unmatched: receipts that matched no open invoice (or could not be
        keyed — e.g. an unknown bank account).
    """

    upload: pd.DataFrame
    ambiguous: pd.DataFrame
    unmatched: pd.DataFrame
    _bank_total: int = field(default=0)
    _fuzzy_resolved: int = field(default=0)

    def summary(self) -> str:
        easy = len(self.upload) - self._fuzzy_resolved
        return (
            f"{self._bank_total} bank receipts -> "
            f"{len(self.upload)} applied "
            f"({easy} exact, {self._fuzzy_resolved} by description), "
            f"{len(self.ambiguous)} ambiguous, "
            f"{len(self.unmatched)} unmatched"
        )


def _read_bank(bank_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the bank receipts and subsidiary-details tabs from the bank file."""
    bank = pd.read_excel(bank_path, engine="calamine", sheet_name=BANK_SHEET)
    # Drop the answer-key remittance column, then name the rest positionally.
    bank = bank.iloc[:, : len(BANK_COLUMNS)].copy()
    bank.columns = BANK_COLUMNS
    bank = bank.dropna(how="all").reset_index(drop=True)

    subs = pd.read_excel(
        bank_path, engine="calamine", sheet_name=SUBSIDIARY_SHEET, header=None
    )
    return bank, subs


def _prepare_bank(bank: pd.DataFrame, accounts: dict) -> pd.DataFrame:
    """Resolve each receipt to a subsidiary/currency/account and a match key."""
    bank = bank.copy()
    suffixes = bank["account"].map(account_suffix)
    bank["subsidiary"] = suffixes.map(lambda s: accounts[s].subsidiary if s in accounts else None)
    bank["currency"] = suffixes.map(lambda s: accounts[s].currency if s in accounts else None)
    bank["account_full"] = suffixes.map(lambda s: accounts[s].full_name if s in accounts else None)

    keyable = bank["subsidiary"].notna() & bank["currency"].notna() & bank["amount"].notna()
    bank["match_key"] = None
    bank.loc[keyable, "match_key"] = bank.loc[keyable].apply(
        lambda r: build_match_key(r["subsidiary"], r["currency"], r["amount"]), axis=1
    )
    return bank


def _prepare_ar(ar: pd.DataFrame) -> pd.DataFrame:
    """Compute a match key per open invoice from its subsidiary/currency/balance.

    The open balance (not the original amount) is what a fresh receipt clears,
    so it is what the key is built on.
    """
    ar = ar.copy()
    iso = ar["Currency"].map(normalize_currency)
    keyable = (
        ar["Subsidiary Internal ID"].notna()
        & iso.notna()
        & ar["Open Balance"].notna()
    )
    ar["match_key"] = None
    ar.loc[keyable, "match_key"] = ar.loc[keyable].apply(
        lambda r: build_match_key(
            r["Subsidiary Internal ID"], iso[r.name], r["Open Balance"]
        ),
        axis=1,
    )
    return ar


def _build_upload(pairs: list[tuple[pd.Series, pd.Series]]) -> pd.DataFrame:
    """Assemble the NetSuite upload rows from (receipt, invoice) pairs."""
    rows = []
    for rec, inv in pairs:
        amount = round(float(rec["amount"]), 2)
        pay_date = pd.to_datetime(rec["payment_date"]).strftime("%-m/%-d/%y")
        # Payment-level External ID / Payment #: keyed on the specific invoice
        # so two receipts sharing a match key get distinct ids, yet still
        # deterministic, so re-running never double-creates a payment.
        external_id = build_payment_id(
            inv["Internal ID"], amount, account_suffix(rec["account"]) or "", pay_date
        )
        rows.append(
            {
                "Policy #: Do Not Map": inv["Coalition Policy Number"],
                "Insured Name: Do Not Map": inv["Insured Name"],
                "Invoice #: Do Not Map": inv["Document Number"],
                "Invoice Internal ID": inv["Internal ID"],
                "A/R Account Internal ID": inv["Account Internal ID"],
                "Customer ID": inv["Name"],
                "Payment: Payment Amount": amount,
                "Invoices: Payment": amount,
                "Payment Verification: Do Not Map": amount,
                "Payment Difference: Do Not Map": 0,
                "Total Unapplied Payment: Do Not Map": 0,
                "Date": pay_date,
                "Memo": None,
                "Pmt Incr: Do Not Map": None,
                "Pmt Numerator: Do Not Map": None,
                "Pmt Denominator: Do Not Map": None,
                "Payment #": external_id,
                "External ID": external_id,
                "Account": rec["account_full"],
                "Currency": inv["Currency"],
                "Subsidiary": inv["Subsidiary Internal ID"],
            }
        )
    return pd.DataFrame(rows, columns=UPLOAD_COLUMNS)


def run_cash_application(bank_path: Path, open_ar_path: Path) -> CashApplicationResult:
    """Run the easy-tier cash application.

    :param bank_path: path to the bank-data workbook (with a *Bank Data* tab and
        a *Subsidiary Details* tab).
    :param open_ar_path: path to the open-AR report workbook.
    """
    bank_raw, subs = _read_bank(bank_path)
    accounts = load_account_reference(subs)
    bank = _prepare_bank(bank_raw, accounts)

    ar = pd.read_excel(open_ar_path, engine="calamine")
    ar = _prepare_ar(ar)

    # Invoice candidates per key, and receipts sharing that key. A receipt is
    # only "easy" when the key is 1:1 in BOTH directions: exactly one open
    # invoice AND exactly one receipt. Two receipts of equal amount in the same
    # subsidiary/currency would otherwise both apply to (and overpay) the same
    # invoice, so they belong in review, not the upload.
    invoice_counts = ar["match_key"].value_counts()
    keyed = bank["match_key"].notna()
    receipt_counts = bank.loc[keyed, "match_key"].value_counts()
    bank["candidates"] = bank["match_key"].map(invoice_counts).fillna(0).astype(int)
    bank["receipt_dupes"] = bank["match_key"].map(receipt_counts).fillna(0).astype(int)

    ar_groups = {k: g for k, g in ar.groupby("match_key")}

    # Tier 1 — easy: the key is 1:1 in BOTH directions (one invoice, one receipt).
    easy_mask = (bank["candidates"] == 1) & (bank["receipt_dupes"] == 1)
    pairs: list[tuple[pd.Series, pd.Series]] = [
        (rec, ar_groups[rec["match_key"]].iloc[0])
        for _, rec in bank[easy_mask].iterrows()
    ]

    # Tier 2 — fuzzy: receipts that matched candidates but weren't a clean 1:1.
    # Use the bank description to pick the right invoice among the candidates.
    ambiguous_mask = (bank["candidates"] >= 1) & ~easy_mask
    fuzzy: list[tuple[int, pd.Series, pd.Series]] = []
    leftover_idx: list[int] = []
    for idx, rec in bank[ambiguous_mask].iterrows():
        winner, _ = disambiguate(rec["description"], ar_groups[rec["match_key"]])
        (fuzzy.append((idx, rec, winner)) if winner is not None
         else leftover_idx.append(idx))

    # Guard: if two receipts fuzzily resolve to the SAME invoice, that invoice
    # can't absorb both — send all the colliders back to review.
    invoice_hits = pd.Series([w["Internal ID"] for _, _, w in fuzzy]).value_counts()
    for idx, rec, winner in fuzzy:
        if invoice_hits.get(winner["Internal ID"], 0) == 1:
            pairs.append((rec, winner))
        else:
            leftover_idx.append(idx)

    upload = _build_upload(pairs)
    ambiguous = bank.loc[leftover_idx].reset_index(drop=True)
    unmatched = bank[bank["candidates"] == 0].reset_index(drop=True)

    return CashApplicationResult(
        upload=upload,
        ambiguous=ambiguous,
        unmatched=unmatched,
        _bank_total=len(bank),
        _fuzzy_resolved=len(pairs) - int(easy_mask.sum()),
    )


def write_result(result: CashApplicationResult, out_dir: Path) -> Path:
    """Write the upload (and an unresolved-review file) to ``out_dir``.

    Returns the path to the upload CSV.
    """
    upload_path = out_dir / f"Cash Application Upload - {date.today()}.csv"
    result.upload.to_csv(upload_path, index=False)

    review_cols = ["data_date", "payment_date", "account", "description", "amount",
                   "subsidiary", "currency", "candidates"]
    review = pd.concat(
        [
            result.ambiguous.assign(reason="multiple candidate invoices"),
            result.unmatched.assign(reason="no candidate invoice"),
        ]
    )
    if not review.empty:
        keep = [c for c in review_cols if c in review.columns] + ["reason"]
        review[keep].to_csv(
            out_dir / f"Cash Application Review - {date.today()}.csv", index=False
        )
    return upload_path
