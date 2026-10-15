"""Vantage Day 3 account current in pipeui: the one-time wiring, and a check of a build against the
file that was sent.

The "STMVantageAccountCurrentResults256" report (NetSuite search 6490, full history) is joined
to the STM Limits, Antares, Endorsements and Master reports. The "Vantage BDX" set
(``pipeui_functions/vantage/transforms.py``) keeps the month's Master rows and puts the limits at
Vantage's share. ``rename`` / ``select_columns`` give it the sent file's layout, and the report's
Output writes ``VantageAccountCurrentResults<YYYY><MM>.csv`` (Data → the report → Outputs →
Build output files). ``setup_pipeline`` creates all of that; ``check`` builds a month and diffs
it against the sent file.
"""
from __future__ import annotations

from pathlib import Path

from finance_tools.bdx_reports import allianz_us as A

AC_REPORT = "Vantage AC"
AC_SAMPLE = "STMVantageAccountCurrentResults575.csv"

FUNCTION_SET = "Vantage BDX"
SET_MEMBERS = (  # the gate first: it cuts the full-history Account Current to the month's rows
    "vantage_master_gate", "vantage_relabel_transactions", "vantage_apply_limits", "vantage_module",
    "vantage_package_key",
)
SHARED_MEMBERS = ("allianz_us_formats",)
"""Members reused from the Allianz US transforms (yes/no columns written as 'Yes' / 'No')."""
TRANSFORMS_FILE = "pipeui_functions/vantage/transforms.py"

RENAMES = {
    "Breach Response Costs Sublimit": "Breach Response Costs",
    "Ransomware and Cyber Extortion": "Cyber Extortion",
    "Business Interruption and Extra Expense": "Business Interruption And Extra Expense",
    "Proof of Loss Preparation Expenses Sublimit": "Proof of Loss Preparation Expenses",
    "Phishing/Impersonation Repair": "Phising Sublimit",
    "Run-Off": "Run Off [Y/N]",
    "Run-Off Start Date": "Run Off Start Date",
    "Run-Off End Date": "Run Off End Date",
}
"""The joined report's column names → the sent file's."""

# The sent file's columns, in order (Sept 2026 send). Not built: Employee Count (out of scope),
# Attachment Point (no rule yet for the excess rows it's set on) and Sequence (a row number).
SENT_COLUMNS: tuple[str, ...] = (
    "Internal ID", "External ID", "Insured Name", "Policy Type", "Policy Number", "Module", "Full Policy",
    "Coalition Policy Number", "Policy Effective Date", "Policy Expiration Date", "Transaction Effective Date",
    "Date Created", "Transaction Type", "Transaction Description", "Transaction Effective (Bind) Date",
    "Aggregate Total Limit", "Total Limit", "Vantage Quota Share %", "Vantage Limit of Liability", "SIR",
    "Total Bound Premium", "Vantage Bound Premium", "Total Earned Premium", "Total Unearned Premium",
    "Coalition Commission %", "Vantage $ Commission To Coalition", "Vantage Net Premium", "Total TRIA",
    "Vantage TRIA", "Tria Accepted (Yes / No)", "Broker", "Broker Address", "Broker City", "Broker State",
    "Broker Zip Code", "Broker Commission %", "Broker Reported License Number",
    "Reported License Entity / Individual", "Coalition Secondary Review", "Carrier Referral",
    "Account Current Month End", "Current Month End", "Policy Status Indicator", "Comments",
    "Insured Address Line 1", "Insured Address Line 2", "Insured City", "Insured State", "Insured Zip Code",
    "Revenue", "Gross Profit / Net Revenue", "Industry", "GICS Code", "Network and Information Security",
    "Regulatory Fines and Penalties", "Multimedia Content", "PCI Fines and Assessments", "Breach Response",
    "Breach Response Costs", "Crisis Management and Public Relationship", "Cyber Extortion",
    "Business Interruption And Extra Expense", "Enhanced Waiting Period (Y/N)", "Digital Asset Restoration",
    "Funds Transfer Fraud", "Reputation Repair", "BI/PD - Third Party", "BI/PD - First Party", "Pollution",
    "Systems Integrity Restoration", "Computer Replacement", "Technology E&O", "Service Fraud", "TCPA",
    "Primary Insurance", "Reputational Harm Loss", "Insurance Program", "Market", "Retroactive Date",
    "NJ Transaction Number", "Renewal of Policy", "Currency", "Retroactive Short Date",
    "Extended Reporting Period", "ERP Tail Date", "Country", "Primary Carrier",
    "Proof of Loss Preparation Expenses", "Invoice Manipulation Sublimit", "Phising Sublimit",
    "Funds Transfer Liability Sublimit", "Criminal Reward Sublimit", "Court Attendance Sublimit",
    "MPL Sublimit", "Excess Layer", "Surplus 3.0", "Breach Response Separate Limit", "DBI Security Failure",
    "DBI Voluntary Shutdown", "DBI Systems Failure", "Contingent Business Interruption (CBI)",
    "CBI Security Failure", "CBI System Failure", "CBI Voluntary Shutdown", "CBI Non IT Security Failure",
    "CBI Non IT System Failure", "Missed Bid", "Corrective Action Plan", "Enhanced Privacy",
    "Per Event Limit", "Account Domain Names", "NAICS Industry Code", "Industry Classification",
    "Anyone Claim (Unlimited Reinstatements)", "Non-IT Vendor CBI", "Package Key", "Run Off [Y/N]",
    "Run Off Start Date", "Run Off End Date", "Data Recovery and Computer Replacement Costs",
)

OUTPUT = {
    "name": "Vantage",
    "file_name": "VantageAccountCurrentResults{YYYY}{MM}.csv",
    "format": "csv",
    "filter_column": None,
    "filter_value": None,
    "columns": list(SENT_COLUMNS),
}
SENT_FOLDER = "Day 3"
"""Where the month's sent file lives, under Account Current/<YYYY-MM>."""


def setup_pipeline(client) -> list[str]:
    """Wires the Vantage report in pipeui; safe to re-run (only what's missing or different changes).
    Returns what was done."""
    done = []
    client.scan_functions()
    fn = {
        **A._function_ids(client, SET_MEMBERS, TRANSFORMS_FILE),
        **A._function_ids(client, SHARED_MEMBERS + ("allianz_master_columns",)),
    }
    sources = client.sources()
    ac = _report(sources)
    master = A._report_for(sources, A.MASTER_REPORT, A.MASTER_SAMPLE)
    sid = ac["source_id"]

    if A._ensure_function_step(client, master["source_id"], fn["allianz_master_columns"], "allianz_master_columns"):
        done.append(f"attached allianz_master_columns to {master['source_name']}")

    steps = client.pipeline(sid)
    joined = {s["builtin_config"]["right_source_id"] for s in steps if s.get("builtin_type") == "join"}
    if master["source_id"] not in joined:
        client.attach_builtin(sid, "join", {
            "right_source_id": master["source_id"], "join_type": "left", "use_transformed": True,
            "on": [{"left_col": A.KEY, "right_col": "Master Internal ID"}], "keep_columns": "all",
        })
        done.append(f"joined {master['source_name']} on {A.KEY} = Master Internal ID")

    # The month's rows now come from the Master gate, not a date filter.
    for step in [s for s in client.pipeline(sid) if s.get("builtin_type") == "date_range"]:
        client.detach_builtin(sid, step["step_id"])
        done.append("removed the date_range filter (the Master gate picks the month's rows)")

    set_id = client.save_function_set(
        FUNCTION_SET, [fn[name] for name in SET_MEMBERS + SHARED_MEMBERS],
        "Vantage Day 3 account current: the month's Master rows, soft deletes / binder edits "
        "relabelled, limits at Vantage's share, Module, Package Key and Yes/No columns as sent.",
    )
    if not any(s.get("set_id") == set_id for s in client.pipeline(sid)):
        client.attach_step(sid, set_id=set_id)
        done.append(f"attached set {FUNCTION_SET}")

    for builtin_type, config in (
        ("rename", {"renames": RENAMES}),
        ("select_columns", {"columns": list(SENT_COLUMNS), "excluded": []}),
    ):
        key = "renames" if builtin_type == "rename" else "columns"
        existing = next((s for s in client.pipeline(sid) if s.get("builtin_type") == builtin_type), None)
        if existing is None:
            client.attach_builtin(sid, builtin_type, config)
            done.append(f"attached {builtin_type}")
        elif existing["builtin_config"].get(key) != config[key]:
            client.patch_builtin(sid, existing["step_id"], config)
            done.append(f"updated {builtin_type}")

    current = client.outputs(sid)
    as_saved = [{k: o.get(k) for k in OUTPUT} for o in current["outputs"]]
    if as_saved != [OUTPUT]:
        client.save_outputs(sid, [OUTPUT], current.get("summary"))
        done.append(f"saved the output {OUTPUT['file_name']}")
    return done


def _report(sources: list[dict]) -> dict:
    return A._report_for(sources, AC_REPORT, AC_SAMPLE)


def sent_file(sent_dir: Path, month: str) -> Path | None:
    """The newest ``VantageAccountCurrentResults<YYYYMM>*`` in ``sent_dir``."""
    stem = f"VantageAccountCurrentResults{month.replace('-', '')}"
    files = [p for p in sent_dir.glob(f"{stem}*") if p.suffix.lower() in (".csv", ".xlsx")]
    return max(files, key=lambda p: p.stat().st_mtime, default=None)


def check(client, month: str, sent_dir: Path) -> tuple[dict, list[A.BookParity]]:
    """Builds the month's file in pipeui (as the Build output files button does) and compares it with
    the one sent in ``sent_dir``. Returns (the build response, parity — empty without a sent file)."""
    built = client.build_outputs(_report(client.sources())["source_id"], month)
    sent = sent_file(sent_dir, month)
    if sent is None or not built["files"]:
        return built, []
    sent_df = A.read_deliverable(sent)
    sent_df = sent_df.drop(columns=[c for c in sent_df.columns if c.startswith("Unnamed:")])
    return built, [A.compare_book(f"Vantage ({sent.name})", A.read_deliverable(Path(built["files"][0]["path"])), sent_df)]
