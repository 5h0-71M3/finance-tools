from datetime import date
from typing import Literal

import pandas as pd
from dateutil.relativedelta import relativedelta

from finance_tools.bar.core.reports.policy_list import _quota_share_headers, _reported_headers, _reported_date_headers, \
    carrier_info_tuples

from finance_tools.bar.validation.api import (
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
from finance_tools.io.directory_handler import FOLDERS
from finance_tools.tasks.masterfile.masterfile_validation import infer_reported_date

f = FOLDERS()


def download_validation_log():
    """Generates the summary sheet for all available Carriers in the Account Current folder
    """
    #  [Split]
    day_dict = {
        1: [validate_vantage],
        5: [
            validate_ascot,
            validate_allianz,
            validate_lloyds
        ],
        10: [
            validate_chaucer,
            validate_fortegra,
            validate_hartford,
            validate_hdi,
            validate_msig
        ],
        15: [
            validate_lloyds_us,
            validate_lloyds_er,
            validate_swissre
        ]
    }

    # [1.1] add the functions in a loop so we can iterate through
    fn_store = [
        validate_vantage,
        validate_ascot,
        validate_allianz,
        validate_chaucer,
        validate_fortegra,
        validate_hartford,
        validate_hdi,
        validate_msig,
        validate_lloyds,
        validate_lloyds_er,
        validate_lloyds_us,
        validate_swissre,
    ]

    # [1.2] get the summary results
    summary_results = []
    validation_results = []
    errored_results = []
    for fn in fn_store:
        try:
            # [1.2.1] Creating the Summary Sheet
            summary_result = fn("summary")
            summary_results.append(summary_result)

            # [1.2.2] Creating the Error Log
            validation_result = fn("error")
            validation_results.append(validation_result)
        except ValueError as ve:
            print(f"{ve}: {fn.__name__} [ve]")
            errored_results.append(str(fn.__name__))
        except KeyError as ke:
            print(f"{ke}: {fn.__name__} [ke]")
            errored_results.append(str(fn.__name__))
        except FileNotFoundError as fnf:
            print(f"{fnf}: {fn.__name__} [fnf]")
            errored_results.append(str(fn.__name__))

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
    print(f"DID NOT CREATE: {errored_results}")


def export_masterfile_reported(
        curr_master: Literal['cyber', 'mpl'] | pd.DataFrame | None = None,
        year: int | None = None,
        month: int | None = None,
) -> pd.DataFrame:
    """creates the upload file for the transactions your reported for the month on
    Netsuite, based on the Master File

    :param curr_master: the Master File you want to create the file from
    :param year: the year of the reporting. Defaults to previous month's year
    :param month: the month of the reporting. Defaults to previous month
    :return: a Dataframe consisting of which carriers reported and when
    """
    _end_of_previous_month = date.today() + relativedelta(day=31)
    carrier_info_mapping = carrier_info_tuples()
    """
    (0) quota share header
    (1) carrier subsidiary name
    (2) carrier reported header
    (3) carrier reported date header
    (4) report date
    (5) misc header for getting the correct filter - None if empty
    (6) carrier commission %
    """

    # [Part 0]: set up the variables
    if curr_master is None:
        curr_master = f.get_cyber_master(tab="master")
    elif isinstance(curr_master, str):
        if curr_master.lower() == 'cyber':
            curr_master = f.get_cyber_master(tab="master")
        else:
            curr_master = f.get_mpl_master(tab="master")
    else:
        curr_master = curr_master.copy()

    if year is None:
        year = _end_of_previous_month.year
    if month is None:
        month = _end_of_previous_month.month

    # [Part 1]: Create a dataframe with the columns we want to handle
    # [1.1]: Call the header functions / date handler
    quota_share = _quota_share_headers()
    reported_headers = _reported_headers()
    reported_date_headers = _reported_date_headers()
    key_dates = infer_reported_date(year, month)

    # [1.2]: create a list of headers we want to deal with
    # for (1) having an IID and (2) filtering BDX files (3) masterfile pulled from
    headers = ["Internal ID", "Subsidiary [Agency Customer]"]
    headers.extend(quota_share)  # adding Quota Share Columns
    headers.extend(reported_headers)  # adding Reported Columns
    headers.extend(reported_date_headers)  # adding Reported Date Columns

    # [1.2.1]: going to organize this so we can have a deliverable and working header
    deliverable_headers = []
    deliverable_headers.extend(reported_headers)
    deliverable_headers.extend(reported_date_headers)

    if "From" in curr_master:
        headers.append("From")
        deliverable_headers.append("From")

    # [1.3]: Happy Path with Zurich and returning the values quickly
    if "Zurich Quota Share" in curr_master:
        # [1.3.1]: updating the fields we need for only Zurich
        zurich_headers = [
            "Internal ID",
            "Reported - Zurich Date",
            "Reported - Zurich"
        ]
        # [1.3.2]: getting the carrier mapping for Zurich
        zurich = carrier_info_mapping.get("zurich_us")
        temp_master = curr_master[zurich_headers].copy()

        # [1.3.3]: updating the reported fields
        temp_master[zurich[2]] = "Yes"
        temp_master[zurich[3]] = key_dates[zurich[4]]
        # [1.3.4]:
        return temp_master
    # ===Note=== This is the Zurich Happy Path to prevent errors

    # [1.4]: apply the headers to the current masterfile we pulled

    # ==note== we also need to remove the Zurich headers to avoid an error
    headers.remove("Zurich Quota Share")
    headers.remove("Reported - Zurich")
    headers.remove("Reported - Zurich Date")
    deliverable_headers.remove("Reported - Zurich Date")
    deliverable_headers.remove("Reported - Zurich")

    working_master = curr_master[headers].copy()
    working_master["Internal ID"] = working_master["Internal ID"].fillna(0)
    working_master["Internal ID"] = [f"i{int(iid)}" for iid in working_master["Internal ID"]]
    working_master: pd.DataFrame = working_master.set_index("Internal ID")

    # [Part 2]: iterate through the carriers in the masterfile and encode values
    # [2.1]: Start of iteration for rest of carriers
    del carrier_info_mapping["zurich_us"]
    for carrier_tuple in carrier_info_mapping.values():
        if carrier_tuple[0] not in working_master:  # Quota Share
            raise KeyError(f"{carrier_tuple[0]} not in {working_master.columns}. Add to master.")

        if carrier_tuple[2] not in working_master:  # Reported
            working_master[carrier_tuple[2]] = None
            deliverable_headers.append(carrier_tuple[2])

        if carrier_tuple[3] not in working_master:  # Reported Date
            working_master[carrier_tuple[3]] = None
            deliverable_headers.append(carrier_tuple[3])

        # [2.2]: format and fill the values for quota share
        working_master[carrier_tuple[0]] = working_master[carrier_tuple[0]].fillna(0)

        # [2.3]: create the mask for future slicing
        mask_carrier_quota_share = working_master[carrier_tuple[0]] > 0
        mask_carrier_subsidiary = working_master["Subsidiary [Agency Customer]"] == carrier_tuple[1]
        mask_carrier = mask_carrier_subsidiary & mask_carrier_quota_share

        # [Part 3]: creating a slice to update the reported and reported date values
        # ===note=== there will likely be special cases like arch
        # [3.1] apply the mask and update the reporting values
        working_master.loc[mask_carrier, carrier_tuple[2]] = "Yes"
        working_master[carrier_tuple[3]] = working_master[carrier_tuple[3]].astype(object)
        working_master.loc[mask_carrier, carrier_tuple[3]] = key_dates[carrier_tuple[4]]

    # [Part 4]: this should now have all the relevant fields
    # [4.1]: fix the Internal ID index back
    working_master.index = working_master.index.str[1:]
    return working_master[deliverable_headers].copy()


def swissre_doc_namer(df: pd.DataFrame, f: FOLDERS | None = None):
    """names swissre policy docs in the DOWNLOADS folder, and saves them under
    a SwissRe compliant name.

    File Needs:
        - `Transaction Description`: (Issuance, Endorsement, etc.)
        - `filepath`: with the filename of the PDF file (Dynavax-Technologies-Corporation-Coalition-Policy-041516)
        - `Carrier Policy Number`: which is External ID or Binder ID (Just rename it) (CMP1038812-00)
        - `Policy UUID`: for transmittal (bf4cd63f-e109-4e31-bde8-16808f1b9669)
        - `Coalition Policy Number`: for transmittal (C-4LPE-041516-CYBER-2021)
        - `Endorsement Number`: for filename (0, 35, etc.)
        - `Transaction Type` (New, Renewal)

    :param df:
    :return:
    """
    directory = f
    if f is None:
        directory = FOLDERS()

    naming_map = {
        "cancellation - flat": "CANC",
        "cancellation - pro-rated": "CANC",
        "endorsement": "E",
        "issuance": {"new": "NB", "renewal": "RN"},
        "reinstatement": "REIN"
    }
    """SwissRe convention for naming"""

    naming_needs_endt_suffix = ("cancellation - flat", "cancellation - pro-rated", "endorsement", "reinstatement")

    saved = {}
    df_as_dict = df.to_dict(orient="records")
    for record in df_as_dict:
        if not record["filepath"].endswith(".pdf"):
            record["filepath"] = f'{record["filepath"]}.pdf'
        curr_filepath = directory.DOWNLOADS.path / record["filepath"]

        # Prepping the variables
        desc_keyword = str(record["Transaction Description"]).lower()

        if desc_keyword in naming_needs_endt_suffix:
            endt = "00"
            if record["Endorsement Number"] is not None:
                endt = record["Endorsement Number"]
                if endt <= 9:
                    endt = f"0{endt}"
            naming_convention = f"{record['Carrier Policy Number']}-{naming_map[desc_keyword]}{endt}.pdf"

        else:  # Issuance and Renewals don't add endorsement numbers at the end
            new_or_renewal = str(record["Transaction Type"]).lower()
            naming_convention = f"{record['Carrier Policy Number']}-{naming_map[desc_keyword][new_or_renewal]}.pdf"

        # renaming the file and saving the old name for future reference
        curr_filepath.rename(directory.DOWNLOADS.path / naming_convention)
        saved[record["filepath"]] = naming_convention

    #  final deliverable formatting
    transmittal_columns = ["Policy UUID", "Coalition Policy Number", "Carrier Policy Number"]
    df = df[transmittal_columns].copy()
    df["Carrier Filename"] = [nc for nc in saved.values()]
    df.to_excel(directory.DOWNLOADS / "CCP052025-00-TRANS.xlsx", index=False)
