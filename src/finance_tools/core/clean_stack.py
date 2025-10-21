# The goal with these clean stacks is going to be so that I can wade through all this complex
# Netsuite grouping for transactions that have a lot of in and outs
from dataclasses import dataclass
from datetime import date

from finance_tools.io.directory_handler import FOLDERS


@dataclass
class CleanRecord:
    """Stores information for each node in the graph
        Information:
        - Internal ID

        Date Information:
            - Date Created
            - Effective Date
            - End Date
            - Transaction Date

        Reported Information:
            - Reported (by Carrier)
            - Reported Date (by Carrier)

        For Sorting:
            - Policy Number
            - Transaction ID
            - Description (Need to Rank Them)
            - Endorsement Index
            - Soft Delete
            - Binder Edit
            - Binder Edit Completed
    """
    internal_id: int
    date_created: date
    effective_date: date
    end_date: date
    transaction_date: date

    policy_number: str
    transaction_id: str
    description: str
    endorsement_index: int
    soft_delete: str | bool
    binder_edit: str | bool
    binder_edit_completed: str | bool

    reported: bool | str | None = None
    reported_date: date | None = None


class CleanStack(list):
    def __init__(self):
        super().__init__()

    def first_transaction(self):
        """should give me the first transaction of the Policy
        """
        return self.pop(0)

    def last_transaction(self):
        """this would be the `most recent` transaction, and is at the back of the stack
        """
        return self.pop(-1)


def clean_stack_from_policy_list():
    f = FOLDERS()
    df = f.get_policy_list()

    # (1) Formatting and Prepping the Policy List
    df["Endorsement Number"] = df["Endorsement Number"].fillna(0).astype(int)  # Issuance (Normal, SD, BE) won't have a number

    # Soft Deletes
    mask_description_is_soft_delete = df["Transaction Description"] == "Soft Delete"
    df.loc[(mask_description_is_soft_delete & df["Total Bound Premium"] < 0), "Transaction Description"] = "Cancellation - Flat"
    df.loc[(mask_description_is_soft_delete & df["Total Bound Premium"] > 0), "Transaction Description"] = "Reinstatement"  # needs to be Issuance if no prior Issuance reported
    df.loc[mask_description_is_soft_delete, "Endorsement Number"] = df["Endorsement Number"] + .1

    # Binder Edits
    df["Binder Edit"] = df["Binder Edit"] == "Yes"
    df["Binder Edit/Soft Delete Complete"] = df["Binder Edit/Soft Delete Complete"] == "Yes"

    df["Binder Code"] = df[(df["Binder Edit"] == "Yes" & df["Binder Edit/Soft Delete Complete"] == "Yes")]["Transaction ID"].str[-1].astype(int)
    print(df["Binder Code"].head())

    df.loc[df["Binder Code"] % 2 != 0, "Endorsement Number"] = df["Endorsement Number"] + 1000.1
    df.loc[df["Binder Code"] % 2 == 0, "Endorsement Number"] = df["Endorsement Number"] - .1

    # (2) sort the Dataframe
    df = df.sort_values(by=["Coalition Policy Number", "Transaction ID", "Endorsement Number"], ascending=[True, True, True])
    df = df.rename(columns={"Transaction ID": "TID", "Endorsement Number": "EN", "Transaction Description": "Description", "Total Bound Premium": "TBP"})

    print(df.info())
    print(df.tail())
    print(df["Coalition Policy Number"].unique())

    print(df[df["Coalition Policy Number"] == "C-4MQ8-453750-CYBER-2025"][["TID", "EN", "Description", "TBP"]])


clean_stack_from_policy_list()

