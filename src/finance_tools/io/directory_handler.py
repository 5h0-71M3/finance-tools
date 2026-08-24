from datetime import date
from typing import Literal

import duckdb
import pandas as pd
from dateutil.relativedelta import relativedelta
from dirlin import Folder, Directory, Path
from dirlin.core.api import DirlinFormatter as Format
from jinja2 import Template
from tqdm import tqdm

from finance_tools.io._config import directory_config


def data_cleaner(
        folder_path: Path,
        export_path: Path,
        query_path: Path,
        out_path: Path,
):
    """Helps convert the XLSX files into something that DuckDB can handle.
    """
    with duckdb.connect() as conn:
        conn.execute("INSTALL excel; LOAD excel;")
        # Get the relevant files
        files = [str(p) for p in folder_path.rglob("*.xlsx")]

        # Query to combine all the Excel files together
        tmpl = Template(query_path.read_text())
        rendered_tmpl = tmpl.render(files=files, range=True)

        # KWARGS based on the template
        # anything with $ is a kw argument
        tmpl_kwarg = {
            "sheet": "Master",
            "header": True,
        }
        df = conn.execute(rendered_tmpl, tmpl_kwarg).df()

        # MAKE IT INTO A PARQUET FILE
        out_path.parent.mkdir(parents=True, exist_ok=True)
        conn.execute(
            f"""
            COPY ({rendered_tmpl})
            TO '{out_path.as_posix()}'
            (FORMAT PARQUET);
            """, tmpl_kwarg
        )
        return df


def get_master_files():
    """uses DuckDB to grab the Master Files from the Masters folder on the Desktop.
    """
    with open("/finance_tools/core/sql/master_file.sql.j2", "r") as f:
        query = f.read()

    with duckdb.connect() as conn:
        results = conn.execute(query)
        df = results.fetchdf()
    return df


class FOLDERS(Directory):
    def __init__(self, path: str | Path | None = None, initialize_posix_path: bool = True):
        """The object for handling directory level tasks.

        """
        super().__init__(path, initialize_posix_path)
        self.DATA_ANALYSIS = Folder(directory_config["data_analysis"])
        self.ACCOUNT_CURRENT = Folder(directory_config["account_current"])

        try:
            self.MASTER_FOLDER = self._get_current_master_path()
        except ValueError as ve:
            raise ValueError(f"CREATE NEW MASTERFILE FOLDER FOR MONTH: {ve}")
        self.PREVIOUS_MASTER_FOLDER = self._get_previous_master_path()

        # Variables and Maps used for parameters and functions
        self._master_tab_mapping = {
            "part_1": "Part 1",
            "part_2": "Part 2",
            "soft_deletes": "Soft Deletes",
            "binder_edits": "Binder Edits",
            "zero_dollar": "Zero Dollar",
            "master": "Master",
            "tie_out": "Tie Out",
        }
        """mapping used for getting the actual tab name on the Masterfile"""

    def download_arch_number_upload(self, limit: int = 8, write: bool = True) -> pd.DataFrame:
        """gets the Arch upload file

        """
        naming_convention = f"Arch_Policy_Number_for_Coalition_Feed"
        combined_df = self.DOWNLOADS.find_and_combine(
            filename_pattern=naming_convention,
            recurse=False,
            limit=limit,
        )
        if write:
            combined_df.to_csv(self.DOWNLOADS / f"Arch Policy Number Upload - {date.today()}.csv")
        return combined_df

    def download_all_master(self):
        ...

    def get_policy_list(
            self,
            path: str | Path | None = None,
            set_index: bool = False,
    ) -> pd.DataFrame:
        """Pulls the most recent policy list from a directory. Unless given, will pull from the DOWNLOADS folder.

        :param set_index: sets Internal ID as index
        :param path: alternate path or specific path to the PolicyList file
        """
        if path is None:
            df = self.DOWNLOADS.open_recent("PolicyList")
        else:
            df = self.folder.open(path)
        if set_index:
            df = df.set_index("Internal ID")
        return df

    def get_stm_transactions(
            self,
            path: str | Path | None = None,
    ) -> pd.DataFrame:
        """Pulls the most recent STM Transactions Saved Search from a directory. Unless given, will pull from the DOWNLOADS folder.

        :param path: alternate path or specific path to the STM Transactions file
        """
        if path is None:
            df = self.DOWNLOADS.open_recent("DataQualityDailyTransactionCheckAllTransactionsSTMResults")
            return df
        df = self.folder.open(path)
        return df

    def get_master_log(
            self,
            path_to_master_files: Folder | Path | None = None,
            tab: list[str] | Literal["part_1", "part_2", "soft_deletes", "binder_edits", "zero_dollar", "master"] | None = None
    ) -> dict[str, pd.DataFrame] | pd.DataFrame:
        """function that gathers all master files from a given path. We can give this function a single tab or a list of tabs.

        Defaults to the DESKTOP/MASTERS folder, **NOT AC FOLDER**.

        ...

        Add this on a monthly basis after Masterfiles have been reported.

        We could use the `Account Current` folder or `Desktop/Masters` in order to get all the masterfiles.
        """
        if tab is None:
            tab = ["part_1", "part_2", "soft_deletes", "binder_edits", "zero_dollar", "master"]

        # logging / progress
        pbar = tqdm(total=len(tab), desc="getting the master files", position=1)

        # Setting up the variables
        if path_to_master_files is None:
            path_to_master_files = self.DESKTOP / "Masters"
        elif isinstance(path_to_master_files, Path):
            path_to_master_files = Folder(path_to_master_files)

        results = {}

        # we want to make sure that the list of strings is a tab in the masterfile
        if isinstance(tab, list):
            # Just want to notify the user if the tab name is not available
            accepted_tab_names = ("part_1", "part_2", "soft_deletes", "binder_edits", "zero_dollar", "master")
            tabs_exist = any([t in accepted_tab_names for t in tab])  # we can just let the user know some of the tabs aren't in the Master
            if tabs_exist is False:
                print(f"Some of the tabs in {tab} is not excepted Masterfile.")
            with pbar:  # context management with the progress bar
                for t in tab:
                    results[t] = self._combine_master_with_error_handle(master_folder_path=path_to_master_files, tab=t)
                    pbar.update()
                pbar.desc = "Done!"
                return results
        return self._combine_master_with_error_handle(master_folder_path=path_to_master_files, tab=tab)

    def _combine_master_with_error_handle(
            self,
            master_folder_path: Folder | Path,
            tab: Literal["part_1", "part_2", "soft_deletes", "binder_edits", "zero_dollar", "master"] | str
    ) -> pd.DataFrame:
        """modularizing the portion of the function that's wrapped in a try / except block so we can loop this or use it a single time.
        This function will use the `find_and_combine` function to gather the masters under the tab name
        """
        if isinstance(tab, str):
            approved_str = tab in ("part_1", "part_2", "soft_deletes", "binder_edits", "zero_dollar", "master")
            if approved_str is False:
                raise TypeError(f"{tab} is not a valid tab name.")

        tab = self._master_tab_mapping.get(tab)
        if isinstance(master_folder_path, Path):
            master_folder_path = Folder(master_folder_path)

        # Combining all the Master Files
        try:
            masters = master_folder_path.find_and_combine(recurse=True, sheet_name=tab, use_cache=True)
        except Exception as e:
            raise e
        return masters

    def _get_current_master_path(self) -> Folder:
        _end_of_previous_month = date.today() + relativedelta(months=-1, day=31)  # used to compare the Effective Date
        _formatted_end_of_previous_month = Folder(self.ACCOUNT_CURRENT / _end_of_previous_month.strftime("%Y-%m"))
        return _formatted_end_of_previous_month

    def _get_previous_master_path(self) -> Folder:
        _end_of_previous_month = date.today() + relativedelta(months=-2, day=31)  # used to compare the Effective Date
        _formatted_end_of_previous_month = Folder(self.ACCOUNT_CURRENT / _end_of_previous_month.strftime("%Y-%m"))
        return _formatted_end_of_previous_month

    def _get_bdx_day_path(self, day: Literal["day3", "day5", "day10", "day15"]) -> Folder:
        """assumes we are pulling for the current Day 3, 5, 10, or 15 folders and not the previous.
        This is where the BDX files are stored.
        """
        day_mapping = {"day3": "Day 3", "day5": "Day 5", "day10": "Day 10", "day15": "Day 15"}
        return Folder(self.MASTER_FOLDER / day_mapping[day])

    def get_cyber_master(
            self,
            tab: Literal['part_1', 'part_2', 'soft_deletes', 'binder_edits', 'zero_dollar', 'master', 'tie_out'],
            previous_master: bool = False,
    ) -> pd.DataFrame:
        """pulls the cyber masterfile

        :param previous_master: whether to pull the master from two months ago. Defaults to False.
        :param tab: pulls the DataFrame based on the tab name you want to pull
        :return: pd.Dataframe
        """
        if previous_master:
            print(f"Pulled from previous Master {self.PREVIOUS_MASTER_FOLDER}")
            print(self.PREVIOUS_MASTER_FOLDER.path)
            return self.PREVIOUS_MASTER_FOLDER.open_recent("Masterfile-Cyber", sheet_name=self._master_tab_mapping[tab])
        return self.MASTER_FOLDER.open_recent("Masterfile-Cyber", sheet_name=self._master_tab_mapping[tab])

    def get_mpl_master(
            self,
            tab: Literal['part_1', 'part_2', 'soft_deletes', 'binder_edits', 'zero_dollar', 'master', 'tie_out'],
            previous_master: bool = False,
    ) -> pd.DataFrame:
        """pulls the MPL masterfile (Zurich)

        :param previous_master: whether to pull the master from two months ago. Defaults to False.
        :param tab: pulls the DataFrame based on the tab name you want to pull
        :return: pd.Dataframe
        """
        if previous_master:
            print(f"Pulled from previous Master {self.PREVIOUS_MASTER_FOLDER}")
            return self.PREVIOUS_MASTER_FOLDER.open_recent("Masterfile-MPL", sheet_name=self._master_tab_mapping[tab])
        return self.MASTER_FOLDER.open_recent("Masterfile-MPL", sheet_name=self._master_tab_mapping[tab])

    def get_allianz_us(self) -> pd.DataFrame:
        """quick function for getting the current Allianz US report from the Account Current Folder (production). NOTE NOT FROM DOWNLOADS"""
        df = self._get_bdx_day_path(day="day5").open_recent("AllianzAccountCurrentResults")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Allianz Quota Share %"] = Format.convert_percentage_to_float(df["Allianz Quota Share %"])
        return df

    def get_allianz_uk(self, version: Literal["excess", "primary"]):
        """quick function for getting the current Allianz UK report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS

        :param version: Whether we want the Excess or Primary version of the UK report
        """
        mapping = {"excess": "Excess", "primary": "Primary"}
        _previous_month_format = (date.today() + relativedelta(months=-1, day=31)).strftime("%-m.%Y")
        df = self._get_bdx_day_path(day="day5").open_recent(f"AllianzAccountUKCurrentResults - {_previous_month_format} - {mapping[version]}")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Allianz Quota Share %"] = Format.convert_percentage_to_float(df["Allianz Quota Share %"])
        return df

    def get_allianz_aus(self, version: Literal["aus", "uk"]):
        """quick function for getting the current Allianz AUS report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS

        :param version: Whether we want the Australia or UK version report
        """
        mapping = {"aus": "(AUS Format)", "uk": "(UK Format)"}
        _previous_month_format = (date.today() + relativedelta(months=-1, day=31)).strftime("%Y.%-m")
        df = self._get_bdx_day_path(day="day5").open_recent(f"AllianzAUSAccountCurrentResults - {_previous_month_format} {mapping[version]}")

        if version == "uk":
            df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
            df["Allianz Quota Share %"] = Format.convert_percentage_to_float(df["Allianz Quota Share %"])
        return df

    def get_allianz_germany(self):
        """quick function for getting the current Allianz Germany report from the Account Current Folder (production). NOTE NOT FROM DOWNLOADS"""
        df = self._get_bdx_day_path(day="day5").open_recent("AllianzDEAccountCurrentResults")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Allianz Quota Share %"] = Format.convert_percentage_to_float(df["Allianz Quota Share %"])
        return df

    def get_allianz_denmark(self):
        df = self._get_bdx_day_path(day="day5").open_recent(f"AllianzDenmarkAccountCurrentResults")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Allianz Quota Share %"] = Format.convert_percentage_to_float(df["Allianz Quota Share %"])
        return df

    def get_ascot(self):
        """quick function for getting the current Ascot report from the Account Current Folder (production). NOTE NOT FROM DOWNLOADS"""
        df = self._get_bdx_day_path(day="day5").open_recent("AscotMonthlyAccountCurrent")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Ascot Quota Share %"] = Format.convert_percentage_to_float(df["Ascot Quota Share %"])
        return df

    def get_lloyds_canada(self, version: Literal["2023", "2024", "2025"]):
        """quick function for getting the current Lloyds Canada report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS

        :param version: which UMR year you are pulling for
        """
        _previous_month_format = (date.today() + relativedelta(months=-1, day=31)).strftime("%-m.%Y")
        df = self._get_bdx_day_path(day="day5").open_recent(f"LloydsCanadaAccountCurrent - {_previous_month_format} ({version})")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Lloyds Quota Share %"] = Format.convert_percentage_to_float(df["Lloyds Quota Share %"])
        return df

    def get_lloyds_uk(self, version: Literal["2023", "2024", "2025"]):
        """quick function for getting the current Lloyds UK report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS

        :param version: which UMR year you are pulling for
        """
        _previous_month_format = (date.today() + relativedelta(months=-1, day=31)).strftime("%-m.%Y")
        filename = f"LloydsUKAccountCurrent - {_previous_month_format} ({version})"
        df = self._get_bdx_day_path(day="day5").open_recent(filename)
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Lloyds Quota Share %"] = Format.convert_percentage_to_float(df["Lloyds Quota Share %"])
        return df

    def get_vantage_bdx(self) -> pd.DataFrame:
        """quick function for getting the current Vantage report from the Account Current Folder (production). NOTE NOT FROM DOWNLOADS"""
        df = self._get_bdx_day_path(day="day3").open_recent("VantageAccountCurrentResults")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Vantage Quota Share %"] = Format.convert_percentage_to_float(df["Vantage Quota Share %"])
        return df

    def get_fortegra_bdx(self):
        """Fortegra: quick function for getting the current report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS
        """
        df = self._get_bdx_day_path(day="day10").open_recent("FortegraAccountCurrent")
        df["Coalition Commission%"] = Format.convert_percentage_to_float(df["Coalition Commission%"])
        df["Fortegra %"] = Format.convert_percentage_to_float(df["Fortegra %"])
        return df

    def get_chaucer_bdx(self):
        """Chaucer: quick function for getting the current report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS
        """
        df = self._get_bdx_day_path(day="day10").open_recent("ChaucerAccountCurrent")
        df["Chaucer %"] = Format.convert_percentage_to_float(df["Chaucer %"])
        return df

    def get_msig_bdx(self):
        """MSIG: quick function for getting the current report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS
        """
        return self._get_bdx_day_path(day="day10").open_recent("MSIGAccountCurrentResults")

    def get_hdi_bdx(self):
        """HDI: quick function for getting the current report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS
        """
        df = self._get_bdx_day_path(day="day10").open_recent("HDICanadaAccountCurrent")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["HDI Quota Share %"] = Format.convert_percentage_to_float(df["HDI Quota Share %"])
        return df

    def get_hartford_bdx(self):
        """Hartford: quick function for getting the current report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS
        """
        df = self._get_bdx_day_path(day="day10").open_recent("HartFordUKAccountCurrentResults")
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Hartford Quota Share %"] = Format.convert_percentage_to_float(df["Hartford Quota Share %"])
        return df

    def get_sre_bdx(self, version: Literal["cad", "usd", "admitted", "surplus"]):
        """quick function for getting the current SwissRe report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS

        :param version: which SwissRe Report you are pulling for
        """
        # Part 1: Creating the date string
        _end_of_previous_month = date.today() + relativedelta(months=-1, day=31)  # used to compare the Effective Date
        _formatted_end_of_previous_month = Folder(self.ACCOUNT_CURRENT / _end_of_previous_month.strftime("%Y-%m"))
        date_string = _end_of_previous_month.strftime("%m%y")

        # Part 2: Used for the surrounding filename
        report_name_mapping = {
            "admitted": ("CCP", "AC Admitted"),
            "surplus": ("CCP", "AC Surplus"),
            "cad": ("CYP", "AC CAD"),
            "usd": ("CYP", "AC USD"),
        }

        # Part 3: Generating the filename given the version
        filename = f"{report_name_mapping[version][0]}000{date_string}-00-{report_name_mapping[version][1]}.xlsx"
        print(filename)
        print("...")
        df = self._get_bdx_day_path(day="day15").open(filename)
        df["Coalition Commission %"] = Format.convert_percentage_to_float(df["Coalition Commission %"])
        df["Swiss Re %"] = Format.convert_percentage_to_float(df["Swiss Re %"])
        return df

    def get_lloyds_er(self, version: Literal["syndicates", "renre"]):
        """quick function for getting the current Lloyds Canada report from the Account Current Folder (production).
        NOTE NOT FROM DOWNLOADS

        :param version: which UMR year you are pulling for
        """
        _previous_month_format = (date.today() + relativedelta(months=-1, day=31)).strftime("%m%Y")
        df = self._get_bdx_day_path(day="day15").open(f"LloydsExecRisk - {version.capitalize()} - {_previous_month_format}.csv")
        return df

    def get_lloyds_us_bdx(self):
        """returns the Lloyds US BDX"""
        df = self._get_bdx_day_path(day="day15").open_recent("Lloyds Account Current")
        df["Coverholder Commission %"] = Format.convert_percentage_to_float(
            df["Coverholder Commission %"])
        df["% GWP written through Lloyd's quota share"] = Format.convert_percentage_to_float(
            df["% GWP written through Lloyd's quota share"])
        return df
