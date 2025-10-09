"""aspen v3, we made this to make it a little easier on ourselves"""
import pandas as pd

from finance_tools.core import MasterFileBdxDetails
from finance_tools.tasks.bdx.base import BaseBDXMixin


class AspenBdxV3(BaseBDXMixin):
    def __init__(self):
        self._init_formatting_object()  # creates the formatting helper

    def _format_bdx(
            self,
            *args,
            **kwargs
    ) -> pd.DataFrame:
        pass

    def carrier_details(self) -> MasterFileBdxDetails:
        pass

    ...

