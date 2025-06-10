"""We're starting this off as a way of seeing which Allianz reports have been sent"""
import pandas as pd
from pathlib import Path

from tqdm import tqdm

from src.io.directory_handler import FOLDERS


def tie_master_to_policy_list(
        policy_list: pd.DataFrame | None = None,
        master_file_path: Path | None = None,
) -> pd.DataFrame:
    """gathers all the needed tabs from the masterfile into individual, referencable dataframes.
    I think this is used for the Ascot report.

    :param policy_list: Dataframe
    :param master_file_path: Path to Master
    :return:
    """
    # [Part 1]: gathering reports and variables that are needed
    f = FOLDERS()

    # [1.1]: Gathering the masterfiles
    tabs = ["master", "binder_edits", "soft_deletes", "zero_dollar",]
    master_mapping = f.get_master_log(master_file_path, tabs)  # gets all the master files

    # [1.2]: generate a single Masterfile sheet with tab information
    master = pd.concat(master_mapping.values(), ignore_index=True)
    master["Internal ID"] = master["Internal ID"].fillna(0)
    master["Internal ID"] = [f"i{int(iid)}" for iid in master["Internal ID"]]
    master: pd.DataFrame = master.set_index("Internal ID")
    # master.to_csv(f.DOWNLOADS / f"Master All Combined - {date.today()}.csv")

    # ===NOTE===: could cut here for separating the two functions

    # [Part 2]: get the policy list with transactions we expect have been sent
    if policy_list is None:
        policy_list = f.DOWNLOADS.open_recent("PolicyList")  # with the BDX template

    # this portion needs to be separated so that any Policy List arg will have the correct index
    policy_list["Internal ID"] = [f"i{int(iid)}" for iid in policy_list["Internal ID"]]
    policy_list: pd.DataFrame = policy_list.set_index("Internal ID")

    # [2.1]: iterate through the Masterfile tabs
    with tqdm(total=len(tabs), desc="encoding tabs", position=1) as pbar:
        for tab in tabs:
            # [2.1.1]: fill the values inside the Masterfile dataframe tab fields
            master[tab] = master[tab].fillna("No")

            # [2.1.2]: create the mask based on the column
            mask_tab_filter = master[tab] == "Yes"
            temp_master = master.loc[mask_tab_filter].copy()

            # [2.1.3]: process the intersection masks and apply
            curr_intersect = policy_list.index.intersection(temp_master.index)  # (1) master filtered by the tab (2) all policy list
            policy_list.loc[curr_intersect, tab] = "Yes"

            # [2.1.4]: need secondary filter for the No's
            mask_not_intersect = ~policy_list.index.isin(temp_master.index)
            policy_list.loc[mask_not_intersect, tab] = "No"
            pbar.update()

    # Part 3: Fix the index and final formatting
    policy_list.index = policy_list.index.str[1:]
    return policy_list

