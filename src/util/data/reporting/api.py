from types import FunctionType
from typing import Callable

import pandas as pd

from src.util.data.reporting._object import Reporting
from src.pipeline.checks.netsuite.carrier_details_section import validate_net_premium, validate_carrier_bound_premium, \
    validate_carrier_net_premium, validate_carrier_commission_to_coalition


class _CallWrapper:
    def __init__(self, func: FunctionType, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.func(*self.args, **self.kwargs)


class CarrierDetailsSection(Reporting):
    """Reporting functionality for the carrier details section

    """
    validate_net_premium = validate_net_premium
    validate_carrier_bound_premium: Callable[[float, float, float, float], tuple[bool, float]] = validate_carrier_bound_premium
    validate_carrier_net_premium: Callable[[float, float, float, float], tuple[bool, float]] = validate_carrier_net_premium
    validate_carrier_commission_to_coalition: Callable[[float, float, float, float, float], tuple[bool, float]] = validate_carrier_commission_to_coalition

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def deliverable(self):
        ...


