"""BDX report list: patterns claim the right exports (and never a route's own output), plus planning."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest
from pipeui.backend.data.base.schema.constants import IngestionMethod
from pipeui.backend.domain.sources.create import pattern_matches

from finance_tools.bdx_reports.manifest import BDX_REPORTS, DEFERRED, reports_for
from finance_tools.bdx_reports.register import (
    ALREADY_REGISTERED,
    BAD_KEY,
    COVERED,
    NO_FILE,
    REGISTER,
    newest_matching_file,
    plan_registrations,
)

# Real export names (shapes from ~/Downloads, 2026-10-13), one per report.
EXAMPLES = {
    "BDX Policy List": "PolicyList257.csv",
    "STM Limits Report": "DataQualityLimitsSTMResults217.csv",
    "STM Transaction Report": "DataQualityDailyTransactionCheckAllTransactionsSTMResults570.csv",
    "Endorsements": "Endorsements 2026-10-01T1601.csv",
    "Antares (Modded for Cyber)": "Antares (Modded for Cyber) 2026-10-01T1558.csv",
    "MPL - Premium Breakdown": "MPL - Premium Breakdown 2026-10-02T0945.csv",
    "Allianz US Master": "Masterfile-Cyber-9.2026-2026-10-01.xlsx",
    "Germany report for Allianz": "Germany report for Allianz 2026-10-08T1142.csv",
    "Vantage AC": "STMVantageAccountCurrentResults575.csv",
    "Lloyds UK AC": "LloydsUKAccountCurrentResults792.csv",
    "Lloyds Canada AC": "LloydsCanadaAccountCurrentResults489.csv",
    "Ascot AC": "AscotAccountCurrentSTMResults182 (1).csv",
    "Technical Premium": "Technical Premium 2026-10-02T0936.csv",
    "Allianz US AC": "AllianzAccountCurrentResults322.csv",
    "Allianz UK AC": "AllianzUKAccountCurrentResults915.csv",
    "Allianz AUS AC (UK format)": "AllianzAUSAccountCurrentUKFormatResults846.csv",
    "Allianz AUS AC": "AllianzAUSAccountCurrentResults113.csv",
    "Allianz Germany AC": "AllianzGERAccountCurrentResults494.csv",
    "Allianz Denmark AC": "AllianzDenmarkAccountCurrentv2Results839.csv",
    "Fortegra AC": "FortegraAccountCurrentSTMSampleResults425 (1).csv",
    "HDI Canada AC": "HDICanadaResults183.csv",
    "Aspen AC": "AspenAccountCurrentResults373.csv",
    "Chaucer AC": "ChaucerAccountCurrentSMResults976.csv",
    "Hartford UK AC": "HartfordUKAccountCurrentResults722.csv",
    "MSIG AUS AC": "MSIGAUSAccountCurrentResults101.csv",
    "Allianz France AC": "AllianzFranceAccountCurrentResults316.csv",
    "Allianz Sweden AC": "AllianzSwedenAccountCurrentResults147.csv",
    "Allianz UK Branch of GmbH AC": "AllianzUKBranchofGmbHAccountCurrentResults629.csv",
    "Zurich AC": "ZurichAccountCurrentSTMResults540.csv",
    "Exec Risks Zurich Premium Report":
        "Exec Risks Zurich Premium Report (need to remove first 3 columns before sending to carrier) 2026-10-02T1359.xlsx",
    "Aspen AC (balance update)": "AspenAccountCurrentBalanceUpdateResults85.csv",
    "Endorsements Type": "Endorsements Type 2026-10-08T1112.csv",
    "Aspen Endorsement Limit Changes": "Aspen Endorsement Limit Changes 2026-10-08T1115.csv",
    "Lloyds US Bordereau": "STMLloydsBordereauCurrentResults233.csv",
    "Swiss Re Canada YTD": "SReAccountCurrentCanadaYTDSTMResults993.csv",
    "Swiss Re Admitted": "SReAccountCurrentADMITTEDSTMResults526.csv",
    "Swiss Re Surplus": "SReAccountCurrentSURPLUSSTMResults123.csv",
    "Swiss Re US YTD": "SReAccountCurrentTDSTMResults406.csv",
    "ER - Limits Merge Report": "ER - Limits Merge Report [updated] 2026-10-13T1035.csv",
    "Antares Report - Sho Copy": "Antares Report - Sho Copy 2026-10-13T1037.csv",
}

# What the otc routes write back into Downloads — none of it may be loaded as an input.
ROUTE_OUTPUTS = [
    "MasterFile-MPL-9.2026-2026-10-01.xlsx",
    "VantageAccountCurrentResults2026-10-01.xlsx",
    "Day 1 Control - 2026-10-01.csv",
    "AllianzAccountCurrentResults - Runoff - 09.2026.csv",
    "AllianzAccountCurrentResults - Multi-National - 09.2026.xlsx",
    "Day 5 Control - 2026-10-13.csv",
    "Day 5 Control - 2026-09.csv",
    "AllianzAccountCurrentResults - 09.2026.csv",
    "LloydsUKAccountCurrent - 9.2026 (2025).xlsx",
    "LloydsCanadaAccountCurrent - 9.2026 (2024).xlsx",
    "AllianzAccountUKCurrentResults - 9.2026 - Primary.xlsx",
    "AllianzAUSAccountCurrentResults - 2026.9 (UK Format).csv",
    "AscotITD - 2026-10-01.csv",
    "AscotMonthlyAccountCurrent-September 2026.xlsx",
    "AllianzDenmarkAccountCurrentResults-2026.09.xlsx",
    "FortegraAccountCurrent - 2026.09.xlsx",
    "HDICanadaAccountCurrent - 2026.09.xlsx",
    "AspenAccountCurrent - 2026.09.xlsx",
    "AspenAccountCurrent (v2) - 2026.09.xlsx",
    "Aspen V2 - 2026-10-01.csv",
    "ChaucerAccountCurrent-2026.09.xlsx",
    "MSIGAccountCurrentResults - 2026.09.xlsx",
    "Zurich Account Current File - 9.2026 (internal).xlsx",
    "ZurichPremiumDataFileResults20260 (internal).xlsx",
    "Lloyds Account Current - 09-2026 - 2026-10-01.csv",
    "CYP0000926-00-AC CAD.xlsx",
    "CCP0000926-00-AC Admitted.xlsx",
    "LloydsExecRisk - Renre - 092026.csv",
    "Carrier Reporting - Reported Upload - 2026-10-01 - ran 2026-10-13.csv",
    "Day 15 Control - 2026-10-01.csv",
]


def test_every_report_has_an_example_and_names_are_unique():
    names = [s.name for s in BDX_REPORTS]
    assert len(names) == len(set(names))
    assert set(names) == set(EXAMPLES)


@pytest.mark.parametrize("spec", BDX_REPORTS, ids=lambda s: s.name)
def test_pattern_claims_its_own_export_and_no_other(spec):
    re.compile(spec.pattern)
    assert pattern_matches(spec.pattern, EXAMPLES[spec.name])
    others = [n for name, n in EXAMPLES.items() if name != spec.name]
    assert not [n for n in others if pattern_matches(spec.pattern, n)]


@pytest.mark.parametrize("output", ROUTE_OUTPUTS)
def test_route_outputs_match_no_input_pattern(output):
    assert [s.name for s in BDX_REPORTS if pattern_matches(s.pattern, output)] == []


def test_specs_are_valid_pipeui_sources():
    for spec in BDX_REPORTS:
        assert IngestionMethod.accepted(spec.ingestion_method)
        assert spec.primary_key
        assert spec.system in ("netsuite", "looker", "masterfile")


def test_deferred_inputs_are_not_also_reports():
    report_names = {s.name for s in BDX_REPORTS}
    for deferred in DEFERRED:
        assert deferred.split(" (")[0] not in report_names


def test_reports_for_route():
    day15 = {s.name for s in reports_for("day15")}
    assert {"Lloyds US Bordereau", "Swiss Re Admitted", "Swiss Re Surplus", "Swiss Re Canada YTD"} == day15
    assert "Endorsements" in {s.name for s in reports_for("day5")}
    assert reports_for(None) == BDX_REPORTS


# ── planning (reads files, never pipeui) ─────────────────────────────────────

def _export(folder: Path, name: str, body: str, age_s: float) -> Path:
    path = folder / name
    path.write_text(body)
    os.utime(path, (time.time() - age_s, time.time() - age_s))
    return path


def test_newest_matching_file_and_age_limit(tmp_path):
    _export(tmp_path, "PolicyList1.csv", "Internal ID\n1\n", age_s=3 * 86400)
    newer = _export(tmp_path, "PolicyList2 (1).csv", "Internal ID\n1\n", age_s=60)
    _export(tmp_path, "PolicyList - notes.csv", "x\n", age_s=10)  # not an export
    assert newest_matching_file(tmp_path, r"PolicyList\d+") == newer
    os.utime(newer, (time.time() - 40 * 86400, time.time() - 40 * 86400))
    assert newest_matching_file(tmp_path, r"PolicyList\d+", max_age_days=30).name == "PolicyList1.csv"


def test_plan_registrations_statuses(tmp_path):
    specs = reports_for("day15")
    _export(tmp_path, "STMLloydsBordereauCurrentResults1.csv", "Internal ID,v\n1,a\n2,b\n", age_s=60)
    _export(tmp_path, "SReAccountCurrentADMITTEDSTMResults1.csv", "Internal ID,v\n1,a\n1,b\n", age_s=60)
    plans = {p.spec.name: p for p in plan_registrations(specs, tmp_path, {"Swiss Re Surplus": None})}
    assert plans["Lloyds US Bordereau"].status == REGISTER
    assert plans["Swiss Re Admitted"].status == BAD_KEY
    assert "repeats" in plans["Swiss Re Admitted"].detail
    assert plans["Swiss Re Surplus"].status == ALREADY_REGISTERED
    assert plans["Swiss Re Canada YTD"].status == NO_FILE


def test_plan_leaves_files_an_existing_report_claims_to_it(tmp_path):
    _export(tmp_path, "STMVantageAccountCurrentResults9.csv", "Internal ID\n1\n", age_s=60)
    existing = {"STMVantageAccountCurrentResults256": r"STMVantageAccountCurrentResults\d+"}
    vantage = tuple(s for s in reports_for("day1") if s.name == "Vantage AC")
    [plan] = plan_registrations(vantage, tmp_path, existing)
    assert plan.status == COVERED
    assert "STMVantageAccountCurrentResults256" in plan.detail
