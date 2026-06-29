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

Match incoming bank receipts to open AR invoices and build the NetSuite
payment upload — automatically, for the cases that can be applied without a
human.

## What it does

A bank file lists money that arrived; the open-AR report lists invoices still
owed. Cash application is the job of deciding *which invoice each receipt
pays*. This package automates the part of that job that is unambiguous, and
sets the rest aside for review.

Every receipt lands in one of three buckets:

| Bucket | Meaning | Output |
|--------|---------|--------|
| **Applied** | The receipt was matched to exactly one invoice | NetSuite upload CSV |
| **Ambiguous** | The receipt matched several candidate invoices and couldn't be resolved confidently | Review CSV |
| **Unmatched** | The receipt matched no open invoice (or couldn't be keyed) | Review CSV |

Precision is favored over recall on purpose: a misapplied payment is worse
than one left for a human, so anything borderline goes to review.

## How matching works

The two documents share almost no fields, and customer names never line up
exactly (the bank truncates and abbreviates). So matching happens in two tiers.

### Tier 1 — deterministic key (exact)

A **match key** is a `UUID5` computed *independently* from each document out of
the only fields the two genuinely share: NetSuite subsidiary + ISO currency +
money amount (rounded to cents). Because `UUID5` is deterministic, the bank
side and the AR side arrive at the *same* UUID whenever they describe the same
payment — so the match is a plain equality join, no fuzzy logic.

A receipt is **easy** only when its key is 1:1 in *both* directions — exactly
one open invoice *and* exactly one receipt share it. (Two receipts of equal
amount in the same subsidiary/currency would otherwise both apply to, and
overpay, the same invoice — so they go to review instead.)

The fields seeding the key are the lever for how aggressive the automation is.
The current seed is deliberately conservative; adding fields (e.g. a parsed
agency) would resolve more of today's ambiguous receipts in a future pass.

### Tier 2 — description fuzzy match (tiebreaker)

When a key matches several candidate invoices, the one extra signal the bank
gives us is the free-text `Description`. The payer named there is fuzzy-matched
(token similarity, tolerant of bank truncation) against each candidate
invoice's agency name. It commits to a candidate only when one clearly wins —
clearing a score threshold *and* beating the runner-up by a margin. A final
guard sends back to review any two receipts that fuzzily resolve to the same
invoice (one invoice can't absorb both).

## Inputs

- **Bank workbook** — a `Bank Data` tab (receipts) and a `Subsidiary Details`
  tab (maps each `x####` account suffix to a subsidiary, ISO currency, and the
  full account name NetSuite expects).
- **Open AR report** — the open invoices, one per row.

## Usage

### CLI

```text
finance-tools apply-cash [--bank "Bank Data"] [--ar "Open AR"]
```

Reads the most recent matching files from the DOWNLOADS folder, writes the
upload (and, if anything is unresolved, a review file) back to that folder, and
prints a one-line summary:

```
142 bank receipts -> 96 applied (88 exact, 8 by description), 31 ambiguous, 15 unmatched
```

### Library

```python
from finance_tools.cash_app import run_cash_application
from finance_tools.cash_app.pipeline import write_result

result = run_cash_application(bank_path, open_ar_path)
print(result.summary())          # human-readable counts
upload_path = write_result(result, out_dir)

result.upload      # applied rows, in the NetSuite upload schema
result.ambiguous   # matched many candidates, left for review
result.unmatched   # matched no candidate
```

## Module layout

| Module | Responsibility |
|--------|----------------|
| `pipeline.py` | Orchestration: read inputs, tier the receipts, build the upload, write files. Entry point `run_cash_application`. |
| `keys.py` | The deterministic match key and payment External ID (both `UUID5`). |
| `reference.py` | Normalize the two vocabularies — account suffixes and currency labels — into the shared fields the key needs. |
| `disambiguate.py` | The Tier-2 description-vs-agency fuzzy tiebreaker. |

## Tests

```text
pytest tests/test_cash_app.py
```

Unit tests are self-contained (no filesystem). The integration against the
example workbooks is exercised manually via `finance-tools apply-cash`.

