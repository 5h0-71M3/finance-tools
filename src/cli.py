from datetime import date

import typer
from rich.console import Console

from src.io.directory_handler import FOLDERS

app = typer.Typer()
console = Console()
f = FOLDERS()


@app.command()
def generate_aspen_soft_delete_sheet():
    # Soft Delete File For Aspen
    df = f.get_master_log(tab="soft_deletes")
    df.to_excel(f.DOWNLOADS / f"All Master Log - Soft Deletes - {date.today()}.xlsx")
