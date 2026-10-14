"""Every export the otc BDX process (`otc/src/carrier/routes`) reads from Downloads, as pipeui reports.

One ``ReportSpec`` per export, listed once even when several days use it. ``pattern`` is a
pipeui filename pattern: a regex that must FULLY match the filename without its extension
(pipeui ``pattern_matches``). That full match is what keeps a route's own output, written back
into Downloads, from being loaded as an input. otc needed ``"Endorsements [0-9]"``-style prefix
guards for this; a full match on ``Endorsements <timestamp>`` doesn't.

Sources, copied because otc isn't importable from here (no pyproject, not a dependency):
- filename prefixes: ``otc/src/carrier/routes/reporting.py`` (``Day*Reporting`` loaders) and
  ``routes.py:71`` (PolicyList)
- NetSuite search / Looker look ids: ``otc/docs/reports.md``, ``otc/docs/bdx/looker_columns.csv``
- filename shapes and primary keys: checked against the newest real exports on 2026-10-13
  (NetSuite ``<Search>Results<n>.csv``; Looker ``<Look> YYYY-MM-DDTHHMM.csv``). Every key below
  was unique and non-null in that export.

``DEFERRED`` lists the inputs that can't be a pipeui report yet. Each one says why.
"""
from __future__ import annotations

from dataclasses import dataclass

from pipeui.backend.data.base.schema.constants import IngestionMethod

LOOKER_TS = r"\d{4}-\d{2}-\d{2}T\d{4}"
"""Looker's export suffix, e.g. ``Endorsements 2026-10-01T1601``."""

UPSERT = IngestionMethod.UPSERT.value


@dataclass(frozen=True)
class ReportSpec:
    name: str
    """pipeui report (source) name"""
    pattern: str
    """full-match regex on the filename stem"""
    primary_key: str
    used_by: tuple[str, ...]
    """otc BDX routes that read it: master, day1, day5, day10, zurich, aspen, day15, lloyds-er, sre-ytd"""
    system: str
    """netsuite | looker | masterfile"""
    search_id: int | None = None
    """NetSuite saved search id or Looker look id"""
    ingestion_method: str = UPSERT
    """every export is a full snapshot keyed on primary_key, so a re-pull updates rows in place"""


def _ns(name: str, prefix: str, used_by: tuple[str, ...], search_id: int | None) -> ReportSpec:
    """NetSuite saved-search export: ``<prefix><n>.csv``, keyed on Internal ID."""
    return ReportSpec(name, rf"{prefix}\d+", "Internal ID", used_by, "netsuite", search_id)


def _looker(name: str, title_regex: str, key: str, used_by: tuple[str, ...], look_id: int | None) -> ReportSpec:
    """Looker look export: ``<title> YYYY-MM-DDTHHMM``."""
    return ReportSpec(name, rf"{title_regex} {LOOKER_TS}", key, used_by, "looker", look_id)


BDX_REPORTS: tuple[ReportSpec, ...] = (
    # ── master file ───────────────────────────────────────────────────────────
    _ns("BDX Policy List", "PolicyList", ("master",), None),  # NetSuite custom record 233, not a search
    # ── shared across days ────────────────────────────────────────────────────
    _ns("STM Limits Report", "DataQualityLimitsSTMResults", ("day1", "day5", "day10", "aspen"), 8180),
    _ns("STM Transaction Report", "DataQualityDailyTransactionCheckAllTransactionsSTMResults",
        ("day1", "day5", "zurich", "aspen"), 6275),
    _looker("Endorsements", "Endorsements", "Endorsement Uuid", ("day1", "day5", "day10", "aspen", "lloyds-er"), 3073),
    _looker("Antares (Modded for Cyber)", r"Antares \(Modded for Cyber\)", "Transaction ID", ("day1", "day5"), 4136),
    _looker("MPL - Premium Breakdown", "MPL - Premium Breakdown", "Transaction ID", ("day5", "day10"), 3551),
    _looker("Germany report for Allianz", "Germany report for Allianz", "Netsuite ID", ("day5", "day10"), 4440),
    # ── Day 1 ─────────────────────────────────────────────────────────────────
    _ns("Vantage AC", "STMVantageAccountCurrentResults", ("day1",), 6490),
    # ── Day 5 ─────────────────────────────────────────────────────────────────
    _ns("Lloyds UK AC", "LloydsUKAccountCurrentResults", ("day5",), 6604),
    _ns("Lloyds Canada AC", "LloydsCanadaAccountCurrentResults", ("day5",), 6611),
    _ns("Ascot AC", "AscotAccountCurrentSTMResults", ("day5",), 6536),
    _looker("Technical Premium", "Technical Premium", "Quote Coalition Policy Number", ("day5",), 3050),
    _ns("Allianz US AC", "AllianzAccountCurrentResults", ("day5",), 6418),
    ReportSpec(  # the month's Cyber Masterfile (Account Current/<YYYY-MM>); pipeui loads its "Master" sheet
        "Allianz US Master", r"Masterfile-Cyber-\d+\.\d+-\d{4}-\d{2}-\d{2}", "Internal ID", ("day5",), "masterfile",
        ingestion_method="replace",
    ),
    _ns("Allianz UK AC", "AllianzUKAccountCurrentResults", ("day5",), 6548),
    _ns("Allianz AUS AC (UK format)", "AllianzAUSAccountCurrentUKFormatResults", ("day5",), 8187),
    _ns("Allianz AUS AC", "AllianzAUSAccountCurrentResults", ("day5",), 7537),
    _ns("Allianz Germany AC", "AllianzGERAccountCurrentResults", ("day5",), 9002),
    _ns("Allianz Denmark AC", "AllianzDenmarkAccountCurrentv2Results", ("day5",), 10110),
    # ── Day 10 ────────────────────────────────────────────────────────────────
    _ns("Fortegra AC", "FortegraAccountCurrentSTMSampleResults", ("day10",), 6282),
    _ns("HDI Canada AC", "HDICanadaResults", ("day10",), 7943),
    _ns("Aspen AC", "AspenAccountCurrentResults", ("day10",), 8421),
    _ns("Chaucer AC", "ChaucerAccountCurrentSMResults", ("day10",), 6170),
    _ns("Hartford UK AC", "HartfordUKAccountCurrentResults", ("day10",), 9108),
    _ns("MSIG AUS AC", "MSIGAUSAccountCurrentResults", ("day10",), 9357),
    _ns("Allianz France AC", "AllianzFranceAccountCurrentResults", ("day10",), 10174),
    _ns("Allianz Sweden AC", "AllianzSwedenAccountCurrentResults", ("day10",), 9851),
    _ns("Allianz UK Branch of GmbH AC", "AllianzUKBranchofGmbHAccountCurrentResults", ("day10",), 11161),
    # ── Day 10, Zurich (?zurich=true) ─────────────────────────────────────────
    _ns("Zurich AC", "ZurichAccountCurrentSTMResults", ("zurich",), 6188),
    ReportSpec(  # Looker xlsx; the title itself carries a note with a digit in it
        "Exec Risks Zurich Premium Report",
        rf"Exec Risks Zurich Premium Report \(need to remove first \d+ columns before sending to carrier\) {LOOKER_TS}",
        "Netsuite Transaction ID", ("zurich",), "looker", 3064,
    ),
    # ── Aspen v2 ──────────────────────────────────────────────────────────────
    _ns("Aspen AC (balance update)", "AspenAccountCurrentBalanceUpdateResults", ("aspen",), 9625),
    _looker("Endorsements Type", "Endorsements Type", "Endorsement Uuid", ("aspen",), 4970),
    _looker("Aspen Endorsement Limit Changes", "Aspen Endorsement Limit Changes", "Endorsement Uuid", ("aspen",), None),
    # ── Day 15 ────────────────────────────────────────────────────────────────
    _ns("Lloyds US Bordereau", "STMLloydsBordereauCurrentResults", ("day15",), 6929),
    _ns("Swiss Re Canada YTD", "SReAccountCurrentCanadaYTDSTMResults", ("day15", "sre-ytd"), 6902),
    _ns("Swiss Re Admitted", "SReAccountCurrentADMITTEDSTMResults", ("day15",), 6194),
    _ns("Swiss Re Surplus", "SReAccountCurrentSURPLUSSTMResults", ("day15",), 6433),
    _ns("Swiss Re US YTD", "SReAccountCurrentTDSTMResults", ("sre-ytd",), 6195),
    # ── Lloyds Executive Risk (/lloyds/er) ────────────────────────────────────
    _looker("ER - Limits Merge Report", r"ER - Limits Merge Report( \[updated\])?", "Netsuite ID", ("lloyds-er",), 4155),
    _looker("Antares Report - Sho Copy", "Antares Report - Sho Copy", "Quote Option ID", ("lloyds-er",), 3707),
)

DEFERRED: dict[str, str] = {
    # no single-column unique key: pipeui reports are keyed on one column (PRIMARY KEY)
    "LloydsACExecutiveRiskResults (NS 6411, lloyds-er)":
        "Internal ID repeats once per Section (110,563 rows / 14,141 ids). Needs a composite key.",
    "Allianz UK - Customer Type (Looker 5270, day5)":
        "Transaction ID repeats and has blanks. Needs a composite key.",
    "Exec Risks Zurich Crime Premium Report (Looker 3063, zurich)":
        "Netsuite Transaction ID repeats (one row per crime coverage line).",
    "Breach Response (Looker 4252, day10/aspen)":
        "Exported without a header row (column0..column3), so there's no key column to name.",
    "Endorsement Query (Looker, day10 MSIG)":
        "No unique column. Filtered to MSIG and de-duplicated by policy inside otc.",
    "All Master Log - Not Reported (finance-tools, aspen)":
        "finance-tools output, not an export. Passed into Aspen v2 but unused there (lifecycle.py:143).",
    # not in Downloads
    "Ascot ITD prior period (day5)": "Read from the Account Current Drive folder, not Downloads.",
    "Swiss Re CCP/CYP YTD prior period (sre-ytd)": "Read from the Account Current Drive folder, not Downloads.",
    "Master file workbook (all days)": "Built by /bdx/master and read from Account Current/<YYYY-MM>. "
                                       "Allianz US loads its Master sheet as the `Allianz US Master` report.",
    # referenced but not loaded by any route today
    "Allianz - Bookroll (day5)": "Loader returns None. The report isn't built yet.",
    "MSIGUSAccountCurrentResults (NS 10165)": "In the Day 10 docstring, but no route loads it.",
}


def reports_for(route: str | None = None) -> tuple[ReportSpec, ...]:
    """The specs a route reads (all of them when ``route`` is None)."""
    if route is None:
        return BDX_REPORTS
    return tuple(spec for spec in BDX_REPORTS if route in spec.used_by)
