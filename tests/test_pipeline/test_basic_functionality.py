from datetime import date

from dirlin.pipeline import Pipeline

from src.file_handling.directory_handler import Directory
from src.pipeline.reports import V1Report
from src.pipeline.reports.bdx import ArchBDX, AllianzUsBDX
from src.pipeline.validation import CarrierDetailsValidation
from src.pipeline.validation.bdx import BasicBDXValidation, AllianzUsBDXValidation, LimitValidation


class TestBasicPipeline:
    def test_setup(self):
        p = Pipeline(Directory.DOWNLOADS, report=V1Report)
        p.get_worksheet()

        results = p.run_validation(CarrierDetailsValidation,)
        print(results)


class TestArchITDPipeline:
    def test_setup(self):
        p = Pipeline(Directory.DOWNLOADS, report=ArchBDX)
        df = p.get_worksheet()
        BasicBDXValidation.run(df, key_column="internal_id", infer_shared=True)
        result = BasicBDXValidation.generate_error_log()
        result.to_csv(Directory.DOWNLOADS.path / f"test_report - {date.today()}.csv")
# 10703


def test_allianz_us_validation():
    p = Pipeline()
    p.add_report_set(report=AllianzUsBDX, validation=AllianzUsBDXValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"Sample Validation Log - {date.today()}.csv")


def test_limit_validation():
    p = Pipeline()
    p.add_report_set(report=AllianzUsBDX, validation=LimitValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"Sample Validation Log - {date.today()}.csv")

