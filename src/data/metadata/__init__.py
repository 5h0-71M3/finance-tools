# Imports for Netsuite Related Metadata
from src.data.metadata.netsuite.carrier_v1 import netsuite_carrierv1_field_mapping as _netsuite_carrierv1_field_mapping
from src.data.metadata.netsuite.carrier_v1 import netsuite_carrierv1_commission_percentage as _netsuite_carrierv1_commission_percentage
from src.data.metadata.netsuite.carrier_v1 import netsuite_carrierv1_bound_premium as _netsuite_carrierv1_bound_premium
from src.data.metadata.netsuite.carrier_v1 import netsuite_carrierv1_net_premium as _netsuite_carrierv1_net_premium
from src.data.metadata.netsuite.carrier_v1 import netsuite_carrierv1_commission_amount as _netsuite_carrierv1_commission_amount
from src.data.metadata.netsuite.carrier_v1 import netsuite_carrierv1_quota_share as _netsuite_carrierv1_quota_share

from src.data.metadata.netsuite.netsuite_limit import netsuite_limit_field_mapping as _netsuite_limit_field_mapping
from src.data.metadata.netsuite.netsuite_limit import netsuite_limit_columns as _netsuite_limit_columns

from src.data.metadata.netsuite.netsuite_surcharge import netsuite_surcharge_field_mapping as _netsuite_surcharge_field_mapping
from src.data.metadata.netsuite.ns_reports import FieldNamingConventions

# Imports for Looker Related Metadata
from src.data.metadata.looker.looker_limit import looker_limit_field_mapping as _looker_limit_field_mapping
from src.data.metadata.looker.looker_limit import looker_limit_columns as _looker_limit_columns

# Imports for Netsuite Related Data Quality Checks
from src.data.metadata.data_quality.policy_page import carrier_details_section as _dq_cd
from src.data.metadata.data_quality.policy_page import coverage_details_section as _dq_covd
from src.data.metadata.data_quality.policy_page import policy_details_section as _dq_pd
from src.data.metadata.data_quality.policy_page import surcharge_section as _sq_s


#########################################
# NETSUITE METADATA SECTION
#########################################
class NetsuiteCarrierV1Metadata:
    """namespace for metadata related to the CarrierV1 report

    Represents the Carrier Details Section.
    If a carrier is added, this section would need to be updated as well.
    """

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

    # BELOW ARE THE PROPS / FUNCTIONS FOR VALIDATING THE DATA
    validate_net_premium = _dq_cd.validate_net_premium
    validate_carrier_net_premium = _dq_cd.validate_carrier_net_premium
    validate_carrier_bound_premium = _dq_cd.validate_carrier_bound_premium
    validate_carrier_commission = _dq_cd.validate_carrier_commission_to_coalition


class NetsuiteLimitMetadata:
    """namespace for metadata related to the Netsuite Limit Report

    If any new limit columns are added, needs tobe added here
    """

    field_mapping = _netsuite_limit_field_mapping
    """High Level Metadata (IID, TID) + Limit Field mapping for normalization"""

    limit_columns = _netsuite_limit_columns
    """List of only the limit columns"""

    # BELOW ARE THE PROPS / FUNCTIONS FOR VALIDATING THE DATA
    recon_agg_limit = _dq_covd.recon_aggregate_total_limit_balance


class NetsuiteSurchargeMetadata:
    """namespace for metadata related to the Netsuite Surcharge Report

    Any new surcharges, or surcharges not identified here will need to be added to the report

    """

    field_mapping = _netsuite_surcharge_field_mapping
    """High Level Metadata (IID, TID) + Surcharge Field mapping for normalization"""

    # BELOW ARE THE PROPS / FUNCTIONS FOR VALIDATING THE DATA
    validate_surcharge_total = _sq_s.validate_surcharge
    validate_kentucky_surcharge = _sq_s.validate_kentucky_surcharges
    validate_pliga_fee = _sq_s.validate_pliga_fee


#########################################
# LOOKER METADATA SECTION
#########################################
class LookerLimitMetadata:
    """namespace for metadata related to the Looker Limit Report

    It looks like we are using this report to compare Looker Data to Netsuite
    """

    field_mapping = _looker_limit_field_mapping
    """High Level Metadata (Quote Coalition Policy Number) + Looker Field mapping for normalization. Might need to add UUID"""

    limit_columns = _looker_limit_columns
    """List of only the looker limit, sublimit, and retention columns"""

    # BELOW ARE THE PROPS / FUNCTIONS FOR VALIDATING THE DATA
    recon_agg_limit = _dq_covd.recon_aggregate_total_limit_balance
