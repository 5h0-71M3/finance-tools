"""For checks related specifically to Fortegra"""
import pandas as pd


###########################################
# CHECKS FOR Fortegra US
###########################################

def fortegra_v2_columns_are_blank(
        carrier_bound_premium: pd.Series,
        carrier_net_premium: pd.Series,
        carrier_bound_less_tria: pd.Series,
        carrier_commission_to_coalition: pd.Series,
        carrier_bound_cyber_less_tria: pd.Series,
        carrier_net_cyber: pd.Series,
) -> pd.Series:
    """bound_premium, net_premium, bound_less_tria, commission, cyber_premium, cyber_net, are not blank.
    """
    results = []
    for cbp, cnp, cblt, cctc, cbclt, cnc in zip(
        carrier_bound_premium,
        carrier_net_premium,
        carrier_bound_less_tria,
        carrier_commission_to_coalition,
        carrier_bound_cyber_less_tria,
        carrier_net_cyber
    ):
        all_records = (cbp, cnp, cblt, cctc, cbclt, cnc)
        if any(pd.isnull(record) or str(record) == "nan" for record in all_records):
            results.append(False)
        else:
            results.append(True)
    return pd.Series(results)
