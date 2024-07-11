import dataclasses
from datetime import datetime
from decimal import Decimal

from objects.base import Transaction
from objects.enums.netsuite import EnumDescription


@dataclasses.dataclass
class TransactionLT(Transaction):
    """
    A Lifetime Transaction Node, used to validate for sequencing.


    Attributes:
        * key: takes in a key, we use 'Internal ID' for the key
        * transaction_id: The external id code
        * description: the type of transaction it is (endorsement, issuance, etc.)
        * report_date: the date the transaction is set to be reported
        * create_date: the date the transaction was created in the system
        * effective_date: the first date the policy is active
        * premium: the premium amount of the transaction
        * policy_uuid: the uuid of the policy that this transaction belongs to
        * be_sd: Binder Edit / Soft Delete Complete column

    """
    key: int
    transaction_id: str
    policy_uuid: str
    description: EnumDescription
    report_date: datetime
    create_date: datetime
    effective_date: datetime
    premium: Decimal
    be_sd: str

    def __repr__(self):
        return f"Key: ({self.description.value} {self.key})"


class SequencePipeline:
    def __init__(self):
        """
        Pipeline for validating transaction sequences.

        This will allow us to know when erroneous transactions are created, when multiple policies are
        under the same insured, and any other check we need regarding the sequence of transactions.

        """
        self.curr_node: TransactionLT | None = None

    @staticmethod
    def _verify_issuance_sequencing(curr_node, check_node) -> bool:
        """
        When the current node is an issuance, we check the check_node for sequencing issues.
        The check node is what comes after the current node.

        :param check_node:
        :return:
        """
        match check_node.description:
            case EnumDescription.issuance:
                if check_node.effective_date.year == curr_node.effective_date.year:
                    if check_node.be_sd == "Yes":
                        # let's let soft deletes and binder edits pass through for now
                        return True
                    # error if there are two issuance transactions, both in the same policy year
                    return False
                return True
            case EnumDescription.reinstatement:
                # a Reinstatement transaction can't follow an Issuance, must follow cancellations
                return False
            case EnumDescription.endorsement:
                return True
            case EnumDescription.soft_delete:
                return True
            case EnumDescription.cancellation_flat:
                if curr_node.policy_uuid == check_node.policy_uuid:
                    if abs(curr_node.premium) - abs(check_node.premium) > .05:
                        # Must cancel each other out. Error if there's a balance.
                        print(f"{abs(curr_node.premium - check_node.premium)}")
                        return False
                return True
            case EnumDescription.cancellation_pro:
                return True
        return False

    @staticmethod
    def _verify_endorsement_sequencing(curr_node, check_node):
        match check_node.description:
            case EnumDescription.issuance:
                print(curr_node)

            case EnumDescription.reinstatement:
                pass

            case EnumDescription.endorsement:
                pass
            case EnumDescription.soft_delete:
                pass
            case EnumDescription.cancellation_flat:
                pass
            case EnumDescription.cancellation_pro:
                pass
        return True

    @staticmethod
    def _verify_cancellation_sequencing(curr_node, check_node):
        match check_node.description:
            case EnumDescription.issuance:
                pass

            case EnumDescription.reinstatement:
                print(curr_node)

            case EnumDescription.endorsement:
                pass
            case EnumDescription.soft_delete:
                pass
            case EnumDescription.cancellation_flat:
                pass
            case EnumDescription.cancellation_pro:
                pass
        return True

    @staticmethod
    def _verify_reinstatement_sequencing(curr_node, check_node):
        match check_node.description:
            case EnumDescription.issuance:
                if check_node.effective_date.year == curr_node.effective_date.year:
                    # error if there are two issuance transactions, both in the same policy year
                    return False
                return True

            case EnumDescription.reinstatement:
                pass

            case EnumDescription.endorsement:
                pass
            case EnumDescription.soft_delete:
                pass
            case EnumDescription.cancellation_flat:
                pass
            case EnumDescription.cancellation_pro:
                pass
        return True

    @staticmethod
    def _verify_soft_delete_sequencing(curr_node, check_node):
        match check_node.description:
            case EnumDescription.issuance:
                pass

            case EnumDescription.reinstatement:
                pass

            case EnumDescription.endorsement:
                pass
            case EnumDescription.soft_delete:
                pass
            case EnumDescription.cancellation_flat:
                pass
            case EnumDescription.cancellation_pro:
                pass
        return True

    def _validate_node_sequence(self, node: TransactionLT) -> bool:
        """
        check node and curr node
        :param node:
        :return:
        """
        # Checking for start of the sequence
        print(f"Current Node: {self.curr_node}, CHECKING: {node}")
        if self.curr_node is None:
            if node.description not in [EnumDescription.issuance, EnumDescription.reinstatement]:
                # a starting node needs to either be an Issuance or Reinstatement
                return False
            self.curr_node = node
            return True

        # Validating the sequence
        check_node = node

        # Current Node => Issuance
        if self.curr_node.description == EnumDescription.issuance:
            result = self._verify_issuance_sequencing(self.curr_node, check_node)
            self.curr_node = check_node
            return result

        # Current Node => Cancellation - Flat or Cancellation Pro-Rated
        elif self.curr_node.description in [EnumDescription.cancellation_flat, EnumDescription.cancellation_pro]:
            result = self._verify_cancellation_sequencing(self.curr_node, check_node)
            self.curr_node = check_node
            return result

        # Current Node => Reinstatement
        elif self.curr_node.description == EnumDescription.reinstatement:
            result = self._verify_reinstatement_sequencing(self.curr_node, check_node)
            self.curr_node = check_node
            return result

        # Current Node => Soft Delete
        elif self.curr_node.description == EnumDescription.soft_delete:
            result = self._verify_soft_delete_sequencing(self.curr_node, check_node)
            self.curr_node = check_node
            return result

        # Current Node => Endorsement
        elif self.curr_node.description == EnumDescription.endorsement:
            result = self._verify_endorsement_sequencing(self.curr_node, check_node)
            self.curr_node = check_node
            return result
        else:
            raise KeyError(f"Unrecognized node description: {self.curr_node.description}")

    def run_pipline(self, nodes: list[TransactionLT], verbose: bool = False) -> (bool, str):
        for node in nodes:
            if verbose:
                print()
                print("...")
                print(node.description)
            if not self._validate_node_sequence(node):
                return False, f"Error on Node {node.key} - invalid sequence {node.description}."
        return True, f"Success!"
