"""Allianz US Day 5 transforms (pipeui_functions/allianz_us/transforms.py) and the split/parity
helpers (bdx_reports/allianz_us.py)."""
import json

import pandas as pd
import pytest

from finance_tools.bdx_reports import allianz_us as A
from finance_tools.pipeui_functions.allianz_us import transforms as T


def _rows(**columns):
    return pd.DataFrame(columns)


def test_relabel_soft_delete_binder_edit_type_and_deleted_id():
    df = _rows(**{
        "Transaction Description": ["soft delete", "soft delete", "Issuance", "Endorsement", "Issuance"],
        "Total Bound Premium": [-10.0, 5.0, -7.0, -7.0, 3.0],
        "External ID": ["A-1", "A-2", "C-X-2026-BE1", "C-X-2026-BE3",
                        "C-4LQL-116667-DELETED-30ee2f9a-ba44-4d3c-a994-9c40583649f9-IL-1000-RN"],
        "Renewal of Policy": [None, "C-OLD", None, None, None],
    })
    out = T.allianz_relabel_transactions(df)
    assert list(out["Transaction Description"]) == [
        "Cancellation - Flat", "Endorsement", "Cancellation - Flat", "Endorsement", "Issuance"]
    assert list(out["Transaction Type"]) == ["New", "Renewal", "New", "New", "New"]
    assert out["External ID"].iloc[4] == "C-4LQL-116667-9c40583649f9-IL-1000-RN"  # otc drops segments [3:8]


@pytest.mark.parametrize("config, expected", [
    ({"package_keys": ["a", "b"]}, "a, b"),
    ({"package_keys": []}, "endorsement_replacement"),
    ({"package_keys": ["a"], "erp": {"x": 1}}, "a, erp"),
    ({"package_keys": ["a"], "cancellation_date": "2026-09-01"}, "cancellation"),
    ({}, None),
])
def test_package_keys_from_config(config, expected):
    df = _rows(Config=[json.dumps(config)], **{"Total Bound Premium": [1.0]})
    assert T.allianz_endorsement_package_keys(df)["Package Keys"].iloc[0] == expected


def test_zero_dollar_endorsement_replacement_dropped():
    df = _rows(Config=[json.dumps({"package_keys": []})] * 2, **{"Total Bound Premium": [0.0, 5.0]})
    assert list(T.allianz_endorsement_package_keys(df)["Total Bound Premium"]) == [5.0]


def test_limits_take_tbp_sign_and_stm_fields_scale_by_quota_share():
    df = _rows(**{
        "Total Bound Premium": [-100.0, 100.0],
        "Allianz Quota Share %": ["10.0%", "10.0%"],
        "Network and Information Security": ["$1,000,000", "-"],
        "Per Event Limit": ["250000", None],
    })
    out = T.allianz_apply_limits(df)
    assert list(out["Network and Information Security"]) == [-1_000_000, 0]
    assert list(out["Per Event Limit"]) == [-25_000.0, 0.0]


def test_mpl_split_applies_quota_share_once():
    df = _rows(**{
        "Total Bound Premium": [14985.0],
        "Allianz Quota Share %": ["10.0%"],
        "Coalition Commission %": ["33.0%"],
        "MPL Sublimit": [500000],
        "MPL Premium": [4714.842],
    })
    out = T.allianz_mpl_cyber_split(df).iloc[0]
    assert out["Total MPL Premium"] == pytest.approx(4714.842)
    assert out["Allianz Bound MPL Premium"] == pytest.approx(471.4842)
    assert out["Allianz Net MPL Premium"] == 315.89
    assert out["Total Cyber Premium"] == pytest.approx(10270.158)
    assert out["Allianz Net Cyber Premium"] == 688.1


def test_mpl_premium_by_policy_drops_duplicated_policies():
    mpl = _rows(**{
        "Quote Coalition Policy Number": ["P1", "P2", "P2"],
        "Total Bound MPL Premium": ["$1,000", "5", "6"],
    })
    out = T.mpl_premium_by_policy(mpl)
    assert list(out["MPL Policy Number"]) == ["P1"]
    assert list(out["MPL Premium"]) == [1000.0]


def test_master_gate_keeps_us_rows_allianz_shares():
    df = _rows(**{
        "Master Allianz Quota Share": [0.2, 0.0, 0.2, None],
        "Master Subsidiary": [T.US_SUBSIDIARY, T.US_SUBSIDIARY, "ProForma : GAAP : MGA Consolidation : Coalition, Inc : Coalition AUS", None],
    })
    assert len(T.allianz_master_gate(df)) == 1


def test_book_split_at_the_new_paper_start():
    df = _rows(**{
        "Policy Effective Date": ["07-12-26", "07-13-26", "09-30-26", None, "09-30-26"],
        "Market": ["ADMITTED", "ADMITTED", "SURPLUS", "ADMITTED", "SURPLUS"],
        "Master Multi-National": ["No", "No", "No", "No", "Yes"],
    })
    assert list(T.allianz_us_book(df)["Book"]) == ["Runoff", "Admitted", "Non-Admitted", "Runoff", "Multi-National"]


def test_commission_columns_by_book_and_program():
    df = _rows(**{
        "Book": ["Runoff", "Non-Admitted", "Non-Admitted", "Admitted"],
        "Insurance Program": ["Large Market", "SMB Program", "Large Market", "Middle Market Program"],
        "Broker Commission %": ["20.0%"] * 4,
        "MGA Commission %": ["14.0%"] * 4,
    })
    out = T.allianz_us_commission_columns(df)
    assert list(out["Broker Commission %"]) == [None, None, "20.0%", None]
    assert list(out["MGA Commission %"]) == [None, "33.0%", "14.0%", "33.0%"]


def test_bookroll_flags():
    df = _rows(**{"Master Policy Version": ["coalition_manuscripted_2026_v1_0", "v3", None]})
    out = T.allianz_bookroll_flags(df)
    assert list(out["Allianz Bookroll"]) == ["Yes", "No", "No"]
    assert set(out["Captive Frontend"]) == {"No"} and set(out["FAC Reinsurance"]) == {"No"}


def test_column_names_after_endorsement_join():
    df = _rows(**{"Endorsement Label": ["ns"], "Endorsement Label_1": ["looker"], "Config": ["{}"]})
    out = T.allianz_us_column_names(df)
    assert out["Endorsement Label_endts"].iloc[0] == "ns" and out["Endorsement Label"].iloc[0] == "looker"
    assert "Config" not in out.columns


def test_outputs_config_one_file_per_book():
    from pipeui.backend.domain.reports.build import fill_period

    assert [o["filter_value"] for o in A.OUTPUTS] == list(A.BOOKS)
    assert all(o["filter_column"] == "Book" for o in A.OUTPUTS)
    by_book = {o["name"]: o for o in A.OUTPUTS}
    assert by_book["Runoff"]["columns"] == list(A.BASE_COLUMNS)
    assert "NYFTZ" in by_book["Admitted"]["columns"] and "NYFTZ" not in by_book["Non-Admitted"]["columns"]
    assert by_book["Multi-National"]["format"] == "xlsx"
    for book, out in by_book.items():  # pipeui fills the template to the sent file's name
        assert fill_period(out["file_name"], "2026-09") == A.file_name(book, "2026-09")
    assert fill_period(A.CONTROL_FILE["file_name"], "2026-09") == "Day 5 Control - 2026-09.csv"


def test_parity_ignores_excel_resave_noise():
    built = pd.DataFrame({"Internal ID": ["1"], "Date Created": ["8/12/2026 1:51 pm"], "Pct": ["14.0%"],
                          "Short": ["01-01-70"], "Upd": ["2026-08-12"], "Amt": ["103266.0"], "Blank": [None]})
    sent = pd.DataFrame({"Internal ID": ["1"], "Date Created": ["8/12/26 13:51"], "Pct": ["0.14"],
                         "Short": ["1/1/70"], "Upd": ["46246"], "Amt": ["103266"], "Blank": ["0"]})
    assert A.compare_book("Runoff", built, sent).matches


def test_parity_reports_real_differences():
    built = pd.DataFrame({"Internal ID": ["1", "2"], "Amt": ["1", "2"]})
    sent = pd.DataFrame({"Internal ID": ["1", "3"], "Amt": ["5", "2"]})
    r = A.compare_book("Runoff", built, sent)
    assert r.only_built == ["2"] and r.only_sent == ["3"] and r.column_diffs == {"Amt": 1}


def test_formats_typed_columns_like_the_deliverable():
    df = pd.DataFrame({
        "Soft Delete": pd.Series([True, False, None], dtype="boolean"),
        "TCPA": [False, True, False],
        "Policy Effective Date": pd.to_datetime(["2026-07-15", "2026-09-30", None]),
        "Insured Name": ["a", "b", "c"],
    })
    out = T.allianz_us_formats(df)
    assert list(out["Soft Delete"]) == ["Yes", "No", None] or list(out["Soft Delete"])[:2] == ["Yes", "No"]
    assert list(out["TCPA"]) == ["FALSE", "TRUE", "FALSE"]
    assert list(out["Policy Effective Date"])[:2] == ["7/15/26", "9/30/26"]
    assert list(out["Insured Name"]) == ["a", "b", "c"]


def test_multinational_flag_loaded_as_boolean():
    df = _rows(**{"Policy Effective Date": ["09-30-26", "09-30-26"], "Market": ["SURPLUS", "SURPLUS"],
                  "Master Multi-National": pd.Series([True, False], dtype="boolean")})
    assert list(T.allianz_us_book(df)["Book"]) == ["Multi-National", "Non-Admitted"]


def test_master_columns_keep_every_row_once_loads_replace_the_month():
    master = _rows(**{
        "Internal ID": [1, 2], "Allianz Quota Share": [0.2, 0.0],
        "Subsidiary [Agency Customer]": [T.US_SUBSIDIARY] * 2, "Policy Version": ["v3", "v3"],
        "Multi-National Policy": ["No", "No"], "Vantage Quota Share": [0.05, 0.0], "Master Month": [None, None],
    })
    assert len(T.allianz_master_columns(master)) == 2
    master["Master Month"] = ["2026-08", "2026-09"]  # legacy stamped extracts: newest month only
    assert list(T.allianz_master_columns(master)["Master Internal ID"]) == [2]


def test_renamed_reports_are_found_by_their_file_pattern():
    sources = [
        {"source_name": "Allianz Master File", "pattern": A.MASTER_PATTERN, "source_id": "m"},
        {"source_name": "Allianz US AC", "pattern": r"AllianzAccountCurrentResults\d+", "source_id": "a"},
    ]
    assert A._report_for(sources, A.MASTER_REPORT, A.MASTER_SAMPLE)["source_id"] == "m"
    assert A._report_for(sources, A.AC_REPORT, A.AC_SAMPLE)["source_id"] == "a"
