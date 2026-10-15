"""Allianz US report (Day 5 BDX) — the transforms that turn the joined Account Current into
the Runoff / Admitted / Non-Admitted deliverables, ported for pipeui.

Ported from otc ``src/carrier/bdx.py`` (``AllianzUSBDX`` / ``AllianzNewPaper``) and
``src/carrier/core/bdx_objects.py`` (``BaseBDX`` helpers), plus the hand edits made to the
Sept 2026 send. otc isn't importable from here, and pipeui only registers functions DEFINED in
the file, so the helpers are copied inline (``_``-prefixed helpers are skipped by discovery).

Pipeline on the "Allianz US AC" report (NetSuite saved search 6418), in order:

  join  Endorsements            Endorsement UUID (endts only) = Endorsement Uuid       (raw)
  join  STM Limits              Internal ID = Internal ID                               (raw)
  join  MPL - Premium Breakdown Coalition Policy Number = MPL Policy Number    (transformed)
  join  Allianz US Master       Internal ID = Master Internal ID              (transformed)
  set   "Allianz US BDX"        allianz_master_gate → allianz_relabel_transactions
                                → allianz_endorsement_package_keys → allianz_apply_limits
                                → allianz_mpl_cyber_split → allianz_us_book
                                → allianz_us_commission_columns → allianz_bookroll_flags
                                → allianz_us_formats → allianz_us_column_names
  select_columns                the deliverable's column order, plus ``Book``

The right-hand reports carry their own one-step pipelines (``mpl_premium_by_policy``,
``allianz_master_columns``) that keep and prefix only the columns the join needs, so nothing
collides with the Account Current's own column names.

Rules taken from the hand edits to the Sept 2026 send (not in otc):
- Multi-National policies (Master tab) go out on their own Multi-National file.
- Runoff goes out without Broker / MGA Commission %; on the new paper, everything outside the
  Large Market program goes out at MGA Commission 33% without Broker Commission %.
- Allianz Bookroll is Yes for manuscripted policy versions. The Sept send overrode this by hand
  on 12 of 36 manuscripted rows; NYFTZ was also typed in by hand.

The report's Outputs (pipeui: Data → Allianz US AC → Outputs) write one file per ``Book`` plus
the Day 5 control file; ``finance-tools allianz-us-bdx setup`` configures them.
"""
import json

import pandas as pd

# Policies effective on or after this date are on the new (Large Market) paper and go out on
# the Admitted / Non-Admitted files; everything else is Runoff. otc: AllianzUSBDX.LARGE_MARKET_START.
LARGE_MARKET_START = pd.Timestamp(2026, 7, 13)

# Master file gate (otc MasterFileTab.as_account_current with AllianzUSBDX.carrier_details).
US_SUBSIDIARY = "ProForma : GAAP : MGA Consolidation : Coalition, Inc"

# Policy versions Allianz takes onto its bookroll (the Master tab's Policy Version).
BOOKROLL_POLICY_VERSION_PREFIX = "coalition_manuscripted"

# The new-paper program that keeps its NetSuite commissions; the rest go out at NEW_PAPER_MGA_COMMISSION.
LARGE_MARKET_PROGRAM = "Large Market"
NEW_PAPER_MGA_COMMISSION = "33.0%"

# Limit columns cleaned to whole numbers carrying the sign of Total Bound Premium (otc bdx.py:98-138).
LIMIT_FIELDS = (
    "Network and Information Security", "Regulatory Fines and Penalties",
    "Multimedia Content", "PCI Fines and Assessments",
    "Breach Response", "Breach Response Costs Sublimit",
    "Crisis Management and Public", "Cyber Extortion",
    "Business Interruption And Extra", "Digital Asset Restoration",
    "Funds Transfer Fraud", "Reputation Repair",
    "BI/PD - Third Party", "BI/PD - First Party",
    "Pollution", "Systems Integrity Restoration",
    "Computer Replacement", "Technology E&O",
    "Service Fraud", "Proof of Loss Preparation Expenses Sublimit",
    "Court Attendance Sublimit", "Criminal Reward Sublimit",
    "Funds Transfer Liability Sublimit", "Phishing Sublimit",
    "Invoice Manipulation Sublimit", "Reputational Harm Loss",
    "Breach Response Costs", "Crisis Management and Public Relationship",
    "Business Interruption And Extra Expense", "Proof of Loss Preparation Expenses",
    "Phising Sublimit", "MPL Sublimit", "Breach Response Cost", "Systems Integrity",
    "Breach Response Separate Limit",
    "DBI Security Failure", "DBI Voluntary Shutdown", "DBI Systems Failure",
    "Contingent Business Interruption (CBI)",
    "CBI Security Failure", "CBI System Failure", "CBI Voluntary Shutdown",
    "CBI Non IT Security Failure", "CBI Non IT System Failure",
    "Missed Bid", "Corrective Action Plan", "Enhanced Privacy", "Per Event Limit",
    "Data Recovery and Computer Replacement Costs",
)

# The limit columns that come from the STM Limits report (100% limits), so they're also scaled
# to Allianz's quota share. The Account Current's own limit columns are already Allianz's share.
STM_QUOTA_SHARED_FIELDS = (
    "Breach Response Separate Limit",
    "DBI Security Failure", "DBI Voluntary Shutdown", "DBI Systems Failure",
    "Contingent Business Interruption (CBI)",
    "CBI Security Failure", "CBI System Failure", "CBI Voluntary Shutdown",
    "CBI Non IT Security Failure", "CBI Non IT System Failure",
    "Missed Bid", "Corrective Action Plan", "Enhanced Privacy", "Per Event Limit",
    "Data Recovery and Computer Replacement Costs",
)

# Columns otc drops before writing (bdx.py:187-194).
DROPPED_COLUMNS = (
    "Unnamed: 0", "Internal ID.1", "Coverage Instances Keys", "Additional Premium", "Config",
    "Quote Status", "Endorsement Created At Date", "ERP Keys", "Cancellation Keys",
)


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
    """A percent column ('14.0%' or 14.0) as a fraction (0.14). Blank → 0. otc format_percentage_to_float."""
    return _num(values).fillna(0) / 100


def _dates(values: pd.Series) -> pd.Series:
    """Dates from NetSuite's 'mm-dd-yy' / Excel's 'm/d/yy' text, or real dates. Unparseable → NaT."""
    if pd.api.types.is_datetime64_any_dtype(values):
        return values
    return pd.to_datetime(values.astype("string"), errors="coerce", format="mixed")


def _yes(values: pd.Series) -> pd.Series:
    """True where a yes/no column says yes, whether pipeui loaded it as text or as a boolean."""
    text = values.astype("string").str.strip().str.lower()
    return text.isin(["yes", "true", "y", "1"]).fillna(False).astype(bool)


def _signed_like(values: pd.Series, tbp: pd.Series) -> pd.Series:
    """``values`` made positive, then negative wherever Total Bound Premium is negative."""
    return values.abs().where(~(tbp < 0), -values.abs())


def _fill_limit(limit: pd.Series, tbp: pd.Series) -> pd.Series:
    """otc BaseBDX.simple_fill_limit: blank / '-' / 'none' / 'no' → 0, '$1,000' → 1000, as a whole
    number carrying the sign of TBP."""
    text = limit.astype("string").fillna("0").str.lower().str.replace("nan", "0").str.strip("$ ")
    text = text.str.replace(",", "").str.replace("-", "0").str.replace("none", "0").str.replace("no", "0")
    whole = pd.to_numeric(text, errors="raise").astype(float).astype(int)
    return _signed_like(whole, tbp)


def _net(bound: pd.Series, commission: pd.Series) -> pd.Series:
    """otc _calculate_net_*: round(bound - bound × commission, 2), row by row (Python's round, so
    cents tie out with what otc sent)."""
    return pd.Series(
        [round(b - b * c, 2) for b, c in zip(bound, commission)], index=bound.index, dtype=float,
    )


def _package_keys(config: object) -> object:
    """otc EndorsementBaseReport._check: the endorsement's package keys from its Looker Config JSON.

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


# ── right-hand reports (each is that report's own one-step pipeline) ─────────────────────────

def mpl_premium_by_policy(df: pd.DataFrame) -> pd.DataFrame:
    """MPL - Premium Breakdown → one row per policy: ``MPL Policy Number``, ``MPL Premium``.

    A policy listed more than once is dropped entirely, as otc does (``keep=False``), so the
    join can't duplicate Account Current rows.
    """
    policy = df["Quote Coalition Policy Number"]
    single = df[~policy.duplicated(keep=False)]
    return pd.DataFrame({
        "MPL Policy Number": single["Quote Coalition Policy Number"].astype("string"),
        "MPL Premium": _num(single["Total Bound MPL Premium"]),
    }).reset_index(drop=True)


def allianz_master_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Master tab of the month's Cyber Masterfile → the columns the Allianz US pipeline needs,
    prefixed: the gate (quota share, subsidiary), the bookroll flag (policy version) and the
    Multi-National split. It also carries Vantage's quota share, for the Vantage report's gate
    (``vantage_master_gate``) — this is the Master report's only step, so the join sees nothing else.

    The report loads with "replace", so it only holds this month's Master. A legacy ``Master Month``
    column (from the old CSV extract) is still honoured — only the newest month is kept, so a
    transaction that dropped off this month's Master can't pass the gate on an old month's row.
    """
    if "Master Month" in df.columns and df["Master Month"].notna().any():
        month = df["Master Month"].astype("string")
        df = df[(month == month.max()).fillna(False)]
    return pd.DataFrame({
        "Master Internal ID": df["Internal ID"],
        "Master Allianz Quota Share": _num(df["Allianz Quota Share"]),
        "Master Subsidiary": df["Subsidiary [Agency Customer]"],
        "Master Policy Version": df["Policy Version"],
        "Master Multi-National": df["Multi-National Policy"],
        "Master Vantage Quota Share": _num(df["Vantage Quota Share"]),
    }).dropna(subset=["Master Internal ID"]).drop_duplicates("Master Internal ID").reset_index(drop=True)


# ── the Allianz US AC pipeline ───────────────────────────────────────────────────────────────

def allianz_relabel_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Soft deletes and binder edits relabelled, Transaction Type set, DELETED ids cleaned.

    - soft delete → 'Cancellation - Flat' when TBP < 0, else 'Endorsement'
    - binder edit (External ID ending BE1/BE3/BE5, not an Endorsement) → 'Cancellation - Flat'
      when TBP < 0, 'Reinstatement' when TBP > 0
    - Transaction Type → 'New' without a Renewal of Policy, else 'Renewal'
    - External ID with a DELETED segment loses the 5 UUID segments after it
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

    renewal = df["Renewal of Policy"]
    df["Transaction Type"] = renewal.isna().map({True: "New", False: "Renewal"})

    def _undelete(tid: object) -> object:
        split = str(tid).split("-")
        if "DELETED" in split:
            del split[3:8]
        return "-".join(split)

    df["External ID"] = df["External ID"].map(_undelete)
    return df


def allianz_endorsement_package_keys(df: pd.DataFrame) -> pd.DataFrame:
    """``Package Keys`` from the joined Endorsements' Config, and $0 endorsement replacements dropped."""
    df = df.copy()
    df["Package Keys"] = df["Config"].map(_package_keys) if "Config" in df.columns else None
    tbp = _num(df["Total Bound Premium"]).fillna(0)
    replacement = (tbp == 0) & (df["Package Keys"] == "endorsement_replacement")
    return df[~replacement].reset_index(drop=True)


def allianz_apply_limits(df: pd.DataFrame) -> pd.DataFrame:
    """Limit columns as whole numbers with TBP's sign; the STM Limits ones scaled to Allianz's share."""
    df = df.copy()
    tbp = _num(df["Total Bound Premium"]).fillna(0)
    quota_share = _pct(df["Allianz Quota Share %"])
    for field in dict.fromkeys(LIMIT_FIELDS):
        if field not in df.columns:
            continue
        df[field] = _fill_limit(df[field], tbp)
        if field in STM_QUOTA_SHARED_FIELDS:
            df[field] = df[field] * quota_share
    return df


def allianz_mpl_cyber_split(df: pd.DataFrame) -> pd.DataFrame:
    """Splits premium into MPL and cyber, at 100% and at Allianz's share, gross and net.

    Total MPL Premium is the policy's MPL premium (100%) with TBP's sign; Allianz's share is
    applied once. Net = share less Coalition commission; cyber net ignores TRIA (otc use_tria=False).
    """
    df = df.copy()
    tbp = _num(df["Total Bound Premium"]).fillna(0)
    quota_share = _pct(df["Allianz Quota Share %"])
    commission = _pct(df["Coalition Commission %"])

    df["MPL Total Limit 100%"] = df["MPL Sublimit"]
    df["Allianz MPL Limit"] = df["MPL Sublimit"]

    mpl = _num(df["MPL Premium"]).fillna(0) if "MPL Premium" in df.columns else pd.Series(0.0, index=df.index)
    df["Total MPL Premium"] = _signed_like(mpl, tbp)
    df["Allianz Bound MPL Premium"] = df["Total MPL Premium"] * quota_share
    df["Allianz Net MPL Premium"] = _net(df["Allianz Bound MPL Premium"], commission)

    df["Total Cyber Premium"] = tbp - df["Total MPL Premium"]
    df["Allianz Bound Cyber Premium"] = df["Total Cyber Premium"] * quota_share
    df["Allianz Net Cyber Premium"] = _net(df["Allianz Bound Cyber Premium"], commission)
    return df


def allianz_master_gate(df: pd.DataFrame) -> pd.DataFrame:
    """Keeps only transactions the month's Master tab gives Allianz a share of, on the US subsidiary."""
    on_master = (_num(df["Master Allianz Quota Share"]).fillna(0) > 0) & (df["Master Subsidiary"] == US_SUBSIDIARY)
    return df[on_master.fillna(False)].reset_index(drop=True)


def allianz_us_book(df: pd.DataFrame) -> pd.DataFrame:
    """``Book``: Runoff before the new paper started (or no effective date); on the new paper,
    Multi-National when the Master tab flags the policy, else Admitted or Non-Admitted by Market."""
    df = df.copy()
    effective = _dates(df["Policy Effective Date"])
    new_paper = (effective >= LARGE_MARKET_START).fillna(False)
    admitted = (df["Market"].astype("string").str.strip().str.upper() == "ADMITTED").fillna(False)
    multinational = _yes(df["Master Multi-National"]) if "Master Multi-National" in df.columns \
        else pd.Series(False, index=df.index)
    df["Book"] = "Runoff"
    df.loc[new_paper & admitted, "Book"] = "Admitted"
    df.loc[new_paper & ~admitted, "Book"] = "Non-Admitted"
    df.loc[new_paper & multinational, "Book"] = "Multi-National"
    return df


def allianz_us_commission_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Broker / MGA Commission % as sent: blank on Runoff; on the new paper outside the Large Market
    program, MGA Commission 33% and Broker Commission blank. Large Market keeps NetSuite's values."""
    df = df.copy()
    runoff = df["Book"] == "Runoff"
    small = ~runoff & (df["Insurance Program"].astype("string").str.strip() != LARGE_MARKET_PROGRAM).fillna(True)
    df["Broker Commission %"] = df["Broker Commission %"].astype("object").mask(runoff | small, None)
    df["MGA Commission %"] = df["MGA Commission %"].astype("object").mask(runoff, None).mask(small, NEW_PAPER_MGA_COMMISSION)
    return df


def allianz_bookroll_flags(df: pd.DataFrame) -> pd.DataFrame:
    """The new-paper bookroll columns: ``Allianz Bookroll`` Yes on a manuscripted policy version
    (Master tab); Captive Frontend / FAC Reinsurance 'No'; NYFTZ left blank (filled by hand)."""
    df = df.copy()
    version = df["Master Policy Version"] if "Master Policy Version" in df.columns else pd.Series(pd.NA, index=df.index)
    on_bookroll = version.astype("string").str.lower().str.startswith(BOOKROLL_POLICY_VERSION_PREFIX).fillna(False)
    df["Allianz Bookroll"] = on_bookroll.map({True: "Yes", False: "No"})
    df["NYFTZ"] = pd.NA
    df["Captive Frontend"] = "No"
    df["FAC Reinsurance"] = "No"
    return df


def allianz_us_formats(df: pd.DataFrame) -> pd.DataFrame:
    """Columns pipeui typed on load, written back the way the deliverable shows them: yes/no
    columns as 'Yes' / 'No' (TCPA as 'TRUE' / 'FALSE'), dates as m/d/yy."""
    df = df.copy()
    for column in df.columns:
        values = df[column]
        if pd.api.types.is_bool_dtype(values) or (
            values.dtype == object and values.dropna().map(type).eq(bool).all() and values.notna().any()
        ):
            words = ("TRUE", "FALSE") if column == "TCPA" else ("Yes", "No")
            df[column] = values.map({True: words[0], False: words[1]}).astype("object")
        elif pd.api.types.is_datetime64_any_dtype(values):
            df[column] = values.map(lambda d: f"{d.month}/{d.day}/{d:%y}" if not pd.isna(d) else None)
    return df


def allianz_us_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """otc's column names after the joins: the Account Current's ``Endorsement Label`` becomes
    ``Endorsement Label_endts`` and the Endorsements copy (``Endorsement Label_1``) takes the plain
    name; otc's dropped columns go."""
    df = df.copy()
    if "Endorsement Label_1" in df.columns:
        df = df.rename(columns={"Endorsement Label": "Endorsement Label_endts"})
        df = df.rename(columns={"Endorsement Label_1": "Endorsement Label"})
    return df.drop(columns=[c for c in DROPPED_COLUMNS if c in df.columns])
