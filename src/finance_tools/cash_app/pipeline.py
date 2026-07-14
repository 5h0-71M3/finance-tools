"""Match bank receipts to open AR invoices and build the NetSuite upload.

The reliable signal in this data is the **amount** (with subsidiary + currency);
the payer named in the free-text ``Description`` is a *minority* signal — most
receipts are wires/ACH that name no agency or insured at all. So matching is a
hybrid:

1. Read the bank receipts + *Subsidiary Details* tab, and the open-AR report.
2. Resolve each receipt's account to a subsidiary + ISO currency + full account
   name, and build the amount key ``subsidiary | currency | amount``.
3. **Amount-unique** (the key is 1:1 in both directions — one invoice, one
   receipt): apply it. This is the backbone and clears the bulk.
4. **Amount collision** (several invoices share the amount): disambiguate by
   fuzzy-matching the description against *only those candidate invoices'*
   agency ``Name`` and ``Insured Name``. A small, grounded candidate set means
   the match is fast and can't wander off to an unrelated name. The winning
   dimension(s) and score are recorded; if both the agency and the insured of
   the winner match, that is noted as corroboration.
5. Anything unresolved is routed to review, enriched with the best-guess
   agency/insured (resolved over the whole customer master via a token-prefix
   index) and a reason.
6. Amount-unique matches also *teach* the payer ledger: a confident agency that
   differs from the cleared invoice's agency is an observed "A pays for B" link.

The bank file's *Uploaded Remittance Advice* column is the human answer key and
is intentionally dropped on read so the automation never sees it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from finance_tools.cash_app.disambiguate import agency_name
from finance_tools.cash_app.history import PayerLedger
from finance_tools.cash_app.keys import build_payment_id
from finance_tools.cash_app.payer import (
    DIMENSIONS,
    build_index,
    payer_tokens,
    resolve_entity,
    score_tokens,
)
from finance_tools.cash_app.reference import (
    account_suffix,
    load_account_reference,
    normalize_currency,
)

#: Disambiguation among an amount's candidate invoices commits only when the top
#: candidate clears this score AND beats the runner-up by ``DISAMBIGUATE_MARGIN``
#: — precision over recall, as a mis-applied payment is worse than a manual one.
DISAMBIGUATE_THRESHOLD = 0.6
DISAMBIGUATE_MARGIN = 0.15

#: The ledger is only *taught* from high-confidence resolutions: a wrong lesson
#: would pollute every future run, so learning keeps a strict bar.
LEARN_THRESHOLD = 0.8

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
class _Application:
    """One applied receipt and how it was matched.

    :param dims: ``[(how, entity, score), ...]``. For the amount backbone this
        is ``[("amount", None, 1.0)]``; for a disambiguated match it is the name
        dimension(s) — agency and/or insured — that pointed at this invoice.
    """

    rec: pd.Series
    inv: pd.Series
    dims: list[tuple[str, str | None, float]]

    @property
    def confidence(self) -> float:
        return max((s for _, _, s in self.dims), default=0.0)

    @property
    def matched_by(self) -> str:
        return "+".join(how for how, _, _ in self.dims)


@dataclass
class CashApplicationResult:
    """Outcome of one cash-application run.

    :param upload: applied receipts in the NetSuite upload schema.
    :param applied_detail: one row per applied receipt with matched-by and the
        per-dimension confidence scores (an audit trail; not uploaded).
    :param ambiguous: receipts whose amount hit invoices but could not be
        cleanly resolved, enriched with best-guess names + reason.
    :param unmatched: receipts whose amount hit no invoice (or that could not be
        keyed — e.g. an unknown bank account), similarly enriched.
    """

    upload: pd.DataFrame
    applied_detail: pd.DataFrame
    ambiguous: pd.DataFrame
    unmatched: pd.DataFrame
    _bank_total: int = field(default=0)
    _amount_unique: int = field(default=0)
    _disambiguated: int = field(default=0)
    _corroborated: int = field(default=0)

    def summary(self) -> str:
        return (
            f"{self._bank_total} bank receipts -> "
            f"{len(self.upload)} applied "
            f"({self._amount_unique} amount-unique, "
            f"{self._disambiguated} name-disambiguated"
            f"; {self._corroborated} corroborated by agency & insured), "
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


def _amount_key(subsidiary: object, currency: str, amount: float) -> str:
    """The ``subsidiary|currency|amount`` join key (the reliable backbone)."""
    return f"{int(subsidiary)}|{currency.upper()}|{round(float(amount), 2):.2f}"


def _prepare_bank(bank: pd.DataFrame, accounts: dict) -> pd.DataFrame:
    """Resolve each receipt to a subsidiary / currency / account and amount key."""
    bank = bank.copy()
    suffixes = bank["account"].map(account_suffix)
    bank["subsidiary"] = suffixes.map(lambda s: accounts[s].subsidiary if s in accounts else None)
    bank["currency"] = suffixes.map(lambda s: accounts[s].currency if s in accounts else None)
    bank["account_full"] = suffixes.map(lambda s: accounts[s].full_name if s in accounts else None)

    base = bank["subsidiary"].notna() & bank["currency"].notna() & bank["amount"].notna()
    bank["amount_key"] = None
    bank.loc[base, "amount_key"] = bank.loc[base].apply(
        lambda r: _amount_key(r["subsidiary"], r["currency"], r["amount"]), axis=1
    )
    return bank


def _prepare_ar(ar: pd.DataFrame) -> pd.DataFrame:
    """Compute the amount key and cleaned agency per open invoice.

    The open balance (not the original amount) is what a fresh receipt clears,
    so it is what the key is built on.
    """
    ar = ar.copy()
    iso = ar["Currency"].map(normalize_currency)
    base = (
        ar["Subsidiary Internal ID"].notna()
        & iso.notna()
        & ar["Open Balance"].notna()
    )
    ar["amount_key"] = None
    ar.loc[base, "amount_key"] = ar.loc[base].apply(
        lambda r: _amount_key(r["Subsidiary Internal ID"], iso[r.name], r["Open Balance"]),
        axis=1,
    )
    ar["agency"] = ar["Name"].map(lambda n: agency_name(n) if isinstance(n, str) else None)
    return ar


def _disambiguate(
    description: str, candidates: pd.DataFrame
) -> tuple[pd.Series | None, list[tuple[str, str | None, float]]]:
    """Pick the invoice among ``candidates`` whose agency/insured the payer names.

    Scores the description against each candidate's agency ``Name`` and
    ``Insured Name`` (only a handful of names, so this is fast and grounded).
    Commits to the top candidate only when it clears the threshold and beats the
    runner-up by the margin; returns the dimension(s) that tied on the winner.
    """
    tokens = payer_tokens(description)
    if not tokens:
        return None, []
    scored: list[tuple[float, pd.Series, list]] = []
    for _, inv in candidates.iterrows():
        best, dims = 0.0, []
        for dim in DIMENSIONS:
            value = dim.value_of(inv.get(dim.ar_column))
            if value is None:
                continue
            s = score_tokens(tokens, value)
            best = max(best, s)
            if s >= DISAMBIGUATE_THRESHOLD:
                dims.append((dim.name, value, round(s, 3)))
        scored.append((best, inv, dims))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[0]
    runner = scored[1][0] if len(scored) > 1 else 0.0
    if top[0] >= DISAMBIGUATE_THRESHOLD and (top[0] - runner) >= DISAMBIGUATE_MARGIN:
        return top[1], top[2]
    return None, []


def _build_upload(apps: list[_Application]) -> pd.DataFrame:
    """Assemble the NetSuite upload rows from applied (receipt, invoice) pairs."""
    rows = []
    for app in apps:
        rec, inv = app.rec, app.inv
        amount = round(float(rec["amount"]), 2)
        pay_date = pd.to_datetime(rec["payment_date"]).strftime("%-m/%-d/%y")
        # Payment-level External ID / Payment #: keyed on the specific invoice
        # so two receipts sharing an amount get distinct ids, yet still
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


def _build_audit(apps: list[_Application]) -> pd.DataFrame:
    """One row per applied receipt: matched-by and each dimension's confidence."""
    rows = []
    for app in apps:
        scores = {how: s for how, _, s in app.dims}
        entities = {how: e for how, e, _ in app.dims}
        row = {
            "payment_date": app.rec["payment_date"],
            "account": app.rec["account"],
            "description": app.rec["description"],
            "amount": round(float(app.rec["amount"]), 2),
            "Customer ID": app.inv["Name"],
            "Insured Name": app.inv["Insured Name"],
            "Invoice #": app.inv["Document Number"],
            "Invoice Internal ID": app.inv["Internal ID"],
            "matched_by": app.matched_by,
            "confidence": round(app.confidence, 3),
        }
        for dim in DIMENSIONS:
            row[f"{dim.name}_matched"] = entities.get(dim.name)
            row[f"{dim.name}_confidence"] = round(scores[dim.name], 3) if dim.name in scores else None
        rows.append(row)
    cols = (
        ["payment_date", "account", "description", "amount", "Customer ID",
         "Insured Name", "Invoice #", "Invoice Internal ID", "matched_by", "confidence"]
        + [f"{d.name}_matched" for d in DIMENSIONS]
        + [f"{d.name}_confidence" for d in DIMENSIONS]
    )
    return pd.DataFrame(rows, columns=cols)


def _review_row(rec: pd.Series, reason: str, indexes: dict, ledger: PayerLedger,
                amount_agencies: set) -> dict:
    """Assemble one review row: reason, best-guess names + confidence, likely target.

    The best-guess names come from resolving over the *whole* master (fast via
    the prefix index) — a hint for the human, with the confidence exposed so an
    unreliable guess is visible as such.
    """
    row = {"reason": reason}
    guesses: dict[str, str | None] = {}
    for dim in DIMENSIONS:
        entity, score = resolve_entity(rec["description"], indexes[dim.name])
        guesses[dim.name] = entity.value if entity is not None else None
        row[f"{dim.name}_matched"] = guesses[dim.name]
        row[f"{dim.name}_confidence"] = round(float(score), 3)

    likely_target = None
    agency_guess = guesses.get("agency")
    if agency_guess is not None:
        covered = ledger.covered_customers(agency_guess)
        hits = {c: n for c, n in covered.items() if c in amount_agencies}
        covered = hits or covered
        if covered:
            likely_target = max(covered, key=covered.get)
    row["likely_target"] = likely_target
    return row


def _with_annotations(df: pd.DataFrame, annot: dict[int, dict]) -> pd.DataFrame:
    """Attach the review columns onto the receipt rows in ``df``."""
    cols = ["reason", "likely_target"] + [f"{d.name}_matched" for d in DIMENSIONS] + [
        f"{d.name}_confidence" for d in DIMENSIONS
    ]
    df = df.copy()
    if df.empty:
        for col in cols:
            df[col] = pd.Series(dtype=object)
        return df.reset_index(drop=True)
    for col in cols:
        df[col] = [annot[i][col] for i in df.index]
    return df.reset_index(drop=True)


def run_cash_application(
    bank_path: Path,
    open_ar_path: Path,
    *,
    ledger: PayerLedger | None = None,
) -> CashApplicationResult:
    """Run the hybrid (amount backbone + agency/insured disambiguation) cash app.

    :param bank_path: path to the bank-data workbook (with a *Bank Data* tab and
        a *Subsidiary Details* tab).
    :param open_ar_path: path to the open-AR report workbook.
    :param ledger: payer→customer ledger to read from and teach; defaults to the
        committed one in this package. Pass an explicit (temp-path) ledger in
        tests so a run never writes the shared file.
    """
    bank_raw, subs = _read_bank(bank_path)
    accounts = load_account_reference(subs)
    bank = _prepare_bank(bank_raw, accounts)

    ar = pd.read_excel(open_ar_path, engine="calamine")
    ar = _prepare_ar(ar)

    indexes = {dim.name: build_index(ar, dim) for dim in DIMENSIONS}
    if ledger is None:
        ledger = PayerLedger.load()

    invoice_counts = ar["amount_key"].value_counts()
    keyed = bank["amount_key"].notna()
    receipt_counts = bank.loc[keyed, "amount_key"].value_counts()
    ar_amount_groups = {k: g for k, g in ar.groupby("amount_key")}
    ar_amount_agencies = ar.groupby("amount_key")["agency"].agg(
        lambda s: {a for a in s.dropna()}
    )

    apps: list[_Application] = []
    tentative: list[tuple[int, _Application]] = []
    annot: dict[int, dict] = {}
    amb_idx: list[int] = []
    unmatched_idx: list[int] = []

    for i, rec in bank.iterrows():
        ak = rec["amount_key"]
        cand_ct = int(invoice_counts.get(ak, 0)) if ak is not None else 0
        rcpt_ct = int(receipt_counts.get(ak, 0)) if ak is not None else 0

        if cand_ct == 0:
            annot[i] = _review_row(
                rec,
                "unknown bank account or missing field" if ak is None
                else "no invoice at this amount",
                indexes, ledger, set(),
            )
            unmatched_idx.append(i)
            continue

        if cand_ct == 1 and rcpt_ct == 1:
            # Amount backbone: the amount is 1:1, apply without needing a name.
            inv = ar_amount_groups[ak].iloc[0]
            tentative.append((i, _Application(rec, inv, [("amount", None, 1.0)])))
            # Ground truth for learning: a confident agency that differs from the
            # cleared invoice's agency is an observed "A pays for B" link.
            entity, score = resolve_entity(rec["description"], indexes["agency"])
            if entity is not None and score >= LEARN_THRESHOLD and entity.value != inv["agency"]:
                ledger.observe(entity.value, inv["agency"])
            continue

        # Amount collision (or two receipts on one invoice): disambiguate by name.
        winner, dims = _disambiguate(rec["description"], ar_amount_groups[ak])
        if winner is not None:
            tentative.append((i, _Application(rec, winner, dims)))
        else:
            annot[i] = _review_row(
                rec, "amount matched multiple invoices; description did not disambiguate",
                indexes, ledger, ar_amount_agencies.get(ak, set()) or set(),
            )
            amb_idx.append(i)

    # Collision guard: two receipts resolving to the SAME invoice can't both
    # apply — send the colliders to review.
    inv_claims = pd.Series([a.inv["Internal ID"] for _, a in tentative]).value_counts()
    for i, app in tentative:
        if inv_claims.get(app.inv["Internal ID"], 0) == 1:
            apps.append(app)
        else:
            rec = bank.loc[i]
            annot[i] = _review_row(
                rec, "another receipt resolved to the same invoice",
                indexes, ledger, ar_amount_agencies.get(rec["amount_key"], set()) or set(),
            )
            amb_idx.append(i)

    upload = _build_upload(apps)
    applied_detail = _build_audit(apps)
    ambiguous = _with_annotations(bank.loc[amb_idx], annot)
    unmatched = _with_annotations(bank.loc[unmatched_idx], annot)

    ledger.save()

    return CashApplicationResult(
        upload=upload,
        applied_detail=applied_detail,
        ambiguous=ambiguous,
        unmatched=unmatched,
        _bank_total=len(bank),
        _amount_unique=sum(1 for a in apps if a.matched_by == "amount"),
        _disambiguated=sum(1 for a in apps if a.matched_by != "amount"),
        _corroborated=sum(1 for a in apps if len(a.dims) > 1),
    )


def write_result(result: CashApplicationResult, out_dir: Path) -> Path:
    """Write the upload, an applied-detail audit, and a review file to ``out_dir``.

    Returns the path to the upload CSV. The applied-detail file carries matched-by
    and per-dimension confidence (kept out of the NetSuite upload so its schema is
    unchanged); the review file carries the best-guess agency/insured, their
    confidences, and the reason each receipt was set aside.
    """
    upload_path = out_dir / f"Cash Application Upload - {date.today()}.csv"
    result.upload.to_csv(upload_path, index=False)

    if not result.applied_detail.empty:
        result.applied_detail.to_csv(
            out_dir / f"Cash Application Applied Detail - {date.today()}.csv",
            index=False,
        )

    base_cols = ["data_date", "payment_date", "account", "description", "amount",
                 "subsidiary", "currency"]
    dim_cols = [f"{d.name}_matched" for d in DIMENSIONS] + [
        f"{d.name}_confidence" for d in DIMENSIONS
    ]
    review_cols = base_cols + dim_cols + ["likely_target", "reason"]
    review = pd.concat([result.ambiguous, result.unmatched])
    if not review.empty:
        keep = [c for c in review_cols if c in review.columns]
        review[keep].to_csv(
            out_dir / f"Cash Application Review - {date.today()}.csv", index=False
        )
    return upload_path
