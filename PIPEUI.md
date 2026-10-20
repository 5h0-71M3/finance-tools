# Running PipeUI
PipeUI is a local data-pipeline app that runs in your browser. It loads the NetSuite and Looker
exports into a local DuckDB database (`pipeui.db`), joins and cleans them, and builds the
carrier BDX / account current files. `finance-tools` starts it and supplies the carrier logic
from `src/finance_tools/pipeui_functions/`.

Everything runs on your own machine. Nothing is uploaded anywhere.

## 1. Before you start
You need:
- a Mac with [`uv`](https://docs.astral.sh/uv/) installed (`brew install uv`). uv installs
  Python 3.12 for you.
- Google Drive for Desktop, with access to the **Operations Share → Carrier Partners →
  Account Current** shared drive. You only need this for the `check` commands and the Masterfile.
- the NetSuite / Looker exports for the month, saved to `~/Downloads`.

## 2. Clone both repos side by side
`finance-tools` installs PipeUI from a folder next to it (`pyproject.toml`:
`pipeui = { path = "../pipeui", editable = true }`), so the two repos **must** sit in the same
parent folder:

```text
~/Developer/
├── finance-tools/
└── pipeui/
```

```text
cd ~/Developer
git clone <finance-tools repo url> finance-tools
git clone https://github.com/mendozasho/pipeui pipeui
```

> **Important:** the BDX features these flows use (reports, auto-ingest watch folders,
> `select_columns`, output files) are on the PipeUI branch `feat/auto-ingest-watch-folders`.
> That branch is **not on the public `main` yet**. Ask Sho for it before you go on. With only
> `main`, the app starts, but the BDX setup commands below will fail.

## 3. Install
```text
cd ~/Developer/finance-tools
uv sync
```

## 4. First-time configuration
Git ignores `pipeui.config.json` and `pipeui.db` because they belong to one machine. Each analyst
creates their own. In the `finance-tools` root:

```text
uv run pipeui init
```

That writes a default `pipeui.config.json` and an empty `pipeui.db`. Open the config and set
it up like this, using your own username in the paths:

```json
{
  "db_path": "pipeui.db",
  "functions_paths": [
    "/Users/<you>/Developer/finance-tools/src/finance_tools/pipeui_functions/shared",
    "/Users/<you>/Developer/finance-tools/src/finance_tools/pipeui_functions/vantage",
    "/Users/<you>/Developer/finance-tools/src/finance_tools/pipeui_functions/allianz_us",
    "/Users/<you>/Developer/finance-tools/src/finance_tools/pipeui_functions/allianz_aus",
    "/Users/<you>/Developer/finance-tools/src/finance_tools/pipeui_functions/msig_aus"
  ],
  "watch_paths": ["/Users/<you>/Downloads"],
  "watch_interval_s": 300,
  "watch_enabled": true,
  "watch_max_age_days": 14,
  "output_dir": "~/Downloads"
}
```

| Setting              | What it does                                                                   |
|----------------------|--------------------------------------------------------------------------------|
| `functions_paths`    | Folders PipeUI scans for carrier transforms and validations                    |
| `watch_paths`        | Folders PipeUI checks for new exports and loads automatically                  |
| `watch_max_age_days` | Ignores exports older than this. Keeps it from loading old files in Downloads  |
| `output_dir`         | Where built BDX / AC files are written                                         |
| `host` / `port`      | Optional. Defaults to `127.0.0.1` / `8000`                                     |

You can also change most of these later in the app under **Settings**.

### Set your folder paths
finance-tools reads your Downloads, Desktop and Google Drive folders from
`finance_tools.config.json` in the repo root. Git ignores it, so each analyst has their own.
Make it from the example:

```text
cp finance_tools.config.example.json finance_tools.config.json
```

Put your Google Drive email into `data_analysis` and `account_current`. `~` works in every path.
Every `finance-tools` command needs this file, including `finance-tools pipeui`, and without it
the CLI stops with `Could not locate finance_tools.config.json`. The Google Drive folders must
also exist: run Google Drive for Desktop and keep the shared drives available.

## 5. Start PipeUI
```text
cd ~/Developer/finance-tools
uv run finance-tools pipeui
```

Open **http://127.0.0.1:8000** in your browser. Keep the terminal open while you use the
app. Press `Ctrl-C` in it to stop the server.

## 6. One-time setup of the BDX reports
Do this once, with PipeUI running, in a **second** terminal. Each command can safely be run
again: anything that's already set up is skipped.

1. Download the month's exports into `~/Downloads`. You need at least Endorsements, the STM
   Limits Report and the MPL Premium Breakdown. Load the Masterfile from Google Drive, not a
   copy in Downloads, because those can be out of date.
2. Register the input reports. Do a dry run first:
   ```text
   uv run finance-tools pipeui-register-bdx --dry-run
   uv run finance-tools pipeui-register-bdx
   ```
   Add `--route day5` (or `master`, `day1`, `day10`, ...) to register only one route's inputs.
   `uv run finance-tools pipeui-register-bdx --help` lists every route.
3. Set up each carrier's pipeline:
   ```text
   uv run finance-tools allianz-us-bdx setup
   uv run finance-tools vantage-bdx setup
   uv run finance-tools msig-aus-bdx setup
   ```

From then on, the watch folder loads new exports into PipeUI on its own. You don't need to
click Ingest.

## 7. The monthly run
In the browser, go to **Data → (report) → Outputs → Build output files**:

| Carrier             | Day    | Report in PipeUI                     |
|---------------------|--------|--------------------------------------|
| Vantage             | Day 3  | `STMVantageAccountCurrentResults256` |
| Allianz US          | Day 5  | `Allianz US AC`                      |
| MSIG Australia      | Day 10 | `MSIG AUS AC`                        |

The files are written to `output_dir` (`~/Downloads` by default).

Optional: to compare a build against the files that were actually sent (Account Current/<month>/Day N):
```text
uv run finance-tools allianz-us-bdx check --month 2026-09
```
The same works with `vantage-bdx` and `msig-aus-bdx`.

## 8. Back up your database
All of your reports, joins and loaded data live in `pipeui.db`. Copy it before any big change,
such as a new carrier setup or a PipeUI update:
```text
cp pipeui.db pipeui.db.2026-10-20-pre-<what>.bak
```
To restore, stop the server and copy the backup back over `pipeui.db`.

## Troubleshooting
| Problem                                           | Fix                                                                                 |
|---------------------------------------------------|-------------------------------------------------------------------------------------|
| `Could not locate pipeui.config.json`             | Run `uv run pipeui init` in the `finance-tools` root                                |
| `Could not locate finance_tools.config.json`      | Copy `finance_tools.config.example.json` to `finance_tools.config.json` (step 4)    |
| `Expected a path to a folder / directory`         | A path in `finance_tools.config.json` doesn't exist. Check the Google Drive paths   |
| `PipeUI isn't reachable at http://127.0.0.1:8000` | Start the server first (`uv run finance-tools pipeui`) in another terminal          |
| `address already in use` on start                 | PipeUI is already running, or something else is using port 8000. Set `"port"` in the config |
| `uv sync` can't find `../pipeui`                  | Clone pipeui next to finance-tools (see step 2)                                     |
| BDX `setup` fails on a missing endpoint or report | You're on pipeui `main`. Switch to the BDX branch (see step 2)                       |
| `No export in ~/Downloads for [...]`              | Download the listed exports, then rerun `setup`                                     |
| A code change in `pipeui/` doesn't show up        | Restart the server for Python changes. Refresh the browser for frontend changes     |
