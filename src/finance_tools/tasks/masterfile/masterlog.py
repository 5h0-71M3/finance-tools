from datetime import date
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

from finance_tools.core.reports.policy_list import carrier_info_tuples
from finance_tools.deliverables import export_masterfile_reported
from finance_tools.io.directory_handler import FOLDERS
from finance_tools.tasks.masterfile.itd_handler import tie_master_to_policy_list


class MasterLogUtility:
    @staticmethod
    def holiday_as_series(
            year: int = date.today().year,
    ) -> pd.Series:
        cal = USFederalHolidayCalendar()
        holidays: pd.Series = cal.holidays(
            f"{year}-01-01",
            f"{year}-12-31",
        )
        return holidays

    @classmethod
    def infer_reported_date(
            cls,
            year: int,
            month: int,
            reported_dates: list[int] | None = None,
    ) -> dict[int, date]:
        """tries to infer the date you reported the BDX based on holiday and reporting date of the carrier
        """

        # [Part 1]: Set up the variables needed for inferring report date
        holidays = cls.holiday_as_series(year)

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

            # [2.4]: append the inferred report date based on the BDX day
            results[day] = curr_date.date()
        return results

    @classmethod
    def infer_reported_date_from_masterfile_name(cls, filename: str) -> dict[int, date]:
        """takes the masterfile name, and gives back a list of report dates based on the BDX
        day, considering weekend and holidays

        :param filename: masterfile name
        """
        try:
            try:
                name, report_date, download_date = filename.split("-", maxsplit=3)
            except ValueError:
                name, program, report_date, other = filename.split("-", maxsplit=4)
                print(filename)
        except ValueError:
            name, program, report_date, other = filename.split("-")
        except Exception as e:
            print(f"EXECPTION ERROR")
            raise e
        month, year = report_date.split(".")
        inferred_date = cls.infer_reported_date(month=int(month), year=int(year))
        return inferred_date


class MasterLog:
    """Handles files and reports related to the use of the Master File.
    
    For example, to get a list of all Master Logs ever reported or if
    we are running a recon on what we had reported previously to carriers.
    """
    f = FOLDERS()
    utl = MasterLogUtility()

    @classmethod
    def _handle_output_param(
            cls,
            filename: str,
            output_path: Path | str | None = None
    ) -> Path:
        """handles and converts the output parameter to the correct type.
        Can add data validations, etc.

        :param output_path: path to the folder where you would like to write the file to
        :return: a clean path
        """
        if output_path is None:
            output_path = cls.f.DOWNLOADS
        elif isinstance(output_path, str):
            output_path = Path(output_path)
        output = output_path / filename
        return output

    @classmethod
    def download_reported_itd(
            cls,
            output: Path | str | None = None,
    ) -> bool:
        """Downloads an ITD version of the Reported Upload file
        """
        itd_master_map = cls.f.get_master_log(tab="master")
        deliverable = itd_master_map["master"]

        # [1.1] we need to get the Reported and Report Date information by carrier
        carrier_info = carrier_info_tuples()
        quota_share_columns = [carrier[0] for carrier in carrier_info.values()]
        reported_columns = [carrier[2] for carrier in carrier_info.values()]
        reported_date_columns = [carrier[3] for carrier in carrier_info.values()]
        bdx_report_date_columns = [carrier[4] for carrier in carrier_info.values()]  # need to infer values / use this to overwrite and not the values / 3, 5, 10, 15 on holiday?

        # [1.2] create the new columns, we're going to need the date the file was reported if possible
        inferred_columns = [f"{reported_column}-inferred" for reported_column in reported_columns]

        # {Masterfile_name: {1: 1/1/2025, 10: 1/10/2025}}
        unique_bdx_dates = {
            source: cls.utl.infer_reported_date_from_masterfile_name(source) for source in deliverable["From"].unique()
        }
        deliverable[inferred_columns] = [unique_bdx_dates[source][bdx_date] for source, bdx_date in zip(deliverable["From"], deliverable[bdx_report_date_columns])]

        # [1.3] Now we need to apply this information
        # deliverable[reported_date_columns] = cls.utl.infer_reported_date()  # this we need to figure out what to do
        deliverable[reported_columns] = ["Yes" if deliverable[quota_share_columns] > 0 else None]  # was reported under carrier if carrier quota over 0.0

        # masks to apply so that we only overwrite reporting on specific ones
        reported_under_carrier = deliverable[reported_columns] == "Yes"
        avoids_previous_reported_values = deliverable[reported_date_columns].isnull()
        mask_reported_new_values = avoids_previous_reported_values & reported_under_carrier

        # [1.4] we only want to apply Reported Date on those that have `yes` for Reported
        # ===note=== we also want to make sure that we don't overwrite previous values for reported_date_columns date
        deliverable[reported_date_columns] = deliverable[inferred_columns] if mask_reported_new_values else deliverable[bdx_report_date_columns]

        deliverable.to_csv(cls.f.DOWNLOADS / f"Reported Upload - downloaded 2025.06.06 - as of {deliverable[inferred_columns].max()}")
        return True

    @classmethod
    def download_reported_for_month(
            cls,
            output: Path | str | None = None,
    ) -> bool:
        """Creates the Reported Upload file for the current month.
        Useful for recon or for the Reported Upload file.

        """
        deliverable = export_masterfile_reported()
        output = cls._handle_output_param(f"Reported Masterfile - {date.today()}.csv", output)

        try:
            deliverable.to_csv(output)
        except Exception as e:
            print(f"Couldn't download reported for month: {e}")
        return False

    @classmethod
    def download_policy_list_master_tie_out(
            cls,
            output: Path | str | None = None,
    ) -> bool:
        """Ties a master report to a Policy List.

        Useful for doing a recon on what was reported or for
        tying out or for creating the Ascot report.

        """
        deliverable = tie_master_to_policy_list()
        output = cls._handle_output_param(f"Reported Masterfile - {date.today()}.csv", output)

        try:
            deliverable.to_csv(output)
            return True
        except Exception as e:
            print(f"Couldn't download PL - Master Tie Out: {e}")
        return False
