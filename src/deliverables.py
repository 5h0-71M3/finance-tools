from datetime import date

import pandas as pd

from src.pipeline.validation.reports import (
    validate_ascot,
    validate_allianz,
    validate_lloyds,
    validate_vantage,
    validate_hartford,
    validate_chaucer,
    validate_fortegra,
    validate_hdi,
    validate_msig,
    validate_lloyds_er,
    validate_swissre,
    validate_lloyds_us
)
from src.io.directory_handler import FOLDERS

f = FOLDERS()


def download_validation_log():
    """Generates the summary sheet for all available Carriers in the Account Current folder

    """
    # [1.1] add the functions in a loop so we can iterate through
    fn_store = [
        validate_ascot,
        validate_allianz,
        validate_chaucer,
        validate_fortegra,
        validate_hartford,
        validate_hdi,
        validate_msig,
        validate_lloyds,
        validate_lloyds_er,
        validate_lloyds,
        validate_swissre,
        validate_vantage,
    ]

    # [1.2] get the summary results
    summary_results = []
    validation_results = []
    for fn in fn_store:
        try:
            # [1.2.1] Creating the Summary Sheet
            summary_result = fn("summary")
            summary_results.append(summary_result)

            # [1.2.2] Creating the Error Log
            validation_result = fn("error")
            validation_results.append(validation_result)
        except ValueError as ve:
            print(ve)

    # === Creating the Summary Sheet for the Carriers ===
    deliverables = []
    for result in summary_results:
        if isinstance(result, list):
            deliverables.extend(result)
            continue
        deliverables.append(result)
    try:
        summary_df = pd.concat(deliverables)
    except ValueError as ve:
        print(ve)
        summary_df = deliverables

    completed = []
    for val in validation_results:
        if isinstance(val, list):
            completed.extend(val)
            continue
        completed.append(val)

    # Saving the Two DataFrames as an Excel File
    with pd.ExcelWriter(f.DOWNLOADS / f"BDX Validation Summary {date.today()} - Available.xlsx") as worksheet:
        summary_df.to_excel(worksheet, sheet_name="Summary")
        for idx, df in enumerate(completed):
            try:
                df.to_excel(worksheet, sheet_name=f"Carrier {df['Group'].iloc[0]}")
            except IndexError as ie:
                print()
                print(df.info())
                print("***")
            except AttributeError as ae:
                print(ae)


if __name__ == "__main__":
    download_validation_log()
