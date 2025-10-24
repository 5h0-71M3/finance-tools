from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd
from dateutil.relativedelta import relativedelta

from finance_tools.core.policy_stack.base import BaseTransactionLifecycle


@dataclass
class SortingAlgoInfo:
    """if no arguments are given will default to the standard aspen algorithm

    Properties:
        - field_order: ["--Coalition Policy Number--", "Policy Index", "Module", "Mod Index", "Soft Delete Index", "Endorsement Number", "Binder Edit Index"]
        - ascending: [True for _ in field_order]

    """
    field_order: str | list[str] | None = None
    """the order in which we want to sort the data
    
    ie: ["--Coalition Policy Number--", "Policy Index", "Module", "Mod Index", "Soft Delete Index", "Endorsement Number", "Binder Edit Index"]
    """

    ascending: bool | list[bool] | None = None
    """whether we want each field to be in ascending or descending order
    
    ie [all_ascending_order = [True for _ in field_order]] 
    """

    def __post_init__(self):
        if self.field_order is None:
            # this is the standard for Aspen right now
            self.field_order = ["--Coalition Policy Number--", "Policy Index", "Module", "Soft Delete Index", "Mod Index", "Sequence Index", "Endorsement Number", "Binder Edit Index", "Internal ID"]
            # self.field_order = ["--Coalition Policy Number--", "Policy Index", "Internal ID"]

        if self.ascending is None:
            self.ascending = [True for _ in self.field_order]

    def as_args(self) -> dict[str, Any]:
        """will return a dictionary with the param: arg key-value pair
        for processing as a groupby dataframe

        Args:
            - by
            - ascending
            - na_position
        """
        param_map = dict()
        param_map["by"] = self.field_order
        param_map["ascending"] = self.ascending
        param_map["na_position"] = "first"
        return param_map


class TransactionLifecycle(BaseTransactionLifecycle):
    """basically an ordered and grouped ITD report, that will give you
    policy-level data (cumsum), with each transaction having its own
    line.

    This report is required for the Aspen BDX v2, and is required for confirming the
    core premium amounts.
    """
    def __init__(
            self,
            stm_transaction_itd: pd.DataFrame,
    ):
        #  The core ordered ITD - off this, we can remove or keep for diff reports
        self.ordered_itd: pd.DataFrame = self._order_itd(stm_transaction_itd)

    def _order_itd(
            self,
            stm_transaction_itd: pd.DataFrame,
            order_only: bool = False,
            sorting_algo: SortingAlgoInfo | None = None,
    ) -> pd.DataFrame:
        """Function responsible for handling the ordering of the ITD report

        :param stm_transaction_itd: a raw, unformatted STM ITD report
        """
        # 2025.03.25 - wanted to make this a little cleaner
        # 2025.04.09 - new issue module vs mod index
        # 2025.05.13 - ran into issues where a 2000 was ahead of 1000 E32. Changed Module and Mod Index in front of Endorsement, accounting for previous changes
        # 2025.05.13 - ran into issues where ND was 2nd, and removing values from the other endorsements. Switched Binder Edit Index and Endorsement Number
        # 2025.05.13 - moving it back since it was ordering wrong - but going to experiment with soft delete index (placing it where BEI was previously)
        if sorting_algo is None:
            sorting_algo = SortingAlgoInfo()

        if order_only is True:
            stm_transaction_itd: pd.DataFrame = stm_transaction_itd.sort_values(
                **sorting_algo.as_args()
            )
            return stm_transaction_itd

        required_columns = self.all_columns.copy()
        working_dataset = stm_transaction_itd[required_columns].copy()

        # ====Part 1: Get the Balance for each transaction====
        # Working on getting a correctly sorted dataset so we can prep for cumsum
        working_dataset["Endorsement Number"] = working_dataset["Endorsement Number"].fillna(0)

        # 2025.05.13 adding this section since the file is not being ordered correctly
        mask_mod_not_zero = working_dataset["Module"] != 0
        mask_mod_not_na = ~working_dataset["Module"].isna()
        # working_dataset["Module"] = working_dataset["Module"].where(mask_mod_not_zero & mask_mod_not_na, working_dataset["Carrier Policy Number Module"])
        working_dataset["Module"] = working_dataset["Module"].fillna(0)

        # 2025.03.21 - adding ordering for Binder edits
        working_dataset["Binder Edit Index"] = [self._trans_id_splitter_to_index(trans_id) for trans_id in working_dataset["-------------Transaction ID-------------"]]

        # 2025.05.13 - adding a Soft Delete index for ordering soft deletes before Binder Edits
        working_dataset["Soft Delete Index"] = [1 if bei == 1 else 0 for bei in working_dataset["Binder Edit Index"]]

        # 2025.03.24 - adding ordering for 2000 and other full mods since it wasn't recognized previously
        working_dataset["Mod Index"] = [self._trans_id_splitter_to_full_mod(trans_id, "mod") for trans_id in working_dataset["-------------Transaction ID-------------"]]

        # 2025.03.24 - adding ordering for policy since Transaction ID messes things up
        working_dataset["Policy Index"] = [self._trans_id_split_to_policy_code(trans_id) for trans_id in working_dataset["-------------Transaction ID-------------"]]

        # 2025.06.09 - we seemed to have been missing the last two numbers of the 4 digit code
        #  this may have caused a lot of the issues we are seeing `10[01]-N`
        working_dataset["Sequence Index"] = [self._trans_id_splitter_to_full_mod(trans_id, "sequence") for trans_id in working_dataset["-------------Transaction ID-------------"]]

        working_dataset: pd.DataFrame = working_dataset.sort_values(
            **sorting_algo.as_args()
        )
        # ***at this point, we are assuming that the working dataset is in correct order***
        # working_dataset[working_dataset["-------------Transaction ID-------------"].duplicated()].to_csv(f"/Users/shomendoza/Downloads/duplicated_tid{datetime.today()} - v1.0.csv")
        return working_dataset

    def as_aspen_itd(
            self,
            endorsement_type: dict | None = None,
            write_to_disc: bool = True,
    ) -> pd.DataFrame:
        """used part as a v2 formatting function to return a clean dictionary of the values we want
        to use for the BDX file. This is used on the Aspen reporting.

        (1) The TRIA Accepted on Policy Level
        (2) The SIR and Limit Balance

        :param write_to_disc: used as a `checkpoint`, save the current state to the drive
        :param endorsement_type: report signifying whether the policy has the unmapped policy
        """
        working_dataset = self.ordered_itd.copy()

        # ====Part 2: Formatting the limits, add PL TRIA, add Endorsement Type====
        # NOTE: 2025.03.25 => if we are to track which line would cause a negative premium, we need to remove the line BEFORE grouping them

        # todo if we were to add the`dead limit` columns, this is where we would add the flag so we can run some logic
        if isinstance(endorsement_type, pd.DataFrame):
            endorsement_type = endorsement_type.reset_index()
            working_dataset = working_dataset.merge(
                endorsement_type,
                how="left",
                left_on="--Coalition Policy Number--",
                right_on="Quote Coalition Policy Number",
            ).reset_index(drop=True)
            working_dataset = working_dataset.drop(columns="Quote Coalition Policy Number")

        # so we're going to move ahead to make sure that the limit columns are numbers that can be added together
        limits_only = self.limits_only_columns.copy()
        working_dataset["Aspen Quota Share"] = working_dataset["Aspen Quota Share"].fillna(0)
        for field in limits_only:
            try:
                working_dataset[field] = self._aspen_fix_string_to_limit(working_dataset[field], working_dataset["TBP"])  # parsing the column
                working_dataset[field] = [
                    int(coverage * aspen_quota) for coverage, aspen_quota in zip(working_dataset[field], working_dataset["Aspen Quota Share"])
                ]  # Need to get the correct quota share
            except Exception as e:
                raise e

        # We need to add the TRIA data in before grouping
        # let's get the TRIA data sorted out so that we have that per policy number
        working_dataset["Tria Accepted (Yes / No)"] = [1 if tria.lower() == "yes" else 0 for tria in working_dataset["Tria Accepted (Yes / No)"]]
        limits_only.append("Tria Accepted (Yes / No)")  # limits_only is a list. We add it now since we already formatted the limits

        # ***This loops through the limit columns and groups and cumsums by policy number***
        working_dataset = self.to_lifecycle(working_dataset, limits_only, "--Coalition Policy Number--")
        working_dataset["Tria Accepted (Yes / No)"] = ["No" if accepted == 0 else "Yes" for accepted in working_dataset["Tria Accepted (Yes / No)"]]

        # ====Part 3: Last Set of Formatting to be able to get dict====
        # bar exit point to test the backup data

        # Adding the Standard Emily Check
        # need to add the Total Limit Balance here, or it will cumsum all the limit balances and come out incorrectly. Need to get to aspen share
        working_dataset["Aggregate Total Limit Balance"] = working_dataset["Aggregate Total Limit Balance"] * working_dataset["Aspen Quota Share"]
        working_dataset["Limit Variance"] = working_dataset["Aggregate Total Limit Balance"] - working_dataset[self.limits_without_sir].max(axis=1)  # Emily Check (max coverage - agg balance)
        working_dataset["Check - Balance to Calculated Agg Diff"] = working_dataset["Aggregate Total Limit"] - working_dataset["Aggregate Total Limit Balance"]  # calculated agg - NS agg
        working_dataset["Check - Negative Limits"] = working_dataset[self.limits_only_columns].min(axis=1)

        # ====Part 4: Adding in Reinstatements after policy is Cancelled / Soft Deleted ====
        description_mapping = self._aspen_transaction_description(working_dataset)
        working_dataset["New Description"] = ["Missing" if str(iid) in ("3159299",) else description_mapping[iid] for iid in working_dataset["Internal ID"]]

        if write_to_disc:
            working_dataset.to_csv(f"/Users/shomendoza/Downloads/lifecycle_check_aspen_{datetime.today()} - v6.0.csv")
        return working_dataset

    def _aspen_transaction_description(
            self,
            dataframe: pd.DataFrame,
    ) -> dict:
        """uses the current description, transaction id, and coalition policy number in order to determine whether the transaction
        description needs to be updated to Reinstatement or not.

        """
        working_transactions = dataframe.to_dict(orient="records")
        temp_dict = {}  # will add the policy and mark it as "TRUE" if an Issuance was found. Policy False or Policy None indicates no Issuance yet
        results = {}

        # or should I process as True if a BE1, Soft Delete, Cancellation - Flat, or Cancellation - Pro-Rated were processed?
        # For Example, Issuance will add the policy with False. Cancellation or any of the 4 above will mark it as True.
        # Once True, it will make any Issuance a Reinstatement at that point
        cancellation_types = ("Cancellation - Flat", "Cancellation - Pro-Rated", "soft delete")
        for policy in working_transactions:
            try:
                temp_dict[policy["--Coalition Policy Number--"]]
            except KeyError:
                temp_dict[policy["--Coalition Policy Number--"]] = False

            if temp_dict[policy["--Coalition Policy Number--"]] is True:
                # means that a previous cancellation was processed
                if policy["Description"] == "Issuance":
                    results[policy["Internal ID"]] = "Reinstatement"
                    continue

            description_is_be_reversal = self._is_be_reversal(policy["-------------Transaction ID-------------"])
            description_is_cancellation = policy["Description"] in cancellation_types  # Needs to be reinstatement after this
            if description_is_cancellation and not description_is_be_reversal:
                temp_dict[policy["--Coalition Policy Number--"]] = True

            # these will always have a set reversal transaction type
            # this is due to processing of (be0, be1, new) and (original, original-nd)
            if description_is_be_reversal:
                # Transaction is a BE1 of a Cancellation
                if policy["Description"] != "soft delete" and policy["Description"] in cancellation_types:
                    results[policy["Internal ID"]] = "Reinstatement"
                # Transaction is a BE1 of an Issuance or Reinstatement
                elif policy["Description"] == "Issuance" or policy["Description"] == "Reinstatement":
                    results[policy["Internal ID"]] = "Cancellation - Flat"
                # Transaction is a BE1 of Endorsement types
                elif policy["Description"] == "Endorsement":
                    results[policy["Internal ID"]] = policy["Description"]
                elif policy["Description"] == "soft delete":
                    if policy["TBP"] < 0:
                        results[policy["Internal ID"]] = "Cancellation - Flat"
                    else:
                        results[policy["Internal ID"]] = "Reinstatement"
                else:
                    raise Exception(f"Unknown transaction description: {policy['Description']}")
                continue
            elif policy["Description"] == "soft delete":
                if policy["TBP"] < 0:
                    results[policy["Internal ID"]] = "Cancellation - Flat"
                else:
                    results[policy["Internal ID"]] = "Reinstatement"
            else:
                results[policy["Internal ID"]] = policy["Description"]
        return results

    def as_data_check(self) -> pd.DataFrame:
        """this will be the first iteration of a function that catches any transactions that will cause balance or limit
        issues in the future. I will move this over to the proper pacakge.

        :return:
        """
        # We want one where we identify the negative values for as is
        # we want a second one where negative values arise from removing transaction from future

        # ===Dataframe Formatting===
        working_dataset = self.ordered_itd.copy()
        working_dataset["T Effective Date"] = pd.to_datetime(working_dataset["T Effective Date"])

        # ===Starting Variables===
        # Filters and Columns
        _end_of_next_month = date.today() + relativedelta(months=+1, day=31)  # used to compare the Effective Date
        _is_current_transactions = working_dataset["T Effective Date"].dt.date <= _end_of_next_month  # filter for effective before or on End of Month
        agg_cols = self.limits_only_columns.copy()  # columns to aggregate with

        # datasets
        for field in agg_cols:
            try:
                working_dataset[field] = self._aspen_fix_string_to_limit(working_dataset[field], working_dataset["TBP"])
            except Exception as e:
                raise e
        current_dataset = working_dataset[_is_current_transactions].copy()  # used as the dataset to identify negative values from future
        all_dataset = working_dataset.copy()
        agg_cols.append("TBP")  # for the next aggregation step

        # ===The Logic===
        # we're going to try and (1) identify problem policy numbers, then (2) figure out which line is causing the issue
        # Aggregate the Dataset with Cumulative Sum
        current_dataset = self.to_lifecycle(current_dataset, agg_cols, "--Coalition Policy Number--")
        all_dataset = self.to_lifecycle(all_dataset, agg_cols, "--Coalition Policy Number--")

        # Saving for use with the Masterfile
        # all_dataset["Aggregate Total Limit Balance"] = all_dataset["Aggregate Total Limit Balance"] * all_dataset["Aspen Quota Share"]

        all_dataset["Limit Variance"] = all_dataset["Aggregate Total Limit Balance"] - all_dataset[self.limits_without_sir].max(axis=1)
        all_dataset["Check - Balance to Calculated Agg Diff"] = all_dataset["Aggregate Total Limit"] - all_dataset["Aggregate Total Limit Balance"]
        all_dataset["Check - Negative Limits"] = all_dataset[self.limits_only_columns].min(axis=1)

        # Filter Dataset with ones that have negative premium
        negative_data_all = all_dataset[all_dataset["TBP"] < 0].copy()  # Without filter, looks at all lines affected
        negative_data_current = current_dataset[current_dataset["TBP"] < 0].copy()  # with the date filter, includes lines we deem `current`

        # Create two lists of Internal ID. One with currently negative, and another with negatives without the future lines
        _iids_with_negative_balance = negative_data_all["Internal ID"].tolist()
        _would_be_negative_without_line = [iid for iid in negative_data_current["Internal ID"] if iid not in _iids_with_negative_balance]  # depends on future line
        _all_affected_lines = _iids_with_negative_balance.copy()  # weird format, but need to do it this way
        _all_affected_lines.extend(_would_be_negative_without_line)  # all internal ids combined
        _all_policies_affected = all_dataset[all_dataset["Internal ID"].isin(_all_affected_lines)]["--Coalition Policy Number--"].unique().tolist()  # For getting policy number

        deliverable = all_dataset[all_dataset["--Coalition Policy Number--"].isin(_all_policies_affected)].copy()
        return deliverable

    @classmethod
    def to_lifecycle(cls, data: pd.DataFrame, agg_cols: list, key_column: str) -> pd.DataFrame:
        """function that takes an ordered dataframe and a list of columns we want to aggregate,
        and performs a cumulative sum aggregation by the given key column.

        Basically, this function will run the main sauce that converts a properly ordered dataframe
        into a lifecycle ITD report.

        :param data: the properly ordered and formatted dataframe that will go through the transformation
        :param agg_cols: the columns we want to perform a cumulative sum aggregation on. For example, TBP, limits, etc.
        :param key_column: the column we want to use as the `by` argument in the `groupby` function
        :return:
        """
        # todo add check to ensure that agg columns have a type that can be processed

        data[[col for col in agg_cols]] = data.groupby(by=key_column)[agg_cols].cumsum()
        return data
