from enum import Enum


class EnumDescription(Enum):
    """
    The Transaction Description field in Netsuite (custrecord_tran_description)
    """
    cancellation_flat = "Cancellation - Flat"
    cancellation_pro = "Cancellation - Pro-Rated"
    endorsement = "Endorsement"
    issuance = "Issuance"
    reinstatement = "Reinstatement"
    soft_delete = "Soft Delete"



