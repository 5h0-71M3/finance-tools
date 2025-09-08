from typing import Callable

import pandas as pd

from archives import netsuite_carrierv1_field_mapping
from foo.pipeline.core.checks.netsuite.carrier_details_section import validate_net_premium
from dirlin.pipeline import Pipeline, Report, Check

from foo.io.directory_handler import Directory


class TestReportingAPILogic:
    def test_init(self):
        ap = Pipeline(Directory.DOWNLOADS)
        r = Report(
            "DataQualityCarrierV1CheckSTMResults",
            field_mapping=netsuite_carrierv1_field_mapping
        )
        df = ap.get_worksheet(report=r)
        assert isinstance(df, pd.DataFrame)

    def test_checks(self):
        ap = Pipeline(Directory.DOWNLOADS)
        validate_net = Check(validate_net_premium)

        assert isinstance(validate_net, Check)
        assert isinstance(validate_net.validate, Callable)
        assert isinstance(validate_net.__annotations__, dict)

        r = Report(
            "DataQualityCarrierV1CheckSTMResults",
            netsuite_carrierv1_field_mapping,
            column_type_floats=["coalition_commission_percent"]
        )
        df = ap.get_worksheet(report=r)
        validate_net.validate(data=df)
