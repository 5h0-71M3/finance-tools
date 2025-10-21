import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

from finance_tools.io.directory_handler import FOLDERS


def infer_reported_date(
        year: int,
        month: int,
        reported_dates: list[int] | None = None,
) -> dict:
    """infers the date you sent out the BDX report based on the weekend and holiday timing
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
