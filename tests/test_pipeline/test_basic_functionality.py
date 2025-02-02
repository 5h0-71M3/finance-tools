from datetime import date

from dirlin.pipeline import Pipeline

from src.file_handling.directory_handler import Directory
from src.pipeline.reports import V1Report
from src.pipeline.reports.bdx import ArchBDX, AllianzUsBDX, VantageBDX, LloydsUK2023BDX, LloydsUK2024BDX, \
    LloydsCanada2023BDX, LloydsCanada2024BDX, AscotBDX, AllianzAusFormatUKBDX, AllianzAusFormatAusBDX, \
    AllianzUKPrimaryBDX, AllianzUKExcessBDX, AllianzDEBDX
from src.pipeline.validation import CarrierDetailsValidation
from src.pipeline.validation.bdx import BasicBDXValidation, AllianzUsBDXValidation, LimitValidation, \
    VantageBDXValidation, LloydsUK2023BDXValidation, LloydsUK2024BDXValidation, LloydsCanada2024BDXValidation, \
    AscotBDXValidation, AllianzAusValidation, AllianzUKValidation, AllianzDEValidation


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
    df.to_csv(Directory.DOWNLOADS.path / f"Allianz Validation Log - {date.today()}.csv")


def test_allianz_uk_validation():
    p = Pipeline()
    p.add_report_set(report=AllianzUKPrimaryBDX, validation=AllianzUKValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"Allianz UK - Primary - Validation Log - {date.today()}.csv")


def test_allianz_non_us_validation():
    p1 = Pipeline()  # aus - aus
    p2 = Pipeline()  # aus - uk
    p3 = Pipeline()  # uk - primary
    p4 = Pipeline()  # uk - excess
    p5 = Pipeline()  # germany

    p1.add_report_set(report=AllianzAusFormatAusBDX, validation=AllianzAusValidation, key_column="internal_id")
    df1 = p1.run_error_log()
    df1.to_csv(Directory.DOWNLOADS.path / f"Allianz AUS - AUS - Validation Log - {date.today()}.csv")

    p2.add_report_set(report=AllianzAusFormatUKBDX, validation=AllianzUKValidation, key_column="internal_id")
    df2 = p2.run_error_log()
    df2.to_csv(Directory.DOWNLOADS.path / f"Allianz AUS - UK - Validation Log - {date.today()}.csv")

    p3.add_report_set(report=AllianzUKPrimaryBDX, validation=AllianzUKValidation, key_column="internal_id")
    df3 = p3.run_error_log()
    df3.to_csv(Directory.DOWNLOADS.path / f"Allianz UK - Primary - Validation Log - {date.today()}.csv")

    p4.add_report_set(report=AllianzUKExcessBDX, validation=AllianzUKValidation, key_column="internal_id")
    df4 = p4.run_error_log()
    df4.to_csv(Directory.DOWNLOADS.path / f"Allianz UK - Excess - Validation Log - {date.today()}.csv")

    p5.add_report_set(report=AllianzDEBDX, validation=AllianzDEValidation, key_column="internal_id")
    df5 = p5.run_error_log()
    df5.to_csv(Directory.DOWNLOADS.path / f"Allianz Germany - Validation Log - {date.today()}.csv")


def test_ascot_validation():
    p = Pipeline()
    p.add_report_set(report=AscotBDX, validation=AscotBDXValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"Ascot Validation Log - {date.today()}.csv")


def test_vantage_validation():
    p = Pipeline()
    p.add_report_set(report=VantageBDX, validation=VantageBDXValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"Vantage Validation Log - {date.today()}.csv")


def test_lloyds_non_us_validation():
    p = Pipeline()
    p.add_report_set(report=LloydsUK2023BDX, validation=LloydsUK2023BDXValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"LloydsUK2023 Validation Log - {date.today()}.csv")

    p2 = Pipeline()
    p2.add_report_set(report=LloydsUK2024BDX, validation=LloydsUK2024BDXValidation, key_column="internal_id")
    df2 = p2.run_error_log()
    df2.to_csv(Directory.DOWNLOADS.path / f"LloydsUK2024 Validation Log - {date.today()}.csv")

    p3 = Pipeline()
    p3.add_report_set(report=LloydsCanada2023BDX, validation=LloydsUK2023BDXValidation, key_column="internal_id")
    df3 = p3.run_error_log()
    df3.to_csv(Directory.DOWNLOADS.path / f"LloydsCanada2023 Validation Log - {date.today()}.csv")

    p4 = Pipeline()
    p4.add_report_set(report=LloydsCanada2024BDX, validation=LloydsCanada2024BDXValidation, key_column="internal_id")
    df4 = p4.run_error_log()
    df4.to_csv(Directory.DOWNLOADS.path / f"LloydsCanada2024 Validation Log - {date.today()}.csv")


def test_limit_validation():
    p = Pipeline()
    p.add_report_set(report=AllianzUsBDX, validation=LimitValidation, key_column="internal_id")
    df = p.run_error_log()
    df.to_csv(Directory.DOWNLOADS.path / f"Sample Validation Log - {date.today()}.csv")
