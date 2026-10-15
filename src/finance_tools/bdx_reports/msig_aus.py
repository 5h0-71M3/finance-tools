"""MSIG Australia Day 10 account current in pipeui: the one-time wiring, and a check of a build
against the file that was sent.

The "MSIG AUS AC" report (NetSuite search 9357, full history) is joined to the STM Limits,
Endorsements, STM Transaction Report, Endorsement Query, MSIG Australia Risk BDX and Master
reports. The "MSIG AUS BDX" set (``pipeui_functions/msig_aus/transforms.py``) keeps the month's
Master rows, ports otc's ``MSIGBDX`` premium fixes and builds MSIG's new written format
(2026.10.14 field list); ``select_columns`` puts it in MSIG's order, and the report's Output
writes ``MSIGAccountCurrentResults - <YYYY>.<MM>.xlsx`` plus a control file (Data → the report →
Outputs → Build output files). ``setup_pipeline`` creates all of that; ``check`` builds a month
and diffs it against the file sent in the old layout.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from finance_tools.bdx_reports import allianz_us as A
from finance_tools.pipeui_functions.msig_aus import transforms as T

AC_REPORT = "MSIG AUS AC"
AC_SAMPLE = "MSIGAUSAccountCurrentResults101.csv"

FUNCTION_SET = "MSIG AUS BDX"
SET_MEMBERS = (  # the renewal flag before the gate: it needs each policy's full history
    "msig_renewal_indicator", "msig_master_gate", "msig_relabel_transactions", "msig_premium_formats",
    "msig_apply_limits", "msig_new_format_fields",
)
TRANSFORMS_FILE = "pipeui_functions/msig_aus/transforms.py"

TXN_PREP = "select_columns + rename"
"""The STM Transaction Report's prep: SQL built-ins, not a Python step (too big for the 30s worker)."""
TXN_RENAMES = {"renames": {A.KEY: "Txn Internal ID", **{f: f"Txn {f}" for f in T.TRANSACTION_REPORT_FIELDS}}}
TXN_SELECT = {"columns": list(TXN_RENAMES["renames"].values()), "excluded": []}
"""pipeui orders the rename first, so the select names the renamed columns."""

# (report name, sample export, the report's step or None, left column, right column)
JOINS = (
    ("STM Limits Report", "DataQualityLimitsSTMResults217.csv", None, A.KEY, A.KEY),
    ("Endorsements", "Endorsements 2026-10-01T1601.csv", None, "Endorsement UUID (endts only)", "Endorsement Uuid"),
    ("STM Transaction Report", "DataQualityDailyTransactionCheckAllTransactionsSTMResults570.csv",
     TXN_PREP, A.KEY, "Txn Internal ID"),
    ("Endorsement Query", "Endorsement Query_2026-10-08-1409.csv",
     "msig_endorsement_exemptions", "Coalition Policy Number", "EQ Coalition Policy Number"),
    ("MSIG Australia Risk BDX", "MSIG Australia Risk BDX 2026-10-09T1616.xlsx",
     "msig_risk_columns", "Coalition Policy Number", "Risk Policy Number"),
)
"""Right-hand reports with a step are joined on that step's (prefixed) output, the rest raw."""

# MSIG's written format, in their order (msi_new_written_format, 2026.10.14). The first 49 are the
# NetSuite search's columns, as sent today. "Insured Name" is listed twice there; it goes out once.
EXISTING_COLUMNS: tuple[str, ...] = (
    "Internal ID", "Insured Name", "Trading As", "Client ID", "Coalition Policy Number", "Policy Effective Date",
    "Policy Expiration Date", "Policy Product Type", "Policy Product Class", "Transaction Type",
    "Transaction Effective Date", "Sum Insured / Policy Limits", "Excess", "State of Risk", "Risk Postcode",
    "Annual Gross Written Premium", "Gross Commission", "Annual GST", "Australia NSW SD", "Australia QLD SD",
    "Australia ACT SD", "Australia VIC SD", "Australia NT SD", "Australia SA SD", "Australia WA SD",
    "Australia TAS SD", "Australia Overseas SD", "Distribution Channel", "Payment Terms", "Broker Name",
    "Broker ABN", "Insured ABN", "Insured GST Status", "Policy Type", "Gross Premium Amount", "Base Premium Amount",
    "Premium GST", "Stamp Duty Total", "Broker ID", "Commission / Brokerage Amount", "GWP ACT Premium",
    "GWP NSW Premium", "GWP NT Premium", "GWP Overseas Premium", "GWP QLD Premium", "GWP SA Premium",
    "GWP TAS Premium", "GWP VIC Premium", "GWP WA Premium",
)
NEW_COLUMNS: tuple[str, ...] = (
    "Transaction Description", "Endorsement Effective Date", "Cancellation Effective Date",
    "Policy Status Indicator", "Renewal of Policy", "Renewal Indicator (Y/N)",
    "ACT SD Duty Exempt Indicator (Y/N)", "NSW SD Duty Exempt Indicator (Y/N)", "NT SD Duty Exempt Indicator (Y/N)",
    "Overseas SD Duty Exempt Indicator (Y/N)", "QLD SD Duty Exempt Indicator (Y/N)",
    "SA SD Duty Exempt Indicator (Y/N)", "TAS SD Duty Exempt Indicator (Y/N)", "VIC SD Duty Exempt Indicator (Y/N)",
    "WA SD Duty Exempt Indicator (Y/N)", "Distribution Channel (Specify)", "BI/PD - First Party",
    "BI/PD - Third Party", "Breach Response", "Breach Response Cost", "Business Interruption And Extra Expense",
    "Computer Replacement", "Court Attendance Sublimit", "Criminal Reward Sublimit",
    "Crisis Management and Public Relationship", "Cyber Extortion", "Digital Asset Restoration",
    "Funds Transfer Fraud", "Funds Transfer Liability Sublimit", "Invoice Manipulation Sublimit", "MPL Sublimit",
    "Multimedia Content", "Network and Information Security", "PCI Fines and Assessments", "Phising Sublimit",
    "Pollution", "Proof of Loss Preparation Expenses", "Regulatory Fines and Penalties", "Reputation Repair",
    "Reputational Harm Loss", "Service Fraud", "System Integrity Restoration", "TCPA", "Technology E&O",
    "GICS Code", "Industry Category", "Industry Name", "N Employees", "Company Revenue", "Agg Limit", "Retention",
    "Enhanced Waiting Period (Y/N)", "ERP Tail Date", "Excess Layer", "Extended Reporting Period",
    "Insured Address Line 1", "Insured Address Line 2", "Insured City", "Insured Primary URL", "Insured State",
    "Insured Zip Code", "Broker Address", "Broker City", "Broker State", "Broker Zip Code",
)
SENT_COLUMNS: tuple[str, ...] = EXISTING_COLUMNS + NEW_COLUMNS

OUTPUT = {
    "name": "MSIG Australia",
    "file_name": "MSIGAccountCurrentResults - {YYYY}.{MM}.xlsx",
    "format": "xlsx",
    "filter_column": None,
    "filter_value": None,
    "columns": list(SENT_COLUMNS),
}
CONTROL_FILE = {
    "file_name": "MSIG Control - {YYYY-MM}.csv", "sum_column": "Base Premium Amount",
    "sum_label": "Base Premium Amount", "label_prefix": "MSIG",
}
SENT_FOLDER = "Day 10"
"""Where the month's sent file lives, under Account Current/<YYYY-MM>."""


def setup_pipeline(client) -> list[str]:
    """Wires the MSIG Australia report in pipeui; safe to re-run (only what's missing or different
    changes). Returns what was done."""
    done = []
    client.scan_functions()
    steps = tuple(join[2] for join in JOINS if join[2] and join[2] != TXN_PREP)
    fn = {
        **A._function_ids(client, SET_MEMBERS + steps, TRANSFORMS_FILE),
        **A._function_ids(client, ("allianz_master_columns",)),
    }
    sources = client.sources()
    ac = _report(sources)
    sid = ac["source_id"]
    master = A._report_for(sources, A.MASTER_REPORT, A.MASTER_SAMPLE)
    joins = [
        (A._report_for(sources, name, sample), step, left, right)
        for name, sample, step, left, right in JOINS
    ] + [(master, "allianz_master_columns", A.KEY, "Master Internal ID")]

    joined = {s["builtin_config"]["right_source_id"] for s in client.pipeline(sid) if s.get("builtin_type") == "join"}
    for right, step, left_col, right_col in joins:
        if step == TXN_PREP:
            done += _ensure_txn_prep(client, right)
        elif step and A._ensure_function_step(client, right["source_id"], fn[step], step):
            done.append(f"attached {step} to {right['source_name']}")
        if right["source_id"] in joined:
            continue
        client.attach_builtin(sid, "join", {
            "right_source_id": right["source_id"], "join_type": "left", "use_transformed": step is not None,
            "on": [{"left_col": left_col, "right_col": right_col}], "keep_columns": "all",
        })
        done.append(f"joined {right['source_name']} on {left_col} = {right_col}")

    set_id = client.save_function_set(
        FUNCTION_SET, [fn[name] for name in SET_MEMBERS],
        "MSIG Australia Day 10 account current: the month's Master rows, otc's MSIGBDX premium fixes, "
        "and MSIG's new written format (sublimits at MSIG's share, renewal / cancellation / endorsement "
        "fields, stamp duty exemptions, industry).",
    )
    if not any(s.get("set_id") == set_id for s in client.pipeline(sid)):
        client.attach_step(sid, set_id=set_id)
        done.append(f"attached set {FUNCTION_SET}")

    select = {"columns": list(SENT_COLUMNS), "excluded": []}
    existing = next((s for s in client.pipeline(sid) if s.get("builtin_type") == "select_columns"), None)
    if existing is None:
        client.attach_builtin(sid, "select_columns", select)
        done.append("attached select_columns")
    elif existing["builtin_config"].get("columns") != select["columns"]:
        client.patch_builtin(sid, existing["step_id"], select)
        done.append("updated select_columns")

    current = client.outputs(sid)
    as_saved = [{k: o.get(k) for k in OUTPUT} for o in current["outputs"]]
    if as_saved != [OUTPUT] or current.get("summary") != CONTROL_FILE:
        client.save_outputs(sid, [OUTPUT], CONTROL_FILE)
        done.append(f"saved the output {OUTPUT['file_name']} and the control file")
    return done


def _ensure_txn_prep(client, report: dict) -> list[str]:
    """The STM Transaction Report's prep: select_columns, then rename to ``Txn *``. Replaces the
    Python step first used for it (``msig_transaction_report_columns``), which timed out."""
    done, sid = [], report["source_id"]
    for step in client.pipeline(sid):
        if step.get("set_name") == "msig_transaction_report_columns":
            client.detach_step(sid, step["source_function_map_id"])
            done.append(f"detached msig_transaction_report_columns from {report['source_name']}")
    for builtin_type, config, key in (("select_columns", TXN_SELECT, "columns"), ("rename", TXN_RENAMES, "renames")):
        existing = next((s for s in client.pipeline(sid) if s.get("builtin_type") == builtin_type), None)
        if existing is None:
            client.attach_builtin(sid, builtin_type, config)
            done.append(f"attached {builtin_type} to {report['source_name']}")
        elif existing["builtin_config"].get(key) != config[key]:
            client.patch_builtin(sid, existing["step_id"], config)
            done.append(f"updated {builtin_type} on {report['source_name']}")
    return done


def _report(sources: list[dict]) -> dict:
    return A._report_for(sources, AC_REPORT, AC_SAMPLE)


def sent_file(sent_dir: Path, month: str) -> Path | None:
    """The month's sent file: otc names it ``MSIGAccountCurrentResults - September 2026.xlsx``."""
    name = pd.Timestamp(f"{month}-01").strftime("MSIGAccountCurrentResults - %B %Y.xlsx")
    path = sent_dir / name
    return path if path.exists() else None


def as_new_format(sent: pd.DataFrame) -> pd.DataFrame:
    """A file sent in the old layout, with its stamp duty exemption columns under the new names and
    values (Yes / No → Y / N), so it compares with a build."""
    sent = sent.drop(columns=[c for c in sent.columns if c.startswith("Unnamed:")])
    for field, indicator in T.EXEMPT_INDICATORS.items():
        if field in sent.columns:
            sent[indicator] = sent.pop(field).map({"Yes": "Y", "No": "N"})
    return sent


def check(client, month: str, sent_dir: Path) -> tuple[dict, list[A.BookParity]]:
    """Builds the month's file in pipeui (as the Build output files button does) and compares it with
    the one sent in ``sent_dir`` on the columns that file has. Returns (the build response, parity —
    empty without a sent file)."""
    built = client.build_outputs(_report(client.sources())["source_id"], month)
    sent = sent_file(sent_dir, month)
    path = next((Path(f["path"]) for f in built["files"] if f["name"] == OUTPUT["name"]), None)
    if sent is None or path is None:
        return built, []
    sent_df = as_new_format(A.read_deliverable(sent))
    built_df = A.read_deliverable(path)
    return built, [A.compare_book(f"MSIG Australia ({sent.name})", built_df, sent_df)]
