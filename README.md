# Available Tools
These are a set of tools we can use in the OTC team to ensure
that carrier reporting sections, and Netsuite are aligned
with other data sources.

# PipeUI
The BDX / account current pipelines run in PipeUI, a local browser app.
See [PIPEUI.md](PIPEUI.md) for setup and how to run it (`finance-tools pipeui`).

# The CLI
Accessing the CLI is pretty easy. Go to the terminal and run the script.
```text
finance-tools [command] [args]
```

## Available functions

| Command                            | Category           | Function                                          |
|------------------------------------|--------------------|---------------------------------------------------|
| `pipeui`                           | `PipeUI`           | Starts the PipeUI app at http://127.0.0.1:8000    |
| `pipeui-register-bdx`              | `PipeUI`           | Registers the BDX input exports as PipeUI reports |
| `allianz-us-bdx setup\|check`      | `PipeUI`           | Allianz US Day 5 AC pipeline setup / parity check |
| `vantage-bdx setup\|check`         | `PipeUI`           | Vantage Day 3 AC pipeline setup / parity check    |
| `msig-aus-bdx setup\|check`        | `PipeUI`           | MSIG AUS Day 10 AC pipeline setup / parity check  |
| `validate-bdx`                     | `BDX Support`      | Runs the validation log for BDX files             |
| `generate-hartford-itd`            | `BDX Support`      | Runs the ITD file required for Hartford           |
| `generate-aspen-soft-delete-sheet` | `BDX Support`      | Runs the Soft Delete sheet required for Vantage   |
| `daily-checks`                     | `Netsuite Uploads` | Runs the Daily Checks for Netsuite                |
| `generate-reported`                | `Netsuite Uploads` | Runs the reported upload file for EOM BDX         |
| `generate-arch-upload`             | `Netsuite Uploads` | Uploads the Arch files for Claims reporting       |
| `sre-policy-docs`                  | `Ad-Hoc`           | Runs the SRE Policy Doc Naming                    |
| `get-itd`                          | `Ad-Hoc`           | Runs the find and combine for the Desktop folders |
| `add_sre_doc_file`                 | `Ad-Hoc`           | Creates the template for SwissRe policy docs      |


