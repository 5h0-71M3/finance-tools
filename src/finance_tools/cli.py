"""Module holding the Command Line Interface Functions"""
from datetime import date

import pandas as pd
import typer
from dirlin import Folder
from rich.console import Console
from typing_extensions import Annotated

from finance_tools.core.checks import find_term_extension_transaction
from finance_tools.deliverables import (
    _convert_date_string_to_folder,
    export_masterfile_reported,
    swissre_doc_namer,
    download_validation_log,
)
from finance_tools.io.directory_handler import FOLDERS
from finance_tools.tasks.ad_hoc import current_reported, compare_to_itd
app = typer.Typer()
console = Console()
f = FOLDERS()


############################
# PIPEUI
############################
def _find_pipeui_project_dir():
    """The dir owning pipeui.config.json, or None.

    Searches upward from CWD first (user standing in the repo), then from the installed
    package location (editable install -> repo src/).
    """
    from pathlib import Path

    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for d in (start, *start.parents):
            if (d / "pipeui.config.json").exists():
                return d
    return None


@app.command()
def pipeui():
    """Launch the PipeUI server (data-pipeline UI) using the repo's pipeui.config.json."""
    import os

    project_dir = _find_pipeui_project_dir()
    if project_dir is None:
        console.print(
            "[red]Could not locate pipeui.config.json.[/red] "
            "Run `pipeui init` in the finance-tools repo root first."
        )
        raise typer.Exit(1)

    os.chdir(project_dir)  # pipeui reads config + db relative to CWD; reload subprocess inherits it
    from pipeui.app.cli import cmd_start  # lazy: pulls in uvicorn only when launching
    console.print(f"[green]Starting PipeUI[/green] (project: {project_dir})")
    cmd_start()


@app.command()
def pipeui_register_bdx(
        route: Annotated[
            str,
            typer.Option(
                "--route", "-r",
                help="only the reports one otc BDX route reads: master, day1, day5, day10, zurich, aspen, "
                     "day15, lloyds-er, sre-ytd. Default: all.",
            )
        ] = None,
        folder: Annotated[str, typer.Option(help="where the exports are downloaded")] = "~/Downloads",
        max_age_days: Annotated[int, typer.Option(help="ignore exports saved longer ago than this (0 = any age)")] = 30,
        url: Annotated[str, typer.Option(help="running pipeui; default reads host/port from pipeui.config.json")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="show what would be registered; change nothing")] = False,
        watch: Annotated[bool, typer.Option(help="add the folder to pipeui's watch folders afterwards")] = True,
):
    """Register the otc BDX input reports in a running PipeUI (start it with `finance-tools pipeui`).

    Each report is registered from the newest matching export in the folder and loaded immediately.
    After that, PipeUI's watch folder loads new downloads by itself. Re-run as more exports arrive:
    reports that are already registered are skipped, and so are exports an existing report already
    claims (that report keeps loading them).
    """
    import json
    from pathlib import Path

    import requests
    from rich.markup import escape
    from rich.table import Table

    from finance_tools.bdx_reports.manifest import DEFERRED, reports_for
    from finance_tools.bdx_reports.register import REGISTER, PipeuiClient, plan_registrations

    specs = reports_for(route)
    if not specs:
        console.print(f"[red]No BDX reports for route {route!r}.[/red]")
        raise typer.Exit(1)

    if url is None:
        project_dir = _find_pipeui_project_dir()
        config = json.loads((project_dir / "pipeui.config.json").read_text()) if project_dir else {}
        url = f"http://{config.get('host', '127.0.0.1')}:{config.get('port', 8000)}"
    client = PipeuiClient(url)
    try:
        existing = client.existing_reports()
    except requests.RequestException:
        console.print(f"[red]PipeUI isn't reachable at {url}.[/red] Start it with `finance-tools pipeui` first.")
        raise typer.Exit(1)

    source_folder = Path(folder).expanduser()
    plans = plan_registrations(specs, source_folder, existing, max_age_days or None)

    table = Table(title=f"BDX reports ({route or 'all routes'}) from {source_folder}")
    for col in ("Report", "Status", "File", "Detail"):
        table.add_column(col)
    for plan in plans:
        status, detail = plan.status, plan.detail
        if plan.status == REGISTER and not dry_run:
            body = client.register_from_path(plan.spec, plan.file)
            if body.get("ok"):
                ingest = body.get("ingest") or {}
                status = "loaded into existing" if body.get("matched_existing") else "registered"
                detail = f"{ingest.get('status')}: {ingest.get('rows_ingested', 0):,} rows"
                if ingest.get("message"):
                    detail += f" ({ingest['message']})"
            else:
                status, detail = "failed", "; ".join(body.get("errors", []))
        cells = (plan.spec.name, status, plan.file.name if plan.file else "", detail)
        table.add_row(*(escape(c) for c in cells))  # filenames like "[updated]" aren't rich markup
    console.print(table)

    if watch and not dry_run:
        paths = client.add_watch_folder(source_folder)
        console.print(f"[green]Watch folders:[/green] {', '.join(paths)}")

    if route is None:
        console.print(f"[dim]{len(DEFERRED)} BDX inputs aren't set up as reports yet — see "
                      f"finance_tools/bdx_reports/manifest.py DEFERRED.[/dim]")


def _pipeui_url(url: str | None) -> str:
    """``url``, or the running pipeui's address from pipeui.config.json."""
    import json

    if url:
        return url
    project_dir = _find_pipeui_project_dir()
    config = json.loads((project_dir / "pipeui.config.json").read_text()) if project_dir else {}
    return f"http://{config.get('host', '127.0.0.1')}:{config.get('port', 8000)}"


@app.command()
def allianz_us_bdx(
        step: Annotated[str, typer.Argument(help="setup | check")],
        month: Annotated[str, typer.Option(help="check: AC month, YYYY-MM. Default: the month 15 days ago")] = None,
        folder: Annotated[str, typer.Option(help="setup: where the exports are downloaded (pipeui's watch folder)")] = "~/Downloads",
        url: Annotated[str, typer.Option(help="running pipeui; default reads host/port from pipeui.config.json")] = None,
):
    """Allianz US Day 5 BDX in PipeUI. The monthly run is in the PipeUI page itself:
    Data → Allianz US AC → Outputs → Build output files.

    \b
    setup  one-time (re-runnable) wiring: the Master report reads the Masterfile's "Master"
           sheet; "Allianz US AC" gets its joins, the "Allianz US BDX" set, select_columns, and
           its outputs (Runoff / Admitted / Non-Admitted / Multi-National + Day 5 control file)
    check  build a month's files through PipeUI and diff them against the files sent
           (Account Current/<month>/Day 5)
    """
    from datetime import timedelta
    from pathlib import Path

    import requests

    from finance_tools.bdx_reports import allianz_us as A
    from finance_tools.bdx_reports.manifest import reports_for
    from finance_tools.bdx_reports.register import PipeuiClient, newest_matching_file
    from finance_tools.io._config import directory_config

    client = PipeuiClient(_pipeui_url(url))
    try:
        client.sources()
    except requests.RequestException:
        console.print(f"[red]PipeUI isn't reachable at {client.base_url}.[/red] Start it with `finance-tools pipeui` first.")
        raise typer.Exit(1)

    if step == "setup":
        source_folder = Path(folder).expanduser()
        specs = {s.name: s for s in reports_for("day5")}
        inputs = ("Endorsements", "STM Limits Report", "MPL - Premium Breakdown")
        newest = {name: newest_matching_file(source_folder, specs[name].pattern) for name in inputs}
        missing = [name for name, file in newest.items() if file is None]
        if missing:
            console.print(f"[red]No export in {source_folder} for {missing}.[/red]")
            raise typer.Exit(1)
        done = A.setup_pipeline(client, *(newest[n].name for n in inputs))
        for line in done or ["already set up — nothing to change"]:
            console.print(f"  {line}")
    elif step == "check":
        month = month or (date.today() - timedelta(days=15)).strftime("%Y-%m")
        sent_dir = Path(directory_config["account_current"]) / month / "Day 5"
        built, results = A.check(client, month, sent_dir)
        for f in built["files"]:
            console.print(f"[green]Wrote[/green] {f['path']} ({f['rows']:,} rows)")
        console.print(A.parity_report(results) or f"No sent files to compare in {sent_dir}.", markup=False, highlight=False)
    else:
        console.print(f"[red]Unknown step {step!r}.[/red] Use setup or check.")
        raise typer.Exit(1)


@app.command()
def vantage_bdx(
        step: Annotated[str, typer.Argument(help="setup | check")],
        month: Annotated[str, typer.Option(help="check: AC month, YYYY-MM. Default: the month 15 days ago")] = None,
        url: Annotated[str, typer.Option(help="running pipeui; default reads host/port from pipeui.config.json")] = None,
):
    """Vantage Day 3 account current in PipeUI. The monthly run is in the PipeUI page itself:
    Data → STMVantageAccountCurrentResults256 → Outputs → Build output files.

    \b
    setup  one-time (re-runnable) wiring: the Vantage report gets the Master join, the
           "Vantage BDX" set, rename / select_columns and its output file
    check  build a month's file through PipeUI and diff it against the file sent
           (Account Current/<month>/Day 3)
    """
    from datetime import timedelta
    from pathlib import Path

    import requests

    from finance_tools.bdx_reports import allianz_us as A
    from finance_tools.bdx_reports import vantage as V
    from finance_tools.bdx_reports.register import PipeuiClient
    from finance_tools.io._config import directory_config

    client = PipeuiClient(_pipeui_url(url))
    try:
        client.sources()
    except requests.RequestException:
        console.print(f"[red]PipeUI isn't reachable at {client.base_url}.[/red] Start it with `finance-tools pipeui` first.")
        raise typer.Exit(1)

    if step == "setup":
        for line in V.setup_pipeline(client) or ["already set up — nothing to change"]:
            console.print(f"  {line}")
    elif step == "check":
        month = month or (date.today() - timedelta(days=15)).strftime("%Y-%m")
        sent_dir = Path(directory_config["account_current"]) / month / V.SENT_FOLDER
        built, results = V.check(client, month, sent_dir)
        for f in built["files"]:
            console.print(f"[green]Wrote[/green] {f['path']} ({f['rows']:,} rows)")
        console.print(A.parity_report(results) or f"No sent file to compare in {sent_dir}.", markup=False, highlight=False)
    else:
        console.print(f"[red]Unknown step {step!r}.[/red] Use setup or check.")
        raise typer.Exit(1)


@app.command()
def msig_aus_bdx(
        step: Annotated[str, typer.Argument(help="setup | check")],
        month: Annotated[str, typer.Option(help="check: AC month, YYYY-MM. Default: the month 15 days ago")] = None,
        url: Annotated[str, typer.Option(help="running pipeui; default reads host/port from pipeui.config.json")] = None,
):
    """MSIG Australia Day 10 account current in PipeUI, in MSIG's new written format. The monthly
    run is in the PipeUI page itself: Data → MSIG AUS AC → Outputs → Build output files.

    \b
    setup  one-time (re-runnable) wiring: the MSIG report gets its joins (STM Limits, Endorsements,
           STM Transaction Report, Endorsement Query, MSIG Australia Risk BDX, Master), the
           "MSIG AUS BDX" set, select_columns, its output file and control file
    check  build a month's file through PipeUI and diff it against the file sent
           (Account Current/<month>/Day 10), on the columns that file has
    """
    from datetime import timedelta
    from pathlib import Path

    import requests

    from finance_tools.bdx_reports import allianz_us as A
    from finance_tools.bdx_reports import msig_aus as M
    from finance_tools.bdx_reports.register import PipeuiClient
    from finance_tools.io._config import directory_config

    client = PipeuiClient(_pipeui_url(url))
    try:
        client.sources()
    except requests.RequestException:
        console.print(f"[red]PipeUI isn't reachable at {client.base_url}.[/red] Start it with `finance-tools pipeui` first.")
        raise typer.Exit(1)

    if step == "setup":
        for line in M.setup_pipeline(client) or ["already set up — nothing to change"]:
            console.print(f"  {line}")
    elif step == "check":
        month = month or (date.today() - timedelta(days=15)).strftime("%Y-%m")
        sent_dir = Path(directory_config["account_current"]) / month / M.SENT_FOLDER
        built, results = M.check(client, month, sent_dir)
        for f in built["files"]:
            console.print(f"[green]Wrote[/green] {f['path']} ({f['rows']:,} rows)")
        console.print(A.parity_report(results) or f"No sent file to compare in {sent_dir}.", markup=False, highlight=False)
    else:
        console.print(f"[red]Unknown step {step!r}.[/red] Use setup or check.")
        raise typer.Exit(1)


############################
# BDX SUPPORT
############################
@app.command()
def validate_bdx():
    """Function for running the validations log for available BDX reports"""
    download_validation_log(f)


@app.command()
def lloyds_risk_bdx(
        period: Annotated[
            str,
            typer.Option(
                "--period",
                "-p",
                help="month being reported, like `2026.09`. Defaults to last month; reads the month before it.",
            )
        ] = None,
        old_dir: Annotated[str, typer.Option(help="override the folder holding last month's sent files")] = None,
        out_dir: Annotated[str, typer.Option(help="override the folder the deliverables are written to")] = None,
        port: int = 8765,
):
    """Opens the Lloyds Risk BDX page: upload the UK / Canada Looker downloads and it writes the 4 deliverables
    into `Day 5/Risk`, keeping each policy on the UMR it was sent under last month.
    """
    import threading
    import webbrowser
    from pathlib import Path

    import uvicorn
    from dateutil.relativedelta import relativedelta

    from finance_tools.lloyds_risk.server import create_app

    if period is None:
        current, previous = f.MASTER_FOLDER.path, f.PREVIOUS_MASTER_FOLDER.path
    else:
        _year, _month = _convert_date_string_to_folder(period)
        _previous = date(_year, _month, 1) + relativedelta(months=-1)
        current = f.ACCOUNT_CURRENT / f"{_year:04d}-{_month:02d}"
        previous = f.ACCOUNT_CURRENT / _previous.strftime("%Y-%m")

    old_path = Path(old_dir).expanduser() if old_dir else Path(previous) / "Day 5" / "Risk"
    out_path = Path(out_dir).expanduser() if out_dir else Path(current) / "Day 5" / "Risk"
    url = f"http://127.0.0.1:{port}"
    console.print(f"[green]Last month's files:[/green] {old_path}")
    console.print(f"[green]Writing to:[/green] {out_path}")
    console.print(f"[green]Open[/green] {url}  (Ctrl+C to stop)")

    threading.Timer(1.0, webbrowser.open, [url]).start()  # give uvicorn a moment to bind first
    uvicorn.run(create_app(old_path, out_path), host="127.0.0.1", port=port, log_level="warning")


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

# /Users/shomendoza/Library/CloudStorage/GoogleDrive-sho.mendoza@coalitioninc.com/Shared drives/Finance/OTC/Data Analysis

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
    opl = f.DOWNLOADS.open_recent("v4 - indexer")

    # Term Extension
    log = find_term_extension_transaction(df, opl)
    log.to_csv(f.DOWNLOADS / f"Daily Check - {date.today()} - 1.csv")


@app.command()
def generate_reported(
        period: Annotated[
            str,
            typer.Option(
                "--period",
                "-p",
                help="masterfile month to pull, like `2026.05`. Defaults to last month.",
            )
        ] = None
):
    """Generates the reported upload for Netsuite. NEED: the Masterfile in Production Account Current folder.
    """
    # the period lets us re-run a closed month; without it we stay on the current MASTER_FOLDER
    if period is None:
        master_folder_path = f.MASTER_FOLDER.path
        name_suffix = ""
    else:
        _year, _month = _convert_date_string_to_folder(period)
        master_folder_path = f.ACCOUNT_CURRENT / f"{_year:04d}-{_month:02d}"
        name_suffix = f"{_year:04d}-{_month:02d} - "
    console.print(f"[green]Reading masterfiles from[/green] {master_folder_path}")

    cyber = export_masterfile_reported(f, period=period)
    mpl = export_masterfile_reported(f, "mpl", period=period)

    cyber.to_csv(f / f"Reported Masterfile - Cyber - {name_suffix}{date.today()}.csv")
    mpl.to_csv(f / f"Reported Masterfile - MPL - {name_suffix}{date.today()}.csv")

    # itd master
    cyber.to_csv(f / f"Reported Masterfile - Cyber - {name_suffix}{date.today()}.csv")


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
def add_sre_doc_file(
        use: Annotated[str, typer.Option("--use", "-u")]
):
    """creates the template file so you can fill it out with the information you need

    :param use: the document to use for the base Internal ID
    :return:
    """
    # Grabbing the File and Finding Internal ID
    required_columns = [
        "Internal ID",
        "Transaction Description",
        "Full Policy",
        "Coalition Policy Number",
        "Endorsement Number",
        "Transaction Type",
        "Policy UUID",
        "Endorsement UUID (endts only)",
    ]

    # Checking which columns are available
    df = f.DOWNLOADS.open_recent(use)
    if "Internal ID" not in df.columns:
        raise KeyError("Internal ID column not found, but is required.")
    columns = set(df.columns)  # get the available columns from whatever report you just pulled
    available = columns & set(required_columns)  # gives you what's available in the df

    # Check to see if we need anything from the Policy List
    need_from_pl = set(required_columns) - columns
    deliverable = df[list(available)].copy()
    if need_from_pl:
        pl = f.get_policy_list(set_index=True)
        deliverable = deliverable.set_index("Internal ID")

        for col in need_from_pl:
            deliverable[col] = pl[col]
        deliverable = deliverable.reset_index(drop=False)

    # Finally, align the columns in the order we expect
    deliverable["filepath"] = None  # user will need to fill this in
    deliverable = deliverable.rename(columns={"Full Policy": "Carrier Policy Number"})
    file_format = [
        "Internal ID",
        "Transaction Description",
        "filepath",
        "Carrier Policy Number",
        "Coalition Policy Number",
        "Endorsement Number",
        "Transaction Type",
        "Policy UUID",
        "Endorsement UUID (endts only)"
    ]
    deliverable = deliverable[file_format].copy()
    filename = f"SwissRe Doc Namer File - {date.today()}.xlsx"
    deliverable.to_excel(f.DOWNLOADS / filename, index=False)


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
        ] = None
):
    """uses find and combine to get the itd from the desktop folders"""
    if carrier == "master":
        df1 = f.get_master_log(tab="master")
        df1.to_csv(f.DOWNLOADS / f"Master - ITD - {date.today()}.csv")
        return

    elif carrier == "antares sho":
        path = f.DESKTOP / f"Antares Looker"
        df = Folder(path).find_and_combine(recurse=True)
        df.to_csv(path / f"Antares (Sho Copy) - ITD - {date.today()}.csv")
        return

    else:
        path = f.DESKTOP / str(carrier).capitalize()
        filename = f"ITD - ran {date.today()} - {carrier}.csv"

        if segment:
            path = path / segment
            filename = f"ITD - ran {date.today()} - {carrier} - {segment}.csv"

        files = Folder(path).find_and_combine(recurse=True)
        files.to_csv(path / filename)


@app.command()
def get_not_reported():
    df = current_reported(f.get_policy_list())
    folder = Folder(f.DESKTOP / "SwissRe/2023")
    itd_df = folder.open("ITD - ran 2025-10-16 - SwissRe - 2023.csv")

    df = compare_to_itd(df, itd_df)
    df.to_excel(f.DOWNLOADS / f"SwissRe Non-Reported - With ITD Info - {date.today()}.xlsx")
