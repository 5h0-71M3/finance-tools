"""related to carrier requests. Could be validations in the future"""
from datetime import date

import pandas as pd

from finance_tools.io.directory_handler import FOLDERS
from dirlin import DirlinFormatter

from finance_tools.core.reports import Subsidiaries


def confirm_arch_commissions(write: bool = False):
    """Arch sent us files of incorrect rates after an upload file was sent to them.
    The task is to confirm how these were missed, and if these are on us or them.

    Files:
        - The Arch file with what they are proposing is incorrect rates
        - the Upload file we sent to Arch to fix
        - a supplemental file that we sent with cancelled policies that didn't need updates
        - STM Report that will help tie the Arch Numbers and Internal IDs

    :return:
    """
    f = FOLDERS()

    # ===[1.1]=== Organize all the files we are dealing with and will need

    # [1.1.1] pull the files
    arch_file_with_errors = f.DOWNLOADS.open("Policies with Wrong Commissions (research).xlsx")
    upload_file_sent_to_arch = f.DOWNLOADS.open("Arch 2025.04.17 - Fix File (Updated) (Research).xlsx")
    supplemental_file = f.DOWNLOADS.open("Arch - Cancelled Policies on Upload - 2025.04.10 (Research).xlsx")
    stm_report = f.get_stm_transactions()

    # [1.1.2] set the indexes for the ones we can to Internal ID and Arch Number for the other
    stm_report["Internal ID"] = [f"i{int(iid)}" for iid in stm_report["Internal ID"]]
    stm_report = stm_report.set_index("Internal ID")

    upload_file_sent_to_arch["Internal ID"] = [f"i{int(iid)}" for iid in upload_file_sent_to_arch["Internal ID"]]
    upload_file_sent_to_arch = upload_file_sent_to_arch.set_index("Internal ID")

    arch_file_with_errors = arch_file_with_errors.set_index("Policy_Number")

    # [1.1.3] handle stm_report (pre-process) (1) reduce size of the dataframe
    headers = [
        "Arch Policy Number",
        "Binder ID",
        "--Coalition Policy Number--",
        "Date Created",
        "Arch Commission%",
        "Arch Bound Premium",
        "Coalition Commission%",
        "-------------Transaction ID-------------"
    ]
    stm_report = stm_report[headers].copy()

    # ===[1.2]=== Merge all the reports together (except the Error File) into STM
    # We should have a fully loaded STM file by the end to tie to the error file with

    # [1.2.1] merging the supplemental file by Binder ID to STM
    # ==note=== we want to pull the Binder IDs from these and assign them to STM
    stm_report = stm_report.reset_index(drop=False)
    stm_report = stm_report.merge(supplemental_file, how="left", left_on="Binder ID", right_on="FULL_POLICY_NUMBER")
    stm_report = stm_report.set_index("Internal ID")

    # [1.2.2] merge the upload_file_sent_to_arch report
    mask_in_uploads = stm_report.index.intersection(upload_file_sent_to_arch.index)
    stm_report.loc[mask_in_uploads, "In Uploads"] = upload_file_sent_to_arch.loc[mask_in_uploads, "Internal ID (to Arch)"]

    # ===[1.3]=== Merge the information from the *New* STM report to the Error File

    # [1.3.1] reset the index for STM and assign the Arch Policy as the index
    stm_report.index = stm_report.index.str[1:]
    stm_report: pd.DataFrame = stm_report.reset_index(drop=False)
    stm_report["Arch Commission%"] = DirlinFormatter.convert_percentage_to_float(stm_report["Arch Commission%"])

    # [1.3.2] we need to group the STM to make it to the Arch Level
    aggregate_fn = {
        "--Coalition Policy Number--": "first",
        "Arch Commission%": "min",
        "Arch Bound Premium": "sum",
        "Note": "first",
        "In Uploads": "first",
    }
    stm_grouped = stm_report.groupby(by="Arch Policy Number", as_index=True).agg(func=aggregate_fn)

    # [1.3.3] now we can tie the two files together
    deliverable = arch_file_with_errors.join(stm_grouped, how="left", lsuffix="_arch")

    if write:
        deliverable.to_excel(f.DOWNLOADS / f"Policies with Wrong Commissions (Results) - {date.today()}.xlsx")
    return deliverable


def match_arch_policy_number(
        stm_report: pd.DataFrame | None = None,
        requested: pd.DataFrame | None = None,
        requested_binder_header: str = "Coalition Full Policy Number"
) -> pd.DataFrame:
    """request to tie the binder id to Coalition Policy Number
    """
    # [1.1] gather all the reports needed to tie out
    f = FOLDERS()
    if stm_report is None:
        stm_report = f.get_stm_transactions()

    if requested is None:
        requested_canada = f.DOWNLOADS.open_recent("Arch Audit", sheet_name="Canada")
        requested_us = f.DOWNLOADS.open_recent("Arch Audit", sheet_name="US")
        requested = pd.concat((requested_canada, requested_us))

        # [1.1.2] Need to group the columns together
        needed_headers = [
            "Binder ID",
            "--Coalition Policy Number--",
        ]
        agg_fn = {"--Coalition Policy Number--": "first"}
        stm_report = stm_report[needed_headers].groupby("Binder ID").agg(agg_fn)

    # [1.2] set the indexes to match. In this case, it may be the binder id
    requested = requested.set_index(requested_binder_header)
    # stm_report = stm_report.set_index("Binder ID")

    # [1.3] write the Coalition Policy Number to the requested file
    requested["Coalition Policy Number"] = stm_report["--Coalition Policy Number--"]

    # [1.4] save down the results
    requested.to_csv(f.DOWNLOADS / f"Arch Audit - Request List - Policy Sample Selection (tied).csv")
    return requested


def lloyds_umr_bound_against(
        subsidiaries: Subsidiaries | list[Subsidiaries] | None = None,
        umr_lookup: str | list[str] | None = None,
        effective_date: date | None = None,
) -> pd.DataFrame:
    """Is it possible to please get a list of UK and Canada policies which were bound against the 2024 UMR binders,
    but with policy effective dates on or after 4/1/2025
    (being the effective date of the renewal binders and after the expiration date of the 2024 binders)?

    :param subsidiaries: The subsidiaries we are searching in. The request was for UK and Canada so defaults to that.
    :param umr_lookup: the UMR we want to check against. Need to look at which ones were the 2024 UMRs. Defaults to 2024 UMRs.
    :param effective_date: the effective date for the policies we are searching under. Includes the date as well.
    """
    # ===[1.0]=== Handling the variables and parameters
    # [1.1] Directory handling
    f = FOLDERS()
    policy_list = f.get_policy_list()

    # [1.2] handle the default variables and params
    if subsidiaries is None:
        subsidiaries = [Subsidiaries.uk.value, Subsidiaries.canada.value]

    if umr_lookup is None:
        umr_lookup = ["B174010161SS24", "B174010160SS24"]

    if effective_date is None:
        effective_date = date(year=2025, month=4, day=1)

    # [1.3] handle the user input
    if isinstance(subsidiaries, Subsidiaries):
        subsidiaries = [subsidiaries]

    if isinstance(umr_lookup, str):
        umr_lookup = [umr_lookup]

    # [1.4] format the policy list for handling dates
    policy_list["Policy Effective Date"] = pd.to_datetime(policy_list["Policy Effective Date"])

    # ===[2.0]=== Creating the masks to get the population that was requested
    # we have the lists in order so we can zip. Need to remember that when using the function in the future.

    # [2.1] create the masks per subsidiaries
    mask_effective_date_on_or_after = policy_list["Policy Effective Date"].dt.date >= effective_date

    # [2.2] Applying the mask for umr values
    mask_umr_matches = policy_list["UMR"].isin(umr_lookup)

    # [2.3] the mask for subsidiary values
    mask_subsidiary_matches = policy_list["Subsidiary [Agency Customer]"].isin(subsidiaries)

    # ===[3.0]=== applying the mask and formatting the deliverable

    # [3.1] define the columns we want for the final deliverable
    columns_wanted = [
        # "Internal ID",
        "Coalition Policy Number",
        "Policy Effective Date",
        "Lloyds Quota Share",
        "Subsidiary [Agency Customer]",
        "Market",
        "UMR",
        "Total Bound Premium",
        "Currency"
    ]

    # [3.2] apply the mask to the current policy list
    # =note= these are 2025.04.01 or after policies, with 2024 UMRs in UK or Canada
    mask_all_applied = mask_umr_matches & mask_subsidiary_matches & mask_effective_date_on_or_after
    filtered_policy_list = policy_list[mask_all_applied].copy()

    # [3.3] prep for grouping
    agg_fn_map = {
        "Policy Effective Date": "min",
        "Lloyds Quota Share": "first",
        "Subsidiary [Agency Customer]": "first",
        "Market": "first",
        "UMR": "first",
        "Total Bound Premium": "sum",
        "Currency": "first",
    }

    # [3.4] Group the table
    grouped_policy_list = filtered_policy_list.groupby(by="Coalition Policy Number", as_index=False).agg(agg_fn_map)

    # [3.5] apply the final headers and deliver
    return grouped_policy_list[columns_wanted]


def allianz_france_testing():
    f = FOLDERS()
    file = f.DOWNLOADS.open_recent("Test Non Pro")

    file["Allianz Quota Share %"] = DirlinFormatter.convert_percentage_to_float(file["Allianz Quota Share %"])
    file["Coalition Commission %"] = DirlinFormatter.convert_percentage_to_float(file["Coalition Commission %"])

    allianz_validation = AllianzUKValidation()
    results = allianz_validation.run_summary(file, "France")

    errors = allianz_validation.run_error_log(file, "France")

    results.to_excel(f.DOWNLOADS / f"Test France - {date.today()}.xlsx")
    errors.to_excel(f.DOWNLOADS / f"Test France - Errors - {date.today()}.xlsx")


