from datetime import date

from dirlin.dq.core import ResultWrapper

from finance_tools.pipeline_v2 import BasicValidation, f, SmallCarrierPipeline, AustraliaPipeline, FortegraPipeline


def test_bigger_pipeline():
    pipe = BasicValidation()
    result: ResultWrapper = pipe.run()
    df = result.as_dataframe("summary")
    df.to_csv(f.DOWNLOADS / f"Validation Summary - {date.today()}.csv")


def test_split_pipeline():
    small_pipeline = SmallCarrierPipeline()
    australia_pipeline = AustraliaPipeline()
    fortegra_pipeline = FortegraPipeline()

    small_df = small_pipeline.run()
    australia_df = australia_pipeline.run()
    fortegra_df = fortegra_pipeline.run()

    small_df.as_dataframe("summary").to_csv(f.DOWNLOADS / f"Validation Summary - small - {date.today()}.csv")
    australia_df.as_dataframe("summary").to_csv(f.DOWNLOADS / f"Validation Summary - AUS - {date.today()}.csv")
    fortegra_df.as_dataframe("summary").to_csv(f.DOWNLOADS / f"Validation Summary - Fortegra - {date.today()}.csv")
