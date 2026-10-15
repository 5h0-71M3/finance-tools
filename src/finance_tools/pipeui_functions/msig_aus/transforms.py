"""MSIG Australia Day 10 account current — the transforms that turn the joined "MSIG AUS AC" report
(NetSuite search 9357, full history) into the file sent to MSIG, ported from otc ``MSIGBDX``
(``carrier/bdx.py``) and extended to MSIG's new written format (2026.10.14 field list).

pipeui only registers functions DEFINED in the file, so ``_num`` / ``_limit`` / ``_package_keys``
are copied inline (``_``-prefixed helpers are skipped by discovery).

Pipeline on the report, in order (``finance-tools msig-aus-bdx setup`` wires it):

  join  STM Limits              Internal ID = Internal ID                              (raw)
  join  Endorsements            Endorsement UUID (endts only) = Endorsement Uuid       (raw)
  join  STM Transaction Report  Internal ID = Txn Internal ID      (select_columns + rename: Txn *)
  join  Endorsement Query       Coalition Policy Number = EQ Coalition Policy Number
                                                                   (msig_endorsement_exemptions)
  join  MSIG Australia Risk BDX Coalition Policy Number = Risk Policy Number  (msig_risk_columns)
  join  Master                  Internal ID = Master Internal ID   (allianz_master_columns)
  set   "MSIG AUS BDX"          msig_renewal_indicator → msig_master_gate → msig_relabel_transactions
                                → msig_premium_formats → msig_apply_limits → msig_new_format_fields
  select_columns                MSIG's field list, in order

Rules (otc ``MSIGBDX`` + ``MasterFile.as_account_current``):
- The month's rows are the ones the month's Master gives MSIG a share of, on the AUS subsidiary.
- Soft deletes become 'Cancellation - Flat' (AGWP < 0) or 'Endorsement'.
- GST is 10% of premium; Gross Premium = Base + GST + Stamp Duty; the state SD / GWP columns carry
  AGWP's sign and are put at MSIG's share. Sum Insured, Excess and the other premium columns
  already come from NetSuite at MSIG's share.
- Sublimits are the STM Limits report's 100% limits × MSIG Quota Share; Agg Limit and Retention
  go out at 100% (as in MSIG's sample row).
"""
import json

import pandas as pd

QUOTA_SHARE = "MSIG Quota Share"
"""A fraction on the Account Current (0.25)."""
MASTER_QUOTA_SHARE = "Master MSIG Quota Share"
AUS_SUBSIDIARY = "Coalition AUS"
GST_RATE = 0.1

SD_STATES = ("NSW", "QLD", "ACT", "VIC", "NT", "SA", "WA", "TAS", "Overseas")
STATE_PREMIUM_COLUMNS = (
    *(f"Australia {state} SD" for state in SD_STATES),
    "GWP ACT Premium", "GWP NSW Premium", "GWP NT Premium", "GWP Overseas Premium", "GWP QLD Premium",
    "GWP SA Premium", "GWP TAS Premium", "GWP VIC Premium", "GWP WA Premium",
)
"""Signed by AGWP and put at MSIG's share (otc ``premium_columns``)."""

EXEMPT_STATES = ("NSW", "VIC", "QLD", "WA", "SA", "ACT", "TAS", "NT", "OVERSEAS")
EXEMPT_FIELDS = tuple(f"REVENUE_AU_{state}_PERCENTAGE_EXEMPT" for state in EXEMPT_STATES)
"""The Endorsement Query's stamp duty exemptions (Yes / No), one per state."""
EXEMPT_INDICATORS = {
    "REVENUE_AU_ACT_PERCENTAGE_EXEMPT": "ACT SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_NSW_PERCENTAGE_EXEMPT": "NSW SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_NT_PERCENTAGE_EXEMPT": "NT SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_OVERSEAS_PERCENTAGE_EXEMPT": "Overseas SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_QLD_PERCENTAGE_EXEMPT": "QLD SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_SA_PERCENTAGE_EXEMPT": "SA SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_TAS_PERCENTAGE_EXEMPT": "TAS SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_VIC_PERCENTAGE_EXEMPT": "VIC SD Duty Exempt Indicator (Y/N)",
    "REVENUE_AU_WA_PERCENTAGE_EXEMPT": "WA SD Duty Exempt Indicator (Y/N)",
}

# MSIG's sublimit column ← the STM Limits report's (None: no source, goes out as 0).
SUBLIMITS = {
    "BI/PD - First Party": "BI/PD - First Party",
    "BI/PD - Third Party": "BI/PD - Third Party",
    "Breach Response": "Breach Response",
    "Breach Response Cost": "Breach Response Costs Sublimit",
    "Business Interruption And Extra Expense": "Business Interruption and Extra Expense",
    "Computer Replacement": "Computer Replacement",
    "Court Attendance Sublimit": "Court Attendance Sublimit",
    "Criminal Reward Sublimit": "Criminal Reward Sublimit",
    "Crisis Management and Public Relationship": "Crisis Management and Public Relationship",
    "Cyber Extortion": "Ransomware and Cyber Extortion",
    "Digital Asset Restoration": "Digital Asset Restoration",
    "Funds Transfer Fraud": "Funds Transfer Fraud",
    "Funds Transfer Liability Sublimit": "Funds Transfer Liability Sublimit",
    "Invoice Manipulation Sublimit": "Invoice Manipulation Sublimit",
    "MPL Sublimit": "MPL Sublimit",
    "Multimedia Content": "Multimedia Content",
    "Network and Information Security": "Network and Information Security",
    "PCI Fines and Assessments": "PCI Fines and Assessments",
    "Phising Sublimit": "Phishing/Impersonation Repair",  # MSIG's spelling
    "Pollution": "Pollution",
    "Proof of Loss Preparation Expenses": "Proof of Loss Preparation Expenses Sublimit",
    "Regulatory Fines and Penalties": "Regulatory Fines and Penalties",
    "Reputation Repair": "Reputation Repair",
    "Reputational Harm Loss": "Reputational Harm Loss",
    "Service Fraud": "Service Fraud",
    "System Integrity Restoration": "Systems Integrity Restoration",
    "TCPA": None,  # US-only cover, not on the STM Limits report
    "Technology E&O": "Technology E&O",
}

# STM Transaction Report columns the file uses. Its prep is SQL built-ins (select_columns, then rename
# to ``Txn <field>``): at 732k rows x 173 columns a Python step outruns pipeui's 30s worker limit.
TRANSACTION_REPORT_FIELDS = (
    "Policy Status Indicator", "GICS Code", "ERP Tail Date", "Extended Reporting Period", "Excess Layer",
    "Insured State",
)
RISK_FIELDS = ("Industry Category", "Industry Name", "N Employees", "Company Revenue")
"""From the MSIG Australia Risk BDX (Looker), one row per policy."""

NO_SOURCE_FIELDS = (
    "Insured Address Line 1", "Insured Address Line 2", "Insured City", "Insured Primary URL",
    "Insured Zip Code", "Broker Address", "Broker City", "Broker State", "Broker Zip Code",
    "Renewal of Policy", "Distribution Channel (Specify)",
)
"""Asked for by MSIG but on no report that covers Australia yet; they go out blank."""

DATE_COLUMNS = (
    "Policy Effective Date", "Policy Expiration Date", "Transaction Effective Date",
    "Endorsement Effective Date", "Cancellation Effective Date", "ERP Tail Date",
)
"""Sent as 'MM-DD-YY' text, as NetSuite exports them and MSIG's format specifies."""

RENEWAL_SUFFIXES = ("RN", "RND")
NEW_SUFFIXES = ("N", "ND")
"""Issuance Transaction IDs end in the business type: CCP1143050-02-TX-1000-RN (D: deleted)."""


def _num(values: pd.Series) -> pd.Series:
    """Numbers from a column that may hold '$1,234', '12.5%', '(100)' or real numbers. Blank → NaN."""
    if pd.api.types.is_numeric_dtype(values):
        return values.astype(float)
    text = values.astype("string").str.strip()
    negative = text.str.startswith("(") & text.str.endswith(")")
    text = text.str.replace(r"[$,%()\s]", "", regex=True)
    out = pd.to_numeric(text, errors="coerce")
    return out.where(~negative.fillna(False), -out)


def _limit(values: pd.Series) -> pd.Series:
    """A limit column as a number: blank / '-' / 'none' / 'no' → 0, '$1,000' → 1000, sign kept."""
    text = values.astype("string").str.strip().str.lower()
    text = text.mask(text.isin(["", "-", "none", "no", "nan", "<na>"]), "0")
    return _num(text).fillna(0)


def _signed(values: pd.Series, sign_of: pd.Series) -> pd.Series:
    """otc parse_numeric_values: |value| with the sign of ``sign_of`` (blank → 0)."""
    magnitude = _num(values).fillna(0).abs()
    return magnitude.where(~(sign_of < 0), -magnitude)


def _yes_no(values: pd.Series) -> pd.Series:
    """'Yes' / 'No' (or True / False) → 'Y' / 'N'; anything else blank."""
    text = values.astype("string").str.strip().str.lower()
    flags = text.map({"yes": "Y", "true": "Y", "y": "Y", "no": "N", "false": "N", "n": "N"})
    return flags.astype(object).where(flags.notna(), None)


def _mm_dd_yy(values: pd.Series) -> pd.Series:
    """Dates (or date text) as 'MM-DD-YY' text; blank → None, unparseable text kept as is."""
    parsed = pd.to_datetime(values, errors="coerce", format="mixed")
    text = parsed.dt.strftime("%m-%d-%y")
    kept = values.astype(object).where(values.notna(), None)
    return text.astype(object).where(parsed.notna(), kept)


def _whole(values: pd.Series, as_type=int) -> pd.Series:
    """Whole numbers (40102010.0 → 40102010, or '40102010' with ``as_type=str``); blank → None."""
    return pd.Series(
        [None if pd.isna(v) else as_type(int(v)) for v in _num(values)], index=values.index, dtype=object,
    )


def _package_keys(config: object) -> object:
    """The endorsement's package keys from its Looker Config JSON (as the Allianz US transforms).

    'endorsement_replacement' when the key is present but empty; ', erp' appended for an ERP;
    'cancellation' overrides everything when there's a cancellation date. None without a Config.
    """
    if config is None or (isinstance(config, float) and pd.isna(config)) or config is pd.NA:
        return None
    try:
        parsed = json.loads(config) if isinstance(config, str) else dict(config)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    keys = parsed.get("package_keys")
    if keys:
        value = ", ".join(keys)
    elif "package_keys" in parsed:
        value = "endorsement_replacement"
    else:
        value = None
    if parsed.get("erp") is not None:
        value = f"{value}, erp"
    if parsed.get("cancellation_date") is not None:
        value = "cancellation"
    return value


# ── right-hand reports (each is that report's only step; the join takes its output) ──────────

def msig_endorsement_exemptions(df: pd.DataFrame) -> pd.DataFrame:
    """Endorsement Query → one row per MSIG Australia policy: ``EQ Coalition Policy Number`` and the
    nine ``REVENUE_AU_*_PERCENTAGE_EXEMPT`` columns (otc ``MSIGBDX._merge_endorsement_query``).

    A policy repeats once per transaction, and about half the rows (mostly soft deletes) carry no
    exemption values, so the latest row that carries any is kept. The query has no Issuance rows:
    a policy with only an Issuance doesn't tie, and goes out blank.
    """
    msig = df[df["CARRIER_BDX_FILE"] == "MSIG Australia"]
    msig = msig[msig[list(EXEMPT_FIELDS)].notna().any(axis=1)].copy()
    msig["EQ Coalition Policy Number"] = msig["COALITION_POLICY_NUMBER"].astype("string").str.strip()
    msig = msig.sort_values("TRANSACTION_CREATION_DATE", kind="stable")
    latest = msig.drop_duplicates("EQ Coalition Policy Number", keep="last")
    return latest[["EQ Coalition Policy Number", *EXEMPT_FIELDS]].reset_index(drop=True)


def msig_risk_columns(df: pd.DataFrame) -> pd.DataFrame:
    """MSIG Australia Risk BDX (Looker) → ``Risk Policy Number`` and the industry / size columns,
    prefixed ``Risk``. One row per policy."""
    out = pd.DataFrame({"Risk Policy Number": df["Policy Number"].astype("string").str.strip()})
    for field in RISK_FIELDS:
        out[f"Risk {field}"] = df[field] if field in df.columns else None
    return out.dropna(subset=["Risk Policy Number"]).drop_duplicates("Risk Policy Number").reset_index(drop=True)


# ── the "MSIG AUS BDX" set ───────────────────────────────────────────────────────────────────

def msig_renewal_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """``Renewal Indicator (Y/N)`` per policy, from its issuance's Transaction ID (STM Limits):
    ``…-RN`` / ``…-RND`` → Y, ``…-N`` / ``…-ND`` → N, else blank. Runs before the gate, on the full
    history, so an endorsement or cancellation gets its policy's flag."""
    df = df.copy()
    suffix = df["Transaction ID (ExtID)"].astype("string").str.split("-").str[-1]
    policy = df["Coalition Policy Number"].astype("string").str.strip()
    renewal = suffix.isin(RENEWAL_SUFFIXES).fillna(False).astype(bool).groupby(policy).transform("any")
    new = suffix.isin(NEW_SUFFIXES).fillna(False).astype(bool).groupby(policy).transform("any")
    df["Renewal Indicator (Y/N)"] = pd.Series(
        ["Y" if r else "N" if n else None for r, n in zip(renewal, new)], index=df.index, dtype=object,
    )
    return df


def msig_master_gate(df: pd.DataFrame) -> pd.DataFrame:
    """Keeps only transactions the month's Master gives MSIG a share of, on the AUS subsidiary."""
    on_master = _num(df[MASTER_QUOTA_SHARE]).fillna(0) > 0
    aus = df["Master Subsidiary"].astype("string").str.strip().str.endswith(AUS_SUBSIDIARY)
    return df[(on_master & aus).fillna(False)].reset_index(drop=True)


def msig_relabel_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """``Transaction Type`` 'soft delete' → 'Cancellation - Flat' when AGWP < 0, else 'Endorsement'
    (otc ``format_transaction_description``)."""
    df = df.copy()
    agwp = _num(df["Annual Gross Written Premium"]).fillna(0)
    kind = df["Transaction Type"].astype("string")
    soft = (kind == "soft delete").fillna(False)
    kind = kind.mask(soft & (agwp < 0), "Cancellation - Flat").mask(soft & ~(agwp < 0), "Endorsement")
    df["Transaction Type"] = kind
    return df


def msig_premium_formats(df: pd.DataFrame) -> pd.DataFrame:
    """otc ``MSIGBDX`` premium fixes: GST at 10%, Gross Premium = Base + GST + Stamp Duty, and the
    state SD / GWP columns signed by AGWP and put at MSIG's share (all to 2dp).

    ``Insured GST Status`` goes back to NetSuite's 'T' / 'F': pipeui reads that column as a boolean.
    """
    df = df.copy()
    gst_status = df["Insured GST Status"].map(
        lambda v: "T" if v is True or str(v).strip().lower() in ("t", "true")
        else "F" if v is False or str(v).strip().lower() in ("f", "false") else None
    )
    df["Insured GST Status"] = gst_status.astype(object)
    agwp = _num(df["Annual Gross Written Premium"]).fillna(0)
    base = _num(df["Base Premium Amount"]).fillna(0)
    stamp_duty = _num(df["Stamp Duty Total"]).fillna(0)
    df["Annual GST"] = (agwp * GST_RATE).round(2)
    df["Premium GST"] = (base * GST_RATE).round(2)
    df["Gross Premium Amount"] = (base + df["Premium GST"] + stamp_duty).round(2)
    df["Stamp Duty Total"] = stamp_duty.round(2)
    quota_share = _num(df[QUOTA_SHARE]).fillna(0)
    for column in STATE_PREMIUM_COLUMNS:
        df[column] = (_signed(df[column], agwp) * quota_share).round(2)
    return df


def msig_apply_limits(df: pd.DataFrame) -> pd.DataFrame:
    """MSIG's sublimit columns: the STM Limits report's 100% limit (blank → 0, sign kept) × MSIG
    Quota Share, under MSIG's names (the STM-named column is dropped so no two names differ only by
    case). ``Agg Limit`` / ``Retention`` are the policy's 100% Aggregate Total Limit / SIR, and
    ``Enhanced Waiting Period (Y/N)`` is Y / N."""
    df = df.copy()
    quota_share = _num(df[QUOTA_SHARE]).fillna(0)
    for target, source in SUBLIMITS.items():
        if source is None or source not in df.columns:
            df[target] = 0.0
            continue
        values = df.pop(source) if source != target else df[source]
        df[target] = _limit(values) * quota_share
    df["Agg Limit"] = _limit(df["Aggregate Total Limit"])
    df["Retention"] = _limit(df["SIR"])
    df["Enhanced Waiting Period (Y/N)"] = _yes_no(df["Enhanced Waiting Period (Y/N)"])
    return df


def msig_new_format_fields(df: pd.DataFrame) -> pd.DataFrame:
    """The rest of MSIG's new written format:

    - Transaction Description: the endorsement's package keys (Endorsements Config), else the
      Transaction Type
    - Endorsement / Cancellation Effective Date: the Transaction Effective Date on those rows
    - the nine SD Duty Exempt Indicators: the Endorsement Query's Yes / No as Y / N (blank untied)
    - from the STM Transaction Report: Policy Status Indicator, GICS Code, ERP Tail Date, Extended
      Reporting Period (Y / N), Excess Layer, Insured State
    - from the Risk BDX: Industry Category, Industry Name, N Employees, Company Revenue
    - blank: the fields no Australian report carries yet (``NO_SOURCE_FIELDS``)
    """
    df = df.copy()
    kind = df["Transaction Type"].astype("string")
    package_keys = df["Config"].map(_package_keys) if "Config" in df.columns else pd.Series(None, index=df.index)
    df["Transaction Description"] = package_keys.where(package_keys.notna(), kind).astype(object)

    effective = df["Transaction Effective Date"]
    df["Endorsement Effective Date"] = effective.where((kind == "Endorsement").fillna(False), None)
    df["Cancellation Effective Date"] = effective.where(kind.str.startswith("Cancellation").fillna(False), None)

    for field, indicator in EXEMPT_INDICATORS.items():
        df[indicator] = _yes_no(df[field]) if field in df.columns else None

    for field in TRANSACTION_REPORT_FIELDS:
        df[field] = df.get(f"Txn {field}")
    df["GICS Code"] = _whole(df["GICS Code"], str)  # sent as text, as the Risk BDX sends it
    df["Extended Reporting Period"] = _yes_no(df["Extended Reporting Period"])
    df["Excess Layer"] = _whole(df["Excess Layer"])

    for field in RISK_FIELDS:
        df[field] = df.get(f"Risk {field}")

    for field in NO_SOURCE_FIELDS:
        df[field] = None

    for field in [f for f in DATE_COLUMNS if f in df.columns]:  # pipeui loads NetSuite's date text as
        df[field] = _mm_dd_yy(df[field])                         # dates; MSIG wants MM-DD-YY text
    return df
