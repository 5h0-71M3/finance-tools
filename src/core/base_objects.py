from dataclasses import dataclass


@dataclass
class MasterFileBdxDetails:
    """Object used to process the final carrier reporting from the Master File.
    Used for creating a BDX from the Masterfile

    :param reported_field: name of the `reported` column  in the Master file
    :param quota_share_field: name of the `quota share` column in the Master file
    :param subsidiary: name of the `subsidiary` column in the Master file

    :param market: [optional] name of the `market` column in the Master file. Used for SwissRe.
    :param umr: [optional] the UMR code for the Carrier BDX we are pulling for. Used for Lloyds.
    :param excess: [Optional] the Primary/Excess split if the carrier splits it by market.
    """
    reported_field: str
    quota_share_field: str
    subsidiary: str

    market: str | None = None
    umr: str | None = None
    excess: str | None = None
