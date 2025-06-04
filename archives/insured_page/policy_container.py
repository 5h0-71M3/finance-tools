import dataclasses
import datetime
from decimal import Decimal
from typing import Optional

import pandas as pd


@dataclasses.dataclass
class TransactionLine:
    """
    Represents a single Transaction. Can be thought of as a row on an Excel sheet that has test_data on a transaction.
    """

    """meta"""
    # Properties used to identify important information
    internal_id: int
    description: str

    """Other IDs"""
    transaction_id: Optional[str] = None

    """Optional Premiums"""
    tria: float | Decimal = None
    tbp: float | Decimal = None

    """Data Fields"""
    date_created: datetime.datetime | datetime.date = None

    def as_dict(self):
        """
        Returns object as a dictionary
        :return:
        """
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SwissReTransactionLine(TransactionLine):
    """
    Represents a single line that checks for SwissRe-centric test_data
    """
    endorsement_number: Optional[int] = None
    policy_uuid: Optional[str] = None
    sre_bound_premium: Optional[float] | Optional[Decimal] = 0


@dataclasses.dataclass
class CoverageDetailTransactionLine(TransactionLine):
    """
    Represents a single line that checks for Coverage Related Data

    Attributes:
        aggregate_limit: tradtional limit field
        aggregate_limit_balance: limit balance on the policy (with most recent endorsement holding the policy balance)
        sir: retention field

    """
    aggregate_limit: Optional[int] = None
    aggregate_limit_balance: Optional[int] = None
    sir: Optional[int] = None


@dataclasses.dataclass
class TransactionOrderLine:
    """
    Used in conjunction with the Transaction Parser and Transaction Stack. This helps to sort the transactions in order.

    Attributes:
        id: str = CMP114331
        code: int = 1000
        split: int = 5
        mod: str = 00
        financial_transaction: bool = False (if soft delete or binder edit)

    """
    id: str
    code: int
    split: int
    mod: Optional[str] = ""
    financial_transaction: bool = False

    def as_dict(self) -> dict:
        """
        Returns object as a dictionary

        :return: The mapping: {id: str, mod: int, code: int, split: int}
        """
        return dataclasses.asdict(self)


class TransactionStack(list):
    """
    A stack of transactions, used for Data Quality on transactions.
    Can be thought of as a Policy object.

    Will only accept Transaction objects when using the t-functions.

    Initializing:
        - from_policy: pulls and creates object. Expects sorted Dataframe

    Functions:
        - t_push: adds a transaction to the stack. Raises error if not type Transaction
        - t_pop: removes a transaction from the stack. Raises error if out of index
        - sum: adds the field param in the stack to get the total number
    """

    def t_push(self, transaction: TransactionLine) -> None:
        if not isinstance(transaction, TransactionLine):
            raise TypeError(f"Expect type Transaction, but got {type(transaction)}")
        self.append(transaction)

    def t_pop(self, index=0) -> TransactionLine:
        """
        a list.pop() with validation for Transaction objects

        :param index: where you would like to pop from
        :return:
        """
        if index >= len(self):
            raise IndexError(f"Index {index} out of range {len(self)}")
        value = self.pop(index)
        return value

    def sum(self, field: str) -> Decimal:
        """
        Iterates through self and sums the value of the field argument

        :param field: the field you want to sum
        :return: the value
        """
        if field not in self[0].as_dict():
            raise KeyError(f"Field {field} is not in {self[0].as_dict()}")
        value: Decimal = Decimal(0)
        for transaction in self:
            if field in transaction.as_dict():
                field_amount = Decimal(transaction.as_dict()[field]).quantize(Decimal('1.00'))
                value += field_amount
                continue
        return value

    def infer_limit(self, missing_transaction: TransactionLine = None) -> TransactionLine:
        """
        INCOMPLETE FUNCTION BUT TRIES TO INFER THE LIMIT

        :param missing_transaction:
        :return:
        """
        stack = TransactionStack(v for v in self)
        potential_issuance_line = None

        if missing_transaction is not None:
            requested_description = missing_transaction.description
        else:
            requested_description = "Reinstatement"  # I think we're defaulting here because the issues usually lies in the reinstatement

        while len(stack) > 0:
            transaction = stack.t_pop()
            if requested_description == "Reinstatement":
                is_issuance = transaction.description == "Issuance"
            else:
                is_issuance = False

            if is_issuance:
                potential_issuance_line = transaction
                break
        return potential_issuance_line

    def validate_mods(self):
        stack = TransactionStack(v for v in self)

        while len(stack) > 0:
            check = stack.t_pop()
            print(check)


class TransactionParser:
    @staticmethod
    def as_transaction_breakdown(transaction_id: str) -> TransactionOrderLine:
        """
        Breaks the Transaction ID down into its components. We need this component in order to sort the TransactionStack correctly.
        This will allow us to get the information from a string that looks like this: CMP1114331-00-GA-1000-N

        Properties:
            - id: CMP114331
            - mod: 00
            - code: 1000
            - split: number of splits (5)
            - financial_transaction: False (if soft delete or binder edit)

        The mapping: {id: str, mod: int, code: int, split: int}

        """
        # defaults to no
        breakdown_map = {"financial_transaction": False}
        split_id = transaction_id.split("-")
        finance_transactions = ["BE0", "BE1", "BE2", "BE3", "BE4", "BE5", "SD", "ND", "ED", "RND"]

        # CYP1086755-01-PE-1000-RN
        if len(split_id) == 5:
            breakdown_map["id"] = transaction_id
            breakdown_map["mod"] = split_id[1]
            breakdown_map["code"] = split_id[3]
            breakdown_map["split"] = 5

            if split_id[-1] in finance_transactions:
                breakdown_map["financial_transaction"] = True
            return TransactionOrderLine(**breakdown_map)

        # CYP1086755-01-PE-1000-RN-BE0
        if len(split_id) == 6:
            breakdown_map["id"] = transaction_id
            breakdown_map["mod"] = split_id[1]
            breakdown_map["code"] = split_id[3]
            breakdown_map["split"] = 6

            if split_id[-1] in finance_transactions:
                breakdown_map["financial_transaction"] = True
            return TransactionOrderLine(**breakdown_map)

        if len(split_id) == 8 or len(split_id) == 9 and split_id[-1] in finance_transactions:
            # C-4MX8-171036-CYBER-2023-ON-1001-E or C-4MX8-171036-CYBER-2023-ON-1001-E-BE1
            breakdown_map["id"] = transaction_id
            breakdown_map["mod"] = ""
            breakdown_map["code"] = split_id[6]
            breakdown_map["split"] = 8

            if split_id[-1] in finance_transactions:
                breakdown_map["financial_transaction"] = True
            return TransactionOrderLine(**breakdown_map)

        if len(split_id) == 9 and split_id[-1] not in finance_transactions:
            # C-4MX8-171036-CYBER-2023-A-ON-1001-E
            breakdown_map["id"] = transaction_id
            breakdown_map["mod"] = ""
            breakdown_map["code"] = split_id[7]
            breakdown_map["split"] = 9

            if split_id[-1] in finance_transactions:
                breakdown_map["financial_transaction"] = True
            return TransactionOrderLine(**breakdown_map)

        if len(split_id) == 10:
            # C-4MX8-171036-CYBER-2023-A-ON-1001-E-BE1
            breakdown_map["id"] = transaction_id
            breakdown_map["mod"] = ""
            breakdown_map["code"] = split_id[7]
            breakdown_map["split"] = 9

            if split_id[-1] in finance_transactions:
                breakdown_map["financial_transaction"] = True
            return TransactionOrderLine(**breakdown_map)
        raise Exception(f"Invalid transaction id breakdown. Please code: {transaction_id}")


def from_policy(mapper: dict, data: pd.DataFrame, policy_number: str) -> TransactionStack:
    """Currently specific to STM Transaction Report. Create Mapper class to extend"""
    data = data.rename(columns=mapper)

    # Used for Categorical Integers
    for column in ("internal_id", "aggregate_limit", "sir", "endorsement_number", "mod"):
        data[column] = data[column].fillna(0)
        data[column] = data[column].astype(int)

    data = data.sort_values(by=["internal_id", "date_created"])
    policy_filter = data["coalition_policy_number"] == policy_number
    data = data[policy_filter].copy()

    policy_stack = TransactionStack()
    for transaction in data.itertuples():
        new_transaction = TransactionLine(
            internal_id=transaction.internal_id,
            description=transaction.description,
            date_created=transaction.date_created,
            tbp=transaction.tbp,
            aggregate_limit=transaction.aggregate_limit,
            sir=transaction.sir,
            endorsement_number=transaction.endorsement_number,
            policy_uuid=transaction.policy_uuid,
            sre_bound_premium=transaction.sre_bound_premium,
            transaction_id=transaction.transaction_id,
            tria=transaction.total_tria
        )
        policy_stack.append(new_transaction)
    return policy_stack
