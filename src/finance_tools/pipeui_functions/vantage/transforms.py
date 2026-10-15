"""Vantage Day 3 account current — the transforms that turn the joined "STMVantageAccountCurrentResults256"
report into the file sent to Vantage, ported for pipeui.

pipeui only registers functions DEFINED in the file, so the helpers shared with the Allianz US
transforms (``_num``, ``_pct``, ``_package_keys``) are copied inline (``_``-prefixed helpers are
skipped by discovery).

Pipeline on the report, in order (``finance-tools vantage-bdx setup`` wires it):

  per-column steps  parse_datetime_column, format_percentage_column, format_zip_column,
                    aspen_fix_string_to_limit
  join  STM Limits              Internal ID = Internal ID                     (raw)
  join  Antares                 External ID = Transaction ID                  (raw)
  join  Endorsements            Endorsement UUID (endts only) = Endorsement Uuid (raw)
  join  Master                  Internal ID = Master Internal ID              (transformed)
  set   "Vantage BDX"           vantage_master_gate → vantage_relabel_transactions
                                → vantage_apply_limits → vantage_module → vantage_package_key
                                → allianz_us_formats
  rename / select_columns       the sent file's names and column order

Rules checked against the July and September 2026 sends:
- The month's rows are the ones the month's Master tab gives Vantage a share of.
- Every limit column is the STM Limits report's 100% limit × Vantage Quota Share %, blank as 0.
- Module is the Full Policy's version suffix (``CCP1097926-03`` → 3), 0 when it has none.
- Dates go out with two-digit years, as sent ('1/1/70 00:00').
"""
import json

import pandas as pd

# Limit columns, as the joined report names them (the STM Limits report's names). All of them go
# out at Vantage's share.
LIMIT_FIELDS = (
    "Network and Information Security", "Regulatory Fines and Penalties", "Multimedia Content",
    "PCI Fines and Assessments", "Breach Response", "Breach Response Costs Sublimit",
    "Crisis Management and Public Relationship", "Ransomware and Cyber Extortion",
    "Business Interruption and Extra Expense", "Digital Asset Restoration", "Funds Transfer Fraud",
    "Reputation Repair", "BI/PD - Third Party", "BI/PD - First Party", "Pollution",
    "Systems Integrity Restoration", "Computer Replacement", "Technology E&O", "Service Fraud",
    "Reputational Harm Loss", "Proof of Loss Preparation Expenses Sublimit", "Invoice Manipulation Sublimit",
    "Phishing/Impersonation Repair", "Funds Transfer Liability Sublimit", "Criminal Reward Sublimit",
    "Court Attendance Sublimit", "MPL Sublimit", "Breach Response Separate Limit",
    "DBI Security Failure", "DBI Voluntary Shutdown", "DBI Systems Failure",
    "Contingent Business Interruption (CBI)", "CBI Security Failure", "CBI System Failure",
    "CBI Voluntary Shutdown", "CBI Non IT Security Failure", "CBI Non IT System Failure",
    "Missed Bid", "Corrective Action Plan", "Enhanced Privacy", "Per Event Limit", "Non-IT Vendor CBI",
    "Data Recovery and Computer Replacement Costs",
)

QUOTA_SHARE = "Vantage Quota Share %"
MASTER_QUOTA_SHARE = "Master Vantage Quota Share"


def _num(values: pd.Series) -> pd.Series:
    """Numbers from a column that may hold '$1,234', '12.5%', '(100)' or real numbers. Blank → NaN."""
    if pd.api.types.is_numeric_dtype(values):
        return values.astype(float)
    text = values.astype("string").str.strip()
    negative = text.str.startswith("(") & text.str.endswith(")")
    text = text.str.replace(r"[$,%()\s]", "", regex=True)
    out = pd.to_numeric(text, errors="coerce")
    return out.where(~negative.fillna(False), -out)


def _pct(values: pd.Series) -> pd.Series:
    """A percent column ('5.00%' or 5.0) as a fraction (0.05). Blank → 0."""
    return _num(values).fillna(0) / 100


def _limit(values: pd.Series) -> pd.Series:
    """A limit column as a number: blank / '-' / 'none' / 'no' → 0, '$1,000' → 1000, sign kept."""
    text = values.astype("string").str.strip().str.lower()
    text = text.mask(text.isin(["", "-", "none", "no", "nan", "<na>"]), "0")
    return _num(text).fillna(0)


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


def parse_datetime_column(field: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(field, errors="coerce", format="mixed")
    formatted = parsed.dt.strftime("%-m/%-d/%y %-H:%M")
    fallback = field.astype(object).where(field.notna(), "")
    return formatted.where(formatted.notna(), fallback)


def vantage_master_gate(df: pd.DataFrame) -> pd.DataFrame:
    """Keeps only transactions the month's Master tab gives Vantage a share of."""
    on_master = _num(df[MASTER_QUOTA_SHARE]).fillna(0) > 0
    return df[on_master.fillna(False)].reset_index(drop=True)


def vantage_relabel_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Soft deletes and binder edits relabelled (otc ``clean_description``, as the Allianz US
    transforms do; Transaction Type and External ID are left as NetSuite sends them).

    - soft delete → 'Cancellation - Flat' when TBP < 0, else 'Endorsement'
    - binder edit (External ID ending BE1/BE3/BE5, not an Endorsement) → 'Cancellation - Flat'
      when TBP < 0, 'Reinstatement' when TBP > 0
    """
    df = df.copy()
    tbp = _num(df["Total Bound Premium"]).fillna(0)
    description = df["Transaction Description"].astype("string").fillna("")

    soft = description == "soft delete"
    description = description.mask(soft & (tbp < 0), "Cancellation - Flat")
    description = description.mask(soft & ~(tbp < 0), "Endorsement")

    last_segment = df["External ID"].astype("string").fillna("").str.split("-").str[-1]
    binder_edit = last_segment.isin(["BE1", "BE3", "BE5"]) & (description != "Endorsement")
    description = description.mask(binder_edit & (tbp < 0), "Cancellation - Flat")
    description = description.mask(binder_edit & (tbp > 0), "Reinstatement")
    df["Transaction Description"] = description
    return df


def vantage_apply_limits(df: pd.DataFrame) -> pd.DataFrame:
    """Limit columns as numbers (blank → 0), scaled to Vantage's quota share."""
    df = df.copy()
    quota_share = _pct(df[QUOTA_SHARE])
    for field in LIMIT_FIELDS:
        if field in df.columns:
            df[field] = _limit(df[field]) * quota_share
    return df


def vantage_module(df: pd.DataFrame) -> pd.DataFrame:
    """``Module``: the Full Policy's version suffix (``CCP1097926-03`` → 3), 0 when it has none."""
    df = df.copy()
    suffix = df["Full Policy"].astype("string").str.extract(r"^[A-Za-z]+\d+-(\d+)$")[0]
    df["Module"] = pd.to_numeric(suffix, errors="coerce").fillna(0).astype(int)
    return df


def vantage_package_key(df: pd.DataFrame) -> pd.DataFrame:
    """``Package Key`` from the joined Endorsements' Config. $0 endorsement replacements stay in."""
    df = df.copy()
    df["Package Key"] = df["Config"].map(_package_keys) if "Config" in df.columns else None
    return df
