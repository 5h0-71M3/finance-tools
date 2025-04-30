from datetime import date

import pandas as pd

from src.file_handling.directory_handler import FOLDERS

"""These may end up as validations in the future"""


def find_erp_with_inactive_policy() -> pd.DataFrame:
    """2025.05.29 the ask here was to identify the following transactions:

    Ask:
        1. Policy: 2025/01 - 2025/12
        2. Was Cancelled - Flat
        3. ERP endorsement starts from 2025/01
        4. Can't have an ERP endorsement with a policy that's never been active

    :return:
    """
    f = FOLDERS()
    policy_list = f.get_policy_list()

    # ===[1.1]=== create the masks we think we'll be needing to solve this
    # [1.1.1] masks for ERP
    mask_transaction_date_matches_effective = policy_list["Transaction Effective Date"] == policy_list["Policy Effective Date"]
    mask_is_erp = policy_list["Extended Reporting Period"] == "Yes"
    mask_erp_matches_policy_effective = mask_is_erp & mask_transaction_date_matches_effective  # these are probably wrong

    # [1.1.2] masks for main policy
    mask_not_soft_delete = policy_list["Soft Delete"] != "Yes"
    mask_not_binder_edit = policy_list["Binder Edit"] != "Yes"
    mask_non_financial_transaction = mask_not_soft_delete & mask_not_binder_edit

    # ===[1.2]=== apply the masks and see where we are
    # [1.2.1] apply the relevant headers
    ticket_related_headers = [
        "Internal ID",
        "Coalition Policy Number",
        "Date Created",
        "Policy Effective Date",
        "Policy Expiration Date",
        "Transaction Effective Date",
        "Extended Reporting Period",
        "Subsidiary [Agency Customer]",
        "Soft Delete",
        "Binder Edit",
        "Total Bound Premium"
    ]

    # [1.2.2] applying and creating new dataframe
    applied_df: pd.DataFrame = policy_list.loc[mask_erp_matches_policy_effective & mask_non_financial_transaction, ticket_related_headers].copy()
    applied_df = applied_df.set_index("Internal ID")

    # [1.2.3] we need one more mask to identify the soft deletes under ERP
    mask_duplicated = applied_df["Coalition Policy Number"].duplicated(keep=False)
    applied_df.to_excel(f.DOWNLOADS / f"ERP Transactions with Effective Date at Start of Policy (All) - {date.today()}.xlsx")

    # [1.2.4] applying the reverse of the duplicated so they are excluded
    applied_df = applied_df.loc[~mask_duplicated].copy()

    # ===[1.3]=== save down the file and see what we have
    applied_df.to_excel(f.DOWNLOADS / f"ERP Transactions with Effective Date at Start of Policy (No Dupe) - {date.today()}.xlsx")
    return applied_df
