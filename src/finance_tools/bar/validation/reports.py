from typing import Literal

import pandas as pd

import finance_tools.bar as pipeline
from finance_tools.io.directory_handler import FOLDERS

from dirlin.core.api import DirlinFormatter as Format

# GLOBAL
f = FOLDERS()


def validate_allianz(deliverable: Literal["summary", "error"]) -> list[pd.DataFrame]:
    """returns a list of DataFrames of the validation results summary for Allianz
    """
    # DATA PULL and FORMATTING
    allianz_us = f.get_allianz_us()
    allianz_uk_primary = f.get_allianz_uk(version="primary")
    allianz_uk_excess = f.get_allianz_uk(version="excess")
    allianz_aus = f.get_allianz_aus(version="aus")
    allianz_aus_as_uk = f.get_allianz_aus(version="uk")
    allianz_germany = f.get_allianz_germany()
    allianz_denmark = f.get_allianz_denmark()

    # VALIDATION and CHECKS
    allianz_us_pipeline = pipeline.AllianzUSValidation()
    allianz_uk_pipeline = pipeline.AllianzUKValidation()
    allianz_australia_pipeline = pipeline.AustraliaValidation()

    # RESULTS of SUMMARY
    if deliverable == "summary":
        allianz_us_results = allianz_us_pipeline.run_summary(allianz_us, "Allianz US")
        allianz_uk_primary_results = allianz_uk_pipeline.run_summary(allianz_uk_primary, "Allianz UK Primary")
        allianz_uk_excess_results = allianz_uk_pipeline.run_summary(allianz_uk_excess, "Allianz UK Excess")
        allianz_aus_results = allianz_australia_pipeline.run_summary(allianz_aus, "Allianz AUS")
        allianz_aus_as_uk_results = allianz_uk_pipeline.run_summary(allianz_aus_as_uk, "Allianz AUS (UK)")
        allianz_germany_results = allianz_uk_pipeline.run_summary(allianz_germany, "Allianz Germany")
        allianz_denmark_results = allianz_uk_pipeline.run_summary(allianz_denmark, "Allianz Denmark")
    else:
        allianz_us_results = allianz_us_pipeline.run_error_log(allianz_us, "Allianz US")
        allianz_uk_primary_results = allianz_uk_pipeline.run_error_log(allianz_uk_primary, "Allianz UK Primary")
        allianz_uk_excess_results = allianz_uk_pipeline.run_error_log(allianz_uk_excess, "Allianz UK Excess")
        allianz_aus_results = allianz_australia_pipeline.run_error_log(allianz_aus, "Allianz AUS")
        allianz_aus_as_uk_results = allianz_uk_pipeline.run_error_log(allianz_aus_as_uk, "Allianz AUS (UK)")
        allianz_germany_results = allianz_uk_pipeline.run_error_log(allianz_germany, "Allianz Germany")
        allianz_denmark_results = allianz_uk_pipeline.run_error_log(allianz_denmark, "Allianz Denmark")

    all_allianz_results = [
        allianz_us_results,
        allianz_aus_results,
        allianz_aus_as_uk_results,
        allianz_denmark_results,
        allianz_germany_results,
        allianz_uk_primary_results,
        allianz_uk_excess_results
    ]
    return all_allianz_results


def validate_ascot(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for Ascot
    """
    ascot = f.get_ascot()
    ascot_pipeline = pipeline.BasicValidationUS()
    if deliverable == "summary":
        ascot_results = ascot_pipeline.run_summary(ascot, "Ascot")
    else:
        ascot_results = ascot_pipeline.run_error_log(ascot, "Ascot")
    return ascot_results


def validate_lloyds(deliverable: Literal["summary", "error"]) -> list[pd.DataFrame]:
    """returns a list of DataFrames of the validation results summary for Lloyds
    """
    basic = pipeline.LloydsValidation()
    all_lloyds_results = []

    try:
        lloyds_uk_2023 = f.get_lloyds_uk(version="2023")
        if deliverable == "summary":
            lloyds_uk_2023_results = basic.run_summary(lloyds_uk_2023, "Lloyds UK 2023")
        else:
            lloyds_uk_2023_results = basic.run_error_log(lloyds_uk_2023, "Lloyds UK 2023")
        all_lloyds_results.append(lloyds_uk_2023_results)
    except FileNotFoundError as fnf:
        print(fnf.args)

    try:
        lloyds_can_2023 = f.get_lloyds_canada(version="2023")
        if deliverable == "summary":
            lloyds_can_2023_results = basic.run_summary(lloyds_can_2023, "Lloyds Canada 2023")
        else:
            lloyds_can_2023_results = basic.run_error_log(lloyds_can_2023, "Lloyds Canada 2023")
        all_lloyds_results.append(lloyds_can_2023_results)
    except FileNotFoundError:
        pass

    lloyds_can_2024 = f.get_lloyds_canada(version="2024")
    lloyds_uk_2024 = f.get_lloyds_uk(version="2024")
    lloyds_can_2025 = f.get_lloyds_canada(version="2025")
    lloyds_uk_2025 = f.get_lloyds_uk(version="2025")

    if deliverable == "summary":
        lloyds_uk_2024_results = basic.run_summary(lloyds_uk_2024, "Lloyds UK 2024")
        lloyds_uk_2025_results = basic.run_summary(lloyds_uk_2025, "Lloyds UK 2025")
        lloyds_can_2024_results = basic.run_summary(lloyds_can_2024, "Lloyds Canada 2024")
        lloyds_can_2025_results = basic.run_summary(lloyds_can_2025, "Lloyds Canada 2025")
    else:
        lloyds_uk_2024_results = basic.run_error_log(lloyds_uk_2024, "Lloyds UK 2024")
        lloyds_uk_2025_results = basic.run_error_log(lloyds_uk_2025, "Lloyds UK 2025")
        lloyds_can_2024_results = basic.run_error_log(lloyds_can_2024, "Lloyds Canada 2024")
        lloyds_can_2025_results = basic.run_error_log(lloyds_can_2025, "Lloyds Canada 2025")

    all_lloyds_results.append(lloyds_uk_2024_results)
    all_lloyds_results.append(lloyds_uk_2025_results)
    all_lloyds_results.append(lloyds_can_2024_results)
    all_lloyds_results.append(lloyds_can_2025_results)

    # RESULTS
    return all_lloyds_results


def validate_lloyds_er(deliverable: Literal["summary", "error"]):
    lloyds_er_version: list[Literal["syndicates", "renre"]] = ["syndicates", "renre"]
    results = []
    basic = pipeline.LloydsExecutiveRiskValidation()

    for report in lloyds_er_version:
        try:
            lloyds_er_df = f.get_lloyds_er(report)
            if deliverable == "summary":
                lloyds_er_results = basic.run_summary(lloyds_er_df, f"Lloyds ER - {report.capitalize()}")
            else:
                lloyds_er_results = basic.run_error_log(lloyds_er_df, f"Lloyds ER - {report.capitalize()}")
            results.append(lloyds_er_results)
        except FileNotFoundError:
            pass
    return results


def validate_lloyds_us(deliverable: Literal["summary", "error"]):
    lloyds_df = f.get_lloyds_us_bdx()
    lloyds_df["Coverholder Commission %"] = Format.convert_percentage_to_float(lloyds_df["Coverholder Commission %"])
    lloyds_df["% GWP written through Lloyd's quota share"] = Format.convert_percentage_to_float(lloyds_df["% GWP written through Lloyd's quota share"])

    lloyds = pipeline.LloydsUnitedStatesValidation()
    if deliverable == "summary":
        results = lloyds.run_summary(lloyds_df, "Lloyds US")
    else:
        results = lloyds.run_error_log(lloyds_df, "Lloyds US")
    return results


def validate_fortegra(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for Fortegra
    """
    fortegra_df = f.get_fortegra_bdx()
    fortegra_df["Coalition Commission%"] = Format.convert_percentage_to_float(fortegra_df["Coalition Commission%"])
    fortegra_df["Fortegra %"] = Format.convert_percentage_to_float(fortegra_df["Fortegra %"])

    fortegra = pipeline.FortegraValidation()
    if deliverable == "summary":
        results = fortegra.run_summary(fortegra_df, "Fortegra")
    else:
        results = fortegra.run_error_log(fortegra_df, "Fortegra")
    return results


def validate_chaucer(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for Chaucer
    """
    chaucer_df = f.get_chaucer_bdx()
    chaucer_df["Chaucer %"] = Format.convert_percentage_to_float(chaucer_df["Chaucer %"])

    chaucer = pipeline.ChaucerValidation()
    if deliverable == "summary":
        results = chaucer.run_summary(chaucer_df, "Chaucer")
    else:
        results = chaucer.run_error_log(chaucer_df, "Chaucer")
    return results


def validate_msig(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for MSIG
    """
    msig_df = f.get_msig_bdx()
    # msig_df["Coalition Commission %"] = Format.convert_percentage_to_float(msig_df["Coalition Commission %"])
    # msig_df["MSIG Quota Share %"] = Format.convert_percentage_to_float(msig_df["MSIG Quota Share %"])

    msig = pipeline.AustraliaValidation()
    if deliverable == "summary":
        results = msig.run_summary(msig_df, "MSIG")
    else:
        results = msig.run_error_log(msig_df, "MSIG")
    return results

def validate_hdi(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for HDI
    """
    hdi_df = f.get_hdi_bdx()
    hdi_df["Coalition Commission %"] = Format.convert_percentage_to_float(hdi_df["Coalition Commission %"])
    hdi_df["HDI Quota Share %"] = Format.convert_percentage_to_float(hdi_df["HDI Quota Share %"])

    hdi = pipeline.BasicValidation()
    if deliverable == "summary":
        results = hdi.run_summary(hdi_df, "HDI")
    else:
        results = hdi.run_error_log(hdi_df, "HDI")
    return results


def validate_hartford(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for Hartford
    """
    hartford_df = f.get_hartford_bdx()
    hartford_df["Coalition Commission %"] = Format.convert_percentage_to_float(hartford_df["Coalition Commission %"])
    hartford_df["Hartford Quota Share %"] = Format.convert_percentage_to_float(hartford_df["Hartford Quota Share %"])

    hartford = pipeline.BasicValidation()
    if deliverable == "summary":
        results = hartford.run_summary(hartford_df, "Hartford")
    else:
        results = hartford.run_error_log(hartford_df, "Hartford")
    return results


def validate_swissre(deliverable: Literal["summary", "error"]) -> list[pd.DataFrame]:
    """returns a DataFrame of the validation results summary for SwissRe
    """
    swissre_reports: list[Literal["surplus", "admitted", "cad", "usd"]] = ["surplus", "admitted", "cad", "usd"]
    swissre_results = []
    basic = pipeline.SwissReValidation()

    for report in swissre_reports:
        try:
            swissre_surplus_df = f.get_sre_bdx(report)
            swissre_surplus_df["Coalition Commission %"] = Format.convert_percentage_to_float(swissre_surplus_df["Coalition Commission %"])
            swissre_surplus_df["Swiss Re %"] = Format.convert_percentage_to_float(swissre_surplus_df["Swiss Re %"])
            if deliverable == "summary":
                swissre_surplus_results = basic.run_summary(swissre_surplus_df, f"SwissRe - {report.capitalize()}")
            else:
                swissre_surplus_results = basic.run_error_log(swissre_surplus_df, f"SwissRe - {report.capitalize()}")
            swissre_results.append(swissre_surplus_results)
        except FileNotFoundError:
            pass
    return swissre_results


def validate_vantage(deliverable: Literal["summary", "error"]) -> pd.DataFrame:
    """returns a DataFrame of the validation results summary for Vantage
    """
    # DATAFRAME PULL AND FORMATTING
    vantage_df = f.get_vantage_bdx()
    vantage_df["Coalition Commission %"] = Format.convert_percentage_to_float(vantage_df["Coalition Commission %"])
    vantage_df["Vantage Quota Share %"] = Format.convert_percentage_to_float(vantage_df["Vantage Quota Share %"])

    # VALIDATION AND CHECKS
    vantage = pipeline.VantageValidation()
    if deliverable == "summary":
        results = vantage.run_summary(vantage_df, "Vantage")
    else:
        results = vantage.run_error_log(vantage_df, "Vantage")
    return results
