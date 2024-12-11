"""Metadata consists of column metadata (to normalize the test_data) and checks (to validate it)

The directory structure reflects this by splitting metadata into 2 directories:
    1. check: holds modules related to checks that are performed on the test_data
    2. report: holds modules related to mapping and updating columns

"""

# Imports for Netsuite Related Metadata
from src.pipeline.reports.metadata._object import Metadata
from src.pipeline.reports.metadata.carrier_v1 import netsuite_carrierv1_field_mapping as _netsuite_carrierv1_field_mapping
from src.pipeline.reports.metadata.carrier_v1 import netsuite_carrierv1_commission_percentage as _netsuite_carrierv1_commission_percentage
from src.pipeline.reports.metadata.carrier_v1 import netsuite_carrierv1_bound_premium as _netsuite_carrierv1_bound_premium
from src.pipeline.reports.metadata.carrier_v1 import netsuite_carrierv1_net_premium as _netsuite_carrierv1_net_premium
from src.pipeline.reports.metadata.carrier_v1 import netsuite_carrierv1_commission_amount as _netsuite_carrierv1_commission_amount
from src.pipeline.reports.metadata.carrier_v1 import netsuite_carrierv1_quota_share as _netsuite_carrierv1_quota_share

from src.pipeline.reports.metadata.netsuite_limit import netsuite_limit_field_mapping as _netsuite_limit_field_mapping
from src.pipeline.reports.metadata.netsuite_limit import netsuite_limit_columns as _netsuite_limit_columns

from src.pipeline.reports.metadata.netsuite_surcharge import netsuite_surcharge_field_mapping as _netsuite_surcharge_field_mapping

# Imports for Looker Related Metadata
from src.pipeline.reports.metadata.looker_limit import looker_limit_field_mapping as _looker_limit_field_mapping
from src.pipeline.reports.metadata.looker_limit import looker_limit_columns as _looker_limit_columns


#########################################
# NETSUITE METADATA SECTION
#########################################
class NetsuiteCarrierV1Metadata(Metadata):
    """namespace for metadata related to the CarrierV1 report

    Represents the Carrier Details Section.
    If a carrier is added, this section would need to be updated as well.
    """

    filename = "DataQualityCarrierV1CheckSTMResults"

    field_mapping = _netsuite_carrierv1_field_mapping
    """High Level Metadata (IID, TID) + Carrier Detail section mapping for normalization. Used for rename operations."""

    commission_percentage_columns = _netsuite_carrierv1_commission_percentage
    """List of strictly the carrier commission percentages columns"""

    bound_premium_columns = _netsuite_carrierv1_bound_premium
    """List of strictly the Carrier Bound Premium columns"""

    net_premium_columns = _netsuite_carrierv1_net_premium
    """List of the Carrier Net Premium Columns"""

    commission_amount_columns = _netsuite_carrierv1_commission_amount
    """List of Carrier Commission Amount Columns"""

    quota_share_columns = _netsuite_carrierv1_quota_share
    """List of Carrier Quota Share Columns"""

    # BELOW ARE THE COLUMNS WE ADD FROM THE COLUMNS ABOVE FOR FORMATTING SIMILAR DATA TYPES
    premium_agg_columns = commission_amount_columns + net_premium_columns + bound_premium_columns
    """List of premium columns (union of commission, net premium, bound premium)"""

    _percentage_agg_columns = commission_percentage_columns + quota_share_columns
    percentage_agg_columns = _percentage_agg_columns.append('coalition_commission_percent')


class NetsuiteLimitMetadata(Metadata):
    """namespace for metadata related to the Netsuite Limit Report

    If any new limit columns are added, needs tobe added here
    """

    field_mapping = _netsuite_limit_field_mapping
    """High Level Metadata (IID, TID) + Limit Field mapping for normalization"""

    limit_columns = _netsuite_limit_columns
    """List of only the limit columns"""


class NetsuiteSurchargeMetadata(Metadata):
    """namespace for metadata related to the Netsuite Surcharge Report

    Any new surcharges, or surcharges not identified here will need to be added to the report

    """

    field_mapping = _netsuite_surcharge_field_mapping
    """High Level Metadata (IID, TID) + Surcharge Field mapping for normalization"""


#########################################
# LOOKER METADATA SECTION
#########################################
class LookerLimitMetadata(Metadata):
    """namespace for metadata related to the Looker Limit Report

    It looks like we are using this report to compare Looker Data to Netsuite
    """

    field_mapping = _looker_limit_field_mapping
    """High Level Metadata (Quote Coalition Policy Number) + Looker Field mapping for normalization. Might need to add UUID"""

    limit_columns = _looker_limit_columns
    """List of only the looker limit, sublimit, and retention columns"""
