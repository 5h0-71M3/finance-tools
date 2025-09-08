from datetime import date
from typing import Literal

import pandas as pd
import typer
from dirlin import Folder
from rich.console import Console
from typing_extensions import Annotated

from .deliverables import download_validation_log, export_masterfile_reported, swissre_doc_namer
from .io.directory_handler import FOLDERS
from .pipeline import DailyValidation

app = typer.Typer()
console = Console()
f = FOLDERS()


############################
# BDX SUPPORT
############################
@app.command()
def validate_bdx():
    """Function for running the validation log for available BDX reports"""
    download_validation_log()


@app.command()
def generate_hartford_itd():
    """IMPORTANT: Needed to create the Hartford Report. NEED: to add previous Hartford Reports to Desktop folders.
    """
    folder = Folder(f.DESKTOP / "Hartford")
    df = folder.find_and_combine(recurse=True)
    df.to_excel(f.DOWNLOADS / f"Hartford ITD Report - {date.today()}.xlsx")


@app.command()
def generate_aspen_soft_delete_sheet():
    """IMPORTANT: Needed to create the Aspen BDX Report. NEED: ADD MASTER file to Desktop Masters folder
    """
    # Soft Delete File For Aspen
    df1 = f.get_master_log(tab="soft_deletes")
    df2 = f.get_master_log(tab="binder_edits")
    df3 = f.get_master_log(tab="zero_dollar")

    df = pd.concat([df1, df2, df3])

    file_path = f.DOWNLOADS / f"All Master Log - Not Reported - {date.today()}.xlsx"
    df.to_excel(file_path)


############################
# NETSUITE UPLOADS
############################
@app.command()
def daily_checks():
    """function for running the `Daily Checks` on Netsuite transactions and returning
    policies that need to be updated or further reviewed. NEED: POLICY LIST in the Downloads folder.

    Currently, runs the following checks:
        1. find_term_extension_transaction: for finding future endorsements that causes negative balance
        2.
    """
    df = f.get_policy_list()
    dv = DailyValidation()

    log = dv.run_error_log(df)
    log.to_csv(f.DOWNLOADS / f"Daily Check - {date.today()}.csv")


@app.command()
def generate_reported():
    """Generates the reported upload for Netsuite. NEED: the Masterfile in Production Account Current folder.
    """
    cyber = export_masterfile_reported()
    mpl = export_masterfile_reported("mpl")

    cyber.to_csv(f / f"Reported Masterfile - Cyber - {date.today()}.csv")
    mpl.to_csv(f / f"Reported Masterfile - MPL - {date.today()}.csv")

    # itd master
    cyber.to_csv(f / f"Reported Masterfile - Cyber - {date.today()}.csv")


@app.command()
def generate_arch_upload(limit: int = 8):
    """Generates the reported upload for Netsuite. NEED: Arch Policy Number email files in DOWNLOADS folder.
    """
    f.download_arch_number_upload(limit=limit)


############################
# AD-HOC
############################
@app.command()
def sre_policy_docs():
    file = f.DOWNLOADS.open_recent("SwissRe Doc Namer")
    swissre_doc_namer(file)


@app.command()
def get_itd(
        carrier: str,
        segment: Annotated[
            str,
            typer.Option(
                "--segment",
                "-s",
                help="handles nested folder like `Lloyds/ER`",
                case_sensitive=True
            )
        ]
):
    """uses find and combine to get the itd from the desktop folders"""
    path = f.DESKTOP / str(carrier).capitalize()
    filename = f"ITD - ran {date.today()} - {carrier}.csv"

    if segment:
        path = path / segment
        filename = f"ITD - ran {date.today()} - {carrier} - {segment}.csv"

    files = Folder(path).find_and_combine(recurse=True)
    files.to_csv(path / filename)
