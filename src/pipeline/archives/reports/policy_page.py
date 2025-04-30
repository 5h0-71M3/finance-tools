from dirlin.pipeline import Report

from src.pipeline.archives.reports.metadata.carrier_v1 import (
    netsuite_carrierv1_field_mapping,
    netsuite_carrierv1_quota_share,
    netsuite_carrierv1_commission_amount,
    netsuite_carrierv1_commission_percentage,
    netsuite_carrierv1_bound_premium,
    netsuite_carrierv1_net_premium,
    netsuite_carrier_comm,
)

########################################
# Carrier V1 Section of the Policy Page
########################################

_float_columns = list(
    netsuite_carrierv1_quota_share
    + netsuite_carrierv1_commission_percentage
    + netsuite_carrier_comm
)

_cash_columns = list(
    netsuite_carrierv1_commission_amount
    + netsuite_carrierv1_bound_premium
    + netsuite_carrierv1_net_premium
)

V1Report = Report(
    name_convention="DataQualityCarrierV1CheckSTMResults",
    field_mapping=netsuite_carrierv1_field_mapping,
    column_type_floats=_float_columns,
    column_type_cash=_cash_columns,
    key_cash_column="tbp"
)
