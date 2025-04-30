# 2025.04.30
from dirlin import Directory

from src.pipeline.validation.carriers import AllianzUSValidation

#  I am a little rusty on this package so let's just go step by step for the next
# hour or so and at least finish this off with the check to determine future
# dates so we can transition into Binder Editing it

FOLDERS = Directory()


def test_validation_allianz():
    allianz_us = AllianzUSValidation()
    allianz_us_report = FOLDERS.DOWNLOADS.open("AllianzAccountCurrentResults - 03.2025.csv")

    validation = allianz_us.run_validation(df=allianz_us_report)
    print(validation.keys())
