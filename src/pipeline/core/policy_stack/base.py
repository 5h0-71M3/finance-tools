from typing import Literal

import pandas as pd


class BaseTransactionLifecycle:
    """used for ordering transactions, and assumes we grouped by limits / premium
    so that we can track whether a single transaction will cause an issue
    """
    _mainline_columns = {
        "Internal ID": "Internal ID",
        "Aspen Quota Share": "Aspen Quota",
        "Endorsement UUID (endts only)": "Endorsement UUID (endts only)",
        "-------------Transaction ID-------------": "External ID",
        "Description": "Transaction Description",
        "Endorsement Number": "end_id",
        "--Coalition Policy Number--": "Coalition Policy Number",
        "Soft Delete": "soft_delete",
        "Module": "mod",
        "Binder Edit": "Binder Edit",
        "TBP": "Total Bound Premium",
        "Tria Accepted (Yes / No)": "Tria Accepted (Yes / No)",
        "T Effective Date": "Transaction Effective Date",
        "Aggregate Total Limit Balance": "Aggregate Total Limit Balance",
        }

    # Will be going through aggregation functions
    _limit_only_columns_map = {
        "Network and Information Security": "Network and Information Security",
        "Regulatory Fines and Penalties": "Regulatory Fines and Penalties",
        "Multimedia Content": "Multimedia Content",
        "PCI Fines and Assessments": "PCI Fines and Assessments",
        "Breach Response": "Breach Response",
        "Breach Response Costs": "Breach Response Costs",
        "Crisis Management and Public Relationship": "Crisis Management and Public Relationship",
        "Cyber Extortion": "Cyber Extortion",
        "Business Interruption And Extra Expense": "Business Interruption And Extra Expense",
        "Digital Asset Restoration": "Digital Asset Restoration",
        "Funds Transfer Fraud": "Funds Transfer Fraud",
        "Reputation Repair": "Reputation Repair",
        "BI/PD - Third Party": "BI/PD - Third Party",
        "BI/PD - First Party": "BI/PD - First Party",
        "Pollution": "Pollution",
        "Systems Integrity Restoration": "Systems Integrity Restoration",
        "Computer Replacement": "Computer Replacement",
        "Technology E&O": "Technology E&O",
        "Service Fraud": "Service Fraud",
        "Reputational Harm Loss": "Reputational Harm Loss",
        "Invoice Manipulation Sublimit": "Invoice Manipulation Sublimit",
        "Phishing Sublimit": "Phishing Sublimit",
        "Funds Transfer Liability Sublimit": "Funds Transfer Liability Sublimit",
        "Criminal Reward Sublimit": "Criminal Reward Sublimit",
        "Court Attendance Sublimit": "Court Attendance Sublimit",
        "Proof of Loss Preparation Expenses": "Proof of Loss Preparation Expenses",
        "MPL Sublimit": "MPL Sublimit",
        "SIR": "SIR / Attachment Point",
        "Aggregate Total Limit": "Aggregate Limit",
    }

    limits_only_columns: list = list(_limit_only_columns_map.keys())
    limits_without_sir = [
        # used in Variance check and including the agg limits will make everything 0
        limit for limit in limits_only_columns if limit not in ("SIR", "Aggregate Total Limit", "Aggregate Total Limit Balance")
    ]
    all_columns: list = list(_mainline_columns | _limit_only_columns_map)

    @classmethod
    def _trans_id_splitter_to_index(cls, transaction_id: str) -> int:
        """function that splits the Transaction ID and attempts to assign a number for the
        Soft Deletes and Binder Edits in the correct order

        :param transaction_id: (external id field)
        :return:
        """
        formatted_ex_id = str(str(transaction_id).split("-")[-1])
        if formatted_ex_id.lower() in ("nd", "sd", "ed", "rnd"):  # soft deletes
            return 1
        elif formatted_ex_id[-3: -1].lower() in ("be",):  # binder edits
            try:
                last_number = int(formatted_ex_id[-1])
            except Exception as e:
                if formatted_ex_id[-1] == "D":
                    return 1
                raise e
            if last_number % 2 == 0:  # is even
                return -2
            else:
                return -1
        return 0

    @classmethod
    def _is_be_reversal(cls, transaction_id: str) -> bool | None:
        """function that determines whether the Binder Edit is a reversal
        based on the Transaction ID suffix

        """
        last_value = str(transaction_id).split("-")[-1]
        # HANDLING BINDER EDITS
        if last_value[-3: -1].lower() in ("be",):
            try:
                be_number = int(last_value[-1])
            except Exception as e:
                if last_value[-1] == "D":
                    return False
                else:
                    raise e
            if be_number % 2 != 0:  # odd number (is a reversal) (BE1)
                return True
        return False

    @classmethod
    def _trans_id_splitter_to_full_mod(cls, transaction_id: str, mod_or_sequence: Literal["mod", "sequence"] | None = None) -> int:
        """takes the transaction ID and returns the full mod (1000, 2000).
        This is used for sorting the ITD into the correct order

        :param transaction_id: (external id field)
        :return:
        """
        split_trans_id = [component for component in str(transaction_id).split("-") if component.isdigit()]  # noticed that trans id only has two digit comps (the mod combo and date)
        try:
            mod_code = split_trans_id[-1]

        except IndexError as ie:
            print(f"Invalid transaction ID: {transaction_id}: {ie}")
            mod_code = 1  # just a default number that won't affect much
            return mod_code
        except Exception as e:
            print(f"Transaction ID: {transaction_id}")
            print(f"Length Transaction ID: {len(split_trans_id)}")
            raise e
        if mod_or_sequence is None:
            return int(mod_code)

        if mod_or_sequence == "mod":
            return int(mod_code[0])
        elif mod_or_sequence == "sequence":
            return int(mod_code[-1])
        else:
            raise Exception(f"Mod or Sequence Not Supported: {mod_or_sequence}")

    @classmethod
    def _trans_id_split_to_policy_code(cls, transaction_id: str) -> str:
        """extracts the Policy Code from the Transaction ID. Defaults to CD
        as a string that won't heavily affect the string. Can be something we change
        in the future.

        """
        split_trans_id = str(transaction_id).split("-")
        try:
            policy_code = split_trans_id[0]
        except IndexError:
            policy_code = "CD"  # just a default number that won't affect much
        return policy_code

    @classmethod
    def _aspen_fix_string_to_limit(cls, coverage_field: pd.Series, premium_field: pd.Series | None = None) -> pd.Series:
        """attempts to parse and format a Limit coverage field

        :param coverage_field: The Limit field
        :param premium_field: The TBP premium field, used to determine limit signature
        """
        # (1) Initial try. We're assuming the limit just needs to be filled
        try:
            coverage_field = coverage_field.fillna(0)
            coverage_field = coverage_field.astype(float).astype(int)
            return coverage_field
        except ValueError:  # tells us that this is formatted as a string
            coverage_field = coverage_field.astype(str).fillna("0")

            # FORMATTING THE STRING TO MAKE IT NUMBER LIKE
            coverage_field = coverage_field.str.strip()  # handles leading whitespace
            coverage_field = coverage_field.str.rstrip("_")  # handles leading whitespace
            coverage_field = coverage_field.str.lower().replace("nan", "0")  # handles nan values
            coverage_field = coverage_field.str.replace("$", "")  # handles dollar signs
            coverage_field = coverage_field.str.replace(",", "")  # handles commas
            coverage_field = coverage_field.str.replace("_", "")  # handles leading whitespace
            coverage_field = coverage_field.str.replace('                                 -', "")  # handling special case

        # (2) Second try. Once we made the string formats, let's see if it converts to a limit
        try:
            coverage_field = pd.to_numeric(coverage_field, errors="coerce", downcast="integer")
            coverage_field = coverage_field.fillna(0)
            coverage_field = coverage_field.astype(int)
            return coverage_field
        except Exception as e:  # tells us we are still running into issues
            print(f"From aspen_fix_string_to_limit: {e}")
            # Let's run it through built in formatters for extra security
            coverage_field = coverage_field.astype(float)
            coverage_field = coverage_field.fillna(0).astype(int)
            print("HERE")

        # (3) optional parameter to allow us to correctly align the premium amounts
        if isinstance(premium_field, pd.Series):
            coverage_field = pd.Series(
                [
                    abs(coverage) if tbp >= 0
                    else abs(coverage) * -1
                    for coverage, tbp in zip(coverage_field, premium_field)
                ]
            )
        return coverage_field
