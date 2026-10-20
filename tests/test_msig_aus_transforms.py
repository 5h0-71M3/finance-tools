"""MSIG Australia Day 10 transforms (pipeui_functions/msig_aus/transforms.py) and the pipeui wiring
constants (bdx_reports/msig_aus.py)."""
import json

import pandas as pd

from finance_tools.bdx_reports import msig_aus as M
from finance_tools.pipeui_functions.msig_aus import transforms as T

AUS = "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Coalition AUS"
US = "ProForma : GAAP : MGA Consolidation : Coalition, Inc"


def _rows(**columns):
    return pd.DataFrame(columns)


def test_master_gate_keeps_aus_rows_msig_has_a_share_of():
    df = _rows(**{
        "Internal ID": [1, 2, 3, 4],
        "Master MSIG Quota Share": [0.25, 0.0, None, 0.25],
        "Master Subsidiary": [AUS, AUS, AUS, US],
    })
    assert list(T.msig_master_gate(df)["Internal ID"]) == [1]


def test_soft_deletes_relabelled_by_agwp_sign():
    df = _rows(**{
        "Transaction Type": ["soft delete", "soft delete", "Issuance", "Cancellation - Flat"],
        "Annual Gross Written Premium": [-10.0, 5.0, -3.0, -4.0],
    })
    assert list(T.msig_relabel_transactions(df)["Transaction Type"]) == [
        "Cancellation - Flat", "Endorsement", "Issuance", "Cancellation - Flat"]


def test_premium_formats_gst_gross_and_state_columns_at_msig_share():
    df = _rows(**{
        "Annual Gross Written Premium": [363.0, -200.0],
        "Base Premium Amount": [363.0, -200.0],
        "Stamp Duty Total": [34.104, -10.0],
        "MSIG Quota Share": [0.25, 0.5],
        "Insured GST Status": [True, "F"],
        **{c: [0.0, 0.0] for c in T.STATE_PREMIUM_COLUMNS},
    })
    df["GWP NSW Premium"] = [435.6, 30.0]
    df["Australia VIC SD"] = ["70.28", "8"]
    out = T.msig_premium_formats(df)
    assert list(out["Annual GST"]) == [36.3, -20.0]
    assert list(out["Premium GST"]) == [36.3, -20.0]
    assert list(out["Gross Premium Amount"]) == [433.4, -230.0]
    assert list(out["Stamp Duty Total"]) == [34.1, -10.0]
    assert list(out["GWP NSW Premium"]) == [108.9, -15.0]
    assert list(out["Australia VIC SD"]) == [17.57, -4.0]
    assert list(out["Insured GST Status"]) == ["T", "F"]


def test_endorsement_query_keeps_latest_row_with_values_per_msig_policy():
    blank = {f: None for f in T.EXEMPT_FIELDS}
    yes = {f: "Yes" if f.startswith("REVENUE_AU_NSW") else "No" for f in T.EXEMPT_FIELDS}
    no = {f: "No" for f in T.EXEMPT_FIELDS}
    rows = [
        {"CARRIER_BDX_FILE": "MSIG Australia", "COALITION_POLICY_NUMBER": "P1 ", "TRANSACTION_CREATION_DATE": "2026-09-01", **no},
        {"CARRIER_BDX_FILE": "MSIG Australia", "COALITION_POLICY_NUMBER": "P1", "TRANSACTION_CREATION_DATE": "2026-09-05", **yes},
        {"CARRIER_BDX_FILE": "MSIG Australia", "COALITION_POLICY_NUMBER": "P1", "TRANSACTION_CREATION_DATE": "2026-09-09", **blank},
        {"CARRIER_BDX_FILE": "Allianz", "COALITION_POLICY_NUMBER": "P2", "TRANSACTION_CREATION_DATE": "2026-09-09", **yes},
    ]
    out = T.msig_endorsement_exemptions(pd.DataFrame(rows))
    assert list(out["EQ Coalition Policy Number"]) == ["P1"]
    assert out.loc[0, "REVENUE_AU_NSW_PERCENTAGE_EXEMPT"] == "Yes"


def test_limits_at_msig_share_under_msig_names_agg_and_retention_at_100():
    df = _rows(**{
        "MSIG Quota Share": [0.25, 0.25],
        "Ransomware and Cyber Extortion": ["1000000", "-0.0"],
        "Phishing/Impersonation Repair": [None, "250000"],
        "Network and Information Security": [1000000.0, "-"],
        "Aggregate Total Limit": ["1000000", "-1000000"],
        "SIR": ["2500", "0"],
        "Enhanced Waiting Period (Y/N)": ["No", "Yes"],
    })
    out = T.msig_apply_limits(df)
    assert list(out["Cyber Extortion"]) == [250000.0, 0.0]
    assert list(out["Phising Sublimit"]) == [0.0, 62500.0]
    assert list(out["Network and Information Security"]) == [250000.0, 0.0]
    assert list(out["TCPA"]) == [0.0, 0.0]
    assert list(out["Agg Limit"]) == [1000000.0, -1000000.0]
    assert list(out["Retention"]) == [2500.0, 0.0]
    assert list(out["Enhanced Waiting Period (Y/N)"]) == ["N", "Y"]
    assert "Ransomware and Cyber Extortion" not in out.columns  # no near-duplicate names left behind


def test_renewal_indicator_is_per_policy_from_the_issuance_transaction_id():
    df = _rows(**{
        "Coalition Policy Number": ["P1", "P1", "P2", "P3", "P4"],
        "Transaction ID (ExtID)": ["CCP1-02-TX-1000-RN", "CCP1-02-TX-1001-E", "C-X-2026-1000-ND", None, "CCP4-01-TX-1000-RND"],
    })
    assert list(T.msig_renewal_indicator(df)["Renewal Indicator (Y/N)"]) == ["Y", "Y", "N", None, "Y"]


def test_new_format_fields():
    df = _rows(**{
        "Transaction Type": ["Issuance", "Endorsement", "Cancellation - Pro-Rated"],
        "Transaction Effective Date": ["06-25-26", pd.Timestamp("2026-07-01"), "08-01-26"],
        "Policy Effective Date": [pd.Timestamp("2026-06-25"), None, "08-01-26"],
        "Config": [None, json.dumps({"package_keys": ["named_insured"]}), None],
        "REVENUE_AU_NSW_PERCENTAGE_EXEMPT": [None, "Yes", "No"],
        "Txn Policy Status Indicator": ["In-Force", "In-Force", "Expired"],
        "Txn GICS Code": [40102010.0, None, 20202020.0],
        "Txn Extended Reporting Period": ["No", "Yes", None],
        "Txn Excess Layer": [0.0, 1.0, None],
        "Risk Industry Name": ["Thrifts and Mortgage Finance", None, None],
        "Addr Insured Zip Code": ["0828", "2000", None],
        "Addr Renewal of Policy": [None, "C-51GV-068470-CYBER-2023", None],
    })
    out = T.msig_new_format_fields(df)
    assert list(out["Transaction Description"]) == ["Issuance", "named_insured", "Cancellation - Pro-Rated"]
    assert list(out["Endorsement Effective Date"]) == [None, "07-01-26", None]
    assert list(out["Transaction Effective Date"]) == ["06-25-26", "07-01-26", "08-01-26"]
    assert list(out["Cancellation Effective Date"]) == [None, None, "08-01-26"]
    assert list(out["NSW SD Duty Exempt Indicator (Y/N)"].fillna("")) == ["", "Y", "N"]
    assert list(out["VIC SD Duty Exempt Indicator (Y/N)"].isna()) == [True, True, True]
    assert list(out["Policy Status Indicator"]) == ["In-Force", "In-Force", "Expired"]
    assert list(out["GICS Code"]) == ["40102010", None, "20202020"]
    assert list(out["Extended Reporting Period"].fillna("")) == ["N", "Y", ""]
    assert list(out["Excess Layer"]) == [0, 1, None]
    assert out.loc[0, "Industry Name"] == "Thrifts and Mortgage Finance"
    assert list(out["Insured Zip Code"]) == ["0828", "2000", None]  # text: NT postcodes keep the 0
    assert out.loc[1, "Renewal of Policy"] == "C-51GV-068470-CYBER-2023"
    assert out["Insured Primary URL"].isna().all()  # no Addr column joined
    assert out["Distribution Channel (Specify)"].isna().all()
    assert list(out["Policy Effective Date"]) == ["06-25-26", None, "08-01-26"]


def test_layout_is_msigs_field_list_without_duplicates():
    assert len(set(M.SENT_COLUMNS)) == len(M.SENT_COLUMNS) == 114
    assert set(T.SUBLIMITS) <= set(M.NEW_COLUMNS)
    assert set(T.EXEMPT_INDICATORS.values()) <= set(M.NEW_COLUMNS)
    assert set(T.NO_SOURCE_FIELDS) <= set(M.NEW_COLUMNS)
    assert set(T.ADDRESS_FIELDS) <= set(M.NEW_COLUMNS)


def test_preps_rename_then_select_the_prefixed_names():
    prep = M.PREPS["Allianz AUS AC (UK format)"]
    assert prep["rename"]["renames"]["Internal ID"] == "Addr Internal ID"
    assert prep["select_columns"]["columns"] == list(prep["rename"]["renames"].values())
    assert {join[0] for join in M.JOINS if join[2] == M.PREP} == set(M.PREPS)


def test_sent_file_compares_in_the_new_format():
    sent = _rows(**{"Unnamed: 0": [0], "Internal ID": ["1"], "REVENUE_AU_NSW_PERCENTAGE_EXEMPT": ["Yes"]})
    out = M.as_new_format(sent)
    assert list(out.columns) == ["Internal ID", "NSW SD Duty Exempt Indicator (Y/N)"]
    assert out.loc[0, "NSW SD Duty Exempt Indicator (Y/N)"] == "Y"
