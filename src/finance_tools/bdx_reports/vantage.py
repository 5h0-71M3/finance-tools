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
from finance_tools.bdx_reports.manifest import BDX_REPORTS

ANTARES = next(spec for spec in BDX_REPORTS if spec.name == "Antares (Modded for Cyber)")
"""Looker 4136: Quote N Employees and Excess Attachment Point, joined on External ID = Transaction ID."""

AC_REPORT = "Vantage AC"
AC_SAMPLE = "STMVantageAccountCurrentResults575.csv"

FUNCTION_SET = "Vantage BDX"
SET_MEMBERS = (  # the gate first: it cuts the full-history Account Current to the month's rows
    "vantage_master_gate", "vantage_relabel_transactions", "vantage_apply_limits", "vantage_antares_fields",
    "vantage_module", "vantage_package_key", "vantage_sequence",
)
SHARED_MEMBERS = ("allianz_us_formats",)
"""Members reused from the Allianz US transforms (yes/no columns written as 'Yes' / 'No')."""
SET_ORDER = (*SET_MEMBERS[:-1], *SHARED_MEMBERS, "vantage_sequence")
"""The set's run order: the row number last."""
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

# The sent file's columns, in order (Sept 2026 send).
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
    "Per Event Limit", "Account Domain Names", "Employee Count", "NAICS Industry Code", "Industry Classification",
    "Anyone Claim (Unlimited Reinstatements)", "Non-IT Vendor CBI", "Package Key", "Run Off [Y/N]",
    "Run Off Start Date", "Run Off End Date", "Attachment Point", "Data Recovery and Computer Replacement Costs",
    "Sequence",
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

    # Employee Count and Attachment Point come from the joined Antares report. Its pattern was saved
    # with bare parentheses, a regex group, so no "Antares (Modded for Cyber) <ts>" file ever matched
    # and the watch folder stopped loading it: give it the manifest's escaped pattern.
    antares = next((s for s in sources if s["source_name"].startswith(ANTARES.name)), None)
    if antares is not None and antares.get("pattern") != ANTARES.pattern:
        client.patch_source(antares["source_id"], {"pattern": ANTARES.pattern})
        done.append(f"{antares['source_name']}: pattern fixed to {ANTARES.pattern}")

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
        FUNCTION_SET, [fn[name] for name in SET_ORDER],
        "Vantage Day 3 account current: the month's Master rows, soft deletes / binder edits "
        "relabelled, limits at Vantage's share, Employee Count / Attachment Point from Antares, "
        "Module, Package Key, Yes/No columns as sent and the Sequence row number.",
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
    """The month's sent file in ``sent_dir``: ``VantageAccountCurrentResults<YYYYMM> (Updated).csv``
    when there is one (the corrected resend), else the plain .csv, else the .xlsx."""
    stem = f"VantageAccountCurrentResults{month.replace('-', '')}"
    candidates = (f"{stem} (Updated).csv", f"{stem}.csv", f"{stem}.xlsx")
    return next((sent_dir / name for name in candidates if (sent_dir / name).exists()), None)


def check(client, month: str, sent_dir: Path) -> tuple[dict, list[A.BookParity]]:
    """Builds the month's file in pipeui (as the Build output files button does) and compares it with
    the one sent in ``sent_dir``. Returns (the build response, parity — empty without a sent file)."""
    built = client.build_outputs(_report(client.sources())["source_id"], month)
    sent = sent_file(sent_dir, month)
    if sent is None or not built["files"]:
        return built, []
    sent_df = A.read_deliverable(sent)
    sent_df = sent_df.drop(columns=[c for c in sent_df.columns if c.startswith("Unnamed:")])
    built_df = A.read_deliverable(Path(built["files"][0]["path"]))
    # Sequence is a row counter, and the sent file's row order isn't NetSuite's: check it counts 1..N
    # instead of comparing it per Internal ID.
    parity = A.compare_book(f"Vantage ({sent.name})", built_df.drop(columns=["Sequence"], errors="ignore"),
                            sent_df.drop(columns=["Sequence"], errors="ignore"))
    if "Sequence" in built_df.columns and list(built_df["Sequence"]) != [str(n) for n in range(1, len(built_df) + 1)]:
        parity.column_diffs["Sequence"] = len(built_df)
        parity.examples["Sequence"] = [("", "not 1..N", "1..N")]
    return built, [parity]
