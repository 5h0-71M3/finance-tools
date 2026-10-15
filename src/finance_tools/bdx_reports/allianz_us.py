"""Allianz US Day 5 BDX in pipeui: the one-time wiring, and a check of a build against the files
that were sent.

pipeui does the monthly work from its UI. The "Allianz US AC" report's pipeline (joins + the
``pipeui_functions/allianz_us/transforms.py`` set + select_columns) produces one table with a
``Book`` column; the report's Outputs write one file per Book plus the Day 5 control file
(Data screen → Allianz US AC → Outputs → Build output files). ``setup_pipeline`` creates all
of that; ``check`` builds a month and diffs it against the sent files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

BOOKS = ("Runoff", "Admitted", "Non-Admitted", "Multi-National")
XLSX_BOOKS = ("Multi-National",)
"""Books written as .xlsx (the rest are .csv, as otc writes them)."""

# The deliverable's columns, in order (Sept 2026 send). Runoff stops at the cyber premium;
# the new-paper books add the bookroll columns, and only Admitted gets NYFTZ.
BASE_COLUMNS: tuple[str, ...] = (
    "Internal ID", "External ID", "Insured Name", "Insured Primary URL", "Policy Type", "Policy Number",
    "Module", "Full Policy", "Coalition Policy Number", "Policy Effective Date", "Policy Expiration Date",
    "Transaction Effective Date", "Date Created", "Transaction Type", "Transaction Description",
    "Transaction Effective (Bind) Date", "Aggregate Total Limit", "Total Limit", "Allianz Quota Share %",
    "Allianz Limit of Liability", "SIR / Attachment Point", "Total Bound Premium", "Allianz Bound Premium",
    "Total Earned Premium", "Total Unearned Premium", "Broker Commission %", "MGA Commission %",
    "Coalition Commission %", "Allianz $ Commission To Coalition", "Allianz Net Premium", "Total TRIA",
    "Allianz TRIA", "Tria Accepted (Yes / No)", "Broker", "Broker Address", "Broker City", "Broker State",
    "Broker Zip Code", "Broker Reported License Number", "Reported License Entity / Individual",
    "Coalition Secondary Review", "Carrier Referral", "Account Current Month End", "Current Month End",
    "Policy Status Indicator", "Comments", "Insured Address Line 1", "Insured Address Line 2", "Insured City",
    "Insured State", "Insured Zip Code", "Revenue", "Gross Profit / Net Revenue", "Industry", "GICS Code",
    "Network and Information Security", "Regulatory Fines and Penalties", "Multimedia Content",
    "PCI Fines and Assessments", "Breach Response", "Crisis Management and Public Relationship",
    "Cyber Extortion", "Business Interruption And Extra Expense", "Digital Asset Restoration",
    "Funds Transfer Fraud", "Reputation Repair", "BI/PD - Third Party", "BI/PD - First Party", "Pollution",
    "Computer Replacement", "Technology E&O", "Service Fraud", "Reputational Harm Loss",
    "Enhanced Waiting Period (Y/N)", "TCPA", "Insurance Program", "Market", "Retroactive Date",
    "NJ Transaction Number", "Renewal of Policy", "Currency", "Retroactive Short Date",
    "Extended Reporting Period", "ERP Tail Date", "Country", "Primary Carrier", "Excess Layer", "Soft Delete",
    "Binder Edit/Soft Delete Complete", "Endorsement Label_endts", "Endorsement Number",
    "Endorsement UUID (endts only)", "Proof of Loss Preparation Expenses", "Invoice Manipulation Sublimit",
    "Phising Sublimit", "Funds Transfer Liability Sublimit", "Criminal Reward Sublimit",
    "Court Attendance Sublimit", "MPL Sublimit", "Breach Response Cost", "Systems Integrity",
    "Quote Coalition Policy Number", "Endorsement Uuid", "Endorsement Index", "Endorsement Label",
    "Endorsement Type", "Cancellation or Reinstatement", "Cancellation Reason", "Cancellation Type",
    "Form Code", "Endorsement Updated At Date", "Transaction ID", "Package Keys", "Surplus 3.0",
    "Breach Response Separate Limit", "DBI Security Failure", "DBI Voluntary Shutdown", "DBI Systems Failure",
    "Contingent Business Interruption (CBI)", "CBI Security Failure", "CBI System Failure",
    "CBI Voluntary Shutdown", "CBI Non IT Security Failure", "CBI Non IT System Failure", "Missed Bid",
    "Corrective Action Plan", "Enhanced Privacy", "Per Event Limit", "Non-IT Vendor CBI",
    "Anyone Claim (Unlimited Reinstatements)", "Run-Off", "Run-Off Start Date", "Run-Off End Date",
    "Data Recovery and Computer Replacement Costs", "MPL Total Limit 100%", "Allianz MPL Limit",
    "Total MPL Premium", "Allianz Bound MPL Premium", "Allianz Net MPL Premium", "Total Cyber Premium",
    "Allianz Bound Cyber Premium", "Allianz Net Cyber Premium",
)
BOOK_COLUMNS: dict[str, tuple[str, ...]] = {
    "Runoff": BASE_COLUMNS,
    "Admitted": BASE_COLUMNS + ("Allianz Bookroll", "NYFTZ", "Captive Frontend", "FAC Reinsurance"),
    "Non-Admitted": BASE_COLUMNS + ("Allianz Bookroll", "Captive Frontend", "FAC Reinsurance"),
    "Multi-National": BASE_COLUMNS + ("Allianz Bookroll", "NYFTZ", "Captive Frontend", "FAC Reinsurance"),
}
PIPELINE_COLUMNS: tuple[str, ...] = BOOK_COLUMNS["Admitted"] + ("Book",)
"""What the pipeline's select_columns step keeps, in order."""

# The sent Admitted file spells it 'Phishing'; every other file (and NetSuite) says 'Phising'.
HEADER_ALIASES = {"Phishing Sublimit": "Phising Sublimit"}

KEY = "Internal ID"
BOUND_PREMIUM = "Allianz Bound Premium"


def file_name(book: str, month: str) -> str:
    """The deliverable's name, e.g. ``AllianzAccountCurrentResults - Runoff - 09.2026.csv``."""
    year, mm = month.split("-")
    ext = "xlsx" if book in XLSX_BOOKS else "csv"
    return f"AllianzAccountCurrentResults - {book} - {mm}.{year}.{ext}"


def read_deliverable(path: Path) -> pd.DataFrame:
    """A sent or rebuilt deliverable, every cell as text."""
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, low_memory=False)


# ── parity with a sent month ──────────────────────────────────────────────────────────────────

_DATE_TEXT = re.compile(r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}( \d{1,2}:\d{2}(:\d{2})?( ?[ap]m)?)?$", re.I)
_EXCEL_EPOCH = pd.Timestamp(1899, 12, 30)


def _normalise_cell(value: object) -> str:
    """A cell as comparable text, so a re-save in Excel isn't reported as a difference:
    '09-30-26' / '9/30/26' / '9/30/2026' → '09-30-26' (two-digit year, because Excel reads
    '01-01-70' as 2070), '8/12/2026 1:51 pm' → '08-12-26 13:51', 'False' → 'false',
    '103266.0' → '103266', '14.0%' / '0.14' → '0.14', and blank → '0'."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA:
        return "0"
    text = str(value).strip()
    if text.lower() in ("", "nan", "none", "<na>", "nat"):
        return "0"
    if text.lower() in ("true", "false"):
        return text.lower()
    if _DATE_TEXT.match(text):
        parsed = pd.to_datetime(text, errors="coerce", format="mixed")
        if not pd.isna(parsed):
            return parsed.strftime("%m-%d-%y %H:%M") if parsed.hour or parsed.minute else parsed.strftime("%m-%d-%y")
    percent = text.endswith("%")
    number = text.rstrip("%").replace(",", "").replace("$", "")
    try:
        value_f = float(number) / (100 if percent else 1)
    except ValueError:
        return text
    value_f = round(value_f, 4)
    return f"{0.0 if value_f == 0 else value_f:g}"


def _excel_serial_as_date(cell: str) -> str | None:
    """'46246' → '08-12-26' when the cell is an Excel date serial (Excel re-saved a date as a number)."""
    try:
        serial = float(cell)
    except ValueError:
        return None
    if not 20000 <= serial <= 80000:
        return None
    return (_EXCEL_EPOCH + pd.Timedelta(days=serial)).strftime("%m-%d-%y")


@dataclass
class BookParity:
    book: str
    built_rows: int
    sent_rows: int
    only_built: list[str]
    only_sent: list[str]
    column_diffs: dict[str, int]
    missing_columns: list[str]
    examples: dict[str, list[tuple[str, str, str]]]

    @property
    def matches(self) -> bool:
        return not (self.only_built or self.only_sent or self.column_diffs or self.missing_columns)


def compare_book(book: str, built: pd.DataFrame, sent: pd.DataFrame, n_examples: int = 3) -> BookParity:
    """Rows only on one side (by Internal ID) and, for shared rows, cells that differ per column."""
    sent = sent.rename(columns=HEADER_ALIASES)
    built_ids = built[KEY].astype(str)
    sent_ids = sent[KEY].astype(str)
    only_built = sorted(set(built_ids) - set(sent_ids))
    only_sent = sorted(set(sent_ids) - set(built_ids))

    shared = sorted(set(built_ids) & set(sent_ids))
    b = built.assign(**{KEY: built_ids}).drop_duplicates(KEY).set_index(KEY).loc[shared]
    s = sent.assign(**{KEY: sent_ids}).drop_duplicates(KEY).set_index(KEY).loc[shared]
    missing = [c for c in s.columns if c not in b.columns]
    diffs, examples = {}, {}
    for column in [c for c in s.columns if c in b.columns]:
        left = b[column].map(_normalise_cell)
        right = s[column].map(_normalise_cell)
        differ = left != right
        if differ.any():  # a date Excel turned into its serial number on one side
            as_dates = right[differ].map(_excel_serial_as_date)
            differ.loc[as_dates.index] = as_dates.ne(left[differ]) | as_dates.isna()
            back = left[differ].map(_excel_serial_as_date)
            differ.loc[back.index] = back.ne(right[differ]) | back.isna()
        if differ.any():
            diffs[column] = int(differ.sum())
            examples[column] = [(i, left[i], right[i]) for i in left.index[differ][:n_examples]]
    return BookParity(book, len(built), len(sent), only_built, only_sent, diffs, missing, examples)


def parity_report(results: list[BookParity]) -> str:
    """Plain-text summary of :func:`compare_book` results."""
    lines = []
    for r in results:
        status = "MATCH" if r.matches else "DIFFERS"
        lines.append(f"{r.book}: {status} — built {r.built_rows} rows, sent {r.sent_rows}")
        if r.only_built:
            lines.append(f"  only in the rebuild ({len(r.only_built)}): {', '.join(r.only_built[:10])}")
        if r.only_sent:
            lines.append(f"  only in the sent file ({len(r.only_sent)}): {', '.join(r.only_sent[:10])}")
        if r.missing_columns:
            lines.append(f"  columns missing from the rebuild: {r.missing_columns}")
        for column, count in sorted(r.column_diffs.items(), key=lambda kv: -kv[1]):
            sample = "; ".join(f"{i}: built {a!r} vs sent {b!r}" for i, a, b in r.examples[column])
            lines.append(f"  {column}: {count} cell(s) differ — e.g. {sample}")
    return "\n".join(lines)


# ── pipeui setup ───────────────────────────────────────────────────────────────────────────────

AC_REPORT = "Allianz US AC"
MASTER_REPORT = "Allianz US Master"
MASTER_SHEET = "Master"
MASTER_PATTERN = r"Masterfile-Cyber-\d+\.\d+-\d{4}-\d{2}-\d{2}"
MASTER_SAMPLE = "Masterfile-Cyber-9.2026-2026-10-01.xlsx"
AC_SAMPLE = "AllianzAccountCurrentResults871.csv"
"""Example file names: a report renamed in pipeui (e.g. "Allianz Master File") is found by the
pattern that claims them."""
"""The month's Cyber Masterfile in Account Current/<YYYY-MM>, e.g. Masterfile-Cyber-9.2026-2026-10-01.xlsx."""
FUNCTION_SET = "Allianz US BDX"
SET_MEMBERS = (  # the gate first: it cuts the full-history Account Current to the month's rows
    "allianz_master_gate", "allianz_relabel_transactions", "allianz_endorsement_package_keys",
    "allianz_apply_limits", "allianz_mpl_cyber_split", "allianz_us_book", "allianz_us_commission_columns",
    "allianz_bookroll_flags", "allianz_us_formats", "allianz_us_column_names",
)
TRANSFORMS_FILE = "pipeui_functions/allianz_us/transforms.py"

FILE_NAME = "AllianzAccountCurrentResults - {book} - {{MM}}.{{YYYY}}.{ext}"
"""A deliverable's pipeui file-name template (the period tokens are filled at build time)."""
OUTPUTS: list[dict] = [
    {
        "name": book,
        "file_name": FILE_NAME.format(book=book, ext="xlsx" if book in XLSX_BOOKS else "csv"),
        "format": "xlsx" if book in XLSX_BOOKS else "csv",
        "filter_column": "Book",
        "filter_value": book,
        "columns": list(BOOK_COLUMNS[book]),
    }
    for book in BOOKS
]
CONTROL_FILE = {
    "file_name": "Day 5 Control - {YYYY-MM}.csv", "sum_column": BOUND_PREMIUM,
    "sum_label": "Bound Premium", "label_prefix": "Allianz - US",
}


def _report_for(sources: list[dict], name: str, sample_file: str | None = None) -> dict:
    """The report called ``name``, or else the one whose pattern claims ``sample_file``."""
    from pipeui.backend.domain.sources.create import pattern_matches

    for source in sources:
        if source["source_name"] == name:
            return source
    if sample_file:
        for source in sources:
            if source.get("pattern") and pattern_matches(source["pattern"], sample_file):
                return source
    raise LookupError(f"No pipeui report for {name!r}. Register it first (`finance-tools pipeui-register-bdx`).")


def _function_ids(client, names: tuple[str, ...], transforms_file: str = TRANSFORMS_FILE) -> dict[str, str]:
    """``name → function_id`` for the transforms discovered from ``transforms_file`` (by default the
    Allianz US one)."""
    found = {}
    for fn in client.functions():
        if fn["function_name"] in names and str(fn.get("module_path", "")).endswith(transforms_file):
            found[fn["function_name"]] = fn["function_id"]
    missing = [n for n in names if n not in found]
    if missing:
        raise LookupError(f"pipeui hasn't discovered {missing} — is {transforms_file} in functions_paths?")
    return found


def _ensure_function_step(client, source_id: str, function_id: str, name: str) -> bool:
    # attaching a lone function wraps it in a set named after the function
    if any(s.get("set_name") == name for s in client.pipeline(source_id)):
        return False
    client.attach_step(source_id, function_id=function_id)
    return True


def setup_pipeline(client, endorsements_file: str, limits_file: str, mpl_file: str) -> list[str]:
    """Wires Allianz US in pipeui; safe to re-run (only what's missing or different changes).

    - "Allianz US Master" loads the Masterfile's Master sheet, replacing last month's rows;
    - the right-hand reports get their one-step pipelines; "Allianz US AC" gets the joins, the
      "Allianz US BDX" set and select_columns;
    - "Allianz US AC" gets its outputs (one file per Book) and the Day 5 control file.

    The ``*_file`` names identify which existing report loads each input when it isn't registered
    under the manifest name (e.g. "Endorsements 2026-06-02T1608"). Returns what was done.
    """
    done = []
    client.scan_functions()
    fn = _function_ids(client, SET_MEMBERS + ("mpl_premium_by_policy", "allianz_master_columns"))
    sources = client.sources()
    ac = _report_for(sources, AC_REPORT, AC_SAMPLE)
    endorsements = _report_for(sources, "Endorsements", endorsements_file)
    limits = _report_for(sources, "STM Limits Report", limits_file)
    mpl = _report_for(sources, "MPL - Premium Breakdown", mpl_file)
    master = _report_for(sources, MASTER_REPORT, MASTER_SAMPLE)

    master_settings = {"sheet_name": MASTER_SHEET, "ingestion_method": "replace", "pattern": MASTER_PATTERN}
    if any(master.get(k) != v for k, v in master_settings.items()):
        client.patch_source(master["source_id"], master_settings)
        done.append(f"{MASTER_REPORT}: loads the {MASTER_SHEET!r} sheet of Masterfile-Cyber-*.xlsx, replacing all rows")

    for source, function in ((mpl, "mpl_premium_by_policy"), (master, "allianz_master_columns")):
        if _ensure_function_step(client, source["source_id"], fn[function], function):
            done.append(f"attached {function} to {source['source_name']}")

    joins = (
        (endorsements, "Endorsement UUID (endts only)", "Endorsement Uuid", False),
        (limits, KEY, KEY, False),
        (mpl, "Coalition Policy Number", "MPL Policy Number", True),
        (master, KEY, "Master Internal ID", True),
    )
    steps = client.pipeline(ac["source_id"])
    joined = {s["builtin_config"]["right_source_id"] for s in steps if s.get("builtin_type") == "join"}
    for right, left_col, right_col, transformed in joins:
        if right["source_id"] in joined:
            continue
        client.attach_builtin(ac["source_id"], "join", {
            "right_source_id": right["source_id"], "join_type": "left", "use_transformed": transformed,
            "on": [{"left_col": left_col, "right_col": right_col}], "keep_columns": "all",
        })
        done.append(f"joined {right['source_name']} on {left_col} = {right_col}")

    set_id = client.save_function_set(
        FUNCTION_SET, [fn[name] for name in SET_MEMBERS],
        "Allianz US Day 5 BDX: otc's AllianzUSBDX plus the Sept 2026 hand edits. "
        "The report's Outputs split the result on Book.",
    )
    if not any(s.get("set_id") == set_id for s in client.pipeline(ac["source_id"])):
        client.attach_step(ac["source_id"], set_id=set_id)
        done.append(f"attached set {FUNCTION_SET}")

    select = {"columns": list(PIPELINE_COLUMNS), "excluded": []}
    existing = next((s for s in client.pipeline(ac["source_id"]) if s.get("builtin_type") == "select_columns"), None)
    if existing is None:
        client.attach_builtin(ac["source_id"], "select_columns", select)
        done.append("attached select_columns")
    elif existing["builtin_config"].get("columns") != select["columns"]:
        client.patch_builtin(ac["source_id"], existing["step_id"], select)
        done.append("updated select_columns")

    current = client.outputs(ac["source_id"])
    as_saved = [{k: o.get(k) for k in OUTPUTS[0]} for o in current["outputs"]]
    if as_saved != OUTPUTS or current["summary"] != {**CONTROL_FILE}:
        client.save_outputs(ac["source_id"], OUTPUTS, CONTROL_FILE)
        done.append(f"saved {len(OUTPUTS)} outputs ({', '.join(BOOKS)}) and the Day 5 control file")
    return done


def check(client, month: str, sent_dir: Path) -> tuple[dict, list[BookParity]]:
    """Builds the month's outputs in pipeui (as the Build output files button does) and compares
    each file with the one sent in ``sent_dir``. Returns (the build response, parity per book)."""
    ac = _report_for(client.sources(), AC_REPORT, AC_SAMPLE)
    built = client.build_outputs(ac["source_id"], month)
    paths = {f["name"]: Path(f["path"]) for f in built["files"]}
    results = []
    for book in BOOKS:
        sent = sent_dir / file_name(book, month)
        if book in paths and sent.exists():
            results.append(compare_book(book, read_deliverable(paths[book]), read_deliverable(sent)))
    return built, results
