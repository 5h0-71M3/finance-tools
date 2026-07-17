"""Allianz US report (Day 5 BDX) — carrier-UNIQUE validation, ported for pipeui.

Mirrors the legacy ``AllianzUSValidation`` MRO
(AllianzUSValidation -> AllianzBasicValidation -> BasicValidation). Only the
Allianz-US-specific check is defined here; the rest are REUSED (no duplication):

  package_key_missing_on_expected_transactions   -> defined below (unique)
  allianz_commission_rate_matches_google_sheet   -> shared/validations.py
  validate_carrier_bound_premium (scalar)        -> shared/validations.py
  validate_carrier_net_premium                   -> vantage/validations.py
  validate_carrier_commission_to_coalition       -> vantage/validations.py
  validate_limit_signature_matches_tbp           -> vantage/validations.py
  transaction_id_is_nan                          -> vantage/validations.py
  surplus_3_0_filled                             -> vantage/validations.py

Column bindings (function param -> report column) for the full Allianz US set:
  transaction_description         -> "Transaction Description"
  soft_delete                     -> "Soft Delete"
  external_id                     -> "External ID"
  package_key                     -> "Package Keys"
  surplus_3_0                     -> "Surplus 3.0"
  policy_effective_date           -> "Policy Effective Date"
  coalition_percent_commission    -> "Coalition Commission %"
  tbp                             -> "Total Bound Premium"
  carrier_bound_premium           -> "Allianz Bound Premium"
  carrier_net_premium             -> "Allianz Net Premium"
  carrier_quota_share             -> "Allianz Quota Share %"
  carrier_percent_commission      -> "Coalition Commission %"
  carrier_commission_to_coalition -> "Allianz $ Commission To Coalition"
  base_limit                      -> "Aggregate Total Limit"
"""
import pandas as pd


def package_key_missing_on_expected_transactions(
    transaction_description: pd.Series,
    soft_delete: pd.Series,
    external_id: pd.Series,
    package_key: pd.Series,
) -> pd.Series[bool]:
    """this check aims to check if there are package keys missing,
    usually due to custom endorsements, where the endorsement
    UUID is missing.

    :return:
    """
    package_key = package_key.fillna("missing")

    results = []
    for desc, sd, eid, pk in zip(
            transaction_description,
            soft_delete,
            external_id,
            package_key
    ):
        if pk == "missing":
            # not expected transactions
            if desc not in ("Cancellation - Flat", "Cancellation - Pro-Rated", "Endorsement"):
                results.append(True)
                continue
            # is a soft delete
            if str(sd) == "Yes":
                results.append(True)
                continue
            # checking if BE series
            last_three_char = str(eid)[-3:]
            first_two_of_last_three_char = last_three_char[:2].lower()
            if first_two_of_last_three_char == "be":
                results.append(True)
                continue
            # otherwise, it should have a Package Key
            results.append(False)
        else:
            # package key is not missing
            results.append(True)
    return pd.Series(results)
