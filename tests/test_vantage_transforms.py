"""Vantage Day 3 transforms (pipeui_functions/vantage/transforms.py) and the pipeui wiring constants
(bdx_reports/vantage.py)."""
import json

import pandas as pd

from finance_tools.bdx_reports import vantage as V
from finance_tools.pipeui_functions.vantage import transforms as T


def _rows(**columns):
    return pd.DataFrame(columns)


def test_master_gate_keeps_rows_vantage_has_a_share_of():
    df = _rows(**{"Internal ID": [1, 2, 3, 4], "Master Vantage Quota Share": [0.05, 0.0, None, "5.0"]})
    assert list(T.vantage_master_gate(df)["Internal ID"]) == [1, 4]


def test_relabel_soft_deletes_and_binder_edits_only():
    df = _rows(**{
        "Transaction Description": ["soft delete", "soft delete", "Issuance", "Issuance", "Endorsement"],
        "Total Bound Premium": [-10.0, 5.0, -7.0, 3.0, 2.0],
        "External ID": ["A-1", "A-2", "C-X-1002-E-BE1", "C-X-1001-E-BE3", "C-X-1003-E-BE1"],
        "Transaction Type": ["Renewal"] * 5,
    })
    out = T.vantage_relabel_transactions(df)
    assert list(out["Transaction Description"]) == [
        "Cancellation - Flat", "Endorsement", "Cancellation - Flat", "Reinstatement", "Endorsement"]
    assert list(out["Transaction Type"]) == ["Renewal"] * 5


def test_limits_scaled_to_quota_share_blank_as_zero_sign_kept():
    df = _rows(**{
        "Vantage Quota Share %": ["5.00%", "5.00%", "5.00%", "5.00%", "10.00%"],
        "Network and Information Security": ["1000000", None, "-250000", "$1,000", "-"],
        "Per Event Limit": [2000000.0, 0.0, None, 1.0, 100.0],
        "Insured Name": ["a", "b", "c", "d", "e"],
    })
    out = T.vantage_apply_limits(df)
    assert list(out["Network and Information Security"]) == [50000.0, 0.0, -12500.0, 50.0, 0.0]
    assert list(out["Per Event Limit"]) == [100000.0, 0.0, 0.0, 0.05, 10.0]
    assert list(out["Insured Name"]) == ["a", "b", "c", "d", "e"]


def test_module_is_the_full_policy_suffix_or_zero():
    df = _rows(**{"Full Policy": ["CCP1097926-03", "CMP1026304-05", "C-4LPE-042725-CEPMM-2026", None]})
    assert list(T.vantage_module(df)["Module"]) == [3, 5, 0, 0]


def test_package_key_keeps_zero_dollar_replacements():
    df = _rows(Config=[json.dumps({"package_keys": ["end_date"]}), json.dumps({"package_keys": []}), None],
               **{"Total Bound Premium": [10.0, 0.0, 5.0]})
    out = T.vantage_package_key(df)
    assert list(out["Package Key"]) == ["end_date", "endorsement_replacement", None]


def test_renames_land_on_sent_columns_and_layout_is_unique():
    assert len(set(V.SENT_COLUMNS)) == len(V.SENT_COLUMNS)
    assert set(V.RENAMES.values()) <= set(V.SENT_COLUMNS)
    assert {"Employee Count", "Attachment Point", "Sequence"}.isdisjoint(V.SENT_COLUMNS)
