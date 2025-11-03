import pandas as pd


def find_term_extension_transaction(
        policy_list: pd.DataFrame,
        ordered_pl: pd.DataFrame,
        term_date_year: int = 2026
) -> pd.DataFrame:
    """identifies transactions with term extension cancellation that is out in the future (by looking at the 2026 transaction date).

    Takes in a standard policy list used for closes or checking the population that we want to confirm. The ordered policy list
    is usually under v4 - indexer - 2025-10-30.csv, and is created by running the stack from `otc-dq`.

    We assume that the policy list used here, is the `BDX` formatted policy list.
    term_date_year is the year we are considering the `future` date that makes it a term extension
    """
    # Clean the data
    transaction_date = pd.to_datetime(policy_list["Transaction Effective Date"])
    effective_date = pd.to_datetime(policy_list["Policy Effective Date"])

    # [1] Get the cancels or soft deletes for the month
    mask_tbp_negative = policy_list["Total Bound Premium"] < 0
    mask_sd_desc = policy_list["Transaction Description"] == "soft delete"
    mask_cancel_desc = policy_list["Transaction Description"].isin(("Cancellation - Flat", "Cancellation - Pro-Rated"))

    # [2] Apply the filters to see which ones were reversed in the month
    mask_soft_deletes = mask_tbp_negative & mask_sd_desc
    mask_cancellations = mask_cancel_desc
    mask_was_reversed = mask_soft_deletes | mask_cancellations

    # [3] From the ones that were cancelled, find out which policies had effective dates in the future
    mask_has_future_effective_in_policy = pd.Series(transaction_date >= f"{term_date_year}-01-01")
    mask_effective_in_curr_year = pd.Series(effective_date < f"{term_date_year}-01-01")
    mask_endt_desc = policy_list["Transaction Description"] == "Endorsement"
    mask_endt_with_future_effective = (mask_has_future_effective_in_policy & mask_effective_in_curr_year) & mask_endt_desc

    # [4] Get the policies from (3). We want to see which policies from (3) was also reversed this month (2)
    policies_with_future_effective = policy_list[mask_endt_with_future_effective]["Coalition Policy Number"].tolist()
    mask_future_endt_in_ordered = policy_list["Coalition Policy Number"].isin(policies_with_future_effective)  # these are policies with future dates
    affected: pd.DataFrame = policy_list[mask_was_reversed & mask_future_endt_in_ordered].copy()  # reversed and policy has an endt with future date

    # [5] Keep only the policies from the ordered sheet
    ordered_pl = ordered_pl[ordered_pl["--Coalition Policy Number--"].isin(affected["Coalition Policy Number"].tolist())].copy()

    policy_list[mask_endt_with_future_effective].to_csv("/Users/shomendoza/Downloads/Just Policies with Future Effective Dates.csv")
    return ordered_pl
