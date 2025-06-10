from abc import abstractmethod
from typing import Any

import dirlin
import pandas as pd
from dirlin import DirlinFormatter

from src.core.base_objects import MasterFileBdxDetails


class BaseBDXMixin:
    formatter: Any

    @abstractmethod
    def _format_bdx(self, *args, **kwargs) -> pd.DataFrame:
        """
        Formatting the final deliverable to the carrier. The inheriting
        class will define how they want the limits to look.
        """

    @abstractmethod
    def carrier_details(self) -> MasterFileBdxDetails:
        """
        Function should generate and return the information
        required in the MasterFileCarrier object

        :return: MasterFileCarrier object specific to the Carrier
        """

    def _init_formatting_object(self, formatter: DirlinFormatter | None = None) -> None:
        """object used for formatting the BDX report. You can call this object in the
        inheriting class' __init__

        :param formatter: an object that helps format reports
        """
        if formatter is None:
            formatter = dirlin.DirlinFormatter()
        self.formatter = formatter

    @classmethod
    def get_limit_columns(cls) -> list[str]:
        ...
