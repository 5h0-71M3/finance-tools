from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta
from pandas.tseries.holiday import USFederalHolidayCalendar

from src.io.directory_handler import FOLDERS
from src.pipeline.core.reports.policy_list import _reported_headers, _reported_date_headers, _quota_share_headers, \
    carrier_info_tuples


def infer_reported_date(
        year: int,
        month: int,
        reported_dates: list[int] | None = None,
) -> dict:
    """infers the date you sent out the BDX report based on the weekend and holidady timing
    """

    # [Part 1]: Set up the variables needed for inferring report date
    # [1.1]: set up the holiday date
    cal = USFederalHolidayCalendar()
    holidays: pd.Series = cal.holidays(
        f"{year}-01-01",
        f"{year}-12-31",
    )

    # [1.2]: set up report dates for carrier reporting
    if reported_dates is None:
        reported_dates = [3, 5, 10, 15]

    # [Part 2]: iterate and determine the dates
    results = {}
    for day in reported_dates:
        # [2.1]: process the current reporting date
        curr_date = pd.Timestamp(year=year, month=month, day=day)

        # [2.2]: determine whether it falls on weekend and adjust
        while curr_date.weekday() >= 5:  # sat: 5, sun: 6
            curr_date -= pd.Timedelta(days=1)

        # [2.3]: determine whether new date falls on a holiday
        while curr_date in holidays or curr_date.weekday() >= 5:
            curr_date -= pd.Timedelta(days=1)

        # [2.4]: append the inferred report date
        results[day] = curr_date.date()
    return results


def export_masterfile_reported(
        curr_master: pd.DataFrame | None = None,
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
    f = FOLDERS()
    _end_of_previous_month = date.today() + relativedelta(months=-1, day=31)
    carrier_info_mapping = carrier_info_tuples()

    # [Part 0]: set up the variables
    if curr_master is None:
        curr_master = f.get_cyber_master(tab="master")
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


def calculate_masterfile_totals():
    f = FOLDERS()
    previous_master = f.get_cyber_master(tab="tie_out", previous_master=True)

    # based on research, we're going to stop the Tie Out portion with the text 'TBP Reconciliation'
    stop_row = previous_master[previous_master["Carrier"] == "TBP Reconciliation"].index[0]
    previous_master: pd.DataFrame = previous_master.iloc[:stop_row]

    # We're going to count the total bound premium for this month's Masterfile
    current_master = f.get_cyber_master(tab="master", previous_master=False)

    # Filtering for Lloyds
    agg_func = {
        "Lloyds Bound Premium": "sum",
        "Internal ID": "count"
    }
    lloyds_balance = current_master[current_master["Lloyds Quota Share"] > 0].groupby("UMR").agg(agg_func).reset_index()
    umr_map = {
        "B133823COA0003": "Lloyds - UK (2023)",
        "B174010140SS23": "Lloyds - ER (2023)",
        "B174010140SS24": "Lloyds - ER (2024)",
        "B174010160SS24": "Lloyds - Canada (2024)",
        "B174010160SS25": "",
        "B174010161SS24": "Lloyds - UK (2024)",
        "B174010161SS25": "",
        "B133822COA0001": "Lloyds - 2023"
    }
    lloyds_balance["UMR"] = []

    tie_out_records = previous_master.to_dict("records")
    new_records = []
    for record in tie_out_records:
        # Adding in all the new information - we're adding it as a record
        # and converting it into a Dataframe after

        tie_out_template = {
            "Carrier": record["Carrier"],
            "Variance": record["Variance"],
            "Check": None,
            "AC - Bound Premium": None,
            "AC - Count": None,
            "Master - Bound Premium": None,
            "Master - Count": None,
            "Notes": record["Notes"],
            "Sho Response": None,
            "ES Comment": None,
            "ES Comment (Last month)": record["ES Comment (Last month)"],
            "ES Comment (2 Months Ago)": record["ES Comment (2 Months Ago)"]
        }
    print(lloyds_balance)
