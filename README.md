# Available Tools
These are a set of tools we can use in the OTC team to ensure
that carrier reporting sections, and Netsuite are aligned
with other data sources.

# The CLI
Accessing the CLI is pretty easy. Go to the terminal and run the script.
```text
finance-tools [command] [args]
```

## Available functions

| Command                            | Category           | Function                                          |
|------------------------------------|--------------------|---------------------------------------------------|
| `validate-bdx`                     | `BDX Support`      | Runs the validation log for BDX files             |
| `generate-hartford-itd`            | `BDX Support`      | Runs the ITD file required for Hartford           |
| `generate-aspen-soft-delete-sheet` | `BDX Support`      | Runs the Soft Delete sheet required for Vantage   |
| `daily-checks`                     | `Netsuite Uploads` | Runs the Daily Checks for Netsuite                |
| `generate-reported`                | `Netsuite Uploads` | Runs the reported upload file for EOM BDX         |
| `generate-arch-upload`             | `Netsuite Uploads` | Uploads the Arch files for Claims reporting       |
| `apply-cash`                       | `Cash Application` | Matches bank receipts to open AR and builds the upload |
| `sre-policy-docs`                  | `Ad-Hoc`           | Runs the SRE Policy Doc Naming                    |
| `get-itd`                          | `Ad-Hoc`           | Runs the find and combine for the Desktop folders |
| `add_sre_doc_file`                 | `Ad-Hoc`           | Creates the template for SwissRe policy docs      |

# Cash Application
Match incoming bank receipts to open AR invoices and build the NetSuite payment
upload — automatically, for the cases that can be applied without a human.

```text
finance-tools apply-cash [--bank "Bank Data"] [--ar "Open AR"]
```

It reads the most recent bank workbook (with `Bank Data` + `Subsidiary Details`
tabs) and open AR report from the DOWNLOADS folder. Each receipt is matched to
an invoice via a deterministic key (subsidiary + currency + amount); receipts
that match exactly one invoice are written to the upload CSV, while receipts
that match several or none are written to a review CSV for a future, more
complex pass. Precision is favored over recall — a misapplied payment is worse
than one left for a human.

See [`src/finance_tools/cash_app/README.md`](src/finance_tools/cash_app/README.md)
for how the matching works in detail.

